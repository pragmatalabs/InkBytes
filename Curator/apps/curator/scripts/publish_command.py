#!/usr/bin/env python3
"""Publish one Backoffice → Curator moderation command to RabbitMQ.

This is the same path the Laravel Backoffice uses (Phase 2.3): a JSON body
`{"id": "<target>"}` published to the `curator.commands` topic exchange with
the command name as the routing key. Curator's `--consume-commands` harness
picks it up and applies the write (it owns public.events / public.pages).

Usage (from apps/curator):
    python scripts/publish_command.py <command> <id> [config.yaml]

Examples:
    python scripts/publish_command.py event.resynthesize 01KT5E6AYJW4014BEYM5V0Z6B7
    python scripts/publish_command.py page.publish      01KT5E6AYJW4014BEYM5V0Z6B7 env.local.yaml
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aio_pika

from core.config import CuratorConfig

VALID = {
    "page.publish", "page.unpublish", "page.drop",
    "event.resynthesize", "event.recluster",
}


async def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    command = sys.argv[1]
    target_id = sys.argv[2]
    cfg_path = sys.argv[3] if len(sys.argv) > 3 else "env.local.yaml"

    if command not in VALID:
        print(f"Unknown command {command!r}. Valid: {sorted(VALID)}")
        return 2

    cfg = CuratorConfig.load(cfg_path)

    conn = await aio_pika.connect_robust(cfg.rabbitmq.url)
    try:
        channel = await conn.channel()
        # Declare with the SAME args the consumer uses (durable topic exchange),
        # so this is idempotent whether or not the consumer ran first.
        exchange = await channel.declare_exchange(
            cfg.rabbitmq.commands_exchange, aio_pika.ExchangeType.TOPIC, durable=True
        )
        body = json.dumps({"id": target_id}).encode("utf-8")
        await exchange.publish(
            aio_pika.Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=command,
        )
        print(f"→ published {command} id={target_id} "
              f"to exchange={cfg.rabbitmq.commands_exchange}")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
