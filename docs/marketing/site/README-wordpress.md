# InkBytes marketing site (inkbytes.news) — build & WordPress handoff

Phase-1 marketing site, **separate from the reader app** (`inkbytes.org`). Built on the
bound **InkBytes Design System** (tokens + components loaded from `../_ds/…`), in the
**blend** register: design-system foundations (Archivo / Spectral / IBM Plex Mono type,
factuality semantics, real DS components) with the marketing brand's **coral accent**
(`#e05c5c`) and **navy editorial bands**.

## Pages (one HTML file per route)
| File | Route | WP template |
|---|---|---|
| `index.html` | `/` | `front-page.php` / `page-home.php` |
| `how-it-works.html` | `/how-it-works` | `page.php` |
| `why.html` | `/why` | `page.php` |
| `features.html` | `/features` | `page.php` |
| `about.html` | `/about` | `page-about.php` |
| `methodology.html` | `/methodology` | `page-methodology.php` |
| `pricing.html` | `/pricing` | `page-pricing.php` |
| `desk.html` | `/desk` | `home.php` (blog index) |
| `desk-rate-cuts.html` | `/desk/{slug}` | `single.php` |
| `contact.html` | `/contact` | `page-contact.php` |
| `privacy.html` · `terms.html` | `/privacy` · `/terms` | `page.php` |
| `404.html` | (not found) | `404.php` |
| `es/*.html` | `/es/…` | same templates (WPML/Polylang) |

**Bilingual:** EN pages sit at the root; Spanish pairs live in `es/`. The header carries a
language toggle (driven by `<body data-alt>`), and `chrome.jsx` swaps nav/footer/CTA strings
off `<body data-lang>`. A privacy-first cookie banner is injected site-wide.

See `WORDPRESS-CONTENT.md` for the full per-page SEO + content export.

## Shared "theme" pieces (→ template parts)
- `assets/site.css` — the whole design layer, built on DS tokens. → `style.css` / enqueued.
- `assets/chrome.jsx` — **Header + Footer**, rendered into `#ib-header` / `#ib-footer` / `#ib-footbar`.
  → `header.php` + `footer.php`. Nav array and the **`READER_URL`** constant live at the top
  (WP: theme constant `INKBYTES_READER_URL`). Active nav state reads `<body data-page="…">`.
- `assets/widgets.jsx` — product-component islands (hero event mock, factuality spectrum,
  source stack) composed from real DS components. Mount points are `<div data-widget="…">`.
- `assets/sprite.js` — injects the InkBytes `#ink` brand mark.

## Per-page content & SEO
Each file's `<head>` carries its own `<title>`, meta description, and Open Graph tags
(verbatim from the content spec). Body copy is inline semantic HTML → maps directly to
WP page content / blocks.

## CTAs
Every "Start reading" points to `https://inkbytes.org` (the reader). Swap the one
`READER_URL` constant in `chrome.jsx` (and the inline CTA hrefs) when checkout ships.

## Load order (must hold when porting)
React → ReactDOM → `_ds_bundle.js` → Babel, then `chrome.jsx` (plain script) and
`widgets.jsx` (`type="text/babel"`). DS components are on `window.InkBytesDesignSystem_119654`.

## Not yet built
FAQ page, `/desk/{category}` archives + more sample posts, newsletter capture, ES versions of
the deeper pages (How it works · Why · Features · Desk · legal), and a branded `og:image`.
The legal pages are shells pending a real legal review before billing.
