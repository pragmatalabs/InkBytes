"""C0 local-embedding spike (scratch, not committed to pipeline).

Compares clustering separation of local Ollama embedders (bge-m3, nomic-embed-text)
against the production OpenAI text-embedding-3-small (1536d) baseline, on the
articles already embedded + assigned to events.

Method: for article pairs, "same event" pairs should be MORE similar than
"different event" pairs. A good embedder gives high intra-event similarity and
low inter-event similarity, and a clean threshold separating them. We mirror the
production embed input: f"{title}\n\n{body_text[:4000]}".

Read-only: pulls data, embeds in-memory, prints a report. No DB writes.
"""
import asyncio, math, json, urllib.request, random
import asyncpg

DSN = "postgresql://inkbytes:inkbytes@localhost:5432/inkbytes"
OLLAMA = "http://localhost:11434/api/embeddings"
LOCAL_MODELS = ["bge-m3", "nomic-embed-text"]
OPENAI_THRESHOLD = 0.62          # production cosine-similarity gate
MAX_INTER_PAIRS = 8000           # cap diff-event pairs for speed
random.seed(42)


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def ollama_embed(model, text):
    req = urllib.request.Request(
        OLLAMA,
        data=json.dumps({"model": model, "prompt": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["embedding"]


def parse_pgvector(s):
    return [float(x) for x in s.strip("[]").split(",")]


async def main():
    conn = await asyncpg.connect(DSN)
    rows = await conn.fetch(
        """
        SELECT a.id, a.title, a.body_text, a.event_id,
               a.embedding::text AS oai
        FROM articles a
        WHERE a.embedding IS NOT NULL
          AND a.event_id IS NOT NULL
          AND a.body_text IS NOT NULL
        """
    )
    await conn.close()

    # Keep only events with >=2 members in our set (those produce intra pairs).
    by_event = {}
    for r in rows:
        by_event.setdefault(r["event_id"], []).append(r)
    multi = {e: rs for e, rs in by_event.items() if len(rs) >= 2}
    arts = [r for rs in multi.values() for r in rs]
    print(f"articles embedded+assigned: {len(rows)}  "
          f"| in multi-member events: {len(arts)} across {len(multi)} events")

    # Embed locally (mirror production input).
    def embed_text(r):
        return f"{r['title']}\n\n{(r['body_text'] or '')[:4000]}"

    vecs = {"openai": {r["id"]: parse_pgvector(r["oai"]) for r in arts}}
    for model in LOCAL_MODELS:
        print(f"embedding {len(arts)} articles with {model} ...", flush=True)
        m = {}
        for i, r in enumerate(arts):
            m[r["id"]] = ollama_embed(model, embed_text(r))
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(arts)}", flush=True)
        vecs[model] = m

    # Build same-event and different-event pair lists (shared across embedders).
    ids = [r["id"] for r in arts]
    event_of = {r["id"]: r["event_id"] for r in arts}
    intra, inter = [], []
    for e, rs in multi.items():
        rl = [r["id"] for r in rs]
        for i in range(len(rl)):
            for j in range(i + 1, len(rl)):
                intra.append((rl[i], rl[j]))
    all_pairs_seen = set()
    while len(inter) < MAX_INTER_PAIRS:
        a, b = random.choice(ids), random.choice(ids)
        if a == b or event_of[a] == event_of[b]:
            continue
        key = (min(a, b), max(a, b))
        if key in all_pairs_seen:
            continue
        all_pairs_seen.add(key)
        inter.append((a, b))
    print(f"pairs: {len(intra)} same-event, {len(inter)} diff-event\n")

    def stats(model):
        V = vecs[model]
        si = [cosine(V[a], V[b]) for a, b in intra]
        di = [cosine(V[a], V[b]) for a, b in inter]
        mi, md = sum(si) / len(si), sum(di) / len(di)
        # Pick threshold maximizing (intra-recall - inter-falsepos) = Youden's J.
        best_t, best_j, best_rec, best_fp = 0, -1, 0, 0
        for k in range(40, 96):
            t = k / 100
            rec = sum(1 for x in si if x >= t) / len(si)
            fp = sum(1 for x in di if x >= t) / len(di)
            if rec - fp > best_j:
                best_j, best_t, best_rec, best_fp = rec - fp, t, rec, fp
        # At a fixed reference threshold for direct comparability.
        ref = OPENAI_THRESHOLD
        ref_rec = sum(1 for x in si if x >= ref) / len(si)
        ref_fp = sum(1 for x in di if x >= ref) / len(di)
        return dict(mi=mi, md=md, gap=mi - md, best_t=best_t, best_j=best_j,
                    best_rec=best_rec, best_fp=best_fp, ref_rec=ref_rec, ref_fp=ref_fp)

    print(f"{'model':<20} {'intra':>6} {'inter':>6} {'gap':>6} "
          f"{'bestT':>6} {'J':>6} {'rec@best':>9} {'fp@best':>8} "
          f"{'rec@.62':>8} {'fp@.62':>7}")
    for model in ["openai"] + LOCAL_MODELS:
        s = stats(model)
        print(f"{model:<20} {s['mi']:>6.3f} {s['md']:>6.3f} {s['gap']:>6.3f} "
              f"{s['best_t']:>6.2f} {s['best_j']:>6.3f} {s['best_rec']:>9.3f} "
              f"{s['best_fp']:>8.3f} {s['ref_rec']:>8.3f} {s['ref_fp']:>7.3f}")
    print("\nReading: 'gap' = mean(intra)-mean(inter), higher=better separation. "
          "'bestT' = Youden-optimal cosine threshold for that embedder. "
          "'rec@best'=same-event recall, 'fp@best'=diff-event false-positive at bestT.")


asyncio.run(main())
