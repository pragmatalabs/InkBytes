# ADR-0009 — Real-time translation as Skill 4 (TRANSLATE)

> *Status: **proposed** · Owner: Julian · Phase: post-v0 (Sprint 2)*

## Context

InkBytes targets a bilingual LATAM + global English audience. As of v0 the
pipeline produces synthesis pages in whichever language Haiku defaults to
(effectively English), regardless of the event's source articles.

Two problems this creates:

1. **Spanish-language outlets** (Milenio MX, El Espectador CO, Clarín AR, …)
   produce ES articles that get synthesized into English pages — an ES reader
   sees a page that feels translated from their own press.

2. **Language toggle in the Reader** (`feed-client.tsx` already has a
   `language` state wired to localStorage) has no data to switch between —
   every page only has one language version.

Adding machine translation via an external service (DeepL / Google Translate)
would introduce a second vendor, a second API key, and quality loss on
journalistic prose. Claude Haiku 4.5 is already paid for, understands
multilingual news, and produces natural-sounding output.

## Decision

Add **Skill 4 — TRANSLATE** to the Curator pipeline. After `SYNTHESIZE`
produces a page, immediately run one Haiku call that translates the headline
and `synthesis_md` into the secondary language and stores the result in a new
`page_translations` table. Skill 4 is **fire-and-forget**: a translation
failure is logged but never blocks or retries the main pipeline.

The synthesis step is also made **language-aware**: `SYNTHESIZE` detects the
dominant language of the event's articles (majority vote on `articles.language`)
and instructs Haiku to write in that language. This gives Spanish-majority
events a native ES page and English-majority events a native EN page, with the
translation producing the counterpart.

### What changes

#### DB — migration 008

```sql
CREATE TABLE page_translations (
    page_id       TEXT NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    lang          TEXT NOT NULL,         -- 'en', 'es', 'pt', …
    headline      TEXT NOT NULL,
    synthesis_md  TEXT NOT NULL,
    translated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY   (page_id, lang)
);
CREATE INDEX idx_page_translations_lang ON page_translations(lang);
```

`pages` rows continue to hold the **source-language** content. Translations
are second-class citizens: they can be regenerated at any time by re-running
Skill 4.

#### New files

| File | Purpose |
|---|---|
| `prompts/translate.md` | System prompt: translate headline + synthesis_md, preserve markdown and proper nouns |
| `contracts/translation_v1.py` | `TranslationResult(headline, synthesis_md)` |
| `skills/translate.py` | `TranslateSkill.run(page_id, headline, synthesis_md, source_lang, target_lang)` |

#### Modified files

| File | Change |
|---|---|
| `prompts/synthesize.md` | Add `DOMINANT_LANGUAGE` input field; rule to write output in that language |
| `skills/synthesize.py` | Compute dominant language (Counter on `rows[*].language`), pass to prompt |
| `services/database_service.py` | `write_translation()`, `fetch_pages_missing_translation(lang)` |
| `core/application.py` | Call `translate.run()` immediately after `synthesize.run()` |
| `core/api_server.py` | `/events` SQL LEFT JOINs `page_translations`; returns `translations` dict inline |
| `main.py` | `--translate-missing` one-shot backfill mode |
| `Reader/apps/web/lib/types.ts` | `translations?: { [lang: string]: { headline: string; synthesis_md: string } }` |
| `Reader/apps/web/app/feed-client.tsx` | Language toggle reads from `event.translations[lang]` or falls back to source |

#### Pipeline flow (after this ADR)

```
ENRICH  (Skill 1)
  ↓  topic, theme, keywords_canonical, entities
CLUSTER (Skill 2)
  ↓  event_id, source_count
SYNTHESIZE (Skill 3)
  ↓  detects dominant_language (en or es)
  ↓  writes pages row in dominant language
TRANSLATE  (Skill 4)          ← NEW
  ↓  one Haiku call: headline + synthesis_md → secondary language
  ↓  writes page_translations row (fire-and-forget)
```

#### Language-aware synthesis logic

```python
from collections import Counter
lang_counts = Counter(r["language"] for r in rows)
dominant = lang_counts.most_common(1)[0][0]  # 'en' or 'es'
# Mixed events (tie) → 'en'
target = "es" if dominant == "en" else "en"
```

Prompt change:
```
DOMINANT_LANGUAGE: {{dominant_language}}
Write the headline and synthesis_md in this language.
```

#### API shape (`/events` list item)

```json
{
  "id": "…",
  "headline": "Messi lidera a Argentina en la final",   ← source lang (es)
  "translations": {
    "en": {
      "headline": "Messi leads Argentina into the final",
      "synthesis_md": "…"
    }
  },
  "category": "sports",
  "topic": "Copa América Final"
}
```

The Reader language toggle picks `translations.en.headline` when EN is
selected, falling back to `headline` if no translation exists (legacy pages
or translation still in-flight).

## Consequences

**Good**
- Bilingual pages at essentially zero marginal cost (~$0.0006/page with Haiku)
- No new external vendor; same API key and rate-limit pool
- Spanish-majority events read naturally in Spanish
- Language toggle in Reader becomes functional
- Architecture is extensible to `pt` (Brazilian Portuguese) by adding one
  more `translate.run()` call per synthesize cycle

**Bad / risks**
- Translation failure silently drops a language version; monitoring needed
  (track `page_translations` coverage in `/status`)
- `synthesis_md` references like `[Source: BBC]` must be preserved verbatim
  (prompt must forbid translating source names)
- Dominant-language heuristic can mismatch: an event with 2 ES and 3 EN
  articles synthesizes in EN even if the 2 ES articles are more substantive

**Neutral**
- `pages` rows are unchanged; `page_translations` is a pure addition
- Existing 29 pages can be backfilled via `--translate-missing` (~$0.02 total)
- Re-synthesis automatically overwrites the translation via `ON CONFLICT DO UPDATE`

## Alternatives considered

**A — Client-side translation (browser native or Google Translate API)**
Rejected. Adds latency, a second vendor, and quality is noticeably worse for
journalistic prose. Browser Translation API has inconsistent support.

**B — Bilingual synthesis in a single call (output both languages at once)**
Rejected. Doubles output tokens (500 words instead of 250) and inflates the
structured schema. Reliability of instructor-validated dual-language JSON is
lower. Two focused calls are more predictable.

**C — Store translations inside the `pages` row (headline_es, synthesis_md_es columns)**
Rejected. Doesn't scale to three+ languages without schema changes each time.
The separate `page_translations` table is extensible with no DDL additions.

**D — Translate at ENRICH time (per-article)**
Rejected. Per-article translation is expensive (~$1.50/1000 articles) and
unnecessary — readers see the synthesized page, not raw article bodies.

## Implementation order

1. Migration 008 (`page_translations`)
2. `translation_v1.py` + `translate.md` + `TranslateSkill`
3. Language-aware synthesis (`synthesize.md` + `synthesize.py`)
4. `write_translation` + `fetch_pages_missing_translation`
5. Wire Skill 4 in `application.py`
6. `/events` API returns `translations` JSON
7. `--translate-missing` backfill CLI mode
8. Reader language toggle reads from inline translations

## Related

- [ADR-0001](0001-curator-collapses-pipeline.md) — Curator skill architecture
- [ADR-0007](0007-synthesize-pending-cli.md) — Synthesize backfill pattern (reused here for `--translate-missing`)
- [`docs/roadmap.md`](../../../docs/roadmap.md)
