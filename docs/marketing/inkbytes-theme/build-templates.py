#!/usr/bin/env python3
"""
Generate InkBytes WordPress page templates from the static marketing site.

For each EN page in ../site/*.html: extract the <main>…</main> body, rewrite the
inter-page *.html links to WordPress permalink paths, swap the DS `data-widget`
divs for get_template_part() calls, and wrap in get_header()/get_footer().

Run from this directory:  python3 build-templates.py
Idempotent — safe to re-run after editing the source HTML.
EN only; the Spanish /es/ pages are a documented fast-follow (needs Polylang).
"""
import re
import pathlib

SRC = pathlib.Path(__file__).parent.parent / "site"
DST = pathlib.Path(__file__).parent / "inkbytes"

# source file -> (target template, human label)
PAGES = {
    "index.html":          ("front-page.php",        "Front page (home)"),
    "how-it-works.html":   ("page-how-it-works.php", "How it works"),
    "why.html":            ("page-why.php",           "Why InkBytes"),
    "features.html":       ("page-features.php",      "Features"),
    "pricing.html":        ("page-pricing.php",       "Pricing"),
    "methodology.html":    ("page-methodology.php",   "Methodology & Trust"),
    "about.html":          ("page-about.php",         "About"),
    "contact.html":        ("page-contact.php",       "Contact"),
    "privacy.html":        ("page-privacy.php",       "Privacy Policy"),
    "terms.html":          ("page-terms.php",         "Terms of Service"),
    "desk.html":           ("page-desk.php",          "The Desk (index)"),
    "desk-rate-cuts.html": ("page-rate-cuts.php",     "The Desk — post"),
    "404.html":            ("404.php",                "404 Not Found"),
}

# href rewrites — most specific first. Reader URL (inkbytes.org) is left intact.
LINKS = [
    ('href="index.html#how"',      'href="/#how"'),
    ('href="index.html#why"',      'href="/#why"'),
    ('href="index.html#features"', 'href="/#features"'),
    ('href="index.html#pricing"',  'href="/#pricing"'),
    ('href="index.html#audience"', 'href="/#audience"'),
    ('href="desk-rate-cuts.html"', 'href="/desk/rate-cuts/"'),
    ('href="how-it-works.html"',   'href="/how-it-works/"'),
    ('href="methodology.html"',    'href="/methodology/"'),
    ('href="features.html"',       'href="/features/"'),
    ('href="pricing.html"',        'href="/pricing/"'),
    ('href="contact.html"',        'href="/contact/"'),
    ('href="privacy.html"',        'href="/privacy/"'),
    ('href="terms.html"',          'href="/terms/"'),
    ('href="about.html"',          'href="/about/"'),
    ('href="desk.html"',           'href="/desk/"'),
    ('href="why.html"',            'href="/why/"'),
    ('href="index.html"',          'href="/"'),
]

MAIN_RE = re.compile(r"(<main>.*</main>)", re.S)
WIDGET_RE = re.compile(r'<div data-widget="([a-z-]+)"></div>')

HEADER = (
    "<?php\n"
    "/**\n"
    " * {label} — generated from site/{src} by build-templates.py.\n"
    " * Re-run the script after editing the source HTML, or edit here directly.\n"
    " *\n"
    " * @package InkBytes\n"
    " */\n"
    "if ( ! defined( 'ABSPATH' ) ) {{ exit; }}\n"
    "get_header();\n"
    "?>\n"
)
FOOTER = "\n<?php\nget_footer();\n"


def widget_sub(m):
    return "<?php get_template_part( 'parts/widget', '%s' ); ?>" % m.group(1)


def main():
    DST.mkdir(parents=True, exist_ok=True)
    for src_name, (tgt_name, label) in PAGES.items():
        src = SRC / src_name
        html = src.read_text(encoding="utf-8")
        m = MAIN_RE.search(html)
        if not m:
            print("!! no <main> in", src_name)
            continue
        body = m.group(1)
        for a, b in LINKS:
            body = body.replace(a, b)
        # Relative asset src (illustrations) -> theme URI, else they 404 on subpages.
        body = re.sub(
            r'src="assets/([^"]+)"',
            lambda mm: 'src="<?php echo esc_url( get_theme_file_uri( \'assets/%s\' ) ); ?>"' % mm.group(1),
            body,
        )
        body = WIDGET_RE.sub(widget_sub, body)
        out = HEADER.format(label=label, src=src_name) + body + FOOTER
        (DST / tgt_name).write_text(out, encoding="utf-8")
        print("  wrote", tgt_name, "(%d bytes)" % len(out))


if __name__ == "__main__":
    main()
