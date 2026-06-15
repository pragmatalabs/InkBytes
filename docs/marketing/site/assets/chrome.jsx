/* ══════════════════════════════════════════════════════════════
   InkBytes marketing — shared chrome (Header + Footer + cookie)
   Bilingual (EN/ES). Reads <body data-lang> and <body data-alt>.
   Maps 1:1 to WP template parts (header.php / footer.php) + WPML/Polylang.
   ══════════════════════════════════════════════════════════════ */
(function () {
  const React = window.React;
  const ReactDOM = window.ReactDOM;
  const DS = window.InkBytesDesignSystem_119654 || {};
  const { Button } = DS;
  const h = React.createElement;

  // Single source of truth for the reader CTA (WP: theme constant INKBYTES_READER_URL)
  const READER_URL = "https://inkbytes.org";

  const LANG = (document.body.dataset.lang === "es") ? "es" : "en";
  const ALT = document.body.dataset.alt || "";

  const I18N = {
    en: {
      nav: [
        { label: "How it works", href: "how-it-works.html", key: "how" },
        { label: "Why InkBytes", href: "why.html",          key: "why" },
        { label: "Pricing",      href: "pricing.html",       key: "pricing" },
        { label: "The Desk",     href: "desk.html",          key: "desk" },
        { label: "Methodology",  href: "methodology.html",   key: "methodology" },
      ],
      cta: "Start reading",
      toggle: "ES", toggleTitle: "Leer en español",
      tag: "Your source for comprehensive news. One elegant page per event — every fact traceable to its source.",
      langLine: "EN · ES  ·  Built in the Dominican Republic",
      cols: [
        { title: "Product", links: [
          { label: "How it works", href: "how-it-works.html" },
          { label: "Why InkBytes", href: "why.html" },
          { label: "Features",     href: "features.html" },
          { label: "Pricing",      href: "pricing.html" },
        ]},
        { title: "Company", links: [
          { label: "About",   href: "about.html" },
          { label: "The Desk", href: "desk.html" },
          { label: "Contact", href: "contact.html" },
        ]},
        { title: "Trust", links: [
          { label: "Methodology", href: "methodology.html" },
          { label: "Privacy",     href: "privacy.html" },
          { label: "Terms",       href: "terms.html" },
        ]},
      ],
      readerCol: "The reader",
      readerNote: "The product lives at the reader app. Browse free.",
      values: "Accuracy · Transparency · Accountability",
      cookie: "We use only essential cookies. No tracking, no ad profiles, no sold data.",
      cookieBtn: "Got it",
      cookiePrivacy: "Privacy",
      cookiePrivacyHref: "privacy.html",
    },
    es: {
      nav: [
        { label: "Cómo funciona", href: "index.html#how",   key: "how" },
        { label: "Precios",       href: "pricing.html",      key: "pricing" },
        { label: "Sobre nosotros", href: "about.html",       key: "about" },
        { label: "Metodología",   href: "methodology.html",  key: "methodology" },
      ],
      cta: "Empezar a leer",
      toggle: "EN", toggleTitle: "Read in English",
      tag: "Tu fuente de noticias completas. Una página por evento — cada dato trazable hasta su fuente.",
      langLine: "EN · ES  ·  Hecho en República Dominicana",
      cols: [
        { title: "Producto", links: [
          { label: "Cómo funciona", href: "index.html#how" },
          { label: "Precios",       href: "pricing.html" },
        ]},
        { title: "Compañía", links: [
          { label: "Sobre nosotros", href: "about.html" },
          { label: "Contacto",       href: "contact.html" },
        ]},
        { title: "Confianza", links: [
          { label: "Metodología", href: "methodology.html" },
          { label: "Privacidad",  href: "../privacy.html" },
          { label: "Términos",    href: "../terms.html" },
        ]},
      ],
      readerCol: "El lector",
      readerNote: "El producto vive en el lector. Explóralo gratis.",
      values: "Precisión · Transparencia · Responsabilidad",
      cookie: "Solo usamos cookies esenciales. Sin rastreo, sin perfiles publicitarios.",
      cookieBtn: "Entendido",
      cookiePrivacy: "Privacidad",
      cookiePrivacyHref: "../privacy.html",
    },
  };
  const T = I18N[LANG];
  const homeHref = "index.html";

  function Mark({ size = 26 }) {
    return h("svg", { className: "brand-mark", width: size, height: size, viewBox: "0 0 1024 1024", "aria-hidden": "true" },
      h("use", { href: "#ink" }));
  }
  function Brand({ footer }) {
    return h("a", { className: "brand" + (footer ? " brand--footer" : ""), href: homeHref, "aria-label": "InkBytes home" },
      h(Mark, null),
      h("span", { className: "brand-word" }, "InkBytes"),
      h("span", { className: "brand-dot" })
    );
  }
  function CTA({ size = "md" }) {
    if (Button) return h(Button, { as: "a", href: READER_URL, variant: "primary", size }, T.cta);
    return h("a", { className: "ib-btn v-primary sz-" + size, href: READER_URL }, T.cta);
  }
  function LangToggle() {
    if (!ALT) return null;
    return h("a", { className: "lang-toggle", href: ALT, title: T.toggleTitle, "aria-label": T.toggleTitle },
      h("span", { className: "lang-cur" }, LANG.toUpperCase()),
      h("span", { className: "lang-sep" }, "/"),
      h("span", { className: "lang-alt" }, T.toggle));
  }

  function Header() {
    const page = (document.body.dataset.page || "");
    return h("div", { className: "wrap nav-inner" },
      h(Brand, null),
      h("nav", { className: "nav-links", "aria-label": "Primary" },
        T.nav.map((n) =>
          h("a", { key: n.key, href: n.href, className: "nav-link" + (page === n.key ? " is-active" : "") }, n.label)
        ),
        h(LangToggle, null),
        h("span", { className: "nav-cta" }, h(CTA, { size: "sm" }))
      )
    );
  }

  function FootCol({ title, links }) {
    return h("div", { className: "foot-col" },
      h("p", { className: "foot-col-title" }, title),
      h("ul", null, links.map((l, i) =>
        h("li", { key: i }, h("a", { href: l.href, className: "foot-link" }, l.label))
      ))
    );
  }
  function Footer() {
    return h("div", { className: "wrap foot-inner" },
      h("div", { className: "foot-brand" },
        h(Brand, { footer: true }),
        h("p", { className: "foot-tag" }, T.tag),
        h("p", { className: "foot-lang mono" }, T.langLine)
      ),
      h("div", { className: "foot-cols" },
        T.cols.map((c, i) => h(FootCol, { key: i, title: c.title, links: c.links })),
        h("div", { className: "foot-col foot-col--cta" },
          h("p", { className: "foot-col-title" }, T.readerCol),
          h("p", { className: "foot-reader-note" }, T.readerNote),
          h(CTA, { size: "sm" })
        )
      )
    );
  }
  function FootBar() {
    const year = new Date().getFullYear();
    return h("div", { className: "wrap foot-bar-inner" },
      h("span", null, "© " + year + " InkBytes"),
      h("span", { className: "foot-values mono" }, T.values),
      h("a", { href: READER_URL, className: "foot-link" }, "inkbytes.org →")
    );
  }

  /* privacy-first cookie banner */
  function CookieBanner() {
    let ok = false;
    try { ok = localStorage.getItem("ib-cookie-ok") === "1"; } catch (e) {}
    const [hidden, setHidden] = React.useState(ok);
    if (hidden) return null;
    const accept = () => { try { localStorage.setItem("ib-cookie-ok", "1"); } catch (e) {} setHidden(true); };
    return h("div", { className: "cookie-banner", role: "region", "aria-label": "Cookie notice" },
      h("p", { className: "cookie-text" }, T.cookie, " ",
        h("a", { href: T.cookiePrivacyHref, className: "cookie-link" }, T.cookiePrivacy)),
      h("button", { className: "ib-btn v-primary sz-sm", onClick: accept }, T.cookieBtn)
    );
  }

  function render(el, node) {
    if (!el) return;
    if (ReactDOM.createRoot) ReactDOM.createRoot(el).render(node);
    else ReactDOM.render(node, el);
  }
  function mount() {
    render(document.getElementById("ib-header"), h(Header, null));
    render(document.getElementById("ib-footer"), h(Footer, null));
    render(document.getElementById("ib-footbar"), h(FootBar, null));
    let cb = document.getElementById("ib-cookie");
    if (!cb) { cb = document.createElement("div"); cb.id = "ib-cookie"; document.body.appendChild(cb); }
    render(cb, h(CookieBanner, null));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
