/* feed.jsx — Header, Feed (3 layouts), StoryCard. */

(function injectFeedCSS() {
  const css = `
  /* feed top bar */
  .feed-top {
    display:flex; align-items:flex-end; justify-content:space-between; gap:18px;
    padding:34px 0 18px; border-bottom:1px solid var(--line);
  }
  .feed-title { font-family:var(--hl-font); font-weight:800; font-size:30px; letter-spacing:-0.02em; line-height:1; }
  .feed-dateline { font-family:"IBM Plex Mono",monospace; font-size:12px; color:var(--muted); margin-top:9px; letter-spacing:.02em; }
  .feed-filter { display:flex; gap:8px; flex-wrap:wrap; }
  .chip {
    appearance:none; border:1px solid var(--line); background:var(--surface);
    color:var(--ink-2); font-size:13px; font-weight:500; padding:7px 14px; border-radius:999px;
    cursor:pointer; transition:.14s; white-space:nowrap;
  }
  .chip:hover { border-color:var(--ink-3); }
  .chip.active { background:var(--ink); border-color:var(--ink); color:#fff; }
  .chip.graph-cta { display:inline-flex; align-items:center; border-color:color-mix(in oklab, var(--accent) 38%, var(--line)); color:var(--accent); font-weight:600; }
  .chip.graph-cta:hover { background:color-mix(in oklab, var(--accent) 8%, var(--surface)); border-color:var(--accent); }

  /* story card base */
  .story { cursor:pointer; }
  .story .kicker-row { display:flex; align-items:center; gap:12px; margin-bottom:12px; }
  .story h2, .story h3 { font-family:var(--hl-font); margin:0; color:var(--ink); letter-spacing:-0.02em; line-height:1.04; text-wrap:balance; transition:color .15s; }
  .story p.dek { color:var(--ink-2); margin:12px 0 0; line-height:1.5; text-wrap:pretty; }
  .story:hover h2, .story:hover h3 { color:color-mix(in oklab, var(--accent) 88%, var(--ink)); }

  /* hero */
  .hero { padding:40px 0 34px; border-bottom:1px solid var(--line); display:grid; gap:26px; grid-template-columns: 1fr; }
  .hero h2 { font-weight:800; font-size:calc(clamp(2.1rem, 4.6vw, 3.9rem) * var(--hl-scale, 1)); }
  .hero p.dek { font-size:clamp(1rem, 1.4vw, 1.22rem); max-width:46ch; }
  .hero .hero-foot { display:flex; align-items:center; flex-wrap:wrap; gap:14px 22px; margin-top:6px; }
  .hero-cov-card {
    align-self:start; border:1px solid var(--line); border-radius:var(--radius);
    background:var(--surface); padding:18px 20px; min-width:210px;
  }
  .hero-cov-card .lbl { font-family:"IBM Plex Mono",monospace; font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
  .hero-cov-card .big { font-family:var(--hl-font); font-weight:800; font-size:34px; letter-spacing:-0.02em; line-height:1; margin-top:8px; }
  @media (min-width: 900px) {
    .hero { grid-template-columns: minmax(0,1fr) 250px; align-items:end; gap:40px; }
  }

  /* grid of cards */
  .grid { display:grid; gap:1px; background:var(--line); border:1px solid var(--line);
    border-radius:var(--radius); overflow:hidden; margin:30px 0 60px; }
  .grid.cols-3 { grid-template-columns: repeat(3, 1fr); }
  .grid.cols-2 { grid-template-columns: repeat(2, 1fr); }
  .card { background:var(--surface); padding:24px 24px 22px; display:flex; flex-direction:column; min-height:230px; }
  .card h3 { font-weight:700; font-size:21px; }
  .card .dek { font-size:14.5px; -webkit-line-clamp:2; line-clamp:2; display:-webkit-box; -webkit-box-orient:vertical; overflow:hidden; }
  .card .card-foot { margin-top:auto; padding-top:18px; }
  .card .card-foot .meta-row { gap:8px 14px; }

  /* uniform grid layout (no hero) — make lead span 2 */
  .grid.uniform .card.lead { grid-column: span 2; min-height:auto; }
  .grid.uniform .card.lead h3 { font-size:30px; font-weight:800; }
  .grid.uniform .card.lead .lead-cov { margin-top:18px; display:flex; align-items:center; gap:12px; }
  .grid.uniform .card.lead .lead-cov .cov-num { font-size:14px; }

  /* stream rows */
  .stream { margin:18px 0 60px; }
  .row {
    display:grid; grid-template-columns: 84px 1fr auto; gap:26px; align-items:center;
    padding:24px 4px; border-bottom:1px solid var(--line); cursor:pointer;
  }
  .row:hover { background:var(--surface); }
  .row .row-when { font-family:"IBM Plex Mono",monospace; font-size:12px; color:var(--muted); }
  .row .row-cat { font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--accent); margin-bottom:6px; }
  .row h3 { font-weight:700; font-size:22px; }
  .row .dek { font-size:14px; -webkit-line-clamp:1; line-clamp:1; display:-webkit-box; -webkit-box-orient:vertical; overflow:hidden; }
  .row-right { display:flex; flex-direction:column; align-items:flex-end; gap:10px; min-width:170px; }

  /* density */
  body.compact .card { padding:18px 18px 16px; min-height:auto; }
  body.compact .card .dek { display:none; }
  body.compact .hero { padding:28px 0 24px; }
  body.compact .row { padding:16px 4px; }

  @media (max-width: 900px) {
    .grid.cols-3, .grid.cols-2 { grid-template-columns: 1fr; }
    .grid.uniform .card.lead { grid-column: span 1; }
    .row { grid-template-columns: 1fr; gap:12px; padding:20px 2px; }
    .row .row-when { display:none; }
    .row-right { flex-direction:row; align-items:center; justify-content:space-between; min-width:0; width:100%; }
  }
  @media (max-width: 720px) {
    .feed-top { flex-direction:column; align-items:flex-start; gap:14px; }
    .feed-title { font-size:24px; }
  }
  `;
  const s = document.createElement("style");
  s.textContent = css;
  document.head.appendChild(s);
})();

