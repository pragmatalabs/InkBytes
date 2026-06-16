/**
 * InkBytes icon system — extracted from the professional InkBytes icon set.
 *
 * All icons use stroke="currentColor" so they inherit color from CSS.
 * Size is controlled by the `className` prop (default: no explicit size).
 *
 * Source sets:
 *  • breaking-news-icon-set (stroke #010101, 64×64, strokeWidth 1.9)
 *  • artificial-intelligent-icon-set (stroke #001d3d, 48×48, strokeWidth 2)
 *  • computer-technology-icon-set (stroke #001d3d, 48×48, strokeWidth 2)
 *  • help-center-icon-set (stroke #001d3d, 48×48, strokeWidth 2)
 *  • money-icon-set (stroke #010101, 64×64, strokeWidth 1.8)
 *  • sport-icon-set (stroke #010101, 64×64, strokeWidth 1.8)
 *  • electrical-vehicle-icon-set (stroke #001d3d, 64×64, strokeWidth 2)
 */

interface IconProps {
  className?: string;
}

// ── Nav icons ─────────────────────────────────────────────────────────────────

/** News / home — newspaper (breaking-news-icon-set) */
export function NewspaperIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 64 64" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.9">
      <polyline points="21.7 23.6 25.5 20.5 31.5 15.6 37.6 20.5 41.4 23.6"/>
      <polyline points="38.1 21 43.2 16.9 48.3 21 51.4 23.6"/>
      <circle cx="38" cy="13.2" r="2.3"/>
      <path d="M9.4,2.8h0c2.5,0,4.6,2,4.6,4.6v12.9H4.8V7.4c0-2.5,2-4.6,4.6-4.6Z"/>
      <path d="M9.4,2.8h45.3c2.5,0,4.6,2,4.6,4.6v53.8"/>
      <line x1="21.7" y1="28.4" x2="33.3" y2="28.4"/>
      <line x1="21.7" y1="45.4" x2="32.1" y2="45.4"/>
      <line x1="21.7" y1="33.7" x2="51.4" y2="33.7"/>
      <line x1="21.7" y1="50.7" x2="32.1" y2="50.7"/>
      <line x1="21.7" y1="39" x2="51.4" y2="39"/>
      <line x1="21.7" y1="56" x2="32.1" y2="56"/>
      <line x1="41" y1="45.4" x2="51.4" y2="45.4"/>
      <line x1="41" y1="50.7" x2="51.4" y2="50.7"/>
      <line x1="41" y1="56" x2="51.4" y2="56"/>
      <polyline points="59.2 61.2 13.9 61.2 13.9 20.3"/>
      <line x1="36.6" y1="56" x2="36.6" y2="45.4"/>
      <rect x="21.7" y="8.2" width="29.8" height="15.5"/>
    </svg>
  );
}

/** Search — magnifying glass with checkmark (computer-technology-icon-set) */
export function SearchIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <circle cx="19" cy="19" r="13"/>
      <circle cx="19" cy="19" r="9"/>
      <polyline points="26.5 29.5 38.5 41.5 42 38 30 26"/>
      <polyline points="15.5 19 18.5 21 22.5 17"/>
    </svg>
  );
}

/** Entities — wifi/network signal (artificial-intelligent-icon-set) */
export function NetworkIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <path d="M7.6,13.6c9-9,23.7-9,32.7,0"/>
      <path d="M13.1,19.1c6-6,15.8-6,21.8,0"/>
      <path d="M19.5,25.5c2.5-2.5,6.6-2.5,9.1,0"/>
      <circle cx="24" cy="31" r="2"/>
      <polyline points="24 33 27 42 24 42"/>
      <polyline points="24 33 21 42 24 42"/>
    </svg>
  );
}

/** About / info (help-center-icon-set) */
export function InfoIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <rect x="21" y="11.5" width="6" height="16"/>
      <rect x="21" y="31.5" width="6" height="5"/>
      <circle cx="24" cy="24" r="18"/>
    </svg>
  );
}

// ── Category icons ─────────────────────────────────────────────────────────────

