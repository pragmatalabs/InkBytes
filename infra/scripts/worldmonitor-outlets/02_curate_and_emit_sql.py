"""Step 1 — curated high-fit InkBytes outlet candidates from worldmonitor.
Native feeds only (no Google-News redirect feeds). region/language hand-corrected.
Emits: review table, idempotent SQL (ON CONFLICT DO NOTHING), and a feed list for step-2 validation.
Fields match public.outlets conventions: vertical in {general,business,tech}; new outlets priority=3, pulse=false, active=true, min_word_count NULL.
"""
import csv

# (slug, display_name, url, language, region, vertical, feed_url)
PICKS = [
 # --- tech (global/en) ---
 ("theverge","The Verge","https://www.theverge.com/","en","global","tech","https://www.theverge.com/rss/index.xml"),
 ("arstechnica","Ars Technica","https://arstechnica.com/","en","global","tech","https://feeds.arstechnica.com/arstechnica/technology-lab"),
 ("engadget","Engadget","https://www.engadget.com/","en","global","tech","https://www.engadget.com/rss.xml"),
 ("venturebeat","VentureBeat","https://venturebeat.com/","en","global","tech","https://venturebeat.com/feed/"),
 ("zdnet","ZDNet","https://www.zdnet.com/","en","global","tech","https://www.zdnet.com/news/rss.xml"),
 ("tomshardware","Tom's Hardware","https://www.tomshardware.com/","en","global","tech","https://www.tomshardware.com/feeds/all"),
 ("thenextweb","The Next Web","https://thenextweb.com/","en","global","tech","https://thenextweb.com/feed"),
 ("technologyreview","MIT Technology Review","https://www.technologyreview.com/","en","global","tech","https://www.technologyreview.com/feed/"),
 ("fastcompany","Fast Company","https://www.fastcompany.com/","en","global","tech","https://feeds.feedburner.com/fastcompany/headlines"),
 # --- business/finance (global/en) ---
 ("marketwatch","MarketWatch","https://www.marketwatch.com/","en","global","business","http://feeds.marketwatch.com/marketwatch/topstories/"),
 ("ft","Financial Times","https://www.ft.com/","en","global","business","https://www.ft.com/rss/home"),
 ("investing","Investing.com","https://www.investing.com/","en","global","business","https://www.investing.com/rss/news.rss"),
 ("coindesk","CoinDesk","https://www.coindesk.com/","en","global","business","https://www.coindesk.com/arc/outboundfeeds/rss/"),
 ("cointelegraph","Cointelegraph","https://cointelegraph.com/","en","global","business","https://cointelegraph.com/rss"),
 ("seekingalpha","Seeking Alpha","https://seekingalpha.com/","en","global","business","https://seekingalpha.com/market_currents.xml"),
 # --- world/general (global) ---
 ("politico","Politico","https://www.politico.com/","en","global","politics","https://rss.politico.com/politics-news.xml"),
 ("dwnews","DW News","https://www.dw.com/","en","global","general","https://rss.dw.com/xml/rss-en-all"),
 ("france24en","France 24","https://www.france24.com/en/","en","global","general","https://www.france24.com/en/rss"),
 ("france24es","France 24 (Español)","https://www.france24.com/es/","es","global","general","https://www.france24.com/es/rss"),
 ("euronewsen","Euronews","https://www.euronews.com/","en","global","general","https://www.euronews.com/rss?format=xml"),
 ("euronewses","Euronews (Español)","https://es.euronews.com/","es","global","general","https://es.euronews.com/rss?format=xml"),
 ("scmp","South China Morning Post","https://www.scmp.com/","en","global","general","https://www.scmp.com/rss/91/feed/"),
 ("thediplomat","The Diplomat","https://thediplomat.com/","en","global","general","https://thediplomat.com/feed/"),
 ("foreignpolicy","Foreign Policy","https://foreignpolicy.com/","en","global","general","https://foreignpolicy.com/feed/"),
 ("thehindu","The Hindu","https://www.thehindu.com/","en","global","general","https://www.thehindu.com/news/national/feeder/default.rss"),
 ("indianexpress","The Indian Express","https://indianexpress.com/","en","global","general","https://indianexpress.com/section/india/feed/"),
 ("japantoday","Japan Today","https://japantoday.com/","en","global","general","https://japantoday.com/feed/atom"),
 ("kyivindependent","The Kyiv Independent","https://kyivindependent.com/","en","global","general","https://kyivindependent.com/feed"),
 ("meduza","Meduza","https://meduza.io/","en","global","general","https://meduza.io/rss/all"),
 ("moscowtimes","The Moscow Times","https://www.themoscowtimes.com/","en","global","general","https://www.themoscowtimes.com/rss/news"),
 ("cna","Channel News Asia","https://www.channelnewsasia.com/","en","global","general","https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml"),
 # --- europe ---
 ("spiegel","Der Spiegel","https://www.spiegel.de/","de","europe-de","general","https://www.spiegel.de/schlagzeilen/tops/index.rss"),
 ("diezeit","Die Zeit","https://www.zeit.de/","de","europe-de","general","https://newsfeed.zeit.de/index"),
 ("tagesschau","Tagesschau","https://www.tagesschau.de/","de","europe-de","general","https://www.tagesschau.de/xml/rss2/"),
 ("repubblica","La Repubblica","https://www.repubblica.it/","it","europe-it","general","https://www.repubblica.it/rss/homepage/rss2.0.xml"),
 ("ansa","ANSA","https://www.ansa.it/","it","europe-it","general","https://www.ansa.it/sito/notizie/topnews/topnews_rss.xml"),
 ("nos","NOS Nieuws","https://nos.nl/","nl","europe-nl","general","https://feeds.nos.nl/nosnieuwsalgemeen"),
 ("nrc","NRC","https://www.nrc.nl/","nl","europe-nl","general","https://www.nrc.nl/rss/"),
 # --- latam (core vertical) ---
 ("brasilparalelo","Brasil Paralelo","https://www.brasilparalelo.com.br/","pt","latam-br","general","https://www.brasilparalelo.com.br/noticias/rss.xml"),
 ("lasillavacia","La Silla Vacía","https://www.lasillavacia.com/","es","latam-co","general","https://www.lasillavacia.com/rss"),
 ("mexiconewsdaily","Mexico News Daily","https://mexiconewsdaily.com/","en","latam-mx","general","https://mexiconewsdaily.com/feed/"),
]

