"use client";

import { useEffect, useState } from "react";
import { isFollowed, toggleFollowed, FOLLOWED_EVENT } from "@/lib/followed";
import { useLang } from "@/lib/prefs";
import { t } from "@/lib/i18n";

/**
 * "Follow this story" — full-width toggle (prototype). Subscribes the reader to
 * a story's updates; the Saved screen (Slice B) lists followed stories with an
 * "Updated" badge. Persists to localStorage (lib/followed). Reads state on mount
 * + on the same-tab change event so every follow control stays in sync.
 */
export default function FollowButton(props: {
  eventId: string;
  headline: string;
  category: string | null;
  language: string;
}) {
  const { eventId, headline, category, language } = props;
  const lang = useLang();
  const [following, setFollowing] = useState(false);

  useEffect(() => {
    const sync = () => setFollowing(isFollowed(eventId));
    sync();
    window.addEventListener(FOLLOWED_EVENT, sync);
    window.addEventListener("storage", sync); // cross-tab
    return () => {
      window.removeEventListener(FOLLOWED_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, [eventId]);

  return (
    <button
      type="button"
      onClick={() => setFollowing(toggleFollowed({ id: eventId, headline, category, language }))}
      aria-pressed={following}
      className={`mb-10 w-full flex items-center justify-center gap-2 py-3.5 border text-[13.5px] font-semibold tracking-tight transition-colors ${
        following
          ? "border-[var(--accent)] bg-[var(--accent)] text-white"
          : "border-[var(--border)] bg-white text-[var(--ink)] hover:border-[var(--ink)]"
      }`}
    >
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
        {following ? <path d="M20 6 9 17l-5-5" /> : <path d="M12 5v14M5 12h14" />}
      </svg>
      {following ? t(lang, "following_story") : t(lang, "follow_story")}
    </button>
  );
}