/** World / global news (breaking-news-icon-set) */
export function GlobalNewsIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 64 64" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.9">
      <path d="M19.3,39.4c9,0,16.4-7.4,16.4-16.4S28.3,6.7,19.3,6.7,2.9,14,2.9,23.1s7.4,16.4,16.4,16.4Z"/>
      <path d="M29.8,10.5c-3.1,1.8-6.7,2.8-10.5,2.8s-7.4-1-10.5-2.8"/>
      <path d="M29.8,35.6c-3.1-1.8-6.7-2.8-10.5-2.8s-7.4,1-10.5,2.8"/>
      <path d="M19.3,39.4c2.7,0,4.8-7.4,4.8-16.4s-2.2-16.4-4.8-16.4-4.8,7.4-4.8,16.4,2.2,16.4,4.8,16.4Z"/>
      <path d="M2.9,23.1c0-2.7,7.3-4.8,16.4-4.8s16.4,2.2,16.4,4.8-7.3,4.8-16.4,4.8S2.9,25.7,2.9,23.1Z"/>
      <polygon points="2.8 43.9 40.1 43.9 48.3 57.3 2.8 57.3 2.8 43.9"/>
      <polyline points="42 47 61.2 47 61.2 54.7 46.7 54.7"/>
      <line x1="8.4" y1="48.4" x2="17.1" y2="48.4"/>
      <line x1="8.4" y1="52.8" x2="37.1" y2="52.8"/>
      <line x1="40.7" y1="25.1" x2="61.2" y2="25.1"/>
      <line x1="40.7" y1="30.3" x2="61.2" y2="30.3"/>
      <line x1="40.7" y1="35.4" x2="61.2" y2="35.4"/>
      <rect x="40.7" y="13.8" width="20.4" height="5.4"/>
    </svg>
  );
}

/** Business / finance (money-icon-set) */
export function FinancialDataIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 64 64" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8">
      <path d="M8.8,4.4h0c2.6,0,4.7,2.1,4.7,4.7v7.9H4v-7.9c0-2.6,2.1-4.7,4.7-4.7Z"/>
      <path d="M8.8,4.4h42v33.2M41.4,56.7H13.5V17.1"/>
      <rect x="18.4" y="10.3" width="17" height="4.4"/>
      <rect x="39.7" y="10.3" width="6.2" height="4.4"/>
      <line x1="18.4" y1="21" x2="26.6" y2="21"/>
      <line x1="18.4" y1="27.3" x2="42.7" y2="27.3"/>
      <line x1="18.4" y1="33.7" x2="42.7" y2="33.7"/>
      <line x1="18.4" y1="40" x2="26.6" y2="40"/>
      <line x1="18.4" y1="46.3" x2="26.6" y2="46.3"/>
      <path d="M49.7,48.5h-1.5c-1.2,0-2.2-1-2.2-2.2s1-2.2,2.2-2.2h3.7"/>
      <path d="M46,52.8h3.7c1.2,0,2.2-1,2.2-2.2s-1-2.2-2.2-2.2h-1.5"/>
      <path d="M48.9,41.7v2.5M48.9,52.8v2.5"/>
      <path d="M48.9,59.6c6.1,0,11.1-5,11.1-11.1s-5-11.1-11.1-11.1-11.1,5-11.1,11.1,5,11.1,11.1,11.1Z"/>
      <line x1="31.5" y1="40" x2="41.8" y2="40"/>
      <line x1="31.5" y1="46.3" x2="38" y2="46.3"/>
    </svg>
  );
}

/** Technology / AI — monitor with circuit nodes (artificial-intelligent-icon-set) */
export function AIIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <rect x="6" y="35" width="36" height="7"/>
      <rect x="17" y="35" width="14" height="3"/>
      <path d="M9.2,14h29.7c1.2,0,2.2,1,2.2,2.2v18.8H7v-18.8c0-1.2,1-2.2,2.2-2.2Z"/>
      <circle cx="24" cy="28" r="2"/>
      <circle cx="32" cy="28" r="2"/>
      <circle cx="16" cy="28" r="2"/>
      <line x1="24" y1="19" x2="24" y2="26"/>
      <polyline points="16 26 16 23 32 23 32 26"/>
    </svg>
  );
}

