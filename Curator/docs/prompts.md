# Curator — Prompts

> *Prompts are first-class code. They live in `apps/curator/prompts/` as
> `.md` files so they diff well in PR review.*

## Why .md, not inline strings

1. **Diffable** — prompt edits show as plain prose diffs.
2. **Reviewable** — non-engineers (editors, founders) can read and propose
   wording changes without touching Python.
3. **Versionable** — when we bump a prompt incompatibly, we add
   `enrich.v2.md` next to it and migrate code.
4. **Testable** — every prompt change should be paired with a fixture
   replay through `--fixture` to confirm the new wording still produces
   schema-valid JSON.

## Current prompts

| File | Skill | Output schema |
|---|---|---|
| `prompts/enrich.md` | Skill 1 — ENRICH | `EnrichmentResult` |
| `prompts/synthesize.md` | Skill 3 — SYNTHESIZE | `PageV1` |

## How the LLM call works

`LlmService.structured(...)` uses
[`instructor`](https://python.useinstructor.com/) to:

1. Send `system` = the prompt body (everything up to `## Input format`).
2. Send `user` = the structured input the skill assembles.
3. Force a JSON response that validates against the `response_model`.
4. Re-prompt up to 3 times on validation failure (instructor default).

If `ANTHROPIC_API_KEY` is unset the LlmService returns a deterministic
**stub** that matches the schema — useful for offline dev (D2).

## Prompt versioning rules

- A **wording change** that keeps the JSON schema → same file, commit message describes the intent + before/after.
- A **schema change** (new field, removed field) → bump the Pydantic model in `contracts/` AND add `<name>.v2.md`; old code reads v1, new code reads v2 in parallel until cutover.
- Always run `python main.py --fixture fixtures/sample_article.json` after a prompt change. If the output JSON drifts noticeably, capture a new fixture under `fixtures/expected/`.

## Style guide (for the Synthesize prompt voice)

> Locked decision pending in [`docs/mvp-plan.md`](../../docs/mvp-plan.md) §11.

Until the brand voice is locked, the synthesis prompt uses a neutral,
Bloomberg-terse style: short sentences, dates and numbers, attribution
on every contested claim. After the voice is locked we update
`prompts/synthesize.md` accordingly.

## Cost note

Each prompt's system text counts against input tokens on every call.
Today they sit at ~250 tokens each — negligible. Keep them under 500
tokens; if they grow past that, factor shared rules into a `prompts/_shared.md`
and concat at load time.
