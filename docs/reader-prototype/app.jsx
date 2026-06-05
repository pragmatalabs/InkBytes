/* app.jsx — root: routing + tweaks. */

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "feedLayout": "editorial",
  "density": "comfy",
  "accent": "#1f57ff",
  "headlineFont": "Archivo",
  "articleType": "sans",
  "factualityStyle": "pill",
  "hlScale": 1,
  "graphCluster": true,
  "graphLabels": "smart"
}/*EDITMODE-END*/;

const FONT_STACK = {
  "Archivo": '"Archivo", sans-serif',
  "Libre Franklin": '"Libre Franklin", sans-serif',
};

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [route, setRoute] = React.useState({ view: "feed", id: null });
  const { EVENTS } = window.INKBYTES;

  // apply tweak-driven CSS variables
  React.useEffect(() => {
    const r = document.documentElement.style;
    r.setProperty("--accent", t.accent);
    r.setProperty("--hl-font", FONT_STACK[t.headlineFont] || FONT_STACK.Archivo);
    r.setProperty("--article-font", t.articleType === "serif"
      ? '"Spectral", Georgia, serif' : "var(--body-font)");
    r.setProperty("--hl-scale", String(t.hlScale));
    document.body.classList.toggle("compact", t.density === "compact");
  }, [t.accent, t.headlineFont, t.articleType, t.hlScale, t.density]);

  const open = (id) => { setRoute({ view: "event", id }); window.scrollTo(0, 0); };
  const home = () => { setRoute({ view: "feed", id: null }); window.scrollTo(0, 0); };
  const graph = (entity) => { setRoute({ view: "graph", entity: entity || null }); window.scrollTo(0, 0); };

  const ev = route.view === "event" ? EVENTS.find((e) => e.id === route.id) : null;

  return (
    <>
      <Header route={route.view} onHome={home} onGraph={graph} t={t} />
      {route.view === "feed" && <Feed events={EVENTS} onOpen={open} onGraph={graph} t={t} />}
      {route.view === "event" && <EventPage ev={ev} onBack={home} onEntity={graph} t={t} />}
      {route.view === "graph" && (
        <GraphView events={EVENTS} focusEntity={route.entity} onOpenEvent={open}
          cluster={t.graphCluster} labels={t.graphLabels} />
      )}

      <TweaksPanel>
        <TweakSection label="Front view" />
        <TweakRadio label="Feed layout" value={t.feedLayout}
          options={["editorial", "grid", "stream"]}
          onChange={(v) => setTweak("feedLayout", v)} />
        <TweakRadio label="Density" value={t.density}
          options={["comfy", "compact"]}
          onChange={(v) => setTweak("density", v)} />

        <TweakSection label="Intelligence" />
        <TweakRadio label="Factuality" value={t.factualityStyle}
          options={["pill", "score", "bar"]}
          onChange={(v) => setTweak("factualityStyle", v)} />

        <TweakSection label="Type & color" />
        <TweakColor label="Accent" value={t.accent}
          options={["#1f57ff", "#d23f2d", "#1d8a4e", "#6a3df0", "#0f1326"]}
          onChange={(v) => setTweak("accent", v)} />
        <TweakRadio label="Headline" value={t.headlineFont}
          options={["Archivo", "Libre Franklin"]}
          onChange={(v) => setTweak("headlineFont", v)} />
        <TweakRadio label="Article text" value={t.articleType}
          options={["sans", "serif"]}
          onChange={(v) => setTweak("articleType", v)} />
        <TweakSlider label="Headline scale" value={t.hlScale} min={0.85} max={1.18} step={0.01}
          onChange={(v) => setTweak("hlScale", v)} />

        <TweakSection label="Entity graph" />
        <TweakRadio label="Layout" value={t.graphCluster ? "clustered" : "free"}
          options={["clustered", "free"]}
          onChange={(v) => setTweak("graphCluster", v === "clustered")} />
        <TweakRadio label="Labels" value={t.graphLabels}
          options={["smart", "all", "off"]}
          onChange={(v) => setTweak("graphLabels", v)} />
      </TweaksPanel>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
