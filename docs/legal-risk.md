# InkBytes — Legal Risk Memo

> *Status: v1 · Owner: Julian · Last updated: 2026-06-16*
> *⚠️ This is an engineering-side risk map, **not legal advice**. It exists to (a) make the risks explicit and (b) track concrete mitigations. Before charging the first paying user or scaling publicly, get a qualified **IP / media lawyer** in the relevant jurisdiction(s). Treat that review as a launch gate.*

## The core tension (one paragraph)

InkBytes is a **commercial, paywalled** product whose value proposition is *"pay to skip reading the sources."* It scrapes ~65 outlets, **stores full article text** (`articles.body_text`), **displays their images** (hotlinked `og:image`), and publishes **LLM-synthesized** one-pagers designed to **substitute** for the originals. Commercial + reproduces copyrighted reporting + substitutes for the original is the legally riskiest quadrant for a news product. It is survivable, but via **licensing, careful design, and counsel** — not by assuming fair use.

---

## Risk register

Severity = likelihood × damage, for a *paid* launch. Each row names the InkBytes feature that triggers it.

| # | Risk | What triggers it in InkBytes | Severity |
|---|---|---|---|
| L1 | **Copyright — reproduction** | `articles.body_text` stores full copies of copyrighted articles indefinitely (Messor harvest → Postgres). Transient processing is more defensible than indefinite storage. | **High** |
| L2 | **Copyright — market substitution (fair-use factor 4)** | The synthesized page (`pages.synthesis_md`) is built to replace reading the source. The paywall *strengthens* the "harms the market" argument — the factor courts weight most. | **High** |
| L3 | **Unlicensed images** | `lead_image` displays outlet `og:image`s cross-origin — i.e. AP / Getty / Reuters / wire photos with **no license**. Easiest infringement to prove (one photo = one clean claim). ADR-0019 fixed *rendering*, not *licensing*. | **High** |
| L4 | **Paywalled sources** | Bloomberg / WSJ / FT / Economist are configured outlets. These parties litigate; scraping + republishing paywalled content is the most aggressive item in the stack. | **High** |
| L5 | **Defamation (no §230 shield)** | Curator's synthesis is InkBytes' **own generated speech**, not third-party content merely hosted — §230 likely does **not** apply. An LLM hallucination stated as fact about a real person/company = publisher liability. The `factuality` score is not a defense. | **High** |
| L6 | **Anti-bot / access-control circumvention** | Scrapling/Patchright **stealth browsers** defeat bot detection; any paywall bypass. Elevates ToS breach toward CFAA / DMCA §1201, and is bad optics in any suit. | Medium-High |
| L7 | **EU press-publishers' right + sui generis database right** | Targets ES/FR/DE outlets. EU Copyright Directive Art. 15 can *require a license/payment* to publishers for aggregating press content; the Database Directive protects the DB itself. | Medium |
| L8 | **Hot-news misappropriation (US/NY)** | Time-sensitive facts, free-riding on others' newsgathering, direct competition, reduced incentive — InkBytes fits the INS v. AP / NBA v. Motorola fact pattern. | Medium |
| L9 | **GDPR / privacy** | `entities` = named natural persons; reader analytics design (salted IP hash / GeoIP). Needs lawful basis + DPA-grade handling for EU data subjects. | Medium |
| L10 | **Terms-of-Service breach** | Most outlets' ToS forbid automated scraping + commercial reuse → breach-of-contract exposure independent of copyright. | Medium |
| L11 | **Trademark / passing-off** | Outlet names + the avatar/logo stack. Nominative use for attribution is generally OK; implying endorsement/affiliation is not. | Low-Medium |

### What's already (partially) protective
- **Attribution + link-back**: `[n]` citations → `/event/{id}`, source links, the **≥2-source publish gate**. Helps the "transformative aggregator" framing, hot-news, and passing-off. **But attribution ≠ a license** — it does not cure L1–L4.
- **Multi-source synthesis of facts**: facts are uncopyrightable; cross-source re-expression is more defensible than verbatim or single-source paraphrase.
- **Marketing site has `/privacy` + `/terms`** already.

