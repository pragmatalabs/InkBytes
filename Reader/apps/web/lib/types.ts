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

export interface EventPage extends EventSummary {
  event_id: string;
  synthesis_md: string;
  evidence_rail: EvidenceItem[] | string;
  entities: EntityItem[] | string;
  cost_cents: number | null;
  schema_version: string;
}
