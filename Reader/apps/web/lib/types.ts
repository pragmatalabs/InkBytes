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

export interface EventSummary {
  id: string;
  headline: string;
  freshness_at: string;
  published_at: string;
  source_count: number;
  article_count: number;
  topic: string | null;
  /** Broad category derived server-side from topic: politics | business | technology |
   *  sports | health | environment | culture | world */
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

export interface EventPage extends EventSummary {
  event_id: string;
  synthesis_md: string;
  evidence_rail: EvidenceItem[] | string;
  entities: EntityItem[] | string;
  cost_cents: number | null;
  schema_version: string;
  /** Story development timeline: articles ordered by published_at. */
  timeline: TimelineEntry[] | null;
  /** IllustrateSkill media — images + videos ranked by score. Empty for pre-Phase-2 pages. */
  media_rail?: MediaRailItem[];
  /**
   * Event lifecycle status (ADR-0013).
   * 'published' — active story, receiving new articles.
   * 'concluded' — story has gone quiet; page remains visible with a badge.
   */
  status?: "published" | "concluded";
}
