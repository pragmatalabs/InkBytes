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
