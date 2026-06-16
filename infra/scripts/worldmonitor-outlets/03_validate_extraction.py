"""Step 2 — parse-validate curated feeds with newspaper3k (run in inkbytes-messor).
Per outlet: parse feed, sample up to 3 articles, extract with newspaper3k (browser UA).
An article is USABLE if it has a title, word_count >= 50, AND a date (RSS pubDate or
extracted) — because Messor's 48h freshness gate drops undated articles. PASS if a
majority of sampled articles are usable.
"""
import socket, newspaper, feedparser
from newspaper import Article, Config

socket.setdefaulttimeout(20)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
cfg = Config(); cfg.browser_user_agent = UA; cfg.request_timeout = 15
cfg.fetch_images = False; cfg.memoize_articles = False

FEEDS = [
 ("theverge","https://www.theverge.com/rss/index.xml"),
 ("arstechnica","https://feeds.arstechnica.com/arstechnica/technology-lab"),
 ("engadget","https://www.engadget.com/rss.xml"),
 ("venturebeat","https://venturebeat.com/feed/"),
 ("zdnet","https://www.zdnet.com/news/rss.xml"),
 ("tomshardware","https://www.tomshardware.com/feeds/all"),
 ("thenextweb","https://thenextweb.com/feed"),
 ("technologyreview","https://www.technologyreview.com/feed/"),
 ("fastcompany","https://feeds.feedburner.com/fastcompany/headlines"),
 ("marketwatch","http://feeds.marketwatch.com/marketwatch/topstories/"),
 ("ft","https://www.ft.com/rss/home"),
 ("investing","https://www.investing.com/rss/news.rss"),
 ("coindesk","https://www.coindesk.com/arc/outboundfeeds/rss/"),
 ("cointelegraph","https://cointelegraph.com/rss"),
 ("seekingalpha","https://seekingalpha.com/market_currents.xml"),
 ("politico","https://rss.politico.com/politics-news.xml"),
 ("dwnews","https://rss.dw.com/xml/rss-en-all"),
 ("france24en","https://www.france24.com/en/rss"),
 ("france24es","https://www.france24.com/es/rss"),
 ("euronewsen","https://www.euronews.com/rss?format=xml"),
 ("euronewses","https://es.euronews.com/rss?format=xml"),
 ("scmp","https://www.scmp.com/rss/91/feed/"),
 ("thediplomat","https://thediplomat.com/feed/"),
 ("foreignpolicy","https://foreignpolicy.com/feed/"),
 ("thehindu","https://www.thehindu.com/news/national/feeder/default.rss"),
 ("indianexpress","https://indianexpress.com/section/india/feed/"),
 ("japantoday","https://japantoday.com/feed/atom"),
 ("kyivindependent","https://kyivindependent.com/feed"),
 ("meduza","https://meduza.io/rss/all"),
 ("moscowtimes","https://www.themoscowtimes.com/rss/news"),
 ("cna","https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml"),
 ("spiegel","https://www.spiegel.de/schlagzeilen/tops/index.rss"),
 ("diezeit","https://newsfeed.zeit.de/index"),
 ("tagesschau","https://www.tagesschau.de/xml/rss2/"),
 ("repubblica","https://www.repubblica.it/rss/homepage/rss2.0.xml"),
 ("ansa","https://www.ansa.it/sito/notizie/topnews/topnews_rss.xml"),
 ("nos","https://feeds.nos.nl/nosnieuwsalgemeen"),
 ("nrc","https://www.nrc.nl/rss/"),
 ("brasilparalelo","https://www.brasilparalelo.com.br/noticias/rss.xml"),
 ("lasillavacia","https://www.lasillavacia.com/rss"),
 ("mexiconewsdaily","https://mexiconewsdaily.com/feed/"),
]

passes, fails = [], []
print(f"{'slug':<17}{'feed':<6}{'smpl':<6}{'parse':<7}{'dated':<7}{'usable':<8}verdict")
for slug, url in FEEDS:
    try:
        d = feedparser.parse(url, agent=UA)
    except Exception as e:
        print(f"{slug:<17}FEED-ERR  {str(e)[:40]}"); fails.append((slug,"feed-error")); continue
    entries = d.entries[:3]
    if not entries:
        print(f"{slug:<17}{'0':<6}— no items"); fails.append((slug,"no-feed-items")); continue
    parsed = dated = usable = 0
    for e in entries:
        link = e.get("link") or ""
        rss_date = bool(e.get("published_parsed") or e.get("updated_parsed"))
        try:
            a = Article(link, config=cfg); a.download(); a.parse()
            wc = len((a.text or "").split())
            ok_text = bool(a.title) and wc >= 50
            has_date = rss_date or bool(a.publish_date)
        except Exception:
            ok_text = has_date = False
        if ok_text: parsed += 1
        if has_date: dated += 1
        if ok_text and has_date: usable += 1
    n = len(entries)
    verdict = "PASS" if usable >= (n + 1) // 2 and usable >= 1 else "FAIL"
    (passes if verdict == "PASS" else fails).append((slug, f"usable {usable}/{n}"))
    print(f"{slug:<17}{len(d.entries):<6}{n:<6}{parsed:<7}{dated:<7}{usable:<8}{verdict}")

print("\nPASS (" + str(len(passes)) + "): " + " ".join(s for s,_ in passes))
print("\nFAIL (" + str(len(fails)) + "):")
for s, why in fails:
    print(f"  {s:<17}{why}")