/** Sports — football / soccer ball (sport-icon-set) */
export function FootballIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 64 64" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8">
      <path d="M32,60.4c15.6,0,28.4-12.8,28.4-28.4S47.6,3.6,32,3.6,3.6,16.4,3.6,32s12.8,28.4,28.4,28.4Z"/>
      <polygon points="32 20.8 36.8 23.6 41.7 26.4 41.7 32 41.7 37.6 36.8 40.4 32 43.2 27.2 40.4 22.3 37.6 22.3 32 22.3 26.4 27.2 23.6 32 20.8"/>
      <polyline points="39 4.5 35.5 8.5 32 12.5 28.5 8.5 25 4.5"/>
      <polyline points="25 59.5 28.5 55.5 32 51.5 35.5 55.5 39 59.5"/>
      <polyline points="11.7 12.2 13.4 17.2 15.1 22.3 9.9 23.3 4.7 24.3"/>
      <polyline points="52.3 51.8 50.6 46.8 48.9 41.7 54.1 40.7 59.3 39.7"/>
      <polyline points="52.3 12.2 50.6 17.2 48.9 22.3 54.1 23.3 59.3 24.3"/>
      <polyline points="11.7 51.8 13.4 46.8 15.1 41.7 9.9 40.7 4.7 39.7"/>
      <path d="M32,51.5v-8.3M32,20.8v-8.3"/>
      <path d="M15.1,41.7l7.2-4.1M41.7,26.4l7.2-4.1"/>
      <path d="M48.9,41.7l-7.2-4.1M22.3,26.4l-7.2-4.1"/>
    </svg>
  );
}

/** Environment / clean energy — EV charging (electrical-vehicle-icon-set) */
export function ChargingIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 64 64" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <line x1="48.5" y1="12.8" x2="30.6" y2="12.8"/>
      <path d="M25.9,19.6l-7,17.4v11.2c0,1.2.9,2.3,2,2.3h27.5"/>
      <rect x="23.2" y="38.4" width="6.1" height="6.7" rx="1" ry="1"/>
      <path d="M48.5,43.8h-14.6c-.5,0-1-.4-1-1v-2.1c0-.5.4-1,1-1h14.6"/>
      <polyline points="48.5 30.3 27.5 30.3 32 18.2 48.5 18.2"/>
      <path d="M21.1,31.7h-4.6c-.8,0-1.3-1.2-.9-2.1l2.4-5.3c.2-.4.5-.7.9-.7h5.4"/>
      <path d="M32.6,50.5v2c0,3-2.2,5.4-4.9,5.4s-4.9-2.4-4.9-5.4v-2"/>
      <polyline points="22.6 17 25.6 13 21.6 13 24.6 9"/>
      <circle cx="23.6" cy="13" r="7"/>
    </svg>
  );
}

/** Culture / media / arts (breaking-news-icon-set) */
export function ImageMediaIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 64 64" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.9">
      <path d="M26.8,8.1h27.8v32.6M15,28.4v-8.5"/>
      <polygon points="26.8 8.1 26.8 20 15 20 26.8 8.1"/>
      <polyline points="10.4 57 14 53.9 19.7 49 25.3 53.9 28.9 57"/>
      <polyline points="32.2 24.3 34.5 21.5 38.1 16.9 41.7 21.5 44 24.3"/>
      <polyline points="25.8 54.3 30.5 50.3 35.3 54.4 38.3 57"/>
      <polyline points="42 21.9 45 18.1 48.1 21.9 50 24.3"/>
      <path d="M25.6,47.7c1.4,0,2.5-1.1,2.5-2.5s-1.1-2.5-2.5-2.5-2.5,1.1-2.5,2.5,1.1,2.5,2.5,2.5Z"/>
      <rect x="10.4" y="39" width="27.8" height="17.9"/>
      <rect x="32.2" y="12.9" width="17.7" height="11.4"/>
      <polygon points="5.6 28.4 35.6 28.4 44.8 40.7 58.4 40.7 58.4 61.2 5.6 61.2 5.6 28.4"/>
      <polyline points="48.9 8.1 48.9 2.8 9.1 2.8 9.1 28.4"/>
    </svg>
  );
}

