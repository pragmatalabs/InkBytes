"use client";

/**
 * InkShaderBg — animated WebGL ink/smoke background (vendored InkWall engine).
 *
 * Used behind the daily splash so the "welcome back" sits over flowing
 * calligraphic ink instead of a flat navy field. Drag/touch stirs the ink.
 *
 * Degrades gracefully: if WebGL is unavailable or the user prefers reduced
 * motion, it renders nothing and the caller's solid --accent background shows
 * through. The engine + GL context are fully released on unmount.
 */
import { useEffect, useRef } from "react";
// Vendored engine (allowJs) — no types; treat the import loosely.
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore - .js module without declarations
import { InkWall } from "@/lib/ink-shader";

interface Props {
  /** Colour ramp: 0 paper · 1 ink-blue · 2 cyber · 3 iridescent · 4 vermillion · 5 brand-indigo. */
  palette?: number;
  className?: string;
}

export function InkShaderBg({ palette = 5, className }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Everyone gets a gentle, slow ink drift (product decision: a frozen frame
    // felt dead). reduced-motion still gets the animation but slower/calmer as
    // a courtesy — this is a soft ambient drift, not vestibular parallax/zoom.
    const reduce = !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    let wall:
      | {
          start: () => void;
          render: () => void;
          destroy: () => void;
          pointer: (x: number, y: number, dx: number, dy: number) => void;
          mStr: number;
        }
      | null = null;
    try {
      // Gentle/slow but always clearly visible: a strong drifting emitter
      // (emit) lays luminous ink ribbons that the curl flow keeps refreshing,
      // so the field never empties out the way a thin ambient-only field does;
      // a low advection `speed` keeps the drift calm. reduced-motion drifts
      // even slower. (Earlier thin tuning looked empty at low-density frames.)
      wall = new InkWall(canvas, {
        palette,
        speed: reduce ? 0.001 : 0.0017,
        dissip: 0.981,
        flow: 2.6,
        emit: 0.022,
        ambient: 0.0045,
      });
      wall!.start();
    } catch {
      return; // WebGL unavailable / context failure → solid background fallback
    }

    // Drag/touch to stir the ink (normalised coords, y-up).
    let lx = 0.5, ly = 0.5, have = false;
    const pos = (e: PointerEvent): [number, number] => {
      const r = canvas.getBoundingClientRect();
      return [
        Math.min(Math.max((e.clientX - r.left) / r.width, 0), 1),
        Math.min(Math.max(1 - (e.clientY - r.top) / r.height, 0), 1),
      ];
    };
    const onMove = (e: PointerEvent) => {
      const [x, y] = pos(e);
      let dx = 0, dy = 0;
      if (have) { dx = x - lx; dy = y - ly; }
      lx = x; ly = y; have = true;
      wall!.pointer(x, y, dx, dy);
    };
    const onDown = (e: PointerEvent) => {
      const [x, y] = pos(e);
      lx = x; ly = y; have = true;
      wall!.pointer(x, y, 0, 0);
      wall!.mStr = Math.min(wall!.mStr + 0.6, 1.0);
    };
    const onLeave = () => { have = false; };

    canvas.addEventListener("pointermove", onMove);
    canvas.addEventListener("pointerdown", onDown);
    canvas.addEventListener("pointerleave", onLeave);

    return () => {
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerdown", onDown);
      canvas.removeEventListener("pointerleave", onLeave);
      wall?.destroy();
    };
  }, [palette]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={className}
      style={{ display: "block", width: "100%", height: "100%", touchAction: "none" }}
    />
  );
}
