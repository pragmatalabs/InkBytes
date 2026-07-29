"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { relativeTime } from "@/lib/api";
import { themeAccent } from "@/lib/theme-colors";
import { listFollowed, FOLLOWED_EVENT, type FollowedStory } from "@/lib/followed";
import { listSaved as listSavedEvents, SAVED_EVENT as SAVED_EVENTS_EVENT, type SavedEvent } from "@/lib/saved-events";
import SavedOutlooks from "@/components/saved-outlooks";

/**
 * Saved screen (mobile redesign, Slice B1) — the destination for the Save and
 * Follow buttons. Reads three localStorage stores (a signed-in profile later):
 * followed stories, saved events, saved outlooks. Lists render after mount to
 * avoid an SSR/hydration mismatch (localStorage is client-only).
 */

const SECTION = "flex items-center gap-2 mb-3 text-[11px] font-bold uppercase tracking-widest";

function StoryRow({
  id,
  headline,
  category,
  ts,
  verb,
}: {
  id: string;
  headline: string;
  category: string | null;
  ts: number;
  verb: string;
}) {
  return (
    <Link
      href={`/event/${id}`}
      className="grid grid-cols-[4px_1fr] gap-3.5 py-3.5 border-b border-[var(--border)] group"
    >
      <i className="block rounded-sm" style={{ background: themeAccent(category) }} />
      <div className="min-w-0">
        <div className="text-[14.5px] font-semibold leading-snug tracking-tight group-hover:text-[var(--accent)] transition-colors">
          {headline}
        </div>
        <div className="mt-1 flex items-center gap-2 text-[11px] text-[var(--ink-muted)]">
          {category && <span className="font-mono uppercase tracking-wide">{category}</span>}
          <span aria-hidden>·</span>
          <span suppressHydrationWarning>
            {verb} {relativeTime(new Date(ts).toISOString())}
          </span>
        </div>
      </div>
    </Link>
  );
}

function EmptyLine({ children }: { children: React.ReactNode }) {
  return <p className="text-[12.5px] leading-relaxed text-[var(--ink-muted)] mb-8">{children}</p>;
}

export default function SavedPage() {
  const [following, setFollowing] = useState<FollowedStory[] | null>(null);
  const [saved, setSaved] = useState<SavedEvent[] | null>(null);

  useEffect(() => {
    const sync = () => {
      setFollowing(listFollowed());
      setSaved(listSavedEvents());
    };
    sync();
    window.addEventListener(FOLLOWED_EVENT, sync);
    window.addEventListener(SAVED_EVENTS_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(FOLLOWED_EVENT, sync);
      window.removeEventListener(SAVED_EVENTS_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
      <h1 className="text-[1.6rem] sm:text-3xl font-bold tracking-tight mb-8">Saved</h1>

      {/* Following */}
      <section className="mb-9">
        <div className={`${SECTION} text-[var(--accent)]`}>
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Following
        </div>
        {following && following.length > 0 ? (
          following.map((f) => (
            <StoryRow key={f.id} id={f.id} headline={f.headline} category={f.category} ts={f.followedAt} verb="Followed" />
          ))
        ) : (
          <EmptyLine>
            Follow a story from its page to track how it develops — it&rsquo;ll show up here.
          </EmptyLine>
        )}
      </section>

      {/* Saved for offline / read later */}
      <section className="mb-9">
        <div className={`${SECTION} text-[var(--accent)]`}>
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
          </svg>
          Saved stories
        </div>
        {saved && saved.length > 0 ? (
          saved.map((s) => (
            <StoryRow key={s.id} id={s.id} headline={s.headline} category={s.category} ts={s.savedAt} verb="Saved" />
          ))
        ) : (
          <EmptyLine>Tap the bookmark on any story to save it for later.</EmptyLine>
        )}
      </section>

      {/* Saved outlooks — self-contained (renders nothing when empty) */}
      <SavedOutlooks />
    </div>
  );
}
