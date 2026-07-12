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
  // CC BY / BY-SA require a visible credit; CC0 / public domain do not.
  const credit = url && cover?.attribution ? cover : null;
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
      {credit && (
        // NOT an <a>: feed cards wrap EventCover in their own <Link>, and nested
        // anchors are invalid HTML — the parser DOM-corrects them (breaking the
        // card) and React logs a hydration error. A button + window.open keeps
        // the CC credit clickable everywhere, including the event-page hero.
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            const href = credit.source_url || credit.license_url;
            if (href) window.open(href, "_blank", "noopener,noreferrer");
          }}
          className="absolute bottom-0 right-0 max-w-full truncate bg-black/45 text-white/90 text-[9px] leading-tight px-1.5 py-0.5 rounded-tl hover:bg-black/65 cursor-pointer"
          title={`${credit.attribution} — ${credit.license ?? ""} (via ${credit.provider ?? "Wikimedia"})`}
        >
          {credit.attribution} · {credit.license}
        </button>
      )}
    </div>
  );
}
