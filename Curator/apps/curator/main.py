#!/usr/bin/env python3
"""Curator entry point.

Modes:
  --consume                    run forever, consume RabbitMQ events
  --fixture <path>             process one event from a JSON fixture (offline-safe)
  --api-only                   only run the FastAPI surface (no consumer)

Examples:
  python main.py --consume
  python main.py --fixture fixtures/sample_article.json
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

import uvicorn

from core.application import Application
from core.api_server import build_app
from core.config import CuratorConfig


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet third-party libraries; their DEBUG output is overwhelming and rarely useful.
    for noisy in ("instructor", "httpx", "httpcore", "anthropic", "openai", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


async def _run(args: argparse.Namespace) -> None:
    cfg = CuratorConfig.load(args.config)
    _configure_logging(cfg.application.log_level)

    app = Application(cfg)

    # --dry-run skips Postgres entirely (LLM-only path for prompt iteration).
    needs_db = not args.dry_run
    await app.startup(with_db=needs_db)

    # FastAPI surface only when DB is up (status/events endpoints query it).
    # Long-running modes (consume, api-only) keep it up; one-shot modes
    # (fixture) skip it — the embedded server would just confuse the output.
    api_task: asyncio.Task | None = None
    server: uvicorn.Server | None = None
    long_running = args.consume or args.api_only
    if needs_db and long_running:
        api = build_app(app)
        server = uvicorn.Server(uvicorn.Config(
            api, host=cfg.api.host, port=cfg.api.port,
            log_level=cfg.application.log_level.lower(),
        ))
        api_task = asyncio.create_task(server.serve())

    try:
        if args.dry_run:
            await app.run_dry(Path(args.dry_run))
        elif args.fixture:
            await app.run_fixture(Path(args.fixture))
        elif args.consume:
            await app.run_consumer()
        elif args.api_only:
            assert api_task is not None
            await api_task
        else:
            print("Nothing to do. Use --consume, --fixture <path>, --dry-run <path>, or --api-only.")
    finally:
        # Stop uvicorn cleanly (sets the should_exit flag and awaits its loop).
        if server is not None and api_task is not None:
            server.should_exit = True
            try:
                await asyncio.wait_for(api_task, timeout=3.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                api_task.cancel()
        if needs_db:
            await app.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description="InkBytes Curator")
    parser.add_argument("--config", default="env.yaml", help="Path to config YAML")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--consume", action="store_true", help="Consume RabbitMQ events forever (needs DB)")
    grp.add_argument("--fixture", metavar="PATH", help="Process one fixture event end-to-end (needs DB)")
    grp.add_argument("--dry-run", metavar="PATH", help="Run ENRICH+embed only on a fixture; no DB required")
    grp.add_argument("--api-only", action="store_true", help="Run only the FastAPI surface (needs DB)")
    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, loop.stop)
        except NotImplementedError:
            pass  # Windows
    try:
        loop.run_until_complete(_run(args))
        return 0
    finally:
        loop.close()


if __name__ == "__main__":
    sys.exit(main())
