# InkBytes WordPress theme (v2 — multi-page)

The marketing theme for **inkbytes.news**, built from the static design-system site
in [`../site/`](../site/). Multi-page, self-contained, classic WordPress theme.

## Where it runs
`inkbytes.news` WordPress on the **Hostinger box** (`82.112.250.139`,
`/docker/wordpress-yybr`, behind Traefik + LE cert) — the same box as Ollama, NOT
the DO droplet. This directory is the **source of record**; deployed manually
(not in CI).

## Design-system note (important)
The `../site/` pages were authored on the **InkBytes Design System** and load a
compiled DS bundle (`_ds/inkbytes-design-system-…/styles.css` + `_ds_bundle.js`)
plus React + Babel at runtime. **That bundle is not vendored in the repo**, so this
theme is deliberately **self-contained** instead:

- **DS base tokens are reconstructed** in `style.css` (`:root`) — fonts
  (Archivo / Spectral / IBM Plex Mono), the ink/paper/surface/line palette,
  factuality + entity colors, shadows, focus ring. `assets/site.css` (the real
  design layer, copied verbatim) consumes them.
- **The DS React widgets are rendered as static HTML** (`parts/widget-*.php` +
  `assets/widgets.css`) — no React/Babel/CDN at runtime. Better for a marketing
  site's performance and SEO.
- **The chrome (header/footer/cookie) is server-rendered PHP** (`header.php`,
  `footer.php`) translated from `assets/chrome.jsx` — works without JS.

If you later want byte-fidelity with the DS bundle, drop `_ds/` into the theme,
enqueue it, and swap the static parts back to JSX islands. The static approach is
the recommended default.

## Layout
```
inkbytes/
├── style.css              theme header + reconstructed DS :root tokens
├── functions.php          enqueue (fonts→style.css→site.css→widgets.css), reader const,
│                          ib_url()/ib_seo()/ib_outlet_logo()/ib_sparkline() helpers
├── header.php             <head> (per-route <title>/OG from ib_seo), sprite, sticky nav
├── footer.php             footer columns + foot-bar + privacy-first cookie banner
├── sprite.php             #ink brand mark symbol
├── front-page.php         home (generated from site/index.html)
├── page-{slug}.php        how-it-works, why, features, pricing, methodology, about,
│                          contact, privacy, terms, desk, rate-cuts (generated)
├── 404.php                generated from site/404.html
├── index.php              fallback (search/archives)
├── assets/site.css        the design layer (verbatim copy of site/assets/site.css)
├── assets/widgets.css     static shims for the DS widget components
├── assets/illustrations/  the 7 SVG illustrations
└── parts/widget-*.php     static event-mock / two-source / fact-spectrum
```

## Mobile
`site.css` ships desktop-first breakpoints but hides the nav links below 840px with
no menu. The theme adds a **hamburger + drop-down panel** (`header.php` markup +
toggle script; styles in `assets/widgets.css` under "Mobile adaptation") — below
840px the bar shows brand + hamburger, and the panel holds the nav links + the
reader CTA. Plus tighter section/`.wrap` spacing and full-width CTAs on phones
(≤640/≤560px). The header `<title>`/nav are server-rendered, so this all works
without JS except the toggle. Verified at 390px (home, menu, methodology).

## Regenerate the page templates
The `page-*.php` / `front-page.php` / `404.php` are generated from `../site/*.html`:
```bash
cd docs/marketing/inkbytes-theme
python3 build-templates.py     # extracts <main>, rewrites links → WP permalinks,
                               # swaps data-widget divs → get_template_part()
```
Edit the source HTML in `../site/` and re-run, or edit the generated PHP directly.

## Deploy
```bash
cd docs/marketing/inkbytes-theme
find inkbytes -exec xattr -c {} \; 2>/dev/null          # strip macOS quarantine xattr
tar -cf /tmp/ib-theme.tar inkbytes
scp -i ~/.ssh/id_ed25519 /tmp/ib-theme.tar root@82.112.250.139:/tmp/
ssh -i ~/.ssh/id_ed25519 root@82.112.250.139 '
  rm -rf /tmp/t && mkdir /tmp/t && tar -xf /tmp/ib-theme.tar -C /tmp/t
  docker exec wordpress-yybr-wordpress-1 sh -c "rm -rf /var/www/html/wp-content/themes/inkbytes"
  docker cp /tmp/t/inkbytes/. wordpress-yybr-wordpress-1:/var/www/html/wp-content/themes/inkbytes/
  docker exec wordpress-yybr-wordpress-1 chown -R www-data:www-data /var/www/html/wp-content/themes/inkbytes'
```
⚠️ `docker cp` of a tar stream straight from macOS fails on the `com.apple.quarantine`
xattr — strip it first (above) or go via scp + Linux-side extract as shown.
⚠️ Use `docker cp` / `docker exec -i` — a bare `docker exec … 'cat > file'` (no `-i`)
discards stdin and writes a 0-byte file.

## Create the Pages (first deploy only)
`page-{slug}.php` templates only resolve if a Page with that slug exists. The
`seed-pages.php` script creates them all (idempotent), sets pretty permalinks, and
creates `/desk/rate-cuts/` as a child of `/desk/`:
```bash
cat seed-pages.php | ssh -i ~/.ssh/id_ed25519 root@82.112.250.139 \
  'docker exec -i wordpress-yybr-wordpress-1 sh -c "cat > /tmp/seed-pages.php"'
ssh -i ~/.ssh/id_ed25519 root@82.112.250.139 \
  'docker exec wordpress-yybr-wordpress-1 php /tmp/seed-pages.php'
```
The home page needs no Page — `front-page.php` auto-renders it.

## Routes (all verified live, HTTP 200)
`/` · `/how-it-works/` · `/why/` · `/features/` · `/pricing/` · `/methodology/` ·
`/about/` · `/contact/` · `/privacy/` · `/terms/` · `/desk/` · `/desk/rate-cuts/` ·
404 for anything else.

## Not yet (fast-follow)
- **Spanish `/es/…`** pages — `site/es/*.html` exist and `chrome.jsx` carries the ES
  i18n; WordPress bilingual needs **Polylang/WPML** + page-pair linking + `hreflang`.
  The theme is EN-only for now.
- **Contact form** is inert (`onsubmit=return false`) — wire to an email handler / form plugin.
- **The Desk** is static Pages; convert to real WP posts (`home.php` + `single.php`) when the editorial cadence starts.
- Branded `og:image` + `Organization`/`WebSite`/`BlogPosting` structured data.

## Revert to stock theme
`UPDATE wp_options SET option_value='twentytwentyfive' WHERE option_name IN ('template','stylesheet');`
