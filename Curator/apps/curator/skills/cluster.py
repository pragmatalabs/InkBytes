"""Skill 2 — CLUSTER.

Given a freshly-enriched article (with embedding + entities), find its
event cluster:

  1. Pull recent articles (within `recent_window_hours`).
  2. Compute cosine similarity via the pgvector `<=>` operator.
  3. Among neighbours with similarity ≥ threshold, require ≥ N entity
     overlap.
  4. If a match exists, attach to that event_id; otherwise create a new
     event with this article as the seed.

Returns the resolved event_id and similarity distance.
"""
from __future__ import annotations

import logging
from typing import Any

import ulid

from core.config import ClusterCfg
from services.database_service import DatabaseService, _vector_literal

logger = logging.getLogger(__name__)


class ClusterResult:
    __slots__ = ("event_id", "distance", "is_new_event", "source_count")

    def __init__(self, event_id: str, distance: float, is_new_event: bool, source_count: int):
        self.event_id = event_id
        self.distance = distance
        self.is_new_event = is_new_event
        self.source_count = source_count


class ClusterSkill:
    name = "cluster"

    def __init__(self, db: DatabaseService, cfg: ClusterCfg) -> None:
        self.db = db
        self.cfg = cfg

    async def run(
        self,
        *,
        article_id: str,
        embedding: list[float],
        entities: list[dict[str, Any]],
        outlet_id: str,
        language: str,
        scraped_at: Any,
    ) -> ClusterResult:
        threshold_distance = 1.0 - self.cfg.similarity_threshold  # cosine distance
        entity_names = {e["name"].lower() for e in entities if e.get("name")}

        async with self.db.pool.acquire() as conn:  # type: ignore[union-attr]
            # ADR-0031: centroid-linkage + entity-specificity (mega-bucket fix),
            # flag-gated. Off → the legacy single-linkage path below, unchanged.
            if self.cfg.precision_mode:
                return await self._run_precision(
                    conn, article_id=article_id, embedding=embedding,
                    entity_names=entity_names, language=language, scraped_at=scraped_at,
                )
            # Pull candidate neighbours (recent + same language + same event_id if any).
            rows = await conn.fetch(
                """
                SELECT a.id, a.event_id, a.outlet_id,
                       (a.embedding <=> $1::vector) AS distance,
                       ARRAY(SELECT lower(name) FROM entities WHERE article_id = a.id) AS entities
                  FROM articles a
                 WHERE a.embedding IS NOT NULL
                   AND a.language = $2
                   AND a.scraped_at > NOW() - ($3 || ' hours')::interval
                   AND a.id <> $4
                 ORDER BY a.embedding <=> $1::vector ASC
                 LIMIT 20
                """,
                _vector_literal(embedding),
                language,
                str(self.cfg.recent_window_hours),
                article_id,
            )

            # Pick the closest candidate that also passes entity overlap.
            for row in rows:
                if row["distance"] > threshold_distance:
                    break  # subsequent rows are even further
                overlap = entity_names & set(row["entities"] or [])
                if len(overlap) >= self.cfg.entity_overlap_min and row["event_id"]:
                    # Join the existing event.
                    src_count = await conn.fetchval(
                        "SELECT COUNT(DISTINCT outlet_id) FROM articles WHERE event_id = $1",
                        row["event_id"],
                    )
                    # ADR-0033 P0: a "material" attach (core-cluster, distance ≤
                    # material_max_distance) re-floats the event (bumps the
                    # material clock); a tangential re-mention still joins the
                    # event but must NOT re-float it as if it happened today.
                    material = float(row["distance"]) <= self.cfg.material_max_distance
                    await conn.execute(
                        """
                        UPDATE articles SET event_id = $2, cluster_distance = $3
                         WHERE id = $1
                        """,
                        article_id, row["event_id"], float(row["distance"]),
                    )
                    await conn.execute(
                        """
                        UPDATE events
                           SET last_updated_at = NOW(),
                               last_material_update_at = CASE WHEN $2
                                   THEN NOW() ELSE last_material_update_at END,
                               article_count = (SELECT COUNT(*) FROM articles WHERE event_id = $1),
                               source_count  = (SELECT COUNT(DISTINCT outlet_id) FROM articles WHERE event_id = $1)
                         WHERE id = $1
                        """,
                        row["event_id"], material,
                    )
                    # Read back the authoritative distinct-outlet count we just
                    # wrote. (Previously this was approximated in Python from the
                    # candidate set, which under-counted and suppressed synthesis
                    # for genuine 2-source events.)
                    new_source_count = await conn.fetchval(
                        "SELECT source_count FROM events WHERE id = $1", row["event_id"]
                    )

                    # Breaking-news detector (ADR-0024 + 2026-06-12 velocity fix):
                    # an event is breaking when ≥2 distinct pulse outlets have
                    # articles whose scraped_at fall within breaking_window_minutes
                    # OF EACH OTHER (a coverage surge), measured back from the most
                    # recent pulse article — NOT the event's age at processing time
                    # (which pipeline lag made impossible to satisfy). scraped_at is
                    # harvest time, so this is lag-immune. The recency guard stops
                    # reprocessing from retro-flagging an old surge. Fires once
                    # (breaking_at IS NULL); only an attach can trigger it.
                    if self.cfg.breaking_window_minutes > 0:
                        flagged = await conn.fetchval(
                            """
                            WITH pulse_arts AS (
                                SELECT a.outlet_id, a.scraped_at
                                  FROM articles a
                                  JOIN outlets o ON o.id = a.outlet_id
                                 WHERE a.event_id = $1 AND o.pulse
                            ),
                            latest AS (SELECT MAX(scraped_at) AS mx FROM pulse_arts)
                            UPDATE events e
                               SET breaking_at    = NOW(),
                                   breaking_until = NOW() + ($2 || ' hours')::interval
                             WHERE e.id = $1
                               AND e.breaking_at IS NULL
                               AND (SELECT mx FROM latest) > NOW() - ($4 || ' hours')::interval
                               AND (
                                     SELECT COUNT(DISTINCT pa.outlet_id)
                                       FROM pulse_arts pa, latest
                                      WHERE pa.scraped_at
                                            > latest.mx - ($3 || ' minutes')::interval
                                   ) >= 2
                            RETURNING e.id
                            """,
                            row["event_id"],
                            str(self.cfg.breaking_ttl_hours),
                            str(self.cfg.breaking_window_minutes),
                            str(self.cfg.breaking_recency_hours),
                        )
                        if flagged:
                            logger.info(
                                "BREAKING event %s — ≥2 pulse outlets within %d min "
                                "of each other (demotes in %dh)",
                                flagged, self.cfg.breaking_window_minutes,
                                self.cfg.breaking_ttl_hours,
                            )
                    logger.info(
                        "CLUSTER attach %s -> %s (distance=%.3f, overlap=%d, sources=%d, %s)",
                        article_id, row["event_id"], row["distance"], len(overlap),
                        int(new_source_count), "material" if material else "tangential",
                    )
                    return ClusterResult(
                        event_id=row["event_id"],
                        distance=float(row["distance"]),
                        is_new_event=False,
                        source_count=int(new_source_count),
                    )

            # No suitable neighbour → create a new event with this article as seed.
            new_event_id = ulid.new().str
            await conn.execute(
                """
                INSERT INTO events (id, first_seen_at, last_updated_at,
                                    last_material_update_at,
                                    source_count, article_count, language)
                VALUES ($1, $2, $2, $2, 1, 1, $3)
                """,
                new_event_id, scraped_at, language,
            )
            await conn.execute(
                "UPDATE articles SET event_id = $2, cluster_distance = 0 WHERE id = $1",
                article_id, new_event_id,
            )
            logger.info("CLUSTER seed new event %s for article %s", new_event_id, article_id)
            return ClusterResult(event_id=new_event_id, distance=0.0, is_new_event=True, source_count=1)

    async def _maybe_flag_breaking(self, conn, event_id: str) -> None:
        """ADR-0024 velocity breaking detector — fires once when ≥2 distinct pulse
        outlets have articles within breaking_window_minutes of each other. Shared
        by the legacy and precision attach paths."""
        if self.cfg.breaking_window_minutes <= 0:
            return
        flagged = await conn.fetchval(
            """
            WITH pulse_arts AS (
                SELECT a.outlet_id, a.scraped_at
                  FROM articles a JOIN outlets o ON o.id = a.outlet_id
                 WHERE a.event_id = $1 AND o.pulse
            ),
            latest AS (SELECT MAX(scraped_at) AS mx FROM pulse_arts)
            UPDATE events e
               SET breaking_at = NOW(),
                   breaking_until = NOW() + ($2 || ' hours')::interval
             WHERE e.id = $1 AND e.breaking_at IS NULL
               AND (SELECT mx FROM latest) > NOW() - ($4 || ' hours')::interval
               AND (SELECT COUNT(DISTINCT pa.outlet_id) FROM pulse_arts pa, latest
                     WHERE pa.scraped_at > latest.mx - ($3 || ' minutes')::interval) >= 2
            RETURNING e.id
            """,
            event_id, str(self.cfg.breaking_ttl_hours),
            str(self.cfg.breaking_window_minutes), str(self.cfg.breaking_recency_hours),
        )
        if flagged:
            logger.info("BREAKING event %s — ≥2 pulse outlets within %d min (demotes in %dh)",
                        flagged, self.cfg.breaking_window_minutes, self.cfg.breaking_ttl_hours)

    async def _run_precision(self, conn, *, article_id, embedding, entity_names,
                             language, scraped_at) -> ClusterResult:
        """ADR-0031 — centroid-linkage + entity-specificity gate.

        Attach to the nearest event *centroid* (events.centroid) only if its
        distance < precision_distance AND the article shares ≥1 *specific* entity
        (one in ≤ specificity_cap of the recent same-language pool). A ubiquitous
        mega-entity ("Mundial 2026") alone can't merge unrelated stories — the fix
        for World-Cup mega-buckets. Else seed a new event. Maintains events.centroid
        (= avg of member embeddings). Requires events.centroid backfilled before use.
        """
        vec = _vector_literal(embedding)
        win = str(self.cfg.recent_window_hours)

        # 1. Specificity: which of the article's entities are RARE in the recent pool.
        pool_n = await conn.fetchval(
            "SELECT count(*) FROM articles WHERE language = $1 "
            "AND scraped_at > NOW() - ($2 || ' hours')::interval", language, win) or 0
        cap_count = self.cfg.specificity_cap * max(pool_n, 1)
        specific: set[str] = set()
        if entity_names:
            dfrows = await conn.fetch(
                "SELECT lower(ent.name) AS name, count(DISTINCT ent.article_id) AS df "
                "FROM entities ent JOIN articles a ON a.id = ent.article_id "
                "WHERE a.language = $1 AND a.scraped_at > NOW() - ($2 || ' hours')::interval "
                "AND lower(ent.name) = ANY($3::text[]) GROUP BY 1",
                language, win, list(entity_names))
            specific = {r["name"] for r in dfrows if r["df"] <= cap_count}

        # 2. Nearest non-stale event centroid (same language).
        cand = await conn.fetchrow(
            "SELECT e.id, (e.centroid <=> $1::vector) AS distance "
            "FROM events e WHERE e.centroid IS NOT NULL AND e.language = $2 "
            "AND e.status <> 'concluded' "
            "AND e.last_material_update_at > NOW() - ($3 || ' hours')::interval "
            "ORDER BY e.centroid <=> $1::vector ASC LIMIT 1",
            vec, language, win)

        # 3. Attach iff near the centroid AND it shares ≥ specificity_min_shared
        #    specific entities with the event (≥2 stops the accumulating-union
        #    magnet — a lone shared mega-region/team can't merge distinct stories).
        if cand and float(cand["distance"]) < self.cfg.precision_distance and specific:
            n_shared = await conn.fetchval(
                "SELECT count(DISTINCT lower(ent.name)) FROM entities ent "
                "JOIN articles a ON a.id = ent.article_id "
                "WHERE a.event_id = $1 AND lower(ent.name) = ANY($2::text[])",
                cand["id"], list(specific)) or 0
            if int(n_shared) >= self.cfg.specificity_min_shared:
                ev_id, dist = cand["id"], float(cand["distance"])
                material = dist <= self.cfg.material_max_distance
                await conn.execute(
                    "UPDATE articles SET event_id = $2, cluster_distance = $3 WHERE id = $1",
                    article_id, ev_id, dist)
                await conn.execute(
                    """
                    UPDATE events SET
                        last_updated_at = NOW(),
                        last_material_update_at = CASE WHEN $2 THEN NOW() ELSE last_material_update_at END,
                        article_count = (SELECT COUNT(*) FROM articles WHERE event_id = $1),
                        source_count  = (SELECT COUNT(DISTINCT outlet_id) FROM articles WHERE event_id = $1),
                        centroid = (SELECT avg(embedding) FROM articles WHERE event_id = $1 AND embedding IS NOT NULL)
                     WHERE id = $1
                    """, ev_id, material)
                await self._maybe_flag_breaking(conn, ev_id)
                src = await conn.fetchval("SELECT source_count FROM events WHERE id = $1", ev_id)
                logger.info("CLUSTER-P attach %s -> %s (centroid_d=%.3f, spec=%d, sources=%d, %s)",
                            article_id, ev_id, dist, len(specific), int(src),
                            "material" if material else "tangential")
                return ClusterResult(event_id=ev_id, distance=dist, is_new_event=False, source_count=int(src))

        # 4. Seed a new event — centroid = this article's embedding.
        new_event_id = ulid.new().str
        await conn.execute(
            """
            INSERT INTO events (id, first_seen_at, last_updated_at, last_material_update_at,
                                centroid, source_count, article_count, language)
            VALUES ($1, $2, $2, $2, $3::vector, 1, 1, $4)
            """,
            new_event_id, scraped_at, vec, language)
        await conn.execute(
            "UPDATE articles SET event_id = $2, cluster_distance = 0 WHERE id = $1",
            article_id, new_event_id)
        logger.info("CLUSTER-P seed new event %s for article %s (no near+specific match)",
                    new_event_id, article_id)
        return ClusterResult(event_id=new_event_id, distance=0.0, is_new_event=True, source_count=1)
