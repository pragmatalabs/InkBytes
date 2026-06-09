# ADR-0018 — Stable `content_hash`: normalized-prefix fingerprint

> *Status: accepted / implemented · Owner: Julián · Last updated: 2026-06-08*
>
> Fixes the broken duplicate fast-path introduced in [ADR-0015](./0015-synthesis-cost-cap-and-dedup-fastpath.md).

## Context

ADR-0015 added a duplicate-enrichment fast-path: when Messor re-publishes an
article that is already in the DB unchanged, `upsert_article_raw()` keeps the
existing enrichment (it only resets `enriched_at`/`topic`/`embedding`/… when the
content changed) and the consumer skips the ENRICH→EMBED→SYNTHESIZE pipeline
entirely. The change-detection signal is `articles.content_hash`, compared in the
`ON CONFLICT` clause:

```sql
... WHERE articles.content_hash IS DISTINCT FROM EXCLUDED.content_hash
```

**The fast-path never fired in production.** Over a 29-minute window we observed
**0 SKIP / 176 ENRICH**, while only ~30 of those 176 were genuinely new article
rows — the other ~146 were full, paid LLM re-enrichments of articles already in
the DB.

### Root cause — the hash was a *raw* byte hash of unstable input

`upsert_article_raw()` computed:

```python
content_hash = hashlib.md5(
    (art["title"] + (art.get("text") or "")).encode("utf-8")
).hexdigest()
```

`art["text"]` is the body extracted by **newspaper3k**, which is *not stable
across scrapes of the same URL*. Between any two harvest cycles the extraction
differs in ways that change the bytes but not the meaning:

- trailing **boilerplate**: "N min read", "Share this article", newsletter
  call-outs, related-links blocks;
- **dynamic counters**: view counts, comment counts, "updated N hours ago";
- **whitespace / re-rendering jitter**: extra blank lines, re-indentation,
  occasional case changes in re-rendered headers.

So `content_hash` changed on nearly every re-scrape → the `IS DISTINCT FROM`
guard was always true → enrichment was reset to NULL → the article looked "new"
→ a fresh LLM enrichment ran.

### Blast radius

Combined with a Messor re-publish flood (every article re-published on every
4×/day cycle — Messor ADR-0012), this produced a **105k-message backlog** that
cost **~$780** and **~13 days** to drain on the paid LLM (DeepSeek at the time,
~$7.40 / 1000 articles). The fast-path was the one mechanism meant to prevent
exactly this, and it was a no-op.

---

## Decision

Replace the raw byte hash with a **normalized-prefix fingerprint**. The hash is
computed by `_content_hash(title, body)` in
[`services/database_service.py`](../../apps/curator/services/database_service.py):

```python
_HASH_PREFIX_CHARS = 500
_WHITESPACE_RE = re.compile(r"\s+")

def _normalize_for_hash(text: str) -> str:
    # lowercase + collapse every whitespace run to a single space, stripped
    return _WHITESPACE_RE.sub(" ", text or "").strip().lower()

def _content_hash(title: str, body: str) -> str:
    norm_title = _normalize_for_hash(title)
    norm_body = _normalize_for_hash(body)[:_HASH_PREFIX_CHARS]
    return hashlib.md5(f"{norm_title}\n{norm_body}".encode("utf-8")).hexdigest()
```

Two complementary moves:

1. **Normalize** — lowercase and collapse all whitespace runs (spaces, tabs,
   newlines) to a single space. This kills the indentation / blank-line / case
   jitter that newspaper3k introduces on re-render.

2. **Prefix** — hash only the first `_HASH_PREFIX_CHARS` (**500**) characters of
   the normalized body. The substantive *lede* of a news article is stable
   across scrapes; the volatile material (min-read footers, related links,
   live counters) is **appended at the tail** of the extraction, beyond the
   prefix window, so it never moves the hash. Real news ledes comfortably
   exceed 500 chars, so for genuine articles the boilerplate is always outside
   the window.

A genuine edit to the **headline or lede** lands inside the window and changes
the hash, so material content changes still correctly trigger re-enrichment.

