/**
 * Reader UI-chrome i18n (EN/ES). Pure dictionary + `t()` — safe to import in
 * server or client code. The *current* language is the reader's global reading
 * pref (`lib/prefs` getLang / `useLang`); chrome localizes client-side and fills
 * after mount (the app's established hydration pattern — server renders the EN
 * default, the client swaps to ES post-mount), so no SSR cookie / ISR regression.
 *
 * Scope is CHROME ONLY — labels, section headers, button text. It does NOT
 * translate content (headlines, synthesis) — that's the outlet/synthesis
 * language, switched per-story via the sibling-event toggle (ADR-0037). Category
 * keys (CULTURE, WORLD…) are taxonomy, left as-is.
 */
import type { Lang } from "@/lib/prefs";

export type { Lang };

type Dict = Record<string, { en: string; es: string }>;

const DICT: Dict = {
  // ── Bottom nav / header ─────────────────────────────────────────────
  nav_brief:    { en: "Brief",    es: "Resumen" },
  nav_outlook:  { en: "Outlook",  es: "Perspectiva" },
  nav_browse:   { en: "Browse",   es: "Explorar" },
  nav_entities: { en: "Entities", es: "Entidades" },

  // ── ☰ menu ──────────────────────────────────────────────────────────
  menu_title:       { en: "Menu",     es: "Menú" },
  menu_story:       { en: "Story",    es: "Historia" },
  menu_saved:       { en: "Saved",    es: "Guardados" },
  menu_settings:    { en: "Settings", es: "Ajustes" },
  menu_about:       { en: "About",    es: "Acerca de" },
  reading_language: { en: "Reading language", es: "Idioma de lectura" },
  paid_adfree:      { en: "Paid · ad-free",   es: "De pago · sin anuncios" },

  // ── Briefing home (feed-client, isBrief) ────────────────────────────
  todays_briefing:  { en: "Today’s briefing",   es: "El resumen de hoy" },
  weekday_briefing: { en: "{weekday}’s briefing", es: "El resumen del {weekday}" },
  story_one:        { en: "story",   es: "historia" },
  story_many:       { en: "stories", es: "historias" },
  min_unit:         { en: "min",     es: "min" },
  read_count:       { en: "read",    es: "leídas" },
  read_tag:         { en: "READ",    es: "LEÍDO" },
  developing_now:   { en: "Developing now", es: "En desarrollo ahora" },
  the_briefing:     { en: "The briefing",   es: "El resumen" },
  left_count:       { en: "left",    es: "restantes" },
  caught_up:        { en: "You’re caught up", es: "Estás al día" },
  caught_up_desc:   { en: "That’s today’s briefing. New stories arrive through the day — or browse everything now.", es: "Ese es el resumen de hoy. Llegan nuevas historias durante el día — o explora todo ahora." },
  updated_since:    { en: "Updated since you last read this", es: "Actualizado desde tu última lectura" },
  // ── Browse header + sections ────────────────────────────────────────
  browse_title:     { en: "Browse",         es: "Explorar" },
  no_stories_yet:   { en: "No stories yet", es: "Aún no hay historias" },
  clear:            { en: "Clear",          es: "Limpiar" },
  clear_filters:    { en: "Clear filters",  es: "Limpiar filtros" },
  search_events:    { en: "Search events…", es: "Buscar eventos…" },
  trending:         { en: "Trending",       es: "Tendencias" },
  topic_one:        { en: "topic",          es: "tema" },
  topic_many:       { en: "topics",         es: "temas" },
  top_story:        { en: "Top story",      es: "Historia principal" },
  more_stories:     { en: "More stories",   es: "Más historias" },
  regional:         { en: "Regional",       es: "Regional" },
  browse_all:       { en: "Browse all stories →", es: "Explorar todas las historias →" },
  show_all_more:    { en: "Show all {n} more {unit}", es: "Ver {n} {unit} más" },
  todays_outlook:   { en: "Today’s Outlook", es: "Perspectiva de hoy" },
  feed_error:       { en: "The news feed is catching its breath", es: "El feed de noticias está tomando aire" },
  no_events:        { en: "No published events yet.", es: "Aún no hay eventos publicados." },
  no_match:         { en: "No events match your filter.", es: "Ningún evento coincide con tu filtro." },

  // ── Event chrome (action bar + eyebrow) ─────────────────────────────
  briefing:      { en: "Briefing",   es: "Resumen" },
  all_events:    { en: "All events", es: "Todas las historias" },
  developing:    { en: "Developing", es: "En desarrollo" },
  save_story:    { en: "Save this story",   es: "Guardar esta historia" },
  remove_saved:  { en: "Remove from saved", es: "Quitar de guardados" },
  read_in:       { en: "Read in {lang}",       es: "Leer en {lang}" },
  not_available_in: { en: "Not available in {lang}", es: "No disponible en {lang}" },

  // ── Provenance ──────────────────────────────────────────────────────
  source_one:  { en: "source",  es: "fuente" },
  source_many: { en: "sources", es: "fuentes" },
  quote_one:   { en: "quote",   es: "cita" },
  quote_many:  { en: "quotes",  es: "citas" },
  corr_strong:   { en: "Strong corroboration",   es: "Corroboración fuerte" },
  corr_moderate: { en: "Moderate corroboration", es: "Corroboración moderada" },
  corr_limited:  { en: "Limited corroboration",  es: "Corroboración limitada" },
  started: { en: "Started", es: "Inició" },
  updated: { en: "Updated", es: "Actualizado" },
  of:      { en: "of",      es: "de" },

  // ── Cover caption ────────────────────────────────────────────────────
  cover_caption: {
    en: "Illustrative. Not a photograph of this event.",
    es: "Ilustrativa. No es una fotografía del hecho.",
  },

  // ── "This story" grid + drawers ─────────────────────────────────────
  this_story:   { en: "This story",  es: "Esta historia" },
  tap_to_open:  { en: "Tap to open", es: "Toca para abrir" },
  next_story:   { en: "Next story",  es: "Siguiente historia" },
  follow_story:    { en: "Follow this story",    es: "Seguir esta historia" },
  following_story: { en: "Following this story", es: "Siguiendo esta historia" },
  sheet_watch:    { en: "Watch",    es: "Ver" },
  sheet_evidence: { en: "Evidence", es: "Evidencia" },
  sheet_entities: { en: "Entities", es: "Entidades" },
  sheet_related:  { en: "Related",  es: "Relacionadas" },
  video_only: { en: "Video only · no outlet imagery", es: "Solo video · sin imágenes de medios" },
  match: { en: "match", es: "coincidencia" },
  now:   { en: "Now",   es: "Ahora" },

  // ── Entities drawer + detail sheet ──────────────────────────────────
  entities_in_story: { en: "Entities in this story", es: "Entidades en esta historia" },
  explore_graph: { en: "Explore the entity graph", es: "Explorar el grafo de entidades" },
  stat_stories: { en: "Stories", es: "Historias" },
  stat_links:   { en: "Links",   es: "Conexiones" },
  stat_today:   { en: "Today",   es: "Hoy" },
  recent_events: { en: "Recent events", es: "Eventos recientes" },
  connections:   { en: "Connections",   es: "Conexiones" },
  view_full_profile: { en: "View full profile →", es: "Ver perfil completo →" },
  mentioned_in_story: {
    en: "Mentioned in this story. Open the full profile for this {noun}’s stats, recent coverage, and connections.",
    es: "Mencionado en esta historia. Abre el perfil completo para ver estadísticas, cobertura reciente y conexiones de {noun}.",
  },

  // ── Entity type nouns ───────────────────────────────────────────────
  noun_person: { en: "Person",       es: "Persona" },
  noun_org:    { en: "Organisation", es: "Organización" },
  noun_loc:    { en: "Place",        es: "Lugar" },
  noun_event:  { en: "Event",        es: "Evento" },
  noun_other:  { en: "Topic",        es: "Tema" },
};

/** Look up a chrome string in `lang`, with optional `{var}` interpolation. */
export function t(lang: Lang, key: keyof typeof DICT, vars?: Record<string, string | number>): string {
  const entry = DICT[key];
  let s = entry ? entry[lang] : String(key);
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
  return s;
}

const NOUN_KEY: Record<string, keyof typeof DICT> = {
  PERSON: "noun_person", ORG: "noun_org", LOC: "noun_loc", EVENT: "noun_event", OTHER: "noun_other",
};

/** Friendly, localized noun for an entity type (defaults to "Topic"/"Tema"). */
export function entityNoun(lang: Lang, type: string | undefined): string {
  return t(lang, NOUN_KEY[(type ?? "").toUpperCase()] ?? "noun_other");
}
