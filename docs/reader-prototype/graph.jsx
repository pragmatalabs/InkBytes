/* graph.jsx — NLP entity graph: typed nodes, type clustering, focus navigation. */

(function injectGraphCSS() {
  const css = `
  .gv { max-width: 1320px; margin:0 auto; padding: 22px 28px 40px; }
  .gv-head { display:flex; align-items:flex-end; justify-content:space-between; gap:20px; flex-wrap:wrap; margin-bottom:16px; }
  .gv-title { font-family:var(--hl-font); font-weight:800; font-size:30px; letter-spacing:-0.02em; line-height:1; }
  .gv-sub { font-family:"IBM Plex Mono",monospace; font-size:12px; color:var(--muted); margin-top:9px; letter-spacing:.01em; }
  .gv-tools { display:flex; align-items:center; gap:10px; }
  .gv-search {
    display:flex; align-items:center; gap:8px; background:var(--surface);
    border:1px solid var(--line); border-radius:9px; height:38px; padding:0 12px; min-width:200px;
  }
  .gv-search input { border:0; outline:0; background:transparent; font-family:inherit; font-size:14px; color:var(--ink); width:100%; }
  .gv-search input::placeholder { color:var(--muted-2); }

  .legend { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:14px; }
  .legend-item {
    display:inline-flex; align-items:center; gap:8px; padding:6px 12px 6px 10px; border-radius:999px;
    border:1px solid var(--line); background:var(--surface); cursor:pointer; transition:.14s;
    font-size:13px; font-weight:500; color:var(--ink-2); user-select:none;
  }
  .legend-item:hover { border-color:var(--ink-3); }
  .legend-item.off { opacity:.42; }
  .legend-item .sw { width:11px; height:11px; border-radius:50%; flex:none; }
  .legend-item .ct { font-family:"IBM Plex Mono",monospace; font-size:11px; color:var(--muted); }

  .gv-body { display:grid; grid-template-columns: 1fr 340px; gap:18px; align-items:stretch; }
  .gv-stage {
    position:relative; background:
      radial-gradient(circle at 1px 1px, rgba(20,22,28,.05) 1px, transparent 0) 0 0 / 26px 26px,
      var(--surface);
    border:1px solid var(--line); border-radius:var(--radius); overflow:hidden;
    height: min(72vh, 700px); min-height:440px; touch-action:none;
  }
  .gv-svg { display:block; width:100%; height:100%; cursor:grab; }
  .gv-svg.dragging { cursor:grabbing; }
  .gedge { stroke: var(--line); transition: stroke .15s, stroke-opacity .15s, stroke-width .15s; }
  .gnode-c { cursor:pointer; transition: opacity .15s; }
  .gnode-ring { fill:none; }
  .glabel { font-family:"Archivo",sans-serif; font-weight:600; fill: var(--ink); paint-order:stroke; stroke: var(--surface); stroke-width:3px; stroke-linejoin:round; pointer-events:none; transition: opacity .15s; }

  .gv-stage-hint { position:absolute; left:14px; bottom:12px; font-family:"IBM Plex Mono",monospace; font-size:11px; color:var(--muted-2); pointer-events:none; letter-spacing:.02em; }

  /* side panel */
  .gpanel { border:1px solid var(--line); border-radius:var(--radius); background:var(--surface); padding:20px; display:flex; flex-direction:column; min-height:0; overflow:auto; }
  .gpanel-type { display:inline-flex; align-items:center; gap:8px; white-space:nowrap; font-family:"IBM Plex Mono",monospace; font-size:11px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; }
  .gpanel-type .sw { width:9px; height:9px; border-radius:50%; }
  .gpanel-name { font-family:var(--hl-font); font-weight:800; font-size:25px; letter-spacing:-0.02em; line-height:1.06; margin:12px 0 4px; text-wrap:balance; }
  .gpanel-meta { font-size:13px; color:var(--muted); margin-bottom:18px; }
  .gp-lbl { font-family:"IBM Plex Mono",monospace; font-size:10.5px; font-weight:600; letter-spacing:.09em; text-transform:uppercase; color:var(--muted); margin:18px 0 11px; }
  .gp-story { display:block; padding:12px 0; border-top:1px solid var(--line-2); cursor:pointer; }
  .gp-story:first-of-type { border-top:0; }
  .gp-story .k { font-family:"IBM Plex Mono",monospace; font-size:10.5px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--accent); }
  .gp-story h5 { font-family:var(--hl-font); font-weight:700; font-size:15.5px; line-height:1.22; margin:6px 0 8px; color:var(--ink); letter-spacing:-0.01em; transition:color .15s; }
  .gp-story:hover h5 { color:var(--accent); }
  .gp-story .m { display:flex; align-items:center; gap:10px; font-size:12px; color:var(--muted); }
  .gp-chips { display:flex; flex-wrap:wrap; gap:7px; }
  .gp-chip { display:inline-flex; align-items:center; gap:7px; padding:6px 11px; border-radius:999px; border:1px solid var(--line); background:var(--surface); font-size:12.5px; font-weight:500; color:var(--ink-2); cursor:pointer; transition:.14s; }
  .gp-chip:hover { border-color:var(--ink-3); color:var(--ink); }
  .gp-chip .sw { width:8px; height:8px; border-radius:50%; flex:none; }
  .gp-empty-h { font-family:var(--hl-font); font-weight:800; font-size:20px; letter-spacing:-0.01em; margin:2px 0 10px; }
  .gp-empty-p { font-size:14px; line-height:1.55; color:var(--ink-2); margin:0 0 8px; }
  .gp-back { display:inline-flex; align-items:center; gap:8px; white-space:nowrap; font-size:13px; color:var(--muted); cursor:pointer; margin-bottom:14px; }
  .gp-back:hover { color:var(--ink); }

  @media (max-width: 900px) {
    .gv-body { grid-template-columns: 1fr; }
    .gv-stage { height: 56vh; }
    .gv { padding:18px 16px 36px; }
  }
  `;
  const s = document.createElement("style");
  s.textContent = css;
  document.head.appendChild(s);
})();