# step-2 validated survivors (newspaper3k extracts title+body+date)
PASS = {"theverge","arstechnica","engadget","zdnet","tomshardware","thenextweb",
 "technologyreview","coindesk","cointelegraph","dwnews","euronewsen","euronewses",
 "scmp","thediplomat","foreignpolicy","thehindu","japantoday","meduza","moscowtimes",
 "cna","diezeit","tagesschau","ansa","nos","nrc","lasillavacia","mexiconewsdaily"}

def esc(s): return s.replace("'", "''")

VALIDATED = [p for p in PICKS if p[0] in PASS]
with open("/tmp/ib-outlet-insert-validated.sql","w") as f:
    f.write("-- VALIDATED outlet additions from worldmonitor (newspaper3k-verified: title+body+date).\n")
    f.write(f"-- {len(VALIDATED)} outlets. Idempotent. Run on prod:\n")
    f.write("--   docker exec -i inkbytes-postgres psql -U inkbytes -d inkbytes < ib-outlet-insert-validated.sql\n\n")
    for slug,disp,url,lang,region,vert,feed in VALIDATED:
        f.write(
          "INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)\n"
          f"VALUES ('{slug}','{slug}','{esc(disp)}','{url}','{region}','{lang}','{vert}',true,3,'{feed}',false,NOW(),NOW())\n"
          "ON CONFLICT (id) DO NOTHING;\n")
PICKS = VALIDATED  # report only survivors below

with open("/tmp/feeds-to-validate.tsv","w") as f:
    for slug,disp,url,lang,region,vert,feed in PICKS:
        f.write(f"{slug}\t{feed}\n")

# review table
print(f"Curated: {len(PICKS)} outlets  (SQL -> /tmp/ib-outlet-insert.sql, feeds -> /tmp/feeds-to-validate.tsv)\n")
print(f"{'slug':<17}{'display':<26}{'region':<11}{'lang':<5}{'vertical':<9}feed")
for slug,disp,url,lang,region,vert,feed in PICKS:
    print(f"{slug:<17}{disp:<26}{region:<11}{lang:<5}{vert:<9}{feed[:60]}")
