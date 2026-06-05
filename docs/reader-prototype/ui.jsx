/* ui.jsx — shared atoms + icons. Exposes components on window. */

(function injectUICSS() {
  const css = `
  /* icons */
  .ic { display:inline-block; vertical-align:middle; flex:none; }

  /* outlet monogram */
  .outlet {
    display:inline-flex; align-items:center; justify-content:center;
    border-radius:50%; color:#fff; font-family:"Archivo",sans-serif;
    font-weight:700; line-height:1; flex:none;
    box-shadow: 0 0 0 2px var(--surface);
  }
  .outlet.square { border-radius:6px; }

  /* source stack */
  .src-stack { display:inline-flex; align-items:center; }
  .src-stack .outlet { margin-left:-7px; }
  .src-stack .outlet:first-child { margin-left:0; }
  .src-count { font-size:13px; font-weight:600; color:var(--ink-2); margin-left:9px; white-space:nowrap; }
  .src-count b { font-weight:700; }

  /* factuality */
  .fact { display:inline-flex; align-items:center; gap:7px; white-space:nowrap; }
  .fact-dot { width:8px; height:8px; border-radius:50%; flex:none; }
  .fact-label { font-size:12.5px; font-weight:600; letter-spacing:.01em; }
  .fact-pill {
    display:inline-flex; align-items:center; gap:7px;
    padding:4px 10px 4px 9px; border-radius:999px;
    border:1px solid var(--line); background:var(--surface);
    font-size:12px; font-weight:600; white-space:nowrap;
  }
  .fact-score-num { font-family:"IBM Plex Mono",monospace; font-weight:600; font-size:12px; }
  .fact-bar { width:54px; height:5px; border-radius:99px; background:var(--bg-2); overflow:hidden; }
  .fact-bar > i { display:block; height:100%; border-radius:99px; }

  /* coverage */
  .cov { display:inline-flex; align-items:center; gap:9px; white-space:nowrap; }
  .cov-num { font-size:13px; font-weight:600; color:var(--ink-2); }
  .cov-num span { color:var(--muted); font-weight:500; }

  /* meta row */
  .meta-row { display:flex; align-items:center; flex-wrap:wrap; gap:8px 18px; }
  .meta-sep { width:3px; height:3px; border-radius:50%; background:var(--muted-2); flex:none; }
  .meta-time { font-size:13px; color:var(--muted); font-weight:500; display:inline-flex; align-items:center; gap:6px; }

  /* tag chip */
  .tag {
    display:inline-flex; align-items:center; padding:6px 12px; border-radius:999px;
    border:1px solid var(--line); background:var(--surface);
    font-size:13px; font-weight:500; color:var(--ink-2); cursor:pointer; transition:.15s;
  }
  .tag:hover { border-color:var(--ink-3); color:var(--ink); }

  .live {
    display:inline-flex; align-items:center; gap:6px;
    font-family:"IBM Plex Mono",monospace; font-size:10.5px; font-weight:600;
    letter-spacing:.1em; text-transform:uppercase; color:var(--fact-low);
  }
  .live .pulse {
    width:7px; height:7px; border-radius:50%; background:var(--fact-low);
    box-shadow:0 0 0 0 color-mix(in oklab, var(--fact-low) 60%, transparent);
    animation: ibpulse 1.8s infinite;
  }
  @keyframes ibpulse {
    0% { box-shadow:0 0 0 0 color-mix(in oklab, var(--fact-low) 55%, transparent); }
    70% { box-shadow:0 0 0 7px transparent; }
    100% { box-shadow:0 0 0 0 transparent; }
  }
  `;
  const s = document.createElement("style");
  s.textContent = css;
  document.head.appendChild(s);
})();

const { OUTLETS } = window.INKBYTES;