function Header({ route, onHome, onGraph, t }) {
  return (
    <header className="ib-header">
      <div className="ib-header-inner">
        <div className="ib-logo" onClick={onHome}>InkBytes<span className="dot">.</span></div>
        <div className="ib-search" onClick={onHome}>
          <Icon name="search" size={15} />
          <span>Search events</span>
        </div>
        <nav className="ib-nav">
          <a className={route === "feed" ? "active" : ""} onClick={onHome}>News</a>
          <a className={route === "graph" ? "active" : ""} onClick={() => onGraph(null)}>Entities</a>
          <a>About</a>
        </nav>
      </div>
    </header>
  );
}

function StoryFoot({ ev, factVariant, showCov = true }) {
  return (
    <div className="meta-row">
      <SourceStack ids={ev.sources} size={22} max={4} />
      <MetaSep />
      <Factuality fact={ev.factuality} variant={factVariant} />
      {showCov && <><MetaSep /><Coverage coverage={ev.coverage} showSpark={false} /></>}
      <MetaSep />
      <span className="meta-time">{ev.updatedShort} ago</span>
    </div>
  );
}

function Hero({ ev, onOpen, t }) {
  return (
    <section className="hero" onClick={() => onOpen(ev.id)}>
      <div className="story" style={{ minWidth: 0 }}>
        <div className="kicker-row">
          <span className="kicker">{ev.category}</span>
          {ev.developing && <span className="live"><span className="pulse" />Developing</span>}
        </div>
        <h2>{ev.headline}</h2>
        <p className="dek">{ev.dek}</p>
        <div className="hero-foot">
          <SourceStack ids={ev.sources} size={26} max={5} />
          <MetaSep />
          <Factuality fact={ev.factuality} variant={t.factualityStyle} />
          <MetaSep />
          <span className="meta-time"><Icon name="clock" size={14} /> {ev.updated.replace("Updated ", "")}</span>
        </div>
      </div>
      <div className="hero-cov-card" onClick={(e) => { e.stopPropagation(); onOpen(ev.id); }}>
        <div className="lbl">Coverage</div>
        <div className="big">{ev.coverage.articles}</div>
        <div className="dim" style={{ fontSize: 13, margin: "2px 0 14px" }}>articles · peak {ev.coverage.peak}</div>
        <Sparkline data={ev.coverage.spark} w={206} h={44} />
      </div>
    </section>
  );
}

