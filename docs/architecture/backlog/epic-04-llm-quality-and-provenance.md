# Epic 04 — LLM Quality & Provenance

> *The hardest engineering problem we have is "did Haiku just make that up?" Build the second-pass + provenance + eval set that lets us confidently say no.*

Risk-links: **R-001 (High)**, **R-007 (Medium)** · Sprints: 3 · Total: 16 pts

---

## IB-30 · Two-pass fact-check on SYNTHESIZE output

**As** the platform owner, **I want** every published one-pager to pass a second LLM verification step that checks each claim against the source articles, **so that** R-001 (hallucination) is materially mitigated.

### Acceptance criteria

```gherkin
Given Skill 3 SYNTHESIZE just produced a draft PageV1
When the fact-checker pass runs
Then it receives (draft synthesis_md, [source articles])
And returns a per-sentence verdict: supported / partially_supported / unsupported
And any "unsupported" sentence is removed from synthesis_md before persistence
And the page is only saved if at least 150 words of synthesis remain
```

### Notes

- Second Haiku call with a strict checker prompt in `prompts/factcheck.md`.
- Cost: ~$0.005 per page added → ~$2.50/mo at 500 events/day. Acceptable.
- Track `factcheck_rejected_sentences_count` per page for observability.

**Sprint**: 3 · **Points**: 5 · **Risk**: R-001 · **Priority**: P0

---

## IB-31 · Per-claim provenance markers in synthesis_md

**As** a reader, **I want** to see which source supports each claim in the one-pager, **so that** I can verify the synthesis matches the sources.

### Acceptance criteria

```gherkin
Given a synthesized page has 6 sources in evidence_rail
When the synthesis_md is rendered in the Reader
Then each factual sentence has a `[1]`, `[2]`, ... marker matching evidence_rail index
And clicking a marker scrolls to that source quote
And sentences with no source marker are styled differently (italic gray)
```

### Notes

- Update `prompts/synthesize.md` to require inline `[source: BBC]` style → post-process to indexes.
- PageV1 schema unchanged; rendering is Reader-side.
- ADR R-DR-0001 for the citation style decision.

**Sprint**: 3 · **Points**: 3 · **Risk**: R-001 · **Priority**: P1

---

## IB-32 · Cluster quality evaluation dataset (100 hand-labeled events)

**As** the platform team, **I want** a gold dataset of 100 article-pairs labeled "same event / different event", **so that** I can measure clustering precision/recall and tune thresholds with evidence.

### Acceptance criteria

```gherkin
Given the Curator runs CLUSTER on real harvested articles
When I sample 100 candidate pairs spanning the cosine-distance spectrum
Then a human labels each as same-event / different-event
And the labels are stored in fixtures/cluster_eval.jsonl
And a CI script reports precision, recall, F1 at the current threshold
And a tuning notebook explores 5 threshold values
```

### Notes

- 100 labels = ~2 hours of human work; trivial cost vs. value.
- Adds confidence to the `similarity_threshold` decision.
- Re-run weekly during Sprint-3 to catch drift.

**Sprint**: 3 · **Points**: 3 · **Risk**: R-007 · **Priority**: P1

---

## IB-33 · Prompt replay test harness

**As** the team, **I want** to replay any prompt edit against a fixed fixture set before merging, **so that** prompt regressions don't ship unnoticed.

### Acceptance criteria

```gherkin
Given prompts/enrich.md or prompts/synthesize.md is edited
When CI runs the prompt-replay step
Then it executes ENRICH on 10 frozen fixture articles
And asserts the output JSON parses against EnrichmentResult
And diffs the topic/sentiment/factuality vs. the baseline
And fails the PR if any field changes by > 10% or schema breaks
```

### Notes

- Fixtures in `fixtures/prompt_replay/*.json`.
- Baseline outputs in `fixtures/prompt_replay/baseline/`.
- `--update-baseline` flag for intentional changes.

**Sprint**: 3 · **Points**: 3 · **Risk**: R-001 · **Priority**: P1

---

## IB-34 · Lock brand voice for SYNTHESIZE prompt

**As** the product owner, **I want** the SYNTHESIZE prompt to enforce one specific brand voice (Bloomberg-terse vs NPR-warm vs Atlantic-essayistic), **so that** every one-pager reads consistent and on-brand.

### Acceptance criteria

```gherkin
Given a brand voice document is approved by the PO
When prompts/synthesize.md is updated with the voice rules
Then 5 freshly synthesized pages are reviewed by the PO
And ≥4 of 5 are approved without further edit requests
And an ADR (Reader-0001) records the chosen voice
```

### Notes

- Bloomberg-terse is the working default in v0.
- This story exists because R-013 is currently open.
- Pair with IB-31 (provenance markers) since voice + citations interact.

**Sprint**: 3 · **Points**: 2 · **Risk**: R-013 · **Priority**: P1