function Icon({ name, size = 16, stroke = 2, color = "currentColor", style }) {
  const p = { width: size, height: size, viewBox: "0 0 24 24", fill: "none",
    stroke: color, strokeWidth: stroke, strokeLinecap: "round", strokeLinejoin: "round",
    className: "ic", style };
  switch (name) {
    case "arrow-left": return <svg {...p}><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>;
    case "globe": return <svg {...p}><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></svg>;
    case "clock": return <svg {...p}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>;
    case "arrow-ur": return <svg {...p}><path d="M7 17 17 7"/><path d="M8 7h9v9"/></svg>;
    case "chevron-r": return <svg {...p}><path d="m9 18 6-6-6-6"/></svg>;
    case "search": return <svg {...p}><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>;
    case "layers": return <svg {...p}><path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/></svg>;
    case "trend": return <svg {...p}><path d="M3 17 9 11l4 4 8-8"/><path d="M21 7h-5M21 7v5"/></svg>;
    case "shield": return <svg {...p}><path d="M12 3 4 6v6c0 5 3.5 7.5 8 9 4.5-1.5 8-4 8-9V6l-8-3Z"/></svg>;
    case "check": return <svg {...p}><path d="M20 6 9 17l-5-5"/></svg>;
    default: return null;
  }
}

function OutletLogo({ id, size = 22, square = false }) {
  const o = OUTLETS[id] || { mark: "?", color: "#888" };
  const len = (o.mark || "").length;
  const fs = len >= 3 ? size * 0.34 : len === 2 ? size * 0.42 : size * 0.5;
  return (
    <span className={"outlet" + (square ? " square" : "")}
      title={o.name}
      style={{ width: size, height: size, background: o.color, fontSize: Math.round(fs) }}>
      {o.mark}
    </span>
  );
}

function SourceStack({ ids, max = 4, size = 24, showCount = true }) {
  const shown = ids.slice(0, max);
  const extra = ids.length - shown.length;
  return (
    <span className="src-stack">
      {shown.map((id) => <OutletLogo key={id} id={id} size={size} />)}
      {extra > 0 && (
        <span className="outlet" style={{ width: size, height: size, background: "#c9c8c2",
          color: "#4a4a47", fontSize: Math.round(size * 0.36), marginLeft: -7 }}>+{extra}</span>
      )}
      {showCount && <span className="src-count"><b>{ids.length}</b> sources</span>}
    </span>
  );
}

const FACT_COLOR = { High: "var(--fact-high)", Mixed: "var(--fact-mixed)", Low: "var(--fact-low)" };

function Factuality({ fact, variant = "pill" }) {
  const color = FACT_COLOR[fact.label] || "var(--muted)";
  if (variant === "score") {
    return (
      <span className="fact" title={`Factuality ${fact.score}/100`}>
        <span className="fact-dot" style={{ background: color }} />
        <span className="fact-label" style={{ color }}>{fact.label}</span>
        <span className="fact-score-num dim">{fact.score}</span>
      </span>
    );
  }
  if (variant === "bar") {
    return (
      <span className="fact" title={`Factuality ${fact.score}/100`}>
        <span className="fact-bar"><i style={{ width: fact.score + "%", background: color }} /></span>
        <span className="fact-label" style={{ color }}>{fact.label}</span>
      </span>
    );
  }
  return (
    <span className="fact-pill" title={`Factuality ${fact.score}/100`}>
      <span className="fact-dot" style={{ background: color }} />
      <span style={{ color }}>{fact.label} factuality</span>
    </span>
  );
}

function Sparkline({ data, w = 56, h = 18, color = "var(--accent)", fill = true }) {
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const step = w / (data.length - 1);
  const pts = data.map((d, i) => [i * step, h - ((d - min) / range) * (h - 2) - 1]);
  const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const area = `${line} L ${w} ${h} L 0 ${h} Z`;
  const id = "sg" + Math.round(data.reduce((a, b) => a + b, 0) * 7 + w);
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ display: "block", overflow: "visible" }}>
      {fill && (
        <>
          <defs>
            <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.22" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={area} fill={`url(#${id})`} />
        </>
      )}
      <path d={line} fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="2.1" fill={color} />
    </svg>
  );
}

function Coverage({ coverage, showSpark = true }) {
  return (
    <span className="cov" title={`${coverage.articles} articles · peak ${coverage.peak}`}>
      {showSpark && <Sparkline data={coverage.spark} />}
      <span className="cov-num">{coverage.articles} <span>articles</span></span>
    </span>
  );
}

function MetaSep() { return <span className="meta-sep" />; }

Object.assign(window, { Icon, OutletLogo, SourceStack, Factuality, Sparkline, Coverage, MetaSep });
