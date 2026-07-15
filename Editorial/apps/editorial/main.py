"""InkBytes Editorial service — daily per-theme editorial columns (ADR-0008).

  python main.py --config env.yaml --generate                 # all themes, today
  python main.py --config env.yaml --generate --theme politics --dry-run
  python main.py --config env.yaml --generate --date 2026-06-28 --lang es
  python main.py --config env.yaml --synthesize-missing        # backfill audio only
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date, datetime

from core.application import Application
from core.config import Config


def main() -> None:
    ap = argparse.ArgumentParser(description="InkBytes Editorial service")
    ap.add_argument("--config", default="env.yaml")
    ap.add_argument("--generate", action="store_true",
                    help="Generate editorials (default: every theme for the date)")
    ap.add_argument("--synthesize-missing", action="store_true",
                    help="Backfill TTS audio for editorials that have none yet (ADR-0011)")
    ap.add_argument("--audio-limit", type=int, default=500,
                    help="Max editorials to backfill with --synthesize-missing")
    ap.add_argument("--theme", default=None, help="Limit to one theme")
    ap.add_argument("--lang", default=None, help="Limit to one language (else config.languages)")
    ap.add_argument("--date", default=None, help="Edition date YYYY-MM-DD (default: today)")
    ap.add_argument("--dry-run", action="store_true", help="Print, don't write")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
        datefmt="%H:%M:%S")

    cfg = Config.load(args.config)
    if args.lang:
        cfg.editorial.languages = [args.lang]
    edition = (datetime.strptime(args.date, "%Y-%m-%d").date()
               if args.date else date.today())

    async def run() -> None:
        app = Application(cfg)
        await app.start()
        try:
            if args.synthesize_missing:
                await app.synthesize_missing(args.audio_limit)
                return
            if not args.generate:
                print("nothing to do — pass --generate or --synthesize-missing")
                return
            if args.theme:
                for lang in cfg.editorial.languages:
                    await app.generate_theme(args.theme, lang, edition, args.dry_run)
            else:
                await app.generate_all(edition, args.dry_run)
        finally:
            await app.close()

    asyncio.run(run())


if __name__ == "__main__":
    main()
