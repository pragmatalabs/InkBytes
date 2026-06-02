#!/usr/bin/env python3
"""Compatibility entrypoint for the relocated scraper app.

This wrapper keeps `python main.py` working from repository root while the
scraper code lives in `apps/scraper`.
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    scraper_root = repo_root / "apps" / "scraper"
    target_main = scraper_root / "main.py"

    if not target_main.exists():
        raise FileNotFoundError(f"Expected scraper entrypoint at {target_main}")

    os.chdir(scraper_root)
    sys.path.insert(0, str(scraper_root))
    runpy.run_path(str(target_main), run_name="__main__")


if __name__ == "__main__":
    main()
