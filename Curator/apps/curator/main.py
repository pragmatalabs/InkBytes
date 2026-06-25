#!/usr/bin/env python3
"""Curator entry point.

Modes:
  --consume                    run forever: consume RabbitMQ events AND serve the API (single-node/dev)
  --worker                     consume RabbitMQ events forever, NO API port (scalable worker; container split)
  --api-only                   only run the FastAPI surface on :8060 (no consumer)
  --fixture <path>             process one event from a JSON fixture (offline-safe)
  --reenrich-missing           re-enrich articles in the DB that are missing enrichment (topic IS NULL)
  --conclude-stories           archive events silent for ≥ conclude_after_days days (ADR-0013)

Container topology (root ADR-0007): run one `--api-only` (the :8060 read surface)
plus N `--worker` replicas (the LLM pipeline). `--consume` (API+worker combined)
stays for single-process/dev use.

Examples:
  python main.py --consume
  python main.py --worker
  python main.py --fixture fixtures/sample_article.json
  python main.py --reenrich-missing
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
    # --reenrich-missing always needs DB (fetches + writes enrichment rows).
    needs_db = not args.dry_run
    if args.reenrich_missing or args.synthesize_pending or args.conclude_stories:
        needs_db = True
    await app.startup(with_db=needs_db)

    # FastAPI surface only when DB is up (status/events endpoints query it).
    # Long-running modes (consume, api-only) keep it up; one-shot modes
    # (fixture) skip it — the embedded server would just confuse the output.
    api_task: asyncio.Task | None = None
    server: uvicorn.Server | None = None
    # --consume-commands / --reenrich-missing are focused one-shot/focused harnesses
    # that must NOT bind the FastAPI port.
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
        elif args.consume or args.worker:
            # Both run the full consumer (articles + sessions + commands).
            # --consume also serves the API (long_running); --worker does not,
            # so workers can scale to N replicas with no :8060 port clash.
            await app.run_consumer()
        elif args.consume_commands:
            await app.run_command_consumer()
        elif args.consume_sessions:
            await app.run_session_consumer()
        elif args.reenrich_missing:
            await app.run_reenrich_missing()
        elif args.reenrich_stubs:
            await app.run_reenrich_stubs()
        elif args.synthesize_pending:
            await app.run_synthesize_pending(since_hours=args.since_hours)
        elif args.conclude_stories:
            await app.run_conclude_stories()
        elif args.api_only:
            assert api_task is not None
            # Start the config-refresh loop so admin changes in Backoffice
            # propagate to /status without restarting the API container
            # (same loop the --worker runs; harmless to also run in api-only mode).
            app._config_task = asyncio.create_task(app._config_refresh_loop())
            await api_task
        else:
            print("Nothing to do. Use --consume, --worker, --api-only, --fixture <path>, --dry-run <path>, --reenrich-missing, --reenrich-stubs, or --conclude-stories.")
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
    parser.add_argument("--since-hours", type=int, default=None,
                        help="Scope --synthesize-pending to events with material activity "
                             "in the last N hours (the feed window). Keeps a post-re-cluster "
                             "re-synth bounded to events that will actually surface.")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--consume", action="store_true", help="Consume RabbitMQ events forever AND serve the API on :8060 (single-node/dev; needs DB)")
    grp.add_argument("--worker", action="store_true", help="Consume RabbitMQ events forever, NO API port — scalable worker for the container split (needs DB)")
    grp.add_argument("--consume-commands", action="store_true", help="Consume only Backoffice moderation commands (needs DB; no FastAPI port)")
    grp.add_argument("--consume-sessions", action="store_true", help="Consume only Messor scrape-session run summaries (B12.1; needs DB; no FastAPI port)")
    grp.add_argument("--fixture", metavar="PATH", help="Process one fixture event end-to-end (needs DB)")
    grp.add_argument("--dry-run", metavar="PATH", help="Run ENRICH+embed only on a fixture; no DB required")
    grp.add_argument("--api-only", action="store_true", help="Run only the FastAPI surface (needs DB)")
    grp.add_argument(
        "--reenrich-missing",
        action="store_true",
        help=(
            "Re-enrich articles already in the DB that are missing enrichment "
            "(topic IS NULL). Use after quota recovery."
        ),
    )
    grp.add_argument(
        "--reenrich-stubs",
        action="store_true",
        help=(
            "Re-enrich articles that were processed in stub mode "
            "(keywords_canonical contains 'stub'). Overwrites fake topic/entity "
            "data and re-synthesizes any stub pages."
        ),
    )
    grp.add_argument(
        "--synthesize-pending",
        action="store_true",
        help=(
            "Synthesize events that have ≥2 distinct sources but no published "
            "page yet. Runs once and exits. Use after restarts or bulk re-ingests "
            "when the in-memory synthesis gate was reset."
        ),
    )
    grp.add_argument(
        "--conclude-stories",
        action="store_true",
        help=(
            "Archive published events that have been quiet for ≥ conclude_after_days "
            "days: write a story_arcs row and mark the event 'concluded'. "
            "Disabled when clustering.conclude_after_days == 0 (the default). "
            "Safe to re-run (idempotent). (ADR-0013)"
        ),
    )
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
