/**
 * PersonaIcon — hand-authored monochrome glyphs for the 15 Outlook columns
 * (+ El Editor fallback). One metaphor per persona name (La Mesa = the table,
 * El Balance = the scale, …), drawn on a 24×24 grid with a 2px round stroke,
 * geometric primitives only — Bauhaus reduction, legible at 16px, tinted by
 * `currentColor` so the theme accent (lib/theme-colors.ts) does the coloring.
 *
 * Keyed by the kebab-case persona key stored in `editorials.persona`
 * ("el-circuito"), same keys as Editorial/apps/editorial/personas.py.
 */

interface P {
  className?: string;
}

const S = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

/* politics — La Mesa: round table, top-down, four seats at the cardinals */
const LaMesa = ({ className }: P) => (
  <svg {...S} className={className}>
    <circle cx="12" cy="12" r="6" />
    <path d="M9.5 2.8h5M9.5 21.2h5M2.8 9.5v5M21.2 9.5v5" />
  </svg>
);

/* world — El Atlas: globe, one meridian, one parallel */
const ElAtlas = ({ className }: P) => (
  <svg {...S} className={className}>
    <circle cx="12" cy="12" r="9" />
    <ellipse cx="12" cy="12" rx="4" ry="9" />
    <path d="M3 12h18" />
  </svg>
);

/* business — El Balance: two-pan scale */
const ElBalance = ({ className }: P) => (
  <svg {...S} className={className}>
    <path d="M12 4v14M5.5 7h13M8.5 20h7" />
    <path d="M2.8 10.5a2.7 2.7 0 0 0 5.4 0M2.8 10.5 5.5 7l2.7 3.5" />
    <path d="M15.8 10.5a2.7 2.7 0 0 0 5.4 0M15.8 10.5 18.5 7l2.7 3.5" />
  </svg>
);

/* technology — El Circuito: trace, two nodes, one chip */
const ElCircuito = ({ className }: P) => (
  <svg {...S} className={className}>
    <path d="M4.5 12h5.5V6h6" />
    <circle cx="4.5" cy="12" r="1.4" fill="currentColor" stroke="none" />
    <circle cx="16" cy="6" r="1.4" fill="currentColor" stroke="none" />
    <rect x="13.5" y="13.5" width="7" height="7" rx="1.2" />
  </svg>
);

/* sports — La Tribuna: grandstand steps + flag */
const LaTribuna = ({ className }: P) => (
  <svg {...S} className={className}>
    <path d="M3 20h4.5v-4.5H12V11h4.5V7H21" />
    <path d="M18 7V3.2" />
    <path d="M18 3.2l3.4 1.2L18 5.6" />
  </svg>
);

/* health — El Pulso: EKG spike */
const ElPulso = ({ className }: P) => (
  <svg {...S} className={className}>
    <path d="M3 12h5l2.5-6 3 12 2.5-6h5" />
  </svg>
);

/* environment — La Marea: two waves, the deep current beneath */
const LaMarea = ({ className }: P) => (
  <svg {...S} className={className}>
    <path d="M3 9.5c3-3 6-3 9 0s6 3 9 0" />
    <path d="M3 15.5c3-3 6-3 9 0s6 3 9 0" />
  </svg>
);

/* culture — El Telón: bar + parting drapes */
const ElTelon = ({ className }: P) => (
  <svg {...S} className={className}>
    <path d="M3 4h18" />
    <path d="M9.5 4c0 5.5-2 10-5.5 15" />
    <path d="M14.5 4c0 5.5 2 10 5.5 15" />
  </svg>
);

/* science — El Laboratorio: erlenmeyer flask, liquid line, one bubble */
const ElLaboratorio = ({ className }: P) => (
  <svg {...S} className={className}>
    <path d="M9.5 3h5M13.5 3v6l5.6 9.6a1.6 1.6 0 0 1-1.4 2.4H6.3a1.6 1.6 0 0 1-1.4-2.4L10.5 9V3" />
    <path d="M7.3 15.5h9.4" />
    <circle cx="14.6" cy="12.2" r="1" fill="currentColor" stroke="none" />
  </svg>
);

