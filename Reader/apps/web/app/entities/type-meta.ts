import type { EntityType } from "@/lib/types";

// Shared entity-type metadata — used by the desktop force graph (graph-client)
// and the mobile entity browser (entity-browser). One palette, one order.
export const TYPE_META: Record<EntityType, { label: string; color: string }> = {
  PERSON: { label: "People",        color: "#3b82f6" },
  ORG:    { label: "Organisations", color: "#8b5cf6" },
  LOC:    { label: "Places",        color: "#10b981" },
  EVENT:  { label: "Events",        color: "#f97316" },
  OTHER:  { label: "Topics",        color: "#6b7280" },
};

export const TYPE_ORDER: EntityType[] = ["PERSON", "ORG", "LOC", "EVENT", "OTHER"];
