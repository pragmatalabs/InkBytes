-- Soak report: scheduled-cycle health over the last 24h.
-- Run on the droplet:  docker exec -i inkbytes-postgres psql -U inkbytes -d inkbytes < soak-report.sql
-- Or from the repo:    make soak-report
--
-- "parse_pct" is successful / NEW (non-duplicate) articles — the stored
-- success_rate counts duplicates as failures, which makes healthy outlets
-- look broken. An outlet is green when parse_pct >= 80 (or when it staged
-- nothing because nothing new was published, tot = dup).

\echo '── Cycles in the last 24h ─────────────────────────────────────'
SELECT date_trunc('hour', started_at) AS cycle_hour,
       count(*)                       AS outlet_sessions,
       sum(successful_articles)       AS ok,
       sum(total_articles - duplicates_total) AS new_articles
FROM scrape_sessions
WHERE started_at > NOW() - INTERVAL '24 hours'
GROUP BY 1 ORDER BY 1 DESC;

\echo ''
\echo '── Per-outlet parse success (last 24h) ────────────────────────'
SELECT split_part(session_id, '-', 3) AS outlet,
       count(*)                 AS runs,
       sum(total_articles)      AS tot,
       sum(successful_articles) AS ok,
       sum(duplicates_total)    AS dup,
       CASE WHEN sum(total_articles) - sum(duplicates_total) > 0
            THEN round(100.0 * sum(successful_articles)
                       / (sum(total_articles) - sum(duplicates_total)), 1)
            ELSE NULL END AS parse_pct,
       CASE
         WHEN sum(total_articles) = 0 THEN 'no-urls'
         WHEN sum(total_articles) - sum(duplicates_total) = 0 THEN 'all-dup (ok)'
         WHEN sum(successful_articles)::numeric
              / NULLIF(sum(total_articles) - sum(duplicates_total), 0) >= 0.8 THEN 'GREEN'
         ELSE 'RED'
       END AS verdict
FROM scrape_sessions
WHERE started_at > NOW() - INTERVAL '24 hours'
GROUP BY 1 ORDER BY verdict, ok DESC;

\echo ''
\echo '── Pipeline output (last 24h) ─────────────────────────────────'
SELECT (SELECT count(*) FROM articles WHERE scraped_at   > NOW() - INTERVAL '24 hours') AS articles_24h,
       (SELECT count(*) FROM events   WHERE first_seen_at > NOW() - INTERVAL '24 hours') AS new_events_24h,
       (SELECT count(*) FROM pages    WHERE created_at   > NOW() - INTERVAL '24 hours') AS new_pages_24h;
