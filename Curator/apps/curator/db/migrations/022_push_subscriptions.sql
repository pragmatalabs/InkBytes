-- 022 — Web Push subscriptions for the PWA "Daily Outlook ready" notification.
-- One row per browser push subscription (opt-in). `topics` lets a subscription
-- choose what it wants notified; today only 'outlook-daily' is used.
CREATE TABLE IF NOT EXISTS push_subscriptions (
    endpoint    TEXT PRIMARY KEY,             -- the push service URL (unique per sub)
    p256dh      TEXT NOT NULL,                -- client public key (payload encryption)
    auth        TEXT NOT NULL,                -- client auth secret
    topics      TEXT[] NOT NULL DEFAULT '{outlook-daily}',
    lang        TEXT NOT NULL DEFAULT 'es',   -- preferred edition language
    user_agent  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_sent_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_push_subs_topics ON push_subscriptions USING GIN (topics);