The `ON CONFLICT … WHERE content_hash IS DISTINCT FROM EXCLUDED.content_hash`
clause and the post-upsert `enriched_at` read-back (the actual fast-path test in
`_handle_event`) are unchanged — only the *value* fed into the comparison is now
stable.

### Why 500 chars

- **Long enough** to make accidental collisions between two genuinely different
  articles negligible (a different article at the same URL — already rare, since
  the article `id` is the conflict key — would have to share its first 500
  normalized lede chars).
- **Short enough** to sit safely below the real-body length of essentially all
  news articles, guaranteeing the trailing boilerplate falls outside the window
  regardless of how much churns.

It is a module-level constant, trivially tunable.

---

## Consequences

- **Fast-path fires.** Re-scrapes with newspaper3k noise now hash identically to
  the stored row → enrichment is preserved → ENRICH/EMBED/SYNTHESIZE skipped.
  The ~$780 / 13-day backlog drain class of incident is eliminated.
- **Cost.** Re-enrichment charges for every Messor re-publish cycle drop to ~0;
  only genuinely new or materially-edited articles hit the LLM.
- **Observability.** The SKIP log line in `_handle_event` was promoted from
  `debug` to `info` ("`SKIP … — already enriched, content unchanged`") so the
  fast-path is greppable in production logs. Expect a flood during a backlog
  drain — that is the fix working.
- **Known, accepted limitation — tail-only edits.** A *pure append* to a
  developing story (new paragraphs added after the lede, no change to the first
  500 chars) will NOT be detected and will not re-enrich. This is acceptable:
  (a) the dominant cost driver is byte-identical re-scrapes, not real growth;
  (b) cross-article developments are captured when *new* articles join the
  cluster and re-trigger synthesis; (c) re-enriching on every tail change would
  reopen the cost hole. Corrections/rewrites to the lede *are* detected.
- **No migration needed.** `content_hash` is recomputed on the next upsert of
  each article; the column type and the migration-006 schema are unchanged. The
  first re-scrape after deploy stores the new-style hash; the one after that
  starts skipping.

---

## Alternatives considered

### Hash the full normalized body (no prefix)
Normalization alone kills whitespace/case jitter but **not** dynamic counters
("1.2k views" → "1.3k views") or appended related-links text — those are real
character changes that survive normalization. The prefix is what neutralizes
them, by keeping the volatile tail out of the hash entirely.

### `title + bucketed word_count`
Rejected: `word_count` is itself newspaper3k-derived and drifts with the same
boilerplate, so it would reintroduce the instability it was meant to avoid, and
buckets would mask genuine small edits.

### Material-change threshold (similarity / word-count delta over a cutoff)
Only reset enrichment when the change exceeds a fuzzy threshold. More robust to
tail-edits in principle, but requires fetching the old body and a similarity
computation on every upsert, and a tunable cutoff that can silently mask real
edits. Heavier and less predictable than a deterministic prefix hash;
deferred unless tail-edit detection becomes a real need.

### Enumerate and strip boilerplate patterns
Regex out "N min read", "Related stories", share widgets, etc. Brittle and
outlet-specific — an unbounded maintenance surface. The prefix approach gets the
same result generically because boilerplate is structurally a *tail*
phenomenon.

---

## Verification (local, pre-deploy)

Run through the real `_handle_event` path (`--fixture`) against local infra
(Postgres + Ollama bge-m3 + LLM enrich), one article id re-scraped four times:

| Scrape | Body | Expected | Observed |
|---|---|---|---|
| 1 | clean baseline | full ENRICH | ENRICH (cost logged) |
| 2 | uppercased title + whitespace jitter + trailing boilerplate ("7 min read", view/comment counts, related links) | **SKIP** | **SKIP** — "already enriched, content unchanged", no ENRICH |
| 3 | lede rewritten (material) | full ENRICH | ENRICH (cost logged) |
| 4 | identical to scrape 3 | **SKIP** | **SKIP**, no ENRICH |

Fixtures committed under `fixtures/fixture_dedup_{1_clean,2_noisy,3_changed}.json`
for repeatable manual re-test.
