# Reader ADR-0009 — Rich markdown rendering for the news body

> *Status: accepted · Owner: Julian · Date: 2026-06-13*

## Context

The event page rendered `synthesis_md` with a hand-rolled function that only
split on `\n\n` into paragraphs and chipped `[Source: X]` markers. Anything
richer — headings, **bold**, lists, blockquotes, links, tables — rendered as
raw markdown text. And the synthesis prompt only asked for "200–250 words,
Markdown", so the LLM emitted flat prose with no structure: a dense wall of
text. The body looked poor and was hard to scan.

## Decision

Two coordinated changes — a real renderer **and** prompt rules that give it
structure to render:

### 1. Reader — proper markdown renderer

`components/news-markdown.tsx` renders `synthesis_md` with **react-markdown +
remark-gfm**, replacing the paragraph-only function. Block/inline elements
(h2/h3, p, ul/ol/li, blockquote, a, strong, em, code, hr, tables) are mapped
to brand-styled components (InkBytes `--ink`/`--accent`/`--accent-dot`,
generous line-height, red list markers + blockquote rule). The `.synthesis-body`
drop-cap on the first paragraph is preserved.

Inline source citations (`[Source: BBC]` / `[Fuente: …]`) are turned into
small `<cite>` chips by a tiny **rehype** plugin that walks the HAST, splits
text nodes on the citation pattern, and emits `cite` elements — kept as a
post-markdown pass so it's independent of surrounding structure.

**Safety:** raw HTML is NOT rendered (no `rehype-raw`), so LLM output that
contains `<script>` is escaped as text — no injection surface.

### 2. Curator — synthesis formatting rules

`prompts/synthesize.md` now instructs structured Markdown: a **bold lead**,
`## ` section subheadings for multi-faceted stories (no top-level `#`), a
short **bullet list** for discrete facts/figures, `**bold**` for pivotal
numbers/names (sparingly), explicit source contrast on disagreement, and
inline `[Source: X]` citations on every claim. Budget raised 200–250 → 220–320
words to accommodate structure. The prompt is explicit that thin stories may
stay 1–2 paragraphs — structure is a tool, not mandatory scaffolding.

## Consequences

- The body reads as a scannable one-pager (lead → sections → key points)
  instead of a prose wall; existing plain-prose pages still render fine
  (paragraphs + chips) until they're re-synthesized.
- New deps: `react-markdown`, `remark-gfm` (SSR-safe; the event page stays a
  dynamic server component). Production build verified.
- The chat assistant still uses its own `renderAnswer`; unifying it onto
  `NewsMarkdown` is a possible future cleanup, not done here.

## Verification

Local event seeded with a structured-markdown sample rendered: 2 `##`
headings, 3 bullets (red markers), 1 blockquote, 3 bolds, 1 italic, 6 source
chips, drop-cap lead — zero raw markdown leaking, no console errors; tsc +
production build clean.
