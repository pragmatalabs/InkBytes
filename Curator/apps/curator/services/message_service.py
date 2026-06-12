"""RabbitMQ — async consumer of Messor's `event.article.scraped`.

Uses aio-pika. The consumer hands each message to a callback supplied by
the Application; the callback orchestrates the three skills.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
import openai

from core.config import RmqCfg
from services.llm_service import LlmQuotaError


class ProcessingPausedError(Exception):
    """Raised by the article handler when the Backoffice kill-switch is off.

    The message is requeued (never lost) and the consumer backs off so it does
    not tight-loop while paused. See AppCfg.processing_enabled.
    """


# Seconds to wait before requeuing while processing is paused — throttles the
# (prefetch=1) consumer so a paused worker idles instead of spinning.
_PAUSE_BACKOFF = 5.0

# Transient infrastructure errors — requeue the article so it's retried on
# the next consumer cycle instead of being permanently dropped.
_TRANSIENT_ERRORS = (
    openai.APITimeoutError,
    openai.APIConnectionError,
)

logger = logging.getLogger(__name__)

MessageHandler = Callable[[dict], Awaitable[None]]
# (routing_key, payload) → None — used for Backoffice moderation commands.
CommandHandler = Callable[[str, dict], Awaitable[None]]


class MessageService:
    def __init__(self, cfg: RmqCfg) -> None:
        self.cfg = cfg
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.abc.AbstractChannel | None = None

    async def connect(self) -> None:
        self.connection = await aio_pika.connect_robust(self.cfg.url)
        self.channel = await self.connection.channel()
        # prefetch_count governs how many articles are in flight concurrently.
        # The enrich LLM call (8-17s of network wait) parallelises freely; the
        # CPU-Ollama embed and the cluster-attach are serialised by dedicated
        # locks in Application._handle_event, so raising this no longer risks
        # concurrent embedding requests (the original reason it was 1).
        await self.channel.set_qos(prefetch_count=self.cfg.prefetch_count)
        logger.info("RabbitMQ connected: %s", _scrub(self.cfg.url))

    async def close(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

    async def consume(
        self,
        handler: MessageHandler,
        *,
        on_quota_exhausted: Callable[[], None] | None = None,
    ) -> None:
        """Subscribe to Messor's exchange and dispatch every event to `handler`.

        Error handling:
          LlmQuotaError  → requeue=True (article preserved) + call
                           on_quota_exhausted so the caller can stop the loop.
          Any other error → requeue=False (article dropped after logging).
                            The consumer DOES NOT re-raise, so the aio-pika
                            task survives and the next message is processed.
        """
        assert self.channel
        exchange = await self.channel.declare_exchange(
            self.cfg.consume_exchange, aio_pika.ExchangeType.TOPIC, durable=True
        )
        # Priority queue (ADR-0024): pulse-lane articles arrive with AMQP
        # priority 9 and must jump the backlog. RabbitMQ refuses to redeclare
        # an existing queue with different arguments (PRECONDITION_FAILED), so
        # on a pre-existing non-priority queue we fall back transparently —
        # drain + delete the queue, restart the worker, and the next declare
        # creates it priority-enabled (see ADR-0024 §migration).
        try:
            queue = await self.channel.declare_queue(
                self.cfg.consume_queue, durable=True,
                arguments={"x-max-priority": 10},
            )
        except aio_pika.exceptions.ChannelPreconditionFailed:
            logger.warning(
                "Queue %s exists without x-max-priority — running WITHOUT "
                "priority intake. To enable: drain + delete the queue, then "
                "restart this worker (ADR-0024).",
                self.cfg.consume_queue,
            )
            # The failed declare closed the channel — reopen and redo QoS.
            self.channel = await self.connection.channel()  # type: ignore[union-attr]
            await self.channel.set_qos(prefetch_count=self.cfg.prefetch_count)
            exchange = await self.channel.declare_exchange(
                self.cfg.consume_exchange, aio_pika.ExchangeType.TOPIC, durable=True
            )
            queue = await self.channel.declare_queue(self.cfg.consume_queue, durable=True)
        await queue.bind(exchange, routing_key=self.cfg.consume_routing_key)

        async def _on_msg(msg: AbstractIncomingMessage) -> None:
            try:
                payload = json.loads(msg.body.decode("utf-8"))
                await handler(payload)
                await msg.ack()
            except ProcessingPausedError:
                # Kill-switch is off — preserve the article and back off so the
                # worker idles (no processing, no LLM calls) until re-enabled.
                await asyncio.sleep(_PAUSE_BACKOFF)
                await msg.nack(requeue=True)
                logger.debug("Processing paused — article requeued.")
            except LlmQuotaError as exc:
                # Quota is a hard monthly wall — preserve the article so it can
                # be processed when the limit resets, then signal the caller to
                # stop consuming (no point hammering a wall).
                await msg.nack(requeue=True)
                logger.critical(
                    "Anthropic API quota exhausted — article requeued. %s", exc
                )
                if on_quota_exhausted is not None:
                    on_quota_exhausted()
            except _TRANSIENT_ERRORS as exc:
                # Transient infrastructure failure (Ollama timeout, network
                # blip) — requeue so the article is retried on the next cycle.
                # Do NOT drop: the article is valid, the infrastructure was
                # temporarily unavailable.
                await msg.nack(requeue=True)
                logger.warning(
                    "Transient error for message %s — requeuing. %s: %s",
                    msg.message_id, type(exc).__name__, exc,
                )
            except Exception:
                # Permanent per-article failure (DB error, bad payload that
                # slipped through, etc.) — drop and continue.
                await msg.nack(requeue=False)
                logger.exception(
                    "Pipeline failed for message %s — dropping", msg.message_id
                )

        await queue.consume(_on_msg)
        logger.info(
            "Consuming exchange=%s queue=%s routing=%s",
            self.cfg.consume_exchange, self.cfg.consume_queue, self.cfg.consume_routing_key,
        )

    async def consume_scrape_sessions(self, handler: MessageHandler) -> None:
        """Subscribe to Messor's `scrape.session.completed` run summaries (B12.1).

        Same `messor` topic exchange as the per-article stream, but a dedicated
        queue + routing key so it never competes with the article consumer. Bad
        payloads are logged and ACKed (never requeued) so one malformed summary
        can't wedge the queue — a missed run summary is harmless (Messor
        re-emits / it's just history).
        """
        assert self.channel
        exchange = await self.channel.declare_exchange(
            self.cfg.consume_exchange, aio_pika.ExchangeType.TOPIC, durable=True
        )
        queue = await self.channel.declare_queue(self.cfg.sessions_queue, durable=True)
        await queue.bind(exchange, routing_key=self.cfg.sessions_routing_key)

        async def _on_session(msg: AbstractIncomingMessage) -> None:
            async with msg.process(requeue=False):
                try:
                    payload = json.loads(msg.body.decode("utf-8")) if msg.body else {}
                except Exception:
                    logger.exception(
                        "scrape.session message has non-JSON body — dropping"
                    )
                    return
                try:
                    await handler(payload)
                except Exception:
                    logger.exception("scrape.session handler failed — dropping")
                    # swallow + ACK: a lost run summary is non-fatal history.

        await queue.consume(_on_session)
        logger.info(
            "Consuming scrape-sessions exchange=%s queue=%s routing=%s",
            self.cfg.consume_exchange, self.cfg.sessions_queue,
            self.cfg.sessions_routing_key,
        )

    async def consume_commands(self, handler: CommandHandler) -> None:
        """Subscribe to the Backoffice command exchange (Phase 2.3).

        Each message carries the routing key (the command name, e.g.
        `page.publish`) and a JSON body `{ "id": "<target id>" }`. The handler
        receives `(routing_key, payload)`. Bad payloads / unknown commands are
        logged and ACKed (not requeued) so a single malformed command can't
        wedge the queue.
        """
        assert self.channel
        exchange = await self.channel.declare_exchange(
            self.cfg.commands_exchange, aio_pika.ExchangeType.TOPIC, durable=True
        )
        queue = await self.channel.declare_queue(self.cfg.commands_queue, durable=True)
        await queue.bind(exchange, routing_key=self.cfg.commands_routing_key)

        async def _on_cmd(msg: AbstractIncomingMessage) -> None:
            # ack-on-completion; never requeue a command (it's a one-shot
            # mutation request — re-running it on failure risks double-apply).
            async with msg.process(requeue=False):
                routing_key = msg.routing_key or ""
                try:
                    payload = json.loads(msg.body.decode("utf-8")) if msg.body else {}
                except Exception:
                    logger.exception("command %s has non-JSON body — dropping", routing_key)
                    return
                try:
                    await handler(routing_key, payload)
                except Exception:
                    logger.exception("command handler failed for %s", routing_key)
                    # swallow — ACK anyway; do not requeue a mutation command

        await queue.consume(_on_cmd)
        logger.info(
            "Consuming commands exchange=%s queue=%s routing=%s",
            self.cfg.commands_exchange, self.cfg.commands_queue,
            self.cfg.commands_routing_key,
        )


def _scrub(url: str) -> str:
    """Hide credentials when printing the broker URL."""
    if "@" not in url:
        return url
    scheme_creds, host = url.split("@", 1)
    if "://" in scheme_creds:
        scheme, _ = scheme_creds.split("://", 1)
        return f"{scheme}://***@{host}"
    return f"***@{host}"