---

## Mitigations (tracked)

Ordered by leverage = (risk reduced) ÷ (effort). The first three are cheap and high-certainty.

- [ ] **M0 — Get IP/media counsel before the first paying user.** Single highest-leverage action; commercial launch is the threshold that makes L1–L8 real. *(blocks: first paying user)*
- [ ] **M1 — Stop displaying unlicensed source images** *(kills L3, ~1 day)*. Replace the source-`og:image` hero with **owned, non-photographic, generic** imagery — design in **Curator ADR-0034** ("variation, not a copy"): Tier 1 = owned procedural brand covers (per-event, free, no licensing), Tier 2 = CC0/public-domain generic library, Tier 3 = *stylized, labelled, non-photoreal* AI illustration gated to top stories. **No photoreal AI of real events/people** (misinformation/authenticity risk). Engineering: stop rendering `articles.lead_image` as the hero (extract/store is fine).
- [ ] **M2 — Stop long-term full-text storage** *(reduces L1, medium)*. Keep `body_text` only through enrichment, then purge; retain embeddings + derived fields (theme/entities/summary), not full copies. Engineering: a Curator retention job that NULLs `articles.body_text` after `enriched_at` (+ keep `content_hash` for dedup).
- [ ] **M3 — Drop or license paywalled outlets** *(kills L4)*. Remove Bloomberg/WSJ/FT/Economist from active outlets, or pursue licensing.
- [ ] **M4 — Reconsider stealth fetching** *(reduces L6)*. Honor `robots.txt`; drop stealth/anti-bot evasion for sources that block bots; never bypass paywalls.
- [ ] **M5 — Harden synthesis toward transformative event pages** *(reduces L2)*. Prompt for genuinely cross-source *event* synthesis (not a stand-in for any single article); keep summaries short; lean on the link-out. Engineering: `prompts/synthesize.md`.
- [ ] **M6 — Defamation controls** *(reduces L5)*. Visible "AI-generated summary — verify with sources" labeling on event pages; a public correction/takedown path; treat synthesis as editorial output with a review/escalation path.
- [ ] **M7 — Publisher takedown + opt-out** *(reduces L1/L7/L10)*. A documented takedown channel; honor `robots.txt`/`ai.txt`/meta opt-outs; per-outlet kill switch (Backoffice already has outlet enable/disable).
- [ ] **M8 — Pick a launch jurisdiction deliberately** *(scopes L7/L8/L9)*. EU is strictest (press-publishers' right + GDPR); US has fair use + hot-news; LATAM (incl. DR) varies. Shape ToS, data handling, and outlet mix to the chosen launch market.
- [ ] **M9 — GDPR baseline** *(reduces L9)*. Lawful basis for entity/person data + reader analytics; finalize the analytics PII design (salted IP hash, GeoIP-then-discard) before building it.

---

## Jurisdiction cheat-sheet

- **US** — fair use (4-factor; factor 4 market-harm is the problem here) + NY hot-news misappropriation + DMCA/CFAA for access circumvention. No §230 for own-generated synthesis.
- **EU (ES/FR/DE)** — press-publishers' right (Art. 15), sui generis database right, GDPR. The "Google News had to license/pay" precedent applies to aggregators.
- **LATAM (DR/MX/CO/AR/…)** — civil-law copyright; generally narrower fair-use-style exceptions than the US. Country-specific.

---

## Bottom line

InkBytes is **not clearly legal as-is for a paid product** — it sits in the contested news-aggregation + AI-summarization zone, and the paywall + full-text storage + unlicensed images + own-generated synthesis each add exposure. The path to a defensible launch is: **counsel (M0)** + the cheap high-certainty fixes (**M1 images, M2 storage, M3 paywalled outlets**) + a deliberate jurisdiction choice (**M8**). Until then, treat broad public/paid launch as gated.
