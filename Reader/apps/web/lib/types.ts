export interface Outlet {
  id: string;
  name: string;
  display_name: string;
  url: string;
  region: string;
  language: string;
  vertical: string;
  active: boolean;
  priority: number;
  article_count: number;
  last_seen: string | null;
  events_contributed: number;
}

/** A trending story topic from /topics/trending (ADR-0027). */
export interface TrendingTopic {
  topic: string;
  event_count: number;
  article_count: number;
  /** Representative theme (most common among the topic's articles) — drives
   *  the chip's color accent. May be null for legacy/unthemed topics. */
  theme: string | null;
}

/** ADR-0034 Tier 2 — a license-clean generic cover image (provenance kept). */
export interface CoverImage {
  url: string;
  thumb?: string | null;
  license?: string | null;
  license_url?: string | null;
  /** Set for CC BY / BY-SA (must be credited); null for CC0 / public domain. */
  attribution?: string | null;
  source_url?: string | null;
  provider?: string | null;
}

export interface EventSummary {
  id: string;
  headline: string;
  freshness_at: string;
  /** ADR-0033: when the story actually happened (immutable first_seen_at).
   *  The displayed date — a 9-day-old story reads "9d ago", never "today",
   *  regardless of later tangential touches. Absent on pre-ADR-0033 responses. */
  occurred_at?: string;
  /** ADR-0033: last *material* development — drives ranking (mirrors the
   *  server's lifecycle ordering). Absent on pre-ADR-0033 responses. */
  last_material_update_at?: string;
  published_at: string;
  source_count: number;
  article_count: number;
  topic: string | null;
  /** ADR-0037 cross-language dedup: false when a richer same-story sibling in
   *  another language exists, so the "All" feed shows only the primary. Absent
   *  (treated as true) on pre-ADR-0037 / lifecycle-off responses. */
  primary?: boolean;
  /** ADR-0037: same-story siblings in OTHER languages → { "es": "<page_id>" }.
   *  Powers the "also in {lang}" link. */
  also_languages?: Record<string, string>;
  /** ADR-0034 Tier 2: license-clean generic cover (Openverse CC0/PDM). Null →
   *  the Reader renders the owned procedural cover (Tier 1). */
  cover_image?: CoverImage | null;
  /** Broad enrichment theme (Curator ADR-0032, 15 values): politics | business |
   *  technology | sports | health | environment | culture | world | science |
   *  entertainment | crime | education | lifestyle | religion | disaster */
  category: string | null;
  language: string;
  outlet_names: string[];
  // Phase 1 additions — derived server-side from articles + pages
  /** First ~180 chars of synthesis_md. Reader trims to first sentence for dek. */
  synthesis_excerpt: string | null;
  /** Average article factuality scaled 0–100. null when no scores available. */
  avg_factuality: number | null;
  /** 7 integers: article counts in 6-hour buckets over the last 42 h. */
  coverage_spark: number[];
  /** Cover image URL: best og:image / top_image from event articles. null when
   *  no article has a lead_image (pre-migration rows, or outlet has no og:image). */
  lead_image: string | null;
  /** True when at least one article came from a global-region outlet (AP, Reuters,
   *  BBC, CNN, NPR, etc.). Drives the +6 h freshness bonus in the API ORDER BY
   *  (ADR-0017) and the "Regional" section divider in the Reader. */
  has_global_outlet: boolean;
}

export interface EvidenceItem {
  url: string;
  quote: string;
  source_name: string;
}

export interface EntityItem {
  name: string;
  type: "PERSON" | "ORG" | "LOC" | "EVENT" | "OTHER";
}

// ── Entity graph (ADR-0005, Approach A) ────────────────────────────────────

export type EntityType = "PERSON" | "ORG" | "LOC" | "EVENT" | "OTHER";

export interface GraphPageRef {
  id: string;
  headline: string;
  source_count: number;
  freshness_at: string;
}

export interface GraphNode {
  id: string;          // lowercased entity name — stable key
  label: string;       // display name
  type: EntityType;
  event_count: number;
  pages: GraphPageRef[];
  // Wikidata/Commons enrichment (people; ADR-0034 companion) — optional.
  image?: string | null;              // license-clean Commons portrait (thumb)
  description?: string | null;        // Wikidata one-liner (es|en)
  image_attribution?: string | null;  // required for CC BY / BY-SA
  image_source?: string | null;       // Commons file page
}

export interface GraphEdge {
  source: string;      // node id
  target: string;      // node id
  weight: number;      // events in common
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  meta: { node_count: number; edge_count: number; event_count: number };
}

/** Related event card — returned by GET /events/{id}/related (ADR-0005). */
export interface RelatedEvent {
  id: string;
  headline: string;
  freshness_at: string;
  topic: string | null;
  language: string;
  source_count: number;
  outlet_names: string[];
  /** Composite similarity score: entity_overlap × topic_multiplier */
  score: number;
}

/** One media item in the IllustrateSkill rail — image or video ranked by score. */
export interface MediaRailItem {
  url: string;
  thumb_url: string | null;
  type: "image" | "video";
  title: string | null;
  source_domain: string | null;
  published_at: string | null;
  width: number | null;
  height: number | null;
  score: number;
}

/** One article's contribution to the event timeline. */
export interface TimelineEntry {
  outlet_name: string;
  title: string;
  published_at: string | null;
  scraped_at: string;
}

/** A previous headline preserved when the story's title evolved (ADR-0035). */
export interface TitleHistoryEntry {
  headline: string;
  at: string | null;
  sources: number;
}

// ── Today's [Topic] Outlook — daily editorial (ADR-0008) ───────────────────
export interface OutlookTimelineItem {
  id: string;
  headline: string;
  freshness_at: string;
  source_count: number;
}
/** A daily editorial column for a topic (empty object when no edition exists). */
export interface Outlook {
  theme: string;
  language: string;
  edition_date: string;
  persona: string;
  headline: string;
  body_md: string;
  model: string;
  timeline: OutlookTimelineItem[];
  available_dates: string[];
}
export interface OutlookTopic {
  theme: string;
  edition_date: string;
  headline: string;
  persona: string;
}
/** One edition in the date-grouped Outlook archive (/outlook/archive). */
export interface OutlookArchiveEntry {
  edition_date: string;
  theme: string;
  headline: string;
  persona: string;
}

export interface EventPage extends EventSummary {
  event_id: string;
  synthesis_md: string;
  evidence_rail: EvidenceItem[] | string;
  entities: EntityItem[] | string;
  cost_cents: number | null;
  schema_version: string;
  /** Story development timeline: articles ordered by published_at. */
  timeline: TimelineEntry[] | null;
  /** Prior headlines, oldest→newest, kept as the story's title evolved (ADR-0035). */
  title_history?: TitleHistoryEntry[] | string;
  /** IllustrateSkill media — images + videos ranked by score. Empty for pre-Phase-2 pages. */
  media_rail?: MediaRailItem[];
  /**
   * Event lifecycle status (ADR-0013).
   * 'published' — active story, receiving new articles.
   * 'concluded' — story has gone quiet; page remains visible with a badge.
   */
  status?: "published" | "concluded";
}
