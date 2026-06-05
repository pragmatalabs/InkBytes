/* event.jsx — full event/story page. */

(function injectEventCSS() {
  const css = `
  .ev-wrap { max-width: 760px; margin: 0 auto; padding: 0 28px; }
  .back {
    display:inline-flex; align-items:center; gap:9px; margin:38px 0 30px;
    font-size:14.5px; font-weight:500; color:var(--muted); cursor:pointer; transition:.15s;
  }
  .back:hover { color:var(--ink); }
  .ev-sup { display:flex; align-items:center; gap:12px; color:var(--muted); font-size:14px; margin-bottom:18px; }
  .ev-sup .globe { display:inline-flex; align-items:center; gap:8px; }
  .ev-h1 {
    font-family:var(--hl-font); font-weight:800; letter-spacing:-0.025em; line-height:1.03;
    font-size:calc(clamp(2rem, 4.4vw, 3.05rem) * var(--hl-scale, 1)); margin:0 0 22px; color:var(--ink); text-wrap:balance;
  }
  .ev-tags { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:34px; }

  /* credibility strip */
  .cred {
    display:grid; grid-template-columns: repeat(3, 1fr); gap:1px;
    background:var(--line); border:1px solid var(--line); border-radius:var(--radius);
    overflow:hidden; margin-bottom:40px;
  }
  .cred .cell { background:var(--surface); padding:18px 20px; }
  .cred .clbl { font-family:"IBM Plex Mono",monospace; font-size:10.5px; letter-spacing:.09em; text-transform:uppercase; color:var(--muted); display:flex; align-items:center; gap:7px; }
  .cred .cval { font-family:var(--hl-font); font-weight:800; font-size:30px; letter-spacing:-0.02em; line-height:1; margin-top:11px; display:flex; align-items:baseline; gap:8px; }
  .cred .cval small { font-size:14px; font-weight:600; color:var(--muted); letter-spacing:0; }
  .cred .csub { margin-top:9px; }
  .cred .stack-row { display:flex; align-items:center; gap:0; margin-top:12px; }

  /* article body */
  .ev-body { font-size:19px; line-height:1.62; color:var(--ink-2); font-family:var(--article-font, var(--body-font)); }
  .ev-body p { margin:0 0 26px; text-wrap:pretty; }
  .ev-body p:first-child::first-letter {
    font-family:var(--hl-font); font-weight:800; color:var(--ink);
    float:left; font-size:3.6em; line-height:.78; padding:6px 12px 0 0;
  }
  .srclab {
    font-family:"IBM Plex Mono",monospace; font-size:11.5px; font-weight:500;
    color:var(--muted); background:var(--bg-2); border-radius:5px;
    padding:2px 7px; margin:0 7px; white-space:nowrap; letter-spacing:.01em;
    position:relative; top:-1px;
  }

  .ev-rule { height:1px; background:var(--line); margin:46px 0 0; }
  .sec-head { display:flex; align-items:baseline; justify-content:space-between; margin:46px 0 24px; }
  .sec-head h4 { font-family:"IBM Plex Mono",monospace; font-size:12px; font-weight:600; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin:0; }
  .sec-head .count { font-size:13px; color:var(--muted); }

  /* timeline */
  .tl { position:relative; margin:0 0 8px; padding-left:30px; }
  .tl::before { content:""; position:absolute; left:6px; top:6px; bottom:14px; width:2px; background:var(--line); }
  .tl-item { position:relative; padding:0 0 30px; }
  .tl-item:last-child { padding-bottom:0; }
  .tl-dot { position:absolute; left:-30px; top:3px; width:14px; height:14px; border-radius:50%;
    background:var(--surface); border:2.5px solid var(--muted-2); }
  .tl-item.now .tl-dot { border-color:var(--accent); background:var(--accent); box-shadow:0 0 0 4px color-mix(in oklab, var(--accent) 16%, transparent); }
  .tl-time { font-family:"IBM Plex Mono",monospace; font-size:11.5px; letter-spacing:.04em; text-transform:uppercase; color:var(--accent); font-weight:600; }
  .tl-title { font-family:var(--hl-font); font-weight:700; font-size:17px; color:var(--ink); margin:5px 0 4px; letter-spacing:-0.01em; }
  .tl-detail { font-size:15px; line-height:1.5; color:var(--ink-2); margin:0; }

  /* sources / quotes */
  .quotes { display:grid; grid-template-columns: repeat(2, 1fr); gap:14px; margin-bottom:30px; }
  .qcard { border:1px solid var(--line); border-radius:12px; background:var(--surface); padding:18px 18px 20px;
    display:flex; flex-direction:column; gap:12px; transition:.15s; cursor:pointer; }
  .qcard:hover { border-color:var(--ink-3); transform:translateY(-1px); box-shadow:0 6px 22px -14px rgba(0,0,0,.3); }
  .qcard-top { display:flex; align-items:center; gap:10px; }
  .qcard-name { font-weight:600; font-size:14px; color:var(--ink); flex:1; }
  .qcard-quote { font-family:"Spectral",Georgia,serif; font-style:italic; font-size:15.5px; line-height:1.5; color:var(--ink-2); margin:0; }
  .ev-foot { padding:50px 0 90px; text-align:center; color:var(--muted-2); font-size:13px; font-family:"IBM Plex Mono",monospace; }

  @media (max-width:720px){
    .ev-wrap { padding:0 16px; }
    .cred { grid-template-columns:1fr; }
    .quotes { grid-template-columns:1fr; }
    .ev-body { font-size:17.5px; }
  }
  `;
  const s = document.createElement("style");
  s.textContent = css;
  document.head.appendChild(s);
})();

