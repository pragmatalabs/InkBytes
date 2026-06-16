"""Build an InkBytes outlet-candidate list from the worldmonitor feed report.

Reads /tmp/wm-feeds.csv (worldmonitor) + /tmp/ib-outlets.psv (existing InkBytes
outlets), keeps OK feeds, dedups by registrable domain against what we already
harvest, classifies (vertical/region/language), and writes a review CSV +
markdown grouped by vertical. Single-outlet feeds become candidates; multi-source
Google-News topic queries are listed separately (they don't fit the per-outlet model).
"""
import csv, re, urllib.parse
from collections import defaultdict

# multi-label public suffixes we care about (LATAM/ES/EU + common)
MULTI = {"co.uk","com.mx","com.do","com.ar","com.br","com.co","com.uy","com.pe",
         "com.ve","com.ec","com.gt","org.uk","com.au","co.il","com.tr",
         "gov.uk","gov.cn","go.jp","edu.sg","net.au","org.au","ac.uk","co.jp",
         "co.kr","co.in","com.sg","com.cn"}
# feed served via a CDN/proxy host -> the real outlet domain
CDN_FIX = {"uecdn.es": "elmundo.es", "feedburner.com": None, "feeds.feedburner.com": None}
CC_LATAM = {"mx":"mx","ar":"ar","co":"co","cl":"cl","pe":"pe","uy":"uy","ve":"ve",
            "br":"br","do":"do","ec":"ec","pr":"pr","gt":"gt","bo":"bo","py":"py"}
CC_EU = {"es":"es","fr":"fr","de":"de","it":"it","uk":"uk","nl":"nl","ch":"ch","pt":"pt"}
ES_DOMAINS = {"clarin.com","milenio.com","eluniversal.com.mx","animalpolitico.com",
              "proceso.com.mx","eltiempo.com","lasillavacia.com","elpais.com",
              "elmundo.es","infobae.com"}
PT_DOMAINS = {"oglobo.globo.com","folha.uol.com.br","brasilparalelo.com.br","globo.com"}

def registrable(host):
    host = host.lower().lstrip(".")
    if host.startswith("www."): host = host[4:]
    parts = host.split(".")
    last2 = ".".join(parts[-2:]); last3 = ".".join(parts[-3:])
    if last2 in MULTI and len(parts) >= 3:
        return last3
    return last2

def host_of(url):
    try: return urllib.parse.urlparse(url).netloc.lower()
    except Exception: return ""

def true_outlet(url):
    """Return (domain, is_aggregation). For Google-News site: queries, extract the site."""
    h = host_of(url)
    if "news.google.com" in h:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("q", [""])[0]
        m = re.search(r"site:([a-z0-9.\-]+)", q, re.I)
        if m:
            return registrable(m.group(1)), False
        return "news.google.com", True   # topic/OR query — multi-source aggregation
    reg = registrable(h)
    if reg in CDN_FIX and CDN_FIX[reg]:
        reg = CDN_FIX[reg]
    return reg, False

def classify(domain, url, wm_cat):
    reg = domain
    cc = reg.split(".")[-1]
    lang = "en"
    region = "global"
    if reg in PT_DOMAINS or reg.endswith(".com.br") or cc == "br":
        lang, region = "pt", "latam-br"
    elif reg in ES_DOMAINS:
        lang = "es"
        region = "europe-es" if reg in {"elpais.com","elmundo.es"} else "latam-" + (
            "mx" if reg.endswith(".mx") else "ar" if reg=="clarin.com" else "co" if reg in {"eltiempo.com","lasillavacia.com"} else "xx")
    elif cc == "co" and reg not in {"eltiempo.com","lasillavacia.com","semana.com",
                                     "elcolombiano.com","larepublica.co","portafolio.co"}:
        pass  # .co is a generic vanity TLD (theblock.co, goodgoodgood.co) — keep global/en
    elif cc in CC_LATAM:
        lang, region = "es", "latam-" + CC_LATAM[cc]
    elif cc in CC_EU:
        lang = "es" if cc=="es" else "fr" if cc=="fr" else "de" if cc=="de" else "en"
        region = "europe-" + CC_EU[cc]
    if "hl=es" in url: lang = "es"
    return region, lang

# existing domains
existing = set()
with open("/tmp/ib-outlets.psv") as f:
    for line in f:
        cols = line.rstrip("\n").split("|")
        for u in cols[1:3]:
            if u.strip():
                existing.add(registrable(host_of(u) or u))

rows = list(csv.DictReader(open("/tmp/wm-feeds.csv")))
cands = {}          # domain -> record
aggregations = []   # google-news topic queries
seen_existing = set()
for r in rows:
    if r["Status"] != "OK": continue
    dom, is_agg = true_outlet(r["URL"])
    if is_agg:
        aggregations.append((r["Variant"], r["Category"], r["Feed Name"], r["URL"]))
        continue
    if dom in existing:
        seen_existing.add(dom); continue
    region, lang = classify(dom, r["URL"], r["Category"])
    if dom not in cands:
        slug = re.sub(r"[^a-z0-9]", "", dom.split(".")[0])
        cands[dom] = {"name": slug, "display_name": r["Feed Name"], "url": f"https://{dom}/",
                      "language": lang, "region": region, "verticals": set(), "feed_url": r["URL"],
                      "wm_cats": set()}
    cands[dom]["verticals"].add(r["Variant"])
    cands[dom]["wm_cats"].add(r["Category"])

# write CSV
with open("/tmp/ib-outlet-candidates.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["name","display_name","url","language","region","vertical","feed_url","wm_categories"])
    for dom, c in sorted(cands.items(), key=lambda kv: (sorted(kv[1]["verticals"])[0], kv[0])):
        w.writerow([c["name"], c["display_name"], c["url"], c["language"], c["region"],
                    "|".join(sorted(c["verticals"])), c["feed_url"], "|".join(sorted(c["wm_cats"]))])

# summary
print(f"OK feeds: {sum(1 for r in rows if r['Status']=='OK')} | already-have (deduped out): {len(seen_existing)} "
      f"| NEW candidates: {len(cands)} | aggregation queries (separate): {len(aggregations)}")
byv = defaultdict(list)
for dom, c in cands.items():
    byv[sorted(c["verticals"])[0]].append((dom, c))
for v in sorted(byv):
    print(f"\n### {v}  ({len(byv[v])})")
    for dom, c in sorted(byv[v]):
        print(f"  - {c['display_name']:<28} {c['region']:<11} {c['language']}  {dom}")
print("\n### Google-News topic/aggregation feeds (NOT per-outlet — review separately):")
for var, cat, name, url in aggregations:
    print(f"  - [{var}/{cat}] {name}")