const ENTITY_TYPES = {
  // Place
  "Iran":"Place","United States":"Place","Israel":"Place","Lebanon":"Place","Strait of Hormuz":"Place",
  "Brazil":"Place","China":"Place","Kuwait":"Place","Amazon":"Place",
  // Person
  "Donald Trump":"Person","Benjamin Netanyahu":"Person","Marco Rubio":"Person","Israel Katz":"Person",
  // Organization
  "Hezbollah":"Org","Federal Reserve":"Org","ECB":"Org","Bank of England":"Org","FDA":"Org",
  // Topic (default)
};
const TYPE_META = {
  Place: { label: "Place",        color: "#2563eb" },
  Person:{ label: "Person",       color: "#e0552d" },
  Org:   { label: "Organization", color: "#1d8a4e" },
  Topic: { label: "Topic",        color: "#8b5cf6" },
};
const TYPE_ORDER = ["Place", "Person", "Org", "Topic"];

function typeOf(name) { return ENTITY_TYPES[name] || "Topic"; }

function buildGraph(events) {
  const nodes = {};
  const links = {};
  events.forEach((ev) => {
    const ents = ev.entities || ev.tags || [];
    ents.forEach((name) => {
      if (!nodes[name]) nodes[name] = { id: name, name, type: typeOf(name), events: [], deg: 0 };
      if (!nodes[name].events.includes(ev.id)) nodes[name].events.push(ev.id);
    });
    for (let i = 0; i < ents.length; i++)
      for (let j = i + 1; j < ents.length; j++) {
        const k = [ents[i], ents[j]].sort().join("\u0001");
        links[k] = (links[k] || 0) + 1;
      }
  });
  const nodeList = Object.values(nodes);
  const linkList = Object.entries(links).map(([k, w]) => {
    const [a, b] = k.split("\u0001");
    nodes[a].deg += w; nodes[b].deg += w;
    return { source: a, target: b, w };
  });
  return { nodes: nodeList, links: linkList, nodeMap: nodes };
}

