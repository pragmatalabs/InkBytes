"use client";

import { useState } from "react";
import ProceduralCover from "@/components/procedural-cover";
import type { CoverImage } from "@/lib/types";

/**
 * ADR-0034 event cover. Renders the license-clean generic image (Tier 2, Openverse
 * CC0/PDM) when present, layered over the owned procedural cover (Tier 1). If the
 * image is missing or fails to load, the procedural cover shows through — so there
 * is always a safe, on-brand visual and never a broken image. Never the source
 * outlet's og:image.
 */
export default function EventCover({
  id, category, cover, className = "",
}: { id: string; category?: string | null; cover?: CoverImage | null; className?: string }) {
  const [ok, setOk] = useState(true);
  const url = cover && ok ? (cover.thumb || cover.url) : null;
  return (
    <div className={`relative overflow-hidden ${className}`}>
      <ProceduralCover id={id} category={category} className="w-full h-full" />
      {url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={url}
          alt=""
          loading="lazy"
          onError={() => setOk(false)}
          className="absolute inset-0 w-full h-full object-cover"
        />
      )}
    </div>
  );
}