function Card({ ev, onOpen, lead, t }) {
  return (
    <article className={"story card" + (lead ? " lead" : "")} onClick={() => onOpen(ev.id)}>
      <div className="kicker-row">
        <span className="kicker">{ev.category}</span>
        {ev.developing && <span className="live"><span className="pulse" />Live</span>}
      </div>
      <h3>{ev.headline}</h3>
      {ev.dek && <p className="dek">{ev.dek}</p>}
      {lead && (
        <div className="lead-cov">
          <Sparkline data={ev.coverage.spark} w={120} h={26} />
          <span className="cov-num">{ev.coverage.articles} <span style={{ color: "var(--muted)", fontWeight: 500 }}>articles · peak {ev.coverage.peak}</span></span>
        </div>
      )}
      <div className="card-foot">
        <StoryFoot ev={ev} factVariant={t.factualityStyle === "pill" ? "score" : t.factualityStyle} showCov={false} />
      </div>
    </article>
  );
}

function Row({ ev, onOpen, t }) {
  return (
    <article className="row story" onClick={() => onOpen(ev.id)}>
      <div className="row-when">{ev.updatedShort} ago</div>
      <div style={{ minWidth: 0 }}>
        <div className="row-cat">{ev.category}{ev.developing ? " · Developing" : ""}</div>
        <h3>{ev.headline}</h3>
        {ev.dek && <p className="dek dim">{ev.dek}</p>}
      </div>
      <div className="row-right">
        <SourceStack ids={ev.sources} size={22} max={4} />
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Factuality fact={ev.factuality} variant={t.factualityStyle === "pill" ? "bar" : t.factualityStyle} />
          <Coverage coverage={ev.coverage} showSpark={true} />
        </div>
      </div>
    </article>
  );
}

function Feed({ events, onOpen, onGraph, t }) {
  const [cat, setCat] = React.useState("All");
  const cats = ["All", ...Array.from(new Set(events.map((e) => e.category)))];
  const list = cat === "All" ? events : events.filter((e) => e.category === cat);
  const lead = list[0];
  const rest = list.slice(1);

  const today = new Date(2026, 5, 3).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });

  return (
    <main className="ib-shell">
      <div className="feed-top">
        <div>
          <div className="feed-title">Today’s events</div>
          <div className="feed-dateline">{today.toUpperCase()} · {events.length} tracked</div>
        </div>
        <div className="feed-filter">
          {cats.map((c) => (
            <button key={c} className={"chip" + (c === cat ? " active" : "")} onClick={() => setCat(c)}>{c}</button>
          ))}
          <button className="chip graph-cta" onClick={() => onGraph && onGraph(null)}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: 6 }}><circle cx="5" cy="6" r="2.4"/><circle cx="19" cy="7" r="2.4"/><circle cx="12" cy="18" r="2.4"/><path d="M7 7 17 7M6.5 8 11 16M17.5 9 13 16"/></svg>
            Entity graph
          </button>
        </div>
      </div>

      {t.feedLayout === "editorial" && (
        <>
          {lead && <Hero ev={lead} onOpen={onOpen} t={t} />}
          <div className="grid cols-3">
            {rest.map((ev) => <Card key={ev.id} ev={ev} onOpen={onOpen} t={t} />)}
          </div>
        </>
      )}

      {t.feedLayout === "grid" && (
        <div className="grid cols-2 uniform">
          {list.map((ev, i) => <Card key={ev.id} ev={ev} onOpen={onOpen} lead={i === 0} t={t} />)}
        </div>
      )}

      {t.feedLayout === "stream" && (
        <div className="stream">
          {list.map((ev) => <Row key={ev.id} ev={ev} onOpen={onOpen} t={t} />)}
        </div>
      )}
    </main>
  );
}

Object.assign(window, { Header, Feed });
