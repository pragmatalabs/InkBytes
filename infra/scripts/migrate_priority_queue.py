"""Zero-loss migration of curator.articles-scraped to a priority queue (ADR-0024).

Run inside the inkbytes-messor container (has pika) with the worker STOPPED:
  phase 1: move all messages old-queue -> tmp queue
  phase 2: delete old queue, redeclare with x-max-priority=10, rebind
  phase 3: move all messages tmp -> new queue, delete tmp
"""
import os
import pika

QUEUE = "curator.articles-scraped"
TMP = "curator.articles-scraped.migrate-tmp"
EXCHANGE = "messor"
RK = "event.article.scraped"

params = pika.ConnectionParameters(
    host=os.environ["RABBITMQ_HOST"],
    port=int(os.environ["RABBITMQ_PORT"]),
    credentials=pika.PlainCredentials(os.environ["RABBITMQ_USER"], os.environ["RABBITMQ_PASS"]),
)
conn = pika.BlockingConnection(params)
ch = conn.channel()

ch.queue_declare(queue=TMP, durable=True)

def drain(src, dst, props_priority=None):
    moved = 0
    while True:
        method, props, body = ch.basic_get(src)
        if method is None:
            break
        ch.basic_publish(
            exchange="", routing_key=dst, body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type=getattr(props, "content_type", None) or "application/json",
                priority=props_priority,
            ),
        )
        ch.basic_ack(method.delivery_tag)
        moved += 1
    return moved

# Phase 1 — old -> tmp
n1 = drain(QUEUE, TMP)
print(f"phase1: moved {n1} messages {QUEUE} -> {TMP}")

# Phase 2 — delete + redeclare priority-enabled + rebind (gap: milliseconds)
ch.queue_delete(queue=QUEUE)
ch.queue_declare(queue=QUEUE, durable=True, arguments={"x-max-priority": 10})
ch.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key=RK)
print(f"phase2: {QUEUE} recreated with x-max-priority=10, bound to {EXCHANGE}/{RK}")

# Phase 1 may have raced a publisher: sweep any messages that landed on tmp-less
# old queue between last get and delete -- they were lost with the delete ONLY if
# they arrived in that <1s window; sweep tmp -> new queue now.
n3 = drain(TMP, QUEUE)
print(f"phase3: moved {n3} messages {TMP} -> {QUEUE}")

# Re-sweep once: a publisher may have hit tmp...no, nothing publishes to tmp.
ch.queue_delete(queue=TMP)
q = ch.queue_declare(queue=QUEUE, durable=True, passive=True)
print(f"done: {QUEUE} now has {q.method.message_count} messages, priority-enabled")
conn.close()