/** Politics / official statement (breaking-news-icon-set) */
export function OfficialAnnouncementIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 64 64" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.9">
      <polygon points="24.8 4.8 14.8 18.5 19.6 25.3 35.8 20.5 24.8 4.8"/>
      <line x1="22.4" y1="8.1" x2="29.2" y2="17.8"/>
      <path d="M19.6,25.3l-1.4,1c-1.9,1.3-4.5.9-5.8-1-1.3-1.9-.9-4.5,1-5.8l1.4-1"/>
      <path d="M28.2,9.7c1.6-1.1,3.9-.8,5,.9,1.1,1.6.8,3.9-.9,5"/>
      <polyline points="17.6 26.7 24.1 33.5 27.8 30.9 24.7 26.9 25.5 23.6"/>
      <line x1="38.5" y1="6.9" x2="36.1" y2="8.6"/>
      <line x1="41.3" y1="11.3" x2="38.4" y2="12.3"/>
      <line x1="35.3" y1="2.8" x2="33.4" y2="5.2"/>
      <line x1="47" y1="40.3" x2="24.6" y2="40.3"/>
      <line x1="47" y1="44.5" x2="24.6" y2="44.5"/>
      <line x1="35.8" y1="36.1" x2="24.6" y2="36.1"/>
      <path d="M42.5,61.2h-23.2V28.4M19.3,25.5v-.6M35.8,20.5h16.5v30.8"/>
      <polygon points="42.5 61.2 42.5 51.3 52.4 51.3 42.5 61.2"/>
      <rect x="36.4" y="25.2" width="10.7" height="7.3"/>
      <rect x="24.6" y="48.8" width="9.7" height="8.4"/>
    </svg>
  );
}

/** Health — question mark with concentric rings (help-center-icon-set) */
export function HelpIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <path d="M20.6,18.5v-.8c0-.9.8-1.7,1.7-1.7h2.2c1.6,0,2.9,1.3,2.9,2.9v2.4c0,1.6-1.3,2.9-2.9,2.9h-1.2v3.5"/>
      <line x1="23.3" y1="30.6" x2="23.3" y2="32"/>
      <circle cx="24" cy="24" r="18"/>
      <circle cx="24" cy="24" r="14"/>
    </svg>
  );
}

// ── Category icons (ADR-0032 item 1 — 7 added themes) ───────────────────────────
// Authored on a 48×48 grid with strokeWidth 2 + round caps/joins to match the
// help/tech/AI category icons already in use.

/** Science — conical lab flask with liquid + bubbles */
export function ScienceIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <line x1="19" y1="7" x2="29" y2="7"/>
      <path d="M21 7 V20 L11 39 a2 2 0 0 0 1.8 3 H35.2 a2 2 0 0 0 1.8-3 L27 20 V7"/>
      <line x1="16" y1="31" x2="32" y2="31"/>
      <circle cx="21" cy="27" r="1.3"/>
      <circle cx="27" cy="35" r="1.3"/>
    </svg>
  );
}

/** Entertainment — film clapperboard */
export function ClapperboardIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <rect x="8" y="18" width="32" height="23" rx="2"/>
      <path d="M8 18 V13 H40 V18 Z"/>
      <line x1="14" y1="13" x2="11" y2="18"/>
      <line x1="20" y1="13" x2="17" y2="18"/>
      <line x1="26" y1="13" x2="23" y2="18"/>
      <line x1="32" y1="13" x2="29" y2="18"/>
      <line x1="38" y1="13" x2="35" y2="18"/>
    </svg>
  );
}

/** Crime / justice — scales of justice */
export function ScalesIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <circle cx="24" cy="9" r="2"/>
      <line x1="24" y1="11" x2="24" y2="38"/>
      <line x1="13" y1="14" x2="35" y2="14"/>
      <path d="M13 14 L8 25 H18 Z"/>
      <path d="M35 14 L30 25 H40 Z"/>
      <line x1="17" y1="38" x2="31" y2="38"/>
    </svg>
  );
}

