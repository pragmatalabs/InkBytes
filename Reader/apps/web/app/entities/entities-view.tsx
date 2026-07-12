"use client";

/**
 * EntitiesView — responsive shell for /entities.
 *
 * Desktop (≥ sm): the force graph, unchanged.
 * Mobile  (< sm): the EntityBrowser (tabs → cards → bottom sheet); the force
 * graph stays reachable behind "Full graph" with a back bar. The graph is a
 * deliberate opt-in on phones — physics + tiny targets make it a poor default
 * there (Phase 1 of the entity rework).
 */

import { useState } from "react";
import type { GraphData } from "@/lib/types";
import GraphClient from "./graph-client";
import EntityBrowser from "./entity-browser";

export default function EntitiesView({ data }: { data: GraphData }) {
  const [mobileGraph, setMobileGraph] = useState(false);

  return (
    <>
      {/* Mobile */}
      <div className="sm:hidden">
        {mobileGraph ? (
          <>
            <div className="max-w-3xl mx-auto px-4 pt-4">
              <button onClick={() => setMobileGraph(false)}
                className="flex items-center gap-1.5 text-xs font-semibold text-[var(--ink-muted)] hover:text-[var(--ink)] transition-colors">
                ← Entity browser
              </button>
            </div>
            <GraphClient data={data} />
          </>
        ) : (
          <EntityBrowser data={data} onShowGraph={() => setMobileGraph(true)} />
        )}
      </div>

      {/* Desktop */}
      <div className="hidden sm:block">
        <GraphClient data={data} />
      </div>
    </>
  );
}
