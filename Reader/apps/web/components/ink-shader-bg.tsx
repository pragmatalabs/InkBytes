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

    // Honor reduced-motion by NOT animating — but still show the ink as a
    // single static frame (the engine warms up the field on construction, so
    // one render() paints a still ink image). Full motion otherwise.
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
      // Animated path: tuned for a SUBTLE backdrop — steady-state field density
      // ≈ ambient/(1−dissip) ≈ 0.0028/0.027 ≈ 0.10, dark-dominant (white text
      // legible) with thin luminous ribbons from the drifting emitter + drag.
      // Reduced-motion path: a single STATIC frame, but with a stronger emitter
      // during the constructor warm-up so the still image carries visible ink
      // ribbons (the gentle steady-state alone is nearly imperceptible). Higher
      // emit (concentrated strokes) + low ambient keeps dark gaps for text.
      wall = new InkWall(
        canvas,
        reduce
          ? { palette, speed: 0.0024, dissip: 0.982, flow: 2.6, emit: 0.03, ambient: 0.004 }
          : { palette, speed: 0.0024, dissip: 0.973, flow: 2.6, emit: 0.006, ambient: 0.0028 }
      );
      if (reduce) {
        wall!.render(); // static frame, no rAF loop, no pointer stir
        return () => wall?.destroy();
      }
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
