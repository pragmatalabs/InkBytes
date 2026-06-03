"""RabbitMQ — async consumer of Messor's `event.article.scraped`.

Uses aio-pika. The consumer hands each message to a callback supplied by
the Application; the callback orchestrates the three skills.
"""
from __future__ import annotations

import json
import logging
from typing import Awaitable, Callable

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from core.config import RmqCfg

logger = logging.getLogger(__name__)

MessageHandler = Callable[[dict], Awaitable[None]]


class MessageService:
    def __init__(self, cfg: RmqCfg) -> None:
        self.cfg = cfg
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.abc.AbstractChannel | None = None

    async def connect(self) -> None:
        self.connection = await aio_pika.connect_robust(self.cfg.url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=4)
        logger.info("RabbitMQ connected: %s", _scrub(self.cfg.url))

    async def close(self) -> None:
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

    async def consume(self, handler: MessageHandler) -> None:
        """Subscribe to Messor's exchange and dispatch every event to `handler`."""
        assert self.channel
        exchange = await self.channel.declare_exchange(
            self.cfg.consume_exchange, aio_pika.ExchangeType.TOPIC, durable=True
        )
        queue = await self.channel.declare_queue(self.cfg.consume_queue, durable=True)
        await queue.bind(exchange, routing_key=self.cfg.consume_routing_key)

        async def _on_msg(msg: AbstractIncomingMessage) -> None:
            async with msg.process(requeue=False):
                try:
                    payload = json.loads(msg.body.decode("utf-8"))
                    await handler(payload)
                except Exception:
                    logger.exception("handler failed for message %s", msg.message_id)
                    raise

        await queue.consume(_on_msg)
        logger.info(
            "Consuming exchange=%s queue=%s routing=%s",
            self.cfg.consume_exchange, self.cfg.consume_queue, self.cfg.consume_routing_key,
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
