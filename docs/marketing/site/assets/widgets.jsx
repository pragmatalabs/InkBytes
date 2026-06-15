/* ══════════════════════════════════════════════════════════════
   InkBytes marketing — product widget islands (bilingual)
   Composed from REAL design-system components (Factuality,
   SourceStack, Coverage, Sparkline, OutletLogo, Tag, Kicker).
   Reads <body data-lang>. Auto-mounts into [data-widget="…"].
   ══════════════════════════════════════════════════════════════ */
(function () {
  const DS = window.InkBytesDesignSystem_119654 || {};
  const { Factuality, SourceStack, OutletLogo, Coverage, Sparkline, Tag, Kicker } = DS;
  const LANG = (document.body.dataset.lang === "es") ? "es" : "en";
  const SPARK = [6, 9, 7, 14, 11, 26, 41, 38, 52, 47];

  const STR = {
    en: {
      syn: "Synthesized", kicker: "World", date: "Wed, Jun 3, 2026 · 11:40",
      head: "Central banks signal a coordinated shift as inflation cools across markets",
      tags: ["Federal Reserve", "ECB", "Jerome Powell", "Inflation"],
      pre: "Policymakers across major economies converged this week on a more dovish tone, with three central banks ",
      cited: "hinting at rate adjustments as price pressures ease",
      post: ". Officials framed the move as coordinated rather than reactive, citing softer core inflation prints across the euro area and the United States.",
      sources: "Sources", every: "every claim cited",
      fact: [
        { label: "High", score: 94, note: "Corroborated across many independent outlets; claims trace cleanly to source." },
        { label: "Mixed", score: 61, note: "Still developing — outlets diverge on specifics; we flag what isn't settled." },
        { label: "Low", score: 28, note: "Thin or disputed sourcing. Rarely published; never from a single source." },
      ],
    },
    es: {
      syn: "Sintetizado", kicker: "Mundo", date: "Mié, 3 jun 2026 · 11:40",
      head: "Los bancos centrales anticipan un giro coordinado mientras la inflación cede en los mercados",
      tags: ["Reserva Federal", "BCE", "Jerome Powell", "Inflación"],
      pre: "Las autoridades de las principales economías coincidieron esta semana en un tono más flexible, con tres bancos centrales ",
      cited: "insinuando ajustes de tasas a medida que ceden las presiones de precios",
      post: ". Los funcionarios enmarcaron el movimiento como coordinado y no reactivo, citando una inflación subyacente más suave en la eurozona y Estados Unidos.",
      sources: "Fuentes", every: "cada dato citado",
      fact: [
        { label: "High", score: 94, note: "Corroborado por múltiples medios independientes; las afirmaciones se trazan con claridad hasta su fuente." },
        { label: "Mixed", score: 61, note: "Aún en desarrollo — los medios difieren en los detalles; señalamos lo que no está resuelto." },
        { label: "Low", score: 28, note: "Fuentes escasas o en disputa. Rara vez se publica; nunca desde una sola fuente." },
      ],
    },
  };
  const T = STR[LANG];

  function EventMock() {
    return (
      <div className="evt">
        <div className="evt-top">
          <span className="evt-dot" /><span className="evt-dot" /><span className="evt-dot" />
          <span className="evt-url mono">inkbytes.org/event/central-banks-coordinated-shift</span>
          <span className="evt-syn mono">{T.syn}</span>
        </div>
        <div className="evt-body">
          <div className="evt-kick">
            <Kicker>{T.kicker}</Kicker>
            <span className="evt-date mono">{T.date}</span>
          </div>
          <h3 className="evt-h serif">{T.head}</h3>

          <div className="evt-meta">
            <Factuality label="High" score={94} variant="pill" />
            <SourceStack ids={["reuters", "ap", "bloomberg", "guardian", "ft", "cnbc"]} size={24} max={5} />
            <Coverage articles={247} spark={SPARK} peak="Today" />
          </div>

          <div className="evt-tags">
            <Tag dotColor="var(--entity-org)">{T.tags[0]}</Tag>
            <Tag dotColor="var(--entity-org)">{T.tags[1]}</Tag>
            <Tag dotColor="var(--entity-person)">{T.tags[2]}</Tag>
            <Tag dotColor="var(--entity-topic)">{T.tags[3]}</Tag>
          </div>

          <p className="evt-p serif">
            {T.pre}<span className="cited">{T.cited}<sup>1</sup></span>{T.post}
          </p>

          <div className="evt-rail">
            <span className="evt-rail-label mono">{T.sources}</span>
            <span className="evt-rail-logos">
              <OutletLogo id="reuters" size={22} />
              <OutletLogo id="ap" size={22} />
              <OutletLogo id="bloomberg" size={22} />
              <OutletLogo id="ft" size={22} />
              <OutletLogo id="guardian" size={22} />
            </span>
            <span className="evt-rail-cite">+2 · <b>{T.every}</b></span>
          </div>
        </div>
      </div>
    );
  }

  function FactSpectrum() {
    return (
      <div className="fact-grid">
        {T.fact.map((r) => (
          <div className="fact-card" key={r.label}>
            <div className="fact-card-top">
              <Factuality label={r.label} score={r.score} variant="pill" />
              <Factuality label={r.label} score={r.score} variant="bar" />
            </div>
            <p>{r.note}</p>
          </div>
        ))}
      </div>
    );
  }

  function TwoSource() {
    return (
      <div className="twosrc">
        <SourceStack ids={["reuters", "ap", "bloomberg", "guardian", "ft", "cnbc", "wsj"]} size={30} max={6} />
        <Coverage articles={247} spark={SPARK} peak="Today" />
      </div>
    );
  }

  const REGISTRY = { "event-mock": EventMock, "fact-spectrum": FactSpectrum, "two-source": TwoSource };

  function mount() {
    document.querySelectorAll("[data-widget]").forEach((el) => {
      const Comp = REGISTRY[el.getAttribute("data-widget")];
      if (!Comp) return;
      const node = React.createElement(Comp);
      if (ReactDOM.createRoot) ReactDOM.createRoot(el).render(node);
      else ReactDOM.render(node, el);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
