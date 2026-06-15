# InkBytes — WordPress structured-content export

Paste-ready content + SEO for every route, plus the global elements. The full
body copy lives in each HTML file (and maps to WP page content / blocks); this
doc is the **source of record for SEO, IA, and the reusable global strings**.

Reader CTA target (WP theme constant `INKBYTES_READER_URL`): `https://inkbytes.org`

---

## Global elements

**Primary nav (EN):** How it works · Why InkBytes · Pricing · The Desk · Methodology · `Start reading →` reader
**Primary nav (ES):** Cómo funciona · Precios · Sobre nosotros · Metodología · `Empezar a leer →` reader
**Language toggle:** EN ⇄ ES, per-page pairs (`/about` ⇄ `/es/about`, …). WP: WPML / Polylang.

**Footer columns (EN):**
- *Product:* How it works, Why InkBytes, Features, Pricing
- *Company:* About, The Desk, Contact
- *Trust:* Methodology, Privacy, Terms
- *The reader:* note + `Start reading`
- Bottom bar: `© {year} InkBytes` · Accuracy · Transparency · Accountability · `inkbytes.org →`

**Footer columns (ES):** Producto / Compañía / Confianza / El lector · bottom: Precisión · Transparencia · Responsabilidad

**Cookie banner (privacy-first):**
- EN: "We use only essential cookies. No tracking, no ad profiles, no sold data." · *Got it* · Privacy
- ES: "Solo usamos cookies esenciales. Sin rastreo, sin perfiles publicitarios." · *Entendido* · Privacidad

---

## Pages & SEO

| Route | File | WP template | `<title>` | Meta description |
|---|---|---|---|---|
| `/` | `index.html` | `front-page.php` | InkBytes — Your Source for Comprehensive News | One elegant page per event, synthesized from many trusted sources. Skip the noise. Ad-free, citation-traceable news. $9/month. |
| `/how-it-works` | `how-it-works.html` | `page.php` | How InkBytes Works — Multi-Source News Synthesis | A reproducible five-stage pipeline — collect, enrich, cluster, synthesize, verify — with a hard ≥2-source rule. Not a wrapper over a chatbot. |
| `/why` | `why.html` | `page.php` | Why InkBytes — Unbiased, Multi-Source News | The gap between aggregators, chatbots, and reading it all yourself. Synthesis you can trust because you can check the sources. |
| `/features` | `features.html` | `page.php` | Features — InkBytes | Cited claims, entity context, bilingual coverage, no ads, installable app, and a grounded corpus assistant. |
| `/pricing` | `pricing.html` | `page-pricing.php` | Pricing — InkBytes | One simple plan. Headlines free; full multi-source synthesis, citations, and entity context for $9/month. No ads, cancel anytime. |
| `/about` | `about.html` | `page.php` | About InkBytes | A paid, ad-free news reader. Each event gets one elegant, source-cited page. Built in the Dominican Republic — LATAM + global English coverage. |
| `/methodology` | `methodology.html` | `page.php` | Methodology & Trust — How InkBytes Sources and Verifies | Where our news comes from, the ≥2-source rule, how we avoid hallucination, how we handle bias, and how to report a correction. |
| `/desk` | `desk.html` | `home.php` (blog index) | The Desk — InkBytes Editorial & Analysis | Cited daily and weekly analysis across politics, world, business, technology, and more — plus methodology notes and product updates. |
| `/desk/{slug}` | `desk-rate-cuts.html` | `single.php` | {post title} — The Desk · InkBytes | {post dek} |
| `/contact` | `contact.html` | `page-contact.php` | Contact — InkBytes | Get in touch, report a correction, or reach us for press. |
| `/privacy` | `privacy.html` | `page.php` | Privacy Policy — InkBytes | What InkBytes collects, how we handle it, and the privacy-first posture behind the product. No selling data, minimal analytics. |
| `/terms` | `terms.html` | `page.php` | Terms of Service — InkBytes | Subscription terms, acceptable use, attribution to source content, disclaimers, and cancellation for InkBytes. |
| `/404` | `404.html` | `404.php` | Nothing here yet — InkBytes | (noindex) |

Spanish pairs live under `/es/…` (`es/index.html`, `es/about.html`, `es/methodology.html`,
`es/pricing.html`, `es/contact.html`) — same templates, `hreflang` EN⇄ES.

**On every page:** Open Graph (`og:title`, `og:description`, `og:type`, `og:url`) is set in `<head>`.
Add a branded `og:image` and the structured data at launch: `Organization` (name, logo,
founder Julián De La Rosa, sameAs) + `WebSite`+`SearchAction` on home; `BlogPosting`
(author, datePublished, citations) on Desk posts.

---

## Key copy per page (headline / lead / CTA)

The rest of each page's body is in the HTML, section-by-section, ready to lift into blocks.

- **Home** — H1 *One page worth twenty.* / Lead: the fragmentation pitch / CTA: *Start reading — $9/mo*
- **How it works** — H1 *A pipeline, not a chatbot.* / 5 stages (Collect→Enrich→Cluster→Synthesize→Verify) + the ≥2-source rule + "What we don't do"
- **Why** — H1 *The missing middle.* / comparison table + per-alternative breakdown + the edge
- **Features** — H1 *Built for people who need the whole story.* / 6 features
- **Pricing** — H1 *One simple plan. Skip the noise.* / Free vs Member $9/mo + full comparison + "Why paid?"
- **About** — H1 *A paid, ad-free reader…* / mission prose + values + InkPills→InkBytes lineage + founder
- **Methodology** — H1 *It isn't magic. It's traceable aggregation.* / ≥2-source + factuality + 8 trust sections + corrections
- **The Desk** — H1 *Cited analysis. No ads. Corrections in the open.* / featured + theme filter + posts + content types
- **Contact** — H1 *Get in touch.* / General · Corrections · Press + form
- **Privacy / Terms** — legal shells (need legal review before billing)

---

## Editorial standards (apply to every Desk post)
Every external claim cited · No ads / sponsored / affiliate · Corrections in the open ·
Byline + date on everything · Plain, sober voice.
