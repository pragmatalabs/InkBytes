# worldmonitor → InkBytes outlet import

> *Created 2026-06-15 · one-off outlet-onboarding pipeline*

Mines the sibling project **[pragmatalabs/worldmonitor](https://github.com/pragmatalabs/worldmonitor)**
(a fork of koala73/worldmonitor — *AGPL-3.0*) for RSS feeds we can adopt as
InkBytes outlets, dedups against what we already harvest, classifies them to our
`public.outlets` schema, and **parse-validates** each feed with newspaper3k so we
only import outlets that actually extract.

## ⚠️ Licensing
worldmonitor is **AGPL-3.0** (network-copyleft). We did **not** copy any of its
code. Only the **feed URLs** were reused — those are public facts, re-curated into
our own config. Don't lift worldmonitor source files into InkBytes (paid,
network-served) — it would trigger AGPL source-disclosure.

## Result
- worldmonitor publishes ~420 feeds; **374 OK** (status-validated in its own report).
- After dedup vs our 57 existing outlets → 181 net-new single-outlet candidates
  (+120 Google-News topic queries, excluded — they need redirect decoding and
  don't fit our per-outlet model).
- Hand-curated to **41 high-fit news outlets** (dropped think-tanks, gov feeds,
  VC blogs, podcasts — situational-awareness sources, not consumer news).
- **newspaper3k parse-validation → 27 PASS / 14 FAIL.** Failures were paywalls /
  hard anti-bot (FT, MarketWatch, Investing, Seeking Alpha, VentureBeat, Fast
  Company, Politico, Repubblica, Spiegel) or dead/blocked feeds (France 24,
  Indian Express, Kyiv Independent, Brasil Paralelo).
- Final import: **`add_worldmonitor_outlets.sql`** — 27 outlets (7 tech, 2 crypto,
  18 general incl. 5 European + 2 LATAM + Euronews ES). Mostly global-EN/tech/EU;
  does **not** close the LATAM/ES gap (PT outlets dead, mainstream finance paywalled).

## Apply (prod — manual, idempotent)
```bash
docker exec -i inkbytes-postgres psql -U inkbytes -d inkbytes < add_worldmonitor_outlets.sql
```
New rows are `active=true, priority=3, pulse=false` so they trickle in on the
regular 4×/day cycle (below established outlets). **Watch queue depth + cost the
first cycle** — several are high-volume (DW, NRC, The Diplomat) and embeddings are
CPU-bound (~19/min on Hostinger). `ON CONFLICT (id) DO NOTHING` makes re-runs safe.

## Reproduce
Inputs are pulled at runtime (kept out of the repo — worldmonitor's compiled feed
list is their AGPL data):
```bash
# 1. worldmonitor's validated feed report  ->  /tmp/wm-feeds.csv
gh api repos/pragmatalabs/worldmonitor/contents/scripts/rss-feeds-report.csv \
  --jq '.content' | base64 -d > /tmp/wm-feeds.csv
# 2. our existing outlets (for dedup)  ->  /tmp/ib-outlets.psv
ssh root@<droplet> 'docker exec -i inkbytes-postgres psql -U inkbytes -d inkbytes -tA -F"|" \
  -c "SELECT id,coalesce(url,\x27\x27),coalesce(feed_url,\x27\x27),coalesce(region,\x27\x27),coalesce(language,\x27\x27) FROM outlets;"' > /tmp/ib-outlets.psv

python3 01_dedupe_classify.py        # 374 OK -> 181 deduped candidates (review CSV)
python3 02_curate_and_emit_sql.py    # hand-curated 41 -> emits validated SQL (PASS set inside)
# validation runs IN the messor container (has newspaper3k + feedparser):
ssh root@<droplet> 'docker exec -i inkbytes-messor python -' < 03_validate_extraction.py
# fold the PASS list back into 02_curate's PASS set, re-run -> add_worldmonitor_outlets.sql
```
