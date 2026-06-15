"""Read-only clustering prototype (ADR experiment).

Simulates the PROPOSED clustering rules against the LIVE prod corpus without
mutating anything (SELECT-only). Answers two questions for the ADR:

  1. Do the over-broad "mega-bucket" events split into coherent sub-events?
  2. Do healthy multi-source events FRAGMENT below the 2-source publish bar?

Current prod algorithm (skills/cluster.py): single-linkage — an article joins
the event of its *nearest individual neighbour* if cosine distance < 0.50 and
they share >=1 entity. This chains unrelated stories through a dense topic
region (e.g. "Mundial 2026") into 900-article / 800-topic buckets.

Proposed algorithm (this prototype): centroid-linkage + entity specificity —
an article joins the nearest *cluster centroid* only if distance < THRESHOLD
(tighter) AND it shares >=1 *specific* entity with the cluster (an entity that
is NOT ubiquitous in the pool, so a recurring mega-entity like "World Cup"
cannot by itself merge unrelated stories).

Run inside the curator container (has numpy + asyncpg + DATABASE_URL):
  ssh root@<droplet> 'docker exec -i inkbytes-curator-api python -' < this_file
"""
from __future__ import annotations

import asyncio
import os
from collections import Counter

import asyncpg
import numpy as np

# The World Cup near-duplicate pair (the reported symptom).
MEGA_EVENTS = ["01KTMRBKDT84YNE5YQA1NDGS9Q", "01KTMRBKM2A6QE0TGFMHMBCK86"]
THRESHOLDS = [0.30, 0.35, 0.40, 0.45, 0.50]  # cosine-distance bars to sweep (current prod = 0.50)
SPECIFICITY_CAP = 0.10               # an entity is "specific" if it appears in < 10% of pool articles
CONTROL_LIMIT = 40                   # healthy multi-source es events to test for fragmentation


def parse_vec(s):
    if s is None:
        return None
    if isinstance(s, str):
        return np.fromstring(s.strip().lstrip("[").rstrip("]"), sep=",", dtype=np.float32)
    return np.asarray(s, dtype=np.float32)


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


async def fetch_articles(conn, event_ids):
    return await conn.fetch(
        """
        SELECT a.id, a.event_id, a.outlet_id, a.scraped_at, a.topic, a.title,
               a.embedding::text AS emb,
               ARRAY(SELECT lower(name) FROM entities WHERE article_id = a.id) AS ents
          FROM articles a
         WHERE a.event_id = ANY($1::text[]) AND a.embedding IS NOT NULL
         ORDER BY a.scraped_at
        """,
        event_ids,
    )


def build_df(rows):
    df = Counter()
    for r in rows:
        for e in set(r["ents"] or []):
            df[e] += 1
    return df


def simulate(rows, threshold, use_specificity, df, cap):
    """Greedy online centroid clustering in scraped_at order. Returns (clusters, assign)."""
    n = len(rows)
    embs = [unit(parse_vec(r["emb"])) for r in rows]
    spec = [
        {e for e in (r["ents"] or []) if df.get(e, 0) <= cap * n} if use_specificity else set()
        for r in rows
    ]
    clusters = []  # {sum, count, spec_ents:set, members:[idx]}
    assign = []
    for i in range(n):
        v = embs[i]
        best, bestd = -1, 1e9
        for ci, c in enumerate(clusters):
            cen = unit(c["sum"] / c["count"])
            d = 1.0 - float(np.dot(v, cen))
            if d < bestd:
                bestd, best = d, ci
        ok = best >= 0 and bestd < threshold
        if ok and use_specificity:
            ok = len(spec[i] & clusters[best]["spec_ents"]) >= 1
        if ok:
            c = clusters[best]
            c["sum"] += v
            c["count"] += 1
            c["spec_ents"] |= spec[i]
            c["members"].append(i)
            assign.append(best)
        else:
            clusters.append({"sum": v.copy(), "count": 1, "spec_ents": set(spec[i]), "members": [i]})
            assign.append(len(clusters) - 1)
    return clusters, assign


def src_count(rows, idxs):
    return len({rows[i]["outlet_id"] for i in idxs})


def report_mega(rows, df):
    print("\n" + "=" * 78)
    print(f"MEGA-BUCKET TEST — {len(rows)} articles currently in {len(MEGA_EVENTS)} events")
    by_ev = Counter(r["event_id"] for r in rows)
    for ev, c in by_ev.items():
        print(f"  current event {ev}: {c} articles, {src_count(rows, [i for i,r in enumerate(rows) if r['event_id']==ev])} sources")
    for thr in THRESHOLDS:
        for spec in (False, True):
            clusters, _ = simulate(rows, thr, spec, df, SPECIFICITY_CAP)
            sizes = sorted((len(c["members"]) for c in clusters), reverse=True)
            pub = sum(1 for c in clusters if src_count(rows, c["members"]) >= 2)
            sing = sum(1 for c in clusters if len(c["members"]) == 1)
            label = f"thr={thr:.2f} specificity={'ON ' if spec else 'OFF'}"
            print(f"\n  [{label}] -> {len(clusters)} clusters | publishable(>=2 src)={pub} | singletons={sing} | top sizes={sizes[:8]}")
            # coherence of the biggest cluster: distinct topics / size (1.0 = grab-bag)
            top = max(clusters, key=lambda c: len(c["members"]))
            tt = len({rows[i]["topic"] for i in top["members"]})
            print(f"      biggest cluster: {len(top['members'])} arts, {tt} distinct topics ({tt/len(top['members']):.2f} topic ratio), {src_count(rows, top['members'])} sources")
            for i in top["members"][:4]:
                print(f"        - {(rows[i]['title'] or '')[:64]}")