/** Education — graduation cap (mortarboard) + tassel */
export function GraduationCapIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <polygon points="24 12 43 19 24 26 5 19"/>
      <path d="M13 22 V30 c0 3 5 5.5 11 5.5 S35 33 35 30 V22"/>
      <line x1="43" y1="19" x2="43" y2="28"/>
      <circle cx="43" cy="29.5" r="1.5"/>
    </svg>
  );
}

/** Lifestyle — coffee cup with steam */
export function CoffeeCupIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <path d="M11 19 H33 V29 a9 9 0 0 1-9 9 H20 a9 9 0 0 1-9-9 Z"/>
      <path d="M33 21 h4 a4 4 0 0 1 0 8 h-4"/>
      <line x1="10" y1="42" x2="34" y2="42"/>
      <line x1="17" y1="9" x2="17" y2="13"/>
      <line x1="23" y1="9" x2="23" y2="13"/>
      <line x1="29" y1="9" x2="29" y2="13"/>
    </svg>
  );
}

/** Religion — domed place of worship (non-denominational) */
export function PlaceOfWorshipIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <line x1="24" y1="6" x2="24" y2="13"/>
      <path d="M14 26 a10 10 0 0 1 20 0"/>
      <line x1="14" y1="26" x2="14" y2="40"/>
      <line x1="34" y1="26" x2="34" y2="40"/>
      <line x1="20" y1="29" x2="20" y2="40"/>
      <line x1="28" y1="29" x2="28" y2="40"/>
      <line x1="10" y1="40" x2="38" y2="40"/>
    </svg>
  );
}

/** Disaster — warning triangle with exclamation */
export function WarningTriangleIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
      <path d="M24 8 L42 39 H6 Z"/>
      <line x1="24" y1="19" x2="24" y2="29"/>
      <line x1="24" y1="33.5" x2="24" y2="34"/>
    </svg>
  );
}

// ── Feed badge icons ───────────────────────────────────────────────────────────

/** Trending news — lightning bolt (breaking-news-icon-set) */
export function TrendingNewsIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 64 64" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.9">
      <path d="M44.7,28.4v29.6c0,1.7-1.4,3.2-3.2,3.2H13.4c-1.7,0-3.2-1.4-3.2-3.2V13.5c0-1.7,1.4-3.2,3.2-3.2h25.9"/>
      <line x1="23.5" y1="14.8" x2="27.6" y2="14.8"/>
      <line x1="31.1" y1="14.8" x2="31.4" y2="14.8"/>
      <line x1="24" y1="55.3" x2="30.9" y2="55.3"/>
      <rect x="16.8" y="21.6" width="13.3" height="16"/>
      <line x1="16.8" y1="43.1" x2="38.1" y2="43.1"/>
      <line x1="16.8" y1="49.1" x2="38.1" y2="49.1"/>
      <polygon points="42.3 2.8 35.3 19.9 42.2 21.7 36.6 38.3 53.8 17.2 48.4 15.8 53.6 2.8 42.3 2.8"/>
    </svg>
  );
}

