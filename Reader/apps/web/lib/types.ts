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
  language: string;
  outlet_names: string[];
  // Phase 1 additions — derived server-side from articles + pages
  /** First ~180 chars of synthesis_md. Reader trims to first sentence for dek. */
  synthesis_excerpt: string | null;
  /** Average article factuality scaled 0–100. null when no scores available. */
  avg_factuality: number | null;
  /** 7 integers: article counts in 6-hour buckets over the last 42 h. */
  coverage_spark: number[];
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
}