function GraphView({ events, focusEntity, onOpenEvent, cluster = true, labels = "smart" }) {
  const { nodes, links, nodeMap } = React.useMemo(() => buildGraph(events), [events]);
  const evMap = React.useMemo(() => Object.fromEntries(events.map((e) => [e.id, e])), [events]);

  const stageRef = React.useRef(null);
  const posRef = React.useRef(null);       // name -> {x,y,vx,vy,fx,fy}
  const alphaRef = React.useRef(1);
  const rafRef = React.useRef(0);
  const dragRef = React.useRef(null);
  const initedRef = React.useRef(false);

  const [dims, setDims] = React.useState({ w: 800, h: 560 });
  const [, setFrame] = React.useState(0);
  const [selected, setSelected] = React.useState(focusEntity || null);
  const [hovered, setHovered] = React.useState(null);
  const [hidden, setHidden] = React.useState(() => new Set());
  const [query, setQuery] = React.useState("");
  const tRef = React.useRef({ cluster, labels });
  tRef.current = { cluster, labels };

  // adjacency
  const adj = React.useMemo(() => {
    const m = {};
    nodes.forEach((n) => (m[n.name] = new Set()));
    links.forEach((l) => { m[l.source].add(l.target); m[l.target].add(l.source); });
    return m;
  }, [nodes, links]);

  // type anchors arranged on a ring
  const anchors = React.useMemo(() => {
    const cx = dims.w / 2, cy = dims.h / 2;
    const R = Math.min(dims.w, dims.h) * 0.36;
    const a = {};
    TYPE_ORDER.forEach((t, i) => {
      const ang = -Math.PI / 2 + (i / TYPE_ORDER.length) * Math.PI * 2;
      a[t] = { x: cx + Math.cos(ang) * R, y: cy + Math.sin(ang) * R };
    });
    return a;
  }, [dims.w, dims.h]);

  // init positions
  React.useEffect(() => {
    const p = {};
    const prev = posRef.current || {};
    nodes.forEach((n) => {
      if (prev[n.name]) { p[n.name] = prev[n.name]; return; }
      const an = anchors[n.type];
      p[n.name] = { x: an.x + (Math.random() - 0.5) * 80, y: an.y + (Math.random() - 0.5) * 80, vx: 0, vy: 0, fx: null, fy: null };
    });
    posRef.current = p;
    initedRef.current = true;
    alphaRef.current = 1;
    ensureRunning();
  }, [nodes, anchors]);

  // resize observer
  React.useEffect(() => {
    if (!stageRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0].contentRect;
      setDims({ w: Math.max(320, r.width), h: Math.max(360, r.height) });
      alphaRef.current = Math.max(alphaRef.current, 0.5);
      ensureRunning();
    });
    ro.observe(stageRef.current);
    return () => ro.disconnect();
  }, []);

  function ensureRunning() {
    if (rafRef.current) return;
    const loop = () => {
      step();
      setFrame((f) => (f + 1) & 0xffff);
      if (alphaRef.current > 0.02 || dragRef.current) {
        rafRef.current = requestAnimationFrame(loop);
      } else {
        rafRef.current = 0;
      }
    };
    rafRef.current = requestAnimationFrame(loop);
  }
  React.useEffect(() => () => cancelAnimationFrame(rafRef.current), []);

  function step() {
    const p = posRef.current;
    if (!p) return;
    const { w, h } = dims;
    const alpha = alphaRef.current;
    const REP = 6200, LINKD = 108, LINKS = 0.045, CENTER = 0.011, ANCHOR = tRef.current.cluster ? 0.014 : 0.003;
    const list = nodes;
    // repulsion
    for (let i = 0; i < list.length; i++) {
      const a = p[list[i].name]; if (!a) continue;
      for (let j = i + 1; j < list.length; j++) {
        const b = p[list[j].name]; if (!b) continue;
        let dx = a.x - b.x, dy = a.y - b.y;
        let d2 = dx * dx + dy * dy; if (d2 < 1) d2 = 1;
        const d = Math.sqrt(d2);
        const f = (REP / d2) * alpha;
        const fx = (dx / d) * f, fy = (dy / d) * f;
        a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
      }
    }
    // links
    links.forEach((l) => {
      const a = p[l.source], b = p[l.target]; if (!a || !b) return;
      let dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.sqrt(dx * dx + dy * dy) || 1;
      const f = ((d - LINKD) * LINKS) * alpha;
      const fx = (dx / d) * f, fy = (dy / d) * f;
      a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
    });
    // anchor + center + integrate
    list.forEach((n) => {
      const a = p[n.name]; if (!a) return;
      const an = anchors[n.type];
      a.vx += (an.x - a.x) * ANCHOR * alpha;
      a.vy += (an.y - a.y) * ANCHOR * alpha;
      a.vx += (w / 2 - a.x) * CENTER * alpha;
      a.vy += (h / 2 - a.y) * CENTER * alpha;
      if (a.fx != null) { a.x = a.fx; a.y = a.fy; a.vx = 0; a.vy = 0; return; }
      a.vx *= 0.82; a.vy *= 0.82;
      const sp = Math.hypot(a.vx, a.vy); if (sp > 18) { a.vx *= 18 / sp; a.vy *= 18 / sp; }
      a.x += a.vx; a.y += a.vy;
      const pad = 30;
      a.x = Math.max(pad, Math.min(w - pad, a.x));
      a.y = Math.max(pad, Math.min(h - pad, a.y));
    });
    alphaRef.current = Math.max(0, alpha * 0.985);
  }

  // refocus when prop changes
  React.useEffect(() => { if (focusEntity) { setSelected(focusEntity); reheat(0.7); } }, [focusEntity]);
  React.useEffect(() => { reheat(0.6); }, [cluster]);
  function reheat(v = 0.5) { alphaRef.current = Math.max(alphaRef.current, v); ensureRunning(); }

  // pointer handlers
  function clientToSvg(e) {
    const r = stageRef.current.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }
  function onPointerDownNode(e, name) {
    e.stopPropagation();
    const pt = clientToSvg(e);
    const node = posRef.current[name];
    dragRef.current = { name, moved: false, ox: node.x - pt.x, oy: node.y - pt.y };
    node.fx = node.x; node.fy = node.y;
    e.currentTarget.setPointerCapture && e.currentTarget.setPointerCapture(e.pointerId);
    reheat(0.3);
  }
  function onPointerMove(e) {
    if (!dragRef.current) return;
    const pt = clientToSvg(e);
    const node = posRef.current[dragRef.current.name];
    node.fx = pt.x + dragRef.current.ox; node.fy = pt.y + dragRef.current.oy;
    dragRef.current.moved = true;
    reheat(0.25);
  }
  function onPointerUp(e) {
    if (!dragRef.current) return;
    const d = dragRef.current;
    const node = posRef.current[d.name];
    node.fx = null; node.fy = null;
    if (!d.moved) setSelected((s) => (s === d.name ? null : d.name));
    dragRef.current = null;
    reheat(0.3);
  }

  const matched = query.trim().toLowerCase();
  const focusName = hovered || selected;
  const neighborSet = focusName ? adj[focusName] : null;

  const visible = (n) => !hidden.has(n.type);
  const isDim = (name) => {
    const t = nodes.find((n) => n.name === name).type;
    if (hidden.has(t)) return true;
    if (matched && !name.toLowerCase().includes(matched)) return true;
    if (focusName && name !== focusName && !(neighborSet && neighborSet.has(name))) return true;
    return false;
  };
  const radius = (n) => 6 + Math.sqrt(n.events.length) * 4 + Math.min(n.deg, 8) * 0.45;

  const p = posRef.current || {};
  const selNode = selected ? nodeMap[selected] : null;
  const typeCounts = TYPE_ORDER.map((t) => ({ t, n: nodes.filter((x) => x.type === t).length }));
  const topEntities = [...nodes].sort((a, b) => b.events.length - a.events.length || b.deg - a.deg).slice(0, 6);

  function selectAndHeat(name) { setSelected(name); setHovered(null); reheat(0.55); }

  return (
    <main className="gv">
      <div className="gv-head">
        <div>
          <div className="gv-title">Entity graph</div>
          <div className="gv-sub">{nodes.length} ENTITIES · {links.length} LINKS · {events.length} EVENTS</div>
        </div>
        <div className="gv-tools">
          <div className="gv-search">
            <Icon name="search" size={15} color="var(--muted)" />
            <input value={query} placeholder="Find an entity…" onChange={(e) => { setQuery(e.target.value); reheat(0.2); }} />
          </div>
        </div>
      </div>

      <div className="legend">
        {TYPE_ORDER.map((t) => (
          <div key={t} className={"legend-item" + (hidden.has(t) ? " off" : "")}
            onClick={() => { setHidden((h) => { const n = new Set(h); n.has(t) ? n.delete(t) : n.add(t); return n; }); reheat(0.4); }}>
            <span className="sw" style={{ background: TYPE_META[t].color }} />
            {TYPE_META[t].label}
            <span className="ct">{typeCounts.find((c) => c.t === t).n}</span>
          </div>
        ))}
      </div>

      <div className="gv-body">
        <div className="gv-stage" ref={stageRef}>
          <svg className={"gv-svg" + (dragRef.current ? " dragging" : "")} viewBox={`0 0 ${dims.w} ${dims.h}`}
            onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerLeave={onPointerUp}
            onPointerDown={() => setSelected(null)}>
            {/* edges */}
            <g>
              {links.map((l, i) => {
                const a = p[l.source], b = p[l.target]; if (!a || !b) return null;
                if (!visible(nodeMap[l.source]) || !visible(nodeMap[l.target])) return null;
                const active = focusName && (l.source === focusName || l.target === focusName);
                return <line key={i} className="gedge" x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  stroke={active ? "var(--accent)" : "var(--line)"}
                  strokeWidth={active ? 1.6 : 1}
                  strokeOpacity={focusName ? (active ? 0.85 : 0.14) : 0.55} />;
              })}
            </g>
            {/* nodes */}
            <g>
              {nodes.map((n) => {
                const a = p[n.name]; if (!a || !visible(n)) return null;
                const r = radius(n);
                const dim = isDim(n.name);
                const isSel = selected === n.name;
                const col = TYPE_META[n.type].color;
                const showLabel = labels === "all" || isSel || hovered === n.name ||
                  (labels !== "off" && (n.events.length >= 2 || (focusName && (n.name === focusName || (neighborSet && neighborSet.has(n.name))))));
                return (
                  <g key={n.name} className="gnode-c" opacity={dim ? 0.28 : 1}
                    onPointerDown={(e) => onPointerDownNode(e, n.name)}
                    onPointerEnter={() => setHovered(n.name)} onPointerLeave={() => setHovered(null)}>
                    {isSel && <circle className="gnode-ring" cx={a.x} cy={a.y} r={r + 5} stroke={col} strokeWidth="2" opacity="0.5" />}
                    <circle cx={a.x} cy={a.y} r={r} fill={col} stroke="var(--surface)" strokeWidth="2" />
                    {showLabel && (
                      <text className="glabel" x={a.x} y={a.y + r + 13} textAnchor="middle"
                        fontSize={n.events.length >= 2 ? 12 : 11}>{n.name}</text>
                    )}
                  </g>
                );
              })}
            </g>
          </svg>
          <div className="gv-stage-hint">drag to rearrange · click a node to focus</div>
        </div>

        {/* side panel */}
        <aside className="gpanel">
          {selNode ? (
            <>
              <span className="gp-back" onClick={() => setSelected(null)}><Icon name="arrow-left" size={15} /> All entities</span>
              <span className="gpanel-type" style={{ color: TYPE_META[selNode.type].color }}>
                <span className="sw" style={{ background: TYPE_META[selNode.type].color }} />
                {TYPE_META[selNode.type].label}
              </span>
              <div className="gpanel-name">{selNode.name}</div>
              <div className="gpanel-meta">{selNode.events.length} {selNode.events.length === 1 ? "story" : "stories"} · {adj[selNode.name].size} connections</div>

              <div className="gp-lbl">Appears in</div>
              {selNode.events.map((eid) => {
                const ev = evMap[eid];
                return (
                  <div key={eid} className="gp-story" onClick={() => onOpenEvent(eid)}>
                    <span className="k">{ev.category}</span>
                    <h5>{ev.headline}</h5>
                    <div className="m">
                      <SourceStack ids={ev.sources} size={18} max={3} showCount={false} />
                      <span>{ev.sources.length} sources</span>
                      <MetaSep />
                      <span>{ev.updatedShort} ago</span>
                    </div>
                  </div>
                );
              })}

              {adj[selNode.name].size > 0 && (
                <>
                  <div className="gp-lbl">Connected entities</div>
                  <div className="gp-chips">
                    {[...adj[selNode.name]]
                      .sort((a, b) => nodeMap[b].events.length - nodeMap[a].events.length)
                      .map((name) => (
                        <span key={name} className="gp-chip" onClick={() => selectAndHeat(name)}>
                          <span className="sw" style={{ background: TYPE_META[nodeMap[name].type].color }} />
                          {name}
                        </span>
                      ))}
                  </div>
                </>
              )}
            </>
          ) : (
            <>
              <div className="gp-empty-h">Navigate the news by who & what</div>
              <p className="gp-empty-p">Every story is parsed for named entities — people, places, organizations and topics. Nodes that share a story are linked. Click any node to pull up its coverage.</p>
              <div className="gp-lbl">Most connected</div>
              <div className="gp-chips">
                {topEntities.map((n) => (
                  <span key={n.name} className="gp-chip" onClick={() => selectAndHeat(n.name)}>
                    <span className="sw" style={{ background: TYPE_META[n.type].color }} />
                    {n.name}
                    <span style={{ fontFamily: '"IBM Plex Mono",monospace', fontSize: 11, color: "var(--muted)" }}>{n.events.length}</span>
                  </span>
                ))}
              </div>
            </>
          )}
        </aside>
      </div>
    </main>
  );
}

Object.assign(window, { GraphView });