/* entertainment — La Marquesina: marquee board + lights */
const LaMarquesina = ({ className }: P) => (
  <svg {...S} className={className}>
    <rect x="3" y="9" width="18" height="9.5" rx="1.5" />
    <circle cx="8" cy="5" r="1.1" fill="currentColor" stroke="none" />
    <circle cx="12" cy="5" r="1.1" fill="currentColor" stroke="none" />
    <circle cx="16" cy="5" r="1.1" fill="currentColor" stroke="none" />
  </svg>
);

/* crime — El Expediente: case folder + seal */
const ElExpediente = ({ className }: P) => (
  <svg {...S} className={className}>
    <path d="M3 18V5.5A1.5 1.5 0 0 1 4.5 4H9l2 2.5h8.5A1.5 1.5 0 0 1 21 8v10a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18Z" />
    <circle cx="12" cy="13" r="2.4" />
    <path d="M13.8 14.8l2.4 1.6" />
  </svg>
);

/* education — El Aula: mortarboard + tassel */
const ElAula = ({ className }: P) => (
  <svg {...S} className={className}>
    <path d="M12 4.5 21.5 9 12 13.5 2.5 9Z" />
    <path d="M7.5 11.2v3.3c0 1.6 2 2.9 4.5 2.9s4.5-1.3 4.5-2.9v-3.3" />
    <path d="M21.5 9v4.5" />
    <circle cx="21.5" cy="15" r="1" fill="currentColor" stroke="none" />
  </svg>
);

/* lifestyle — La Plaza: open square, gap = the entrance, fountain at center */
const LaPlaza = ({ className }: P) => (
  <svg {...S} className={className}>
    <path d="M9.5 4H5.5A1.5 1.5 0 0 0 4 5.5v13A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5v-13A1.5 1.5 0 0 0 18.5 4h-4" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

/* religion — El Campanario: bell, lip, clapper */
const ElCampanario = ({ className }: P) => (
  <svg {...S} className={className}>
    <path d="M12 3.5V5" />
    <path d="M7 16c0-6 1.5-9.5 5-9.5s5 3.5 5 9.5" />
    <path d="M5 16h14" />
    <circle cx="12" cy="19" r="1.4" fill="currentColor" stroke="none" />
  </svg>
);

/* disaster — La Alerta: beacon tower + broadcast arcs */
const LaAlerta = ({ className }: P) => (
  <svg {...S} className={className}>
    <path d="M9.2 20 12 10.5 14.8 20" />
    <path d="M6 20h12" />
    <path d="M9 7.2a4.2 4.2 0 0 1 6 0" />
    <path d="M6.6 4.4a7.6 7.6 0 0 1 10.8 0" />
  </svg>
);

/* fallback — El Editor: fountain-pen nib */
const ElEditor = ({ className }: P) => (
  <svg {...S} className={className}>
    <path d="M12 3l5 5c0 6-2 9.5-5 13-3-3.5-5-7-5-13l5-5Z" />
    <path d="M12 9.5v4.5" />
  </svg>
);

const ICONS: Record<string, (p: P) => React.ReactElement> = {
  "la-mesa": LaMesa,
  "el-atlas": ElAtlas,
  "el-balance": ElBalance,
  "el-circuito": ElCircuito,
  "la-tribuna": LaTribuna,
  "el-pulso": ElPulso,
  "la-marea": LaMarea,
  "el-telon": ElTelon,
  "el-laboratorio": ElLaboratorio,
  "la-marquesina": LaMarquesina,
  "el-expediente": ElExpediente,
  "el-aula": ElAula,
  "la-plaza": LaPlaza,
  "el-campanario": ElCampanario,
  "la-alerta": LaAlerta,
  "el-editor": ElEditor,
};

export function PersonaIcon({ persona, className }: { persona: string; className?: string }) {
  const Icon = ICONS[persona] ?? ElEditor;
  return <Icon className={className} />;
}
