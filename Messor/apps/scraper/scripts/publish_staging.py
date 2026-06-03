#!/usr/bin/env python3
"""Quick smoke test: publish existing staging files to RabbitMQ.

Usage:
    cd /Volumes/Pragmata/Projects/InkBytes/Messor/apps/scraper
    source .venv/bin/activate
    python scripts/publish_staging.py env.local.yaml
"""
import json, sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from inkbytes.common.system.config.config_loader import ConfigLoader

config_path = sys.argv[1] if len(sys.argv) > 1 else "env.local.yaml"
config = ConfigLoader(config_path)

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("publish_staging")

from services.message_service import MessageService
svc = MessageService(config, logger)

if not svc.connect():
    logger.error("Cannot connect to RabbitMQ. Is the dev stack running?")
    sys.exit(1)

staging_dir = config.storage.staging.local.scraping()
files = glob.glob(os.path.join(staging_dir, "*.db.json"))
if not files:
    logger.warning("No staging files found in %s", staging_dir)
    sys.exit(0)

total = 0
for f in sorted(files):
    with open(f) as fh:
        data = json.load(fh)
    articles = list(data.get("_default", {}).values()) if isinstance(data, dict) and "_default" in data else data
    session_id = os.path.basename(f)
    published = 0
    for a in articles:
        if isinstance(a, dict) and svc.publish_article_event(a, session_id):
            published += 1
    logger.info("  %s → %d/%d events published", session_id, published, len(articles))
    total += published

logger.info("Done. Total events published: %d", total)
svc.close()