def report_control(ctrl_ids, rows, df):
    print("\n" + "=" * 78)
    print(f"FRAGMENTATION TEST — {len(ctrl_ids)} healthy es events, {len(rows)} articles")
    print("  intact = all of an event's articles stay in one cluster")
    print("  dropped-below-2 = event had >=2 sources but its dominant fragment now has <2 (un-publishes)")
    print("  cross-merge = resulting clusters that mix articles from >=2 DIFFERENT original events (over-merge)")
    orig_idx = {ev: [i for i, r in enumerate(rows) if r["event_id"] == ev] for ev in ctrl_ids}
    orig_src = {ev: src_count(rows, ix) for ev, ix in orig_idx.items() if ix}
    for spec in (False, True):
        for thr in THRESHOLDS:
            clusters, assign = simulate(rows, thr, spec, df, SPECIFICITY_CAP)
            intact = frag = lost_pub = 0
            for ev, idxs in orig_idx.items():
                if not idxs:
                    continue
                cl = Counter(assign[i] for i in idxs)
                largest_cluster_id, _ = cl.most_common(1)[0]
                largest_members = [i for i in idxs if assign[i] == largest_cluster_id]
                if len(cl) == 1:
                    intact += 1
                else:
                    frag += 1
                if orig_src[ev] >= 2 and src_count(rows, largest_members) < 2:
                    lost_pub += 1
            # cross-merge: clusters whose members come from >=2 distinct original events
            cl_events = Counter()
            members_by_cluster = {}
            for i, a in enumerate(assign):
                members_by_cluster.setdefault(a, []).append(i)
            cross = sum(1 for ci, mem in members_by_cluster.items()
                        if len({rows[i]["event_id"] for i in mem}) >= 2)
            tag = "ON " if spec else "OFF"
            print(f"  [thr={thr:.2f} spec={tag}] intact={intact}/{len(orig_src)} | fragmented={frag} "
                  f"| dropped-below-2={lost_pub} | cross-merged-clusters={cross}")


FIXED_THR = 0.48                      # event-preserving distance bar for the cap sweep
CAPS = [0.02, 0.03, 0.05, 0.08, 0.10]  # specificity cap sweep (fraction of pool)


def report_cap_sweep(mega, ctrl_ids, ctrl):
    print("\n" + "=" * 78)
    print(f"SPECIFICITY-CAP SWEEP @ fixed distance thr={FIXED_THR} (event-preserving)")
    print("  goal: break the mega-bucket (small biggest-cluster) WITHOUT un-publishing real events")
    mdf = build_df(mega)
    cdf = build_df(ctrl)
    orig_idx = {ev: [i for i, r in enumerate(ctrl) if r["event_id"] == ev] for ev in ctrl_ids}
    orig_src = {ev: src_count(ctrl, ix) for ev, ix in orig_idx.items() if ix}
    for cap in CAPS:
        mc, _ = simulate(mega, FIXED_THR, True, mdf, cap)
        msizes = sorted((len(c["members"]) for c in mc), reverse=True)
        mpub = sum(1 for c in mc if src_count(mega, c["members"]) >= 2)
        cc, assign = simulate(ctrl, FIXED_THR, True, cdf, cap)
        intact = lost = 0
        for ev, idxs in orig_idx.items():
            if not idxs:
                continue
            cl = Counter(assign[i] for i in idxs)
            big, _ = cl.most_common(1)[0]
            if len(cl) == 1:
                intact += 1
            if orig_src[ev] >= 2 and src_count(ctrl, [i for i in idxs if assign[i] == big]) < 2:
                lost += 1
        print(f"\n  cap={cap:.0%}: MEGA -> {len(mc)} clusters, biggest={msizes[0]}, top5={msizes[:5]}, publishable={mpub}")
        print(f"          CONTROL -> intact={intact}/{len(orig_src)}, dropped-below-2={lost}")


async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        mega = await fetch_articles(conn, MEGA_EVENTS)
        ctrl_ev = await conn.fetch(
            """
            SELECT id FROM events
             WHERE status='published' AND language='es'
               AND source_count BETWEEN 2 AND 4
               AND article_count BETWEEN 3 AND 15
             ORDER BY article_count DESC
             LIMIT $1
            """,
            CONTROL_LIMIT,
        )
        ctrl_ids = [r["id"] for r in ctrl_ev]
        ctrl = await fetch_articles(conn, ctrl_ids)

        # entity DF is computed per-pool (the right signal: ubiquitous-in-pool = generic)
        report_mega(mega, build_df(mega))
        report_control(ctrl_ids, ctrl, build_df(ctrl))
        report_cap_sweep(mega, ctrl_ids, ctrl)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
