# InkBytes — Website Content & Structure (inkbytes.news)

> *Status: v1 · Owner: Julián de la Rosa · Last updated: 2026-06-14*
>
> This is the content & information-architecture spec for the **public marketing
> website** at **inkbytes.news** (WordPress). It defines the sitemap, every page's
> purpose and copy, the article/blog content types, brand voice, and SEO metadata
> — enough to build out the whole site, not just the existing landing page.
>
> **Scope boundary.** `inkbytes.news` = the *marketing site* (this doc). The actual
> product — the reader app where you browse synthesized events — lives at
> `inkbytes.org`. Every "Start reading" CTA points to the reader. Sources for this
> doc: [`docs/product.md`](../product.md), [`docs/marketing/index.html`](./index.html),
> the Reader About page, and [`CLAUDE.md`](../../CLAUDE.md).

---

## 0. Table of contents

1. [Site purpose & goals](#1-site-purpose--goals)
2. [Brand foundation (voice, values, visual identity)](#2-brand-foundation)
3. [Information architecture / sitemap](#3-information-architecture--sitemap)
4. [Page-by-page content](#4-page-by-page-content)
5. [Articles & content types ("The Desk", methodology, dispatches)](#5-articles--content-types)
6. [Global elements (header, footer, CTAs, 404, cookie banner)](#6-global-elements)
7. [SEO & metadata](#7-seo--metadata)
8. [Conversion flow](#8-conversion-flow)
9. [Build phasing](#9-build-phasing)
10. [Open questions / decisions](#10-open-questions--decisions)

---

## 1. Site purpose & goals

`inkbytes.news` exists to **explain InkBytes and convert visitors into readers**.
It is the front door; the product is the reader app at `inkbytes.org`.

**Primary goal:** get a visitor to click *Start reading* and open the reader.
**Secondary goals:**
- Build trust in a *news* product (methodology, sourcing, corrections — credibility is the whole game).
- Rank for intent keywords ("unbiased news", "multi-source news synthesis", "ad-free news reader", LATAM-bilingual terms) via an editorial/blog layer.
- Communicate pricing and what's free vs. paid.

**Why WordPress is the right home for it:** marketing pages, a blog/editorial
section, and legal pages are exactly what WordPress does well — and it keeps that
content fully decoupled from the reader app.

---

## 2. Brand foundation

Everything on the site should sound and look like this.

### Mission
> Transform how people consume and understand the news by delivering **accurate,
> unbiased, comprehensive** coverage — synthesized from many trusted sources. One
> elegant page per event. The reader pays to skip the noise.

### Tagline
**Your Source for Comprehensive News.**

### One-line value prop
**One page worth twenty** — every fact traceable to its source.

### Core values (use these as a recurring trust motif)
- **Accuracy** — every fact traceable to its source; automated QA plus review where it applies.
- **Transparency** — the sources behind each page are visible. *It isn't magic — it's traceable aggregation.*
- **Accountability** — errors are corrected in the open; the system learns from its failures.

### Voice & tone
- **Sober, confident, plain.** News-grade credibility. No hype, no exclamation marks, no growth-hacky tricks.
- **Concrete over clever.** "Nothing publishes without at least two independent sources" beats "AI-powered news magic."
- **Honest about what it is.** We aggregate and synthesize; we don't pretend to do original reporting. Say so.
- **Reader-first.** "You're the reader, not the product."
- Bilingual where it counts (EN + LATAM ES). Spanish copy is first-class, not machine-translated afterthought.

### Visual identity (from the live theme — keep consistent)
| Token | Value | Use |
|---|---|---|
| Ink | `#111111` | Body text |
| Background | `#fafaf9` | Page background (warm off-white) |
| Accent (navy) | `#1a1a2e` | Headers, buttons, dark "bands" |
| Accent dot (coral) | `#e05c5c` | Highlights, kickers, the "pulse", CTAs accents |
| Border | `#e5e5e5` | Hairlines, cards |
| Display font | **Newsreader** (serif) | Headlines, the "editorial" feel |
| Body font | **Inter** (sans) | Everything else |
| Logo | InkBytes ink-stroke mark (`#ink` SVG symbol) | Header + footer |

Design language: editorial, calm, lots of whitespace, alternating light/navy
"bands", rounded cards, a pulsing dot to signal "live". Mobile-first.

---

## 3. Information architecture / sitemap

**Primary nav (header):** How it works · Why InkBytes · Pricing · The Desk · **Start reading** (button → reader)
**Footer nav:** Product (How it works, Why InkBytes, Pricing, Features) · Company (About, The Desk, Contact) · Legal (Methodology, Privacy, Terms) · the reader link.

```
inkbytes.news/
├── /                       Home / landing                       [LIVE]
├── /how-it-works           The pipeline, in depth               [proposed]
├── /why                    Why InkBytes vs. the alternatives    [proposed]
├── /features               What you get                         [proposed]
├── /pricing                Plans (Free vs Member)               [proposed]
├── /about                  Mission, story, founder, Pragmata    [proposed]
├── /methodology            Trust: sourcing, QA, corrections     [proposed, HIGH value]
├── /desk                   The Desk — editorial + blog index    [proposed]
│   ├── /desk/{category}/   Editorial columns by theme           [proposed]
│   ├── /desk/methodology/  Transparency essays                  [proposed]
│   └── /desk/dispatches/   Product updates / changelog          [proposed]
├── /faq                    Frequently asked questions           [proposed]
├── /contact                Contact / press                      [proposed]
├── /privacy                Privacy policy                       [proposed, required]
├── /terms                  Terms of service                     [proposed, required]
└── /404                    Not found                            [proposed]
```

> The home page can stay a long single-scroll page whose sections (`#how`, `#why`,
> `#pricing`) double as anchor targets, **and** the same content can exist as
> standalone pages for SEO/deep-linking. Recommendation: keep the one-pager as the
> hero experience; build `/how-it-works`, `/why`, `/pricing` as fuller standalone
> pages over time (see §9).

---

## 4. Page-by-page content

Each page below gives: **purpose**, **slug**, **sections**, **copy** (usable
draft text), and **SEO** title/description. Copy marked *(live)* is already on the
homepage; the rest is new draft text consistent with the brand.

### 4.1 Home — `/`  *(LIVE)*

**Purpose:** the pitch in one scroll; convert to *Start reading*.
**Sections & copy** (already built in the `inkbytes` theme):

- **Hero**
  - Eyebrow: `Ad-free · Multi-source · Citation-traceable`
  - H1: **One page worth twenty.**
  - Sub: *The news is fragmented, noisy, and biased. InkBytes reads many trusted sources for you and synthesizes one elegant, balanced page per event — with every fact traceable to its source. Pay to skip the noise.*
  - CTAs: **Start reading — $9/mo** (→ reader) · **See how it works** (→ #how)
  - Micro: *No ads. No algorithmic feed. Cancel anytime.*
  - Visual: a mock event page ("Central banks signal a coordinated shift…", 6 sources, factuality 0.94, EN·ES, entity chips, "every claim cited").
- **The problem** (navy band): *Twenty tabs. Twenty slants. No clear picture.* — three cards: Fragmented / Noisy / Biased.
- **How it works:** *A reproducible pipeline, not a wrapper over a chatbot.* — 5 steps: Collect → Enrich → Cluster → Synthesize → Verify, with the rule **nothing publishes without ≥ 2 independent sources**.
- **Why InkBytes** (navy band): comparison table vs Google/Apple News, Feedly/Inoreader, Ground News, ChatGPT/Perplexity across Synthesizes / Citation-traceable / Multi-source / Ad-free.
- **Features:** Every claim cited · Entity context · Bilingual coverage · No ads/feed games · Installable app · Ask the corpus.
- **Pricing** (navy band): Free vs **Member $9/mo**.
- **Who it's for:** Executives & analysts · Journalists & researchers · Professionals · Academics & students · The informed citizen.
- **Final CTA** (navy band): *Your source for comprehensive news.* → **Start reading — $9/mo**.

**SEO** — Title: `InkBytes — Your Source for Comprehensive News` · Description: `One elegant page per event, synthesized from many trusted sources. Skip the noise. Ad-free, citation-traceable news. $9/month.`

---

### 4.2 How it works — `/how-it-works`

**Purpose:** earn trust by showing the machinery is principled and reproducible.
**Intro:** *InkBytes is a pipeline, not a chatbot. Five stages turn the open web's firehose into one trustworthy page — and a hard rule sits at the center: nothing publishes without at least two independent sources agreeing it's a story.*

**The five stages** (expand each with 2–3 sentences):
1. **Collect** — We harvest many trusted outlets in parallel, in real time, across English and Spanish. We read homepages and RSS/Atom feeds and keep only fresh stories (a strict freshness window — no stale archive content floating to the top).
2. **Enrich** — Each article is tagged with the people, organizations, and places it mentions, plus its topic and language, and condensed to a short summary.
3. **Cluster** — Articles are grouped by *meaning*, not keywords — semantic similarity plus shared entities — so different outlets covering the same event land together.
4. **Synthesize** — Once a cluster has **≥ 2 distinct sources**, we write one balanced, source-traceable page. Every claim carries a citation back to the reporting it came from.
5. **Verify** — A quality-assurance pass drops any claim that can't be tied back to a real source, and validates each page before it goes live.

**Callout:** *The ≥ 2-source rule* — single-source rumors never become an InkBytes page. If only one outlet has it, we wait.
**Callout:** *What we don't do* — we don't do original reporting, we don't write opinion as fact, and we don't run an engagement-maximizing feed.

**SEO** — Title: `How InkBytes Works — Multi-Source News Synthesis` · Description: `A reproducible five-stage pipeline — collect, enrich, cluster, synthesize, verify — with a hard ≥2-source rule. Not a wrapper over a chatbot.`

---

### 4.3 Why InkBytes — `/why`

**Purpose:** position against the alternatives; own "the missing middle."
**Intro:** *Static aggregators add no synthesis. General chatbots hallucinate and can't be reproduced. Reading ten sources by hand doesn't scale. InkBytes is the missing middle — synthesis you can trust because you can check it.*

Reuse the comparison table (homepage) and expand each row into a short paragraph:
- **Google / Apple News** — opaque algorithmic curation; links, not synthesis; keeps you fragmented; ad-funded.
- **Feedly / Inoreader** — RSS aggregation only; no cross-source analysis.
- **Ground News** — strong on bias *labelling*, but doesn't synthesize a single account.
- **ChatGPT / Perplexity** — can summarize, but hallucinates, cites inconsistently, and isn't reproducible.
- **Reading 10 sources yourself** — the gold standard, and impossible at scale.

**The edge:** *a reproducible, traceable pipeline with programmatic QA and a hard ≥2-source rule — not a thin wrapper over an LLM.*

**SEO** — Title: `Why InkBytes — Unbiased, Multi-Source News` · Description: `The gap between aggregators, chatbots, and reading it all yourself. Synthesis you can trust because you can check the sources.`

---

### 4.4 Features — `/features`

**Purpose:** concrete value, scannable.
**H1:** *Built for people who need the whole story.*
Six features (homepage set, each with a paragraph):
- **Every claim cited** — an evidence rail links each statement back to the original reporting.
- **Entity context** — people, organizations, and places are extracted and linked, so you can follow a story across events.
- **Bilingual coverage** — global English plus LATAM Spanish; one balanced account across languages and borders.
- **No ads, no feed games** — you're the reader, not the product; no tracking-driven feed deciding what you should think.
- **Installable app** — add InkBytes to your home screen; fast, clean, built for daily reading (PWA).
- **Ask the corpus** — a built-in assistant answers questions grounded only in published, cited events — no made-up facts.

**SEO** — Title: `Features — InkBytes` · Description: `Cited claims, entity context, bilingual coverage, no ads, installable app, and a grounded corpus assistant.`

---

### 4.5 Pricing — `/pricing`

**Purpose:** make the free/paid line obvious; convert.
**H1:** *One simple plan. Skip the noise.*
**Sub:** *Headlines are free. The full synthesis, evidence rail, and entity links are for members.*

| | **Free — $0** | **Member — $9/month** |
|---|---|---|
| Browse every event | ✓ | ✓ |
| Headlines & first ~100 words | ✓ | ✓ |
| Full synthesized page | — | ✓ |
| Evidence rail & citations | — | ✓ |
| Entity links & related events | — | ✓ |
| Corpus assistant | — | ✓ |
| Installable app | — | ✓ |
| Ads / tracking / sponsored content | none | none |

**Notes line:** *No ads, ever. Cancel anytime. One flat fee.*
**FAQ teaser:** *Why paid? Because you're the customer, not the product — no ads means no incentive to hijack your attention.*

> ⚠️ **Billing is not live yet.** During the invite phase, "Start reading" opens the
> reader app (`inkbytes.org`); checkout/subscriptions land with Phase 3 (Stripe).
> Until then, present $9/mo as the plan but route CTAs to the reader. (See
> [`docs/STATUS.md`](../STATUS.md) P0 §3 and [`docs/product.md`](../product.md) §7.)

**SEO** — Title: `Pricing — InkBytes` · Description: `One simple plan. Headlines free; full multi-source synthesis, citations, and entity context for $9/month. No ads, cancel anytime.`

---

### 4.6 About — `/about`

**Purpose:** the human story + credibility (a real founder, a real place, a real lineage).
**H1:** *About InkBytes.*

**Copy:**
> InkBytes is a paid, ad-free news reader. Each **event** — a real-world
> development covered by multiple outlets — gets one elegant, source-cited page.
>
> We read many sources, group the articles about the same story, and synthesize
> them into a short, cited brief. You get the substance without the noise. No ads.
> No tracking. No sponsored content. One flat monthly fee.
>
> **Why we built it.** The news is fragmented, noisy, and biased. Getting a
> balanced account of an important event meant opening twenty tabs and reconciling
> twenty slants yourself. InkBytes does that work — and shows its receipts.

**Our values:** Accuracy · Transparency · Accountability (expand the three).

**Lineage (InkPills → InkBytes):** *InkBytes began as InkPills (2023) — the idea of consolidated "pills" of information synthesized from many sources, each referencing its origins. InkBytes is the evolution: same idea, a formalized pipeline, and a name we could ship.*

**Made in:** *Built in the Dominican Republic. LATAM + global English coverage.*
**Founder:** Julián De La Rosa (signature image). A Pragmata Labs venture.

**SEO** — Title: `About InkBytes` · Description: `A paid, ad-free news reader. Each event gets one elegant, source-cited page. Built in the Dominican Republic — LATAM + global English coverage.`

---

### 4.7 Methodology & Trust — `/methodology`  *(HIGH value — this is a news product)*

**Purpose:** the credibility page. For a synthesized-news product, this is the
single most important trust asset. Link to it from the footer and from every page.

**Sections:**
- **Where our information comes from** — we aggregate and synthesize public reporting from established outlets across EN/ES; we link to every source on each page. We do not do original reporting.
- **The ≥ 2-source rule** — no page is published from a single source.
- **How we avoid making things up** — synthesis is constrained to the clustered source articles; a QA pass drops any claim not tied to a source. The corpus assistant answers *only* from published, cited events.
- **Bias** — we preserve source diversity and synthesize a balanced account rather than picking a side; we don't run an engagement-optimizing feed.
- **Freshness** — strict freshness windows keep stale/archive content from resurfacing as "news."
- **Corrections & accountability** — how to report an error; corrections are made in the open and noted on the page.
- **Limitations** — synthesis can lag breaking events; coverage depends on which outlets we harvest; we list our source outlets.
- **Languages & coverage** — current vertical: LATAM bilingual (DR, MX, CO, AR, …) + global English business/tech.

**SEO** — Title: `Methodology & Trust — How InkBytes Sources and Verifies` · Description: `Where our news comes from, the ≥2-source rule, how we avoid hallucination, how we handle bias, and how to report a correction.`

---

### 4.8 The Desk (editorial + blog index) — `/desk`

See §5 for the full content model. The index page introduces the editorial layer:
> **The Desk.** Daily and weekly columns, methodology notes, and product
> dispatches — every claim cited, no ads, corrections in the open.

Lists the latest posts across categories with theme filters.

**SEO** — Title: `The Desk — InkBytes Editorial & Analysis` · Description: `Cited daily and weekly analysis across politics, world, business, technology, and more — plus methodology notes and product updates.`

---

### 4.9 FAQ — `/faq`

Draft Q&A:
- **Is this real journalism / original reporting?** No — InkBytes synthesizes and cites existing reporting from many outlets. We're transparent about that.
- **How do you avoid bias?** We preserve source diversity, require ≥2 independent sources, and synthesize a balanced account instead of an opinion.
- **Does the AI make things up?** Synthesis is constrained to the source articles, and a QA pass drops unsupported claims. The assistant answers only from published, cited events.
- **What's free vs. paid?** Headlines and the first ~100 words are free; the full synthesis, evidence rail, entity links, and assistant are for members ($9/mo).
- **What languages and regions?** Global English plus LATAM Spanish today; expanding.
- **Can I cancel anytime?** Yes. One flat fee, no lock-in.
- **Do you show ads or track me?** No ads, no sponsored content, no attention-hijacking feed.
- **How fresh is it?** We harvest continuously and enforce strict freshness windows.

**SEO** — Title: `FAQ — InkBytes` · Description: `How InkBytes works, how we handle bias and accuracy, what's free vs. paid, languages, and cancellation.`

---

### 4.10 Contact — `/contact`

**Purpose:** reachability + press/corrections.
- General: a contact email (e.g. `hello@inkbytes.news`).
- **Report a correction:** dedicated line that routes to the methodology/corrections process.
- **Press:** brief press blurb + logo download.
- Optional simple contact form (privacy-respecting; no marketing opt-in dark patterns).

**SEO** — Title: `Contact — InkBytes` · Description: `Get in touch, report a correction, or reach us for press.`

---

### 4.11 Legal — `/privacy`, `/terms`  *(required before public launch / billing)*

- **Privacy Policy** — what we collect (account, payment via processor, minimal analytics), no selling data, cookie usage, GDPR/data-subject rights, contact. (Note the reader-analytics design uses salted IP hashes + GeoIP-then-discard — reflect that privacy posture.)
- **Terms of Service** — subscription terms, acceptable use, IP/attribution (we link to and cite original sources; we don't claim ownership of source content), disclaimers (aggregated/synthesized content, not a system of record), cancellation.
- Optional: **Cookie/Consent** notice, **Accessibility** statement.

> These need a proper legal review before billing goes live; the doc just reserves
> the slots and the privacy posture.

---

## 5. Articles & content types

"Articles" on `inkbytes.news` are **not** the synthesized event pages (those live in
the reader at `inkbytes.org`). On the marketing site, articles are the **editorial /
blog layer** — content marketing + SEO + a demonstration of the brand's values.
All of it lives under **The Desk** (`/desk`). WordPress posts, organized by category.

### 5.1 The Desk — editorial columns (`/desk/{theme}/`)
Daily/weekly columns by a **named editorial persona**, grounded in that day's
published events and **cited**. This mirrors the planned Editorial service
(separate from the reader pipeline) — a sober per-theme column, not hot takes.

- **Themes (8):** politics, world, business, technology, culture, health, sports, environment.
- **Bilingual:** Spanish columns are first-class (the Spanish editorial voice — e.g. "La Mesa" — is the quality bar, not a translation).
- **Structure of a column:** bold lede → 2–4 short sections → key-point bullets; 220–320 words; every external claim cited with a link to the underlying event/source; byline + date; corrections appended openly if needed.
- **Cadence:** start weekly per theme; scale toward daily as the Editorial service comes online.

### 5.2 Methodology essays (`/desk/methodology/`)
Transparency-building long-reads: "How we cluster articles by meaning", "Why the
≥2-source rule matters", "How we keep stale news out of the feed", "How the corpus
assistant stays grounded". These double as SEO and as proof of seriousness.

### 5.3 Dispatches / product updates (`/desk/dispatches/`)
Changelog-style posts: new outlets added, new features (entity graph, media rail,
breaking desk), coverage expansion, periodic **transparency reports** (#sources,
#events published, corrections issued). Short, dated, honest.

### 5.4 Press / announcements
Milestones (launch, regions, partnerships). Sober press-release tone.

### Editorial standards (apply to every post)
- **Every external claim is cited.** Link to the source or the InkBytes event.
- **No ads, no sponsored content, no affiliate links.**
- **Corrections in the open** — note what changed and when.
- **Byline + date** on everything; persona columns name the persona.
- **Plain, sober voice** — match §2.

---

## 6. Global elements

- **Header** (sticky, blurred): logo → `/`; links How it works · Why · Pricing · The Desk; **Start reading** button → reader. Collapses links on mobile (button stays).
- **Footer** (navy): logo; columns Product / Company / Legal; line *© {year} InkBytes · Accuracy · Transparency · Accountability*; reader link; language note (EN/ES).
- **Primary CTA** everywhere: **Start reading** → `https://inkbytes.org` (single source of truth: theme constant `INKBYTES_READER_URL`).
- **Cookie/consent banner:** privacy-first — default to declining non-essential; no pre-ticked marketing.
- **404 page:** on-brand, calm — *"Nothing here yet."* + link home + link to The Desk.
- **Newsletter (optional, later):** a single email-capture for The Desk digest — double opt-in, no dark patterns.

---

## 7. SEO & metadata

- **Per-page `<title>` + meta description** as listed in §4. Keep titles ≤ 60 chars, descriptions ≤ 155.
- **Open Graph + Twitter cards** on every page (title, description, `og:type`, `og:url`, a branded `og:image`).
- **Structured data:** `Organization` (name, logo, founder, sameAs) on the home page; `WebSite` with `SearchAction`; `Article`/`BlogPosting` on Desk posts (author, datePublished, citations).
- **`sitemap.xml` + `robots.txt`**; canonical URLs (pin `https://inkbytes.news`, non-www canonical — already pinned in the theme via `WP_HOME`/`WP_SITEURL`).
- **Performance:** the theme is light (system fonts fallback, minimal JS) — keep it that way; Lighthouse ≥ 90.
- **Hreflang** once EN/ES pages are paired.
- **Keyword intents to target:** "unbiased news reader", "multi-source news synthesis", "ad-free news", "news without bias", LATAM-bilingual variants ("noticias sin sesgo", "noticias multi-fuente").

---

## 8. Conversion flow

```
Visitor → inkbytes.news (learn + trust)
        → "Start reading" CTA
        → inkbytes.org reader (browse free: headlines + first ~100 words)
        → hits the paywall on full synthesis
        → [Phase 3] subscribe $9/mo (Stripe)
```

- The marketing site's job ends at the click; the reader handles browse → paywall → subscribe.
- Until billing is live, the funnel ends at "browse the reader (invite/shared password)."
- The Desk feeds the top of the funnel (SEO + trust) and recirculates readers back to the reader app via in-post CTAs and cited event links.

---

## 9. Build phasing

| Phase | Pages | Status |
|---|---|---|
| **P0** | Home (single-scroll landing) | ✅ live (`inkbytes` theme) |
| **P1** | About, Methodology & Trust, Pricing (standalone), Contact | proposed — highest trust/conversion value |
| **P2** | How it works, Why, Features (standalone, SEO) + Privacy/Terms (required before billing) | proposed |
| **P3** | The Desk index + first methodology essays + dispatches | proposed |
| **P4** | Editorial columns per theme (ties to the Editorial service), newsletter, transparency reports | proposed (depends on Editorial service, ADR-0008) |

Recommended next step: **About + Methodology + a standalone Pricing page** — they
do the most for credibility and conversion with the least dependency.

---

## 10. Open questions / decisions

- **Billing timing** — CTAs say "$9/mo" but route to the reader until Stripe (Phase 3). Keep, or soften to "Browse free" until checkout exists? *(Recommend: keep "$9/mo" as the framing, button label "Start reading".)*
- **B2C vs B2B emphasis** — SPARK-X open question (`docs/product.md` §9). Affects whether to add a "For teams / newsroom" page.
- **Launch language** — lead EN, ES, or fully bilingual from day one? Affects hreflang + Desk cadence.
- **Where editorial columns live** — on `inkbytes.news` (WordPress, this doc) for SEO, in the reader, or both? *(Recommend: publish on The Desk for SEO, cross-link to reader events.)*
- **Repo home for this content + the theme** — keep in the InkBytes monorepo under `docs/marketing/`, or extract the marketing site to its own repo (tracked in `docs/STATUS.md` → Marketing site).

---

*This document is the content source of record for inkbytes.news. Update it when
pages or copy change, then reflect structural changes in the WordPress theme.*