/** Live report — camera with speech bubble (breaking-news-icon-set) */
export function LiveReportIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 64 64" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.9">
      <path d="M24,14.3h7.8M40.9,14.3h4.6v22.1H14.2v-12.3"/>
      <polygon points="45.5 19.9 54.5 17.3 54.5 25.4 54.5 33.5 45.5 30.8 45.5 25.4 45.5 19.9"/>
      <line x1="20" y1="28.3" x2="39.8" y2="28.3"/>
      <line x1="20" y1="32.1" x2="39.8" y2="32.1"/>
      <line x1="26" y1="23.8" x2="30.4" y2="23.8"/>
      <line x1="35.4" y1="23.8" x2="39.8" y2="23.8"/>
      <path d="M14.2,20.3c3.3,0,6-2.7,6-6s-2.7-6-6-6-6,2.7-6,6,2.7,6,6,6Z"/>
      <circle cx="36.4" cy="14.3" r="4.5"/>
      <path d="M35.3,36.4c0,3-2.4,5.4-5.4,5.4s-5.4-2.4-5.4-5.4"/>
      <path d="M14.2,24.2c5.4,0,9.8-4.4,9.8-9.8s-4.4-9.8-9.8-9.8S4.4,8.9,4.4,14.3s4.4,9.8,9.8,9.8Z"/>
      <polyline points="28.5 41.6 21.2 59.5 17.2 59.5 25.4 39.4"/>
      <polyline points="31.2 41.6 38.5 59.5 42.6 59.5 34.4 39.4"/>
      <path d="M52.2,37.9c4.1,0,7.4,3.3,7.4,7.4s-3.3,7.4-7.4,7.4-1,0-1.5-.1l-4.1,2.9,1.2-4.3c-1.8-1.3-3-3.5-3-5.9,0-4.1,3.3-7.4,7.4-7.4Z"/>
      <line x1="52.2" y1="41.7" x2="52.2" y2="46.2"/>
      <line x1="52.2" y1="48.9" x2="52.2" y2="48.8"/>
    </svg>
  );
}

/** Hot news — flame with newspaper (breaking-news-icon-set) */
export function HotNewsIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 64 64" className={className} fill="none" stroke="currentColor"
      strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.9">
      <path d="M6.8,3.6h0c2.2,0,3.9,1.8,3.9,3.9v11.2H2.8V7.5c0-2.2,1.8-3.9,3.9-3.9Z"/>
      <path d="M6.8,3.6h39.3c2.2,0,3.9,1.8,3.9,3.9v25.2M40,56.1H10.7V18.7"/>
      <path d="M45.2,31c5.9.4,9.4,6.1,8.9,11.9,0,.9-.3,1.7-.5,2.6-.7,2.4,1.5,4.1,3.1,2.9,1.6-1.1,2.5-2.4,3.4-5,.7,1.5,1.1,3.3,1.1,5.1,0,6.6-5.4,12-12,12s-12-5.4-12-12,1.7-7.1,4.5-9.3c-.3,2.8.2,6.2,2.2,6.1,5.1-.3,4.4-10.1,1.3-14.2Z"/>
      <rect x="16.2" y="11" width="28.4" height="5.5"/>
      <rect x="16.2" y="33.2" width="18.5" height="5.5"/>
      <line x1="16.2" y1="25.8" x2="44.5" y2="25.8"/>
      <line x1="16.2" y1="49.7" x2="30.4" y2="49.7"/>
      <line x1="16.2" y1="21.2" x2="30.4" y2="21.2"/>
      <line x1="16.2" y1="45.1" x2="30.4" y2="45.1"/>
    </svg>
  );
}

// ── Category icon map (for convenience) ──────────────────────────────────────

export type CategoryKey =
  | "politics" | "business" | "technology" | "sports"
  | "health" | "environment" | "culture" | "world"
  | "science" | "entertainment" | "crime" | "education"
  | "lifestyle" | "religion" | "disaster";

const CATEGORY_ICONS: Record<CategoryKey, (p: IconProps) => React.ReactElement> = {
  politics:    OfficialAnnouncementIcon,
  business:    FinancialDataIcon,
  technology:  AIIcon,
  sports:      FootballIcon,
  health:      HelpIcon,
  environment: ChargingIcon,
  culture:     ImageMediaIcon,
  world:       GlobalNewsIcon,
  // ADR-0032 item 1 — 7 added themes.
  science:       ScienceIcon,
  entertainment: ClapperboardIcon,
  crime:         ScalesIcon,
  education:     GraduationCapIcon,
  lifestyle:     CoffeeCupIcon,
  religion:      PlaceOfWorshipIcon,
  disaster:      WarningTriangleIcon,
};

export function CategoryIcon({ category, className }: { category: string; className?: string }) {
  const Icon = CATEGORY_ICONS[category as CategoryKey];
  if (!Icon) return null;
  return <Icon className={className} />;
}