function Paragraph({ segs }) {
  return (
    <p>
      {segs.map((seg, i) =>
        seg.src
          ? <span key={i} className="srclab">Source: {seg.src}</span>
          : <React.Fragment key={i}>{seg.t}</React.Fragment>
      )}
    </p>
  );
}

function CredStrip({ ev, t }) {
  const fc = { High: "var(--fact-high)", Mixed: "var(--fact-mixed)", Low: "var(--fact-low)" }[ev.factuality.label];
  return (
    <div className="cred">
      <div className="cell">
        <div className="clbl"><Icon name="layers" size={13} /> Sources</div>
        <div className="cval">{ev.sources.length}<small>outlets</small></div>
        <div className="stack-row"><SourceStack ids={ev.sources} size={24} max={6} showCount={false} /></div>
      </div>
      <div className="cell">
        <div className="clbl"><Icon name="shield" size={13} /> Factuality</div>
        <div className="cval" style={{ color: fc }}>{ev.factuality.label}</div>
        <div className="csub"><Factuality fact={ev.factuality} variant="bar" /></div>
      </div>
      <div className="cell">
        <div className="clbl"><Icon name="trend" size={13} /> Coverage</div>
        <div className="cval">{ev.coverage.articles}<small>articles</small></div>
        <div className="csub" style={{ marginTop: 8 }}><Sparkline data={ev.coverage.spark} w={150} h={28} /></div>
      </div>
    </div>
  );
}

function Timeline({ items }) {
  return (
    <div className="tl">
      {items.map((it, i) => (
        <div key={i} className={"tl-item" + (i === items.length - 1 ? " now" : "")}>
          <span className="tl-dot" />
          <div className="tl-time">{it.time}</div>
          <div className="tl-title">{it.title}</div>
          <p className="tl-detail">{it.detail}</p>
        </div>
      ))}
    </div>
  );
}

function EventPage({ ev, onBack, onEntity, t }) {
  const { OUTLETS } = window.INKBYTES;
  return (
    <main className="ev-wrap">
      <div className="back" onClick={onBack}><Icon name="arrow-left" size={17} /> All events</div>

      <div className="ev-sup">
        <span className="globe"><Icon name="globe" size={15} /> {ev.sources.length} sources</span>
        <MetaSep />
        <span>{ev.updated}</span>
        {ev.developing && <span className="live" style={{ marginLeft: 2 }}><span className="pulse" />Developing</span>}
      </div>

      <h1 className="ev-h1">{ev.headline}</h1>

      <div className="ev-tags">
        {ev.tags.map((tag) => <span key={tag} className="tag" onClick={() => onEntity && onEntity(tag)}>{tag}</span>)}
      </div>

      <CredStrip ev={ev} t={t} />

      <div className="ev-body">
        {ev.body.map((segs, i) => <Paragraph key={i} segs={segs} />)}
      </div>

      <div className="sec-head"><h4>How this developed</h4><span className="count">{ev.timeline.length} updates</span></div>
      <Timeline items={ev.timeline} />

      <div className="ev-rule" />
      <div className="sec-head"><h4>Sources</h4><span className="count">{ev.quotes.length} quotes</span></div>
      <div className="quotes">
        {ev.quotes.map((q, i) => {
          const o = OUTLETS[q.outlet];
          return (
            <div key={i} className="qcard">
              <div className="qcard-top">
                <OutletLogo id={q.outlet} size={26} square />
                <span className="qcard-name">{o.name}</span>
                <Icon name="arrow-ur" size={16} color="var(--muted-2)" />
              </div>
              <p className="qcard-quote">“{q.text}”</p>
            </div>
          );
        })}
      </div>

      <div className="ev-foot">— end of coverage · InkBytes —</div>
    </main>
  );
}

Object.assign(window, { EventPage });
