-- Backfill feed_url + min_word_count into public.outlets (2026-06-11)
-- All feed URLs verified working from the droplet (curl, browser UA) on 2026-06-11.
BEGIN;
UPDATE outlets SET feed_url = 'https://feeds.bbci.co.uk/news/rss.xml', min_word_count = 25 WHERE name = 'bbc';
UPDATE outlets SET feed_url = 'https://www.aljazeera.com/xml/rss/all.xml', min_word_count = 25 WHERE name = 'aljazeera';
UPDATE outlets SET feed_url = 'https://eldinero.com.do/feed/', min_word_count = 25 WHERE name = 'eldinerodr';
UPDATE outlets SET feed_url = 'https://feeds.npr.org/1001/rss.xml' WHERE name = 'npr';
UPDATE outlets SET feed_url = 'https://www.theguardian.com/world/rss' WHERE name = 'theguardian';
UPDATE outlets SET feed_url = 'https://www.latimes.com/rss2.0.xml' WHERE name = 'latimes';
UPDATE outlets SET feed_url = 'https://gizmodo.com/rss' WHERE name = 'gizmodo';
UPDATE outlets SET feed_url = 'https://www.clarin.com/rss/lo-ultimo/' WHERE name = 'clarin';
UPDATE outlets SET feed_url = 'https://www.cnbc.com/id/100003114/device/rss/rss.html' WHERE name = 'cnbc';
UPDATE outlets SET feed_url = 'https://www.wired.com/feed/rss' WHERE name = 'wired';
UPDATE outlets SET feed_url = 'https://feeds.foxbusiness.com/foxbusiness/latest' WHERE name = 'foxbusiness';
UPDATE outlets SET feed_url = 'https://feeds.bloomberg.com/markets/news.rss' WHERE name = 'bloomberg';
UPDATE outlets SET feed_url = 'https://www.ft.com/rss/home' WHERE name = 'financialtimes';
UPDATE outlets SET feed_url = 'https://www.elfinanciero.com.mx/rss/' WHERE name = 'elfinancierolatam';
UPDATE outlets SET feed_url = 'https://www.eluniversal.com.mx/arc/outboundfeeds/rss/?outputType=xml' WHERE name = 'eluniversalmx';
UPDATE outlets SET feed_url = 'https://www.infobae.com/arc/outboundfeeds/rss/?outputType=xml' WHERE name = 'infobae';
UPDATE outlets SET feed_url = 'https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml' WHERE name = 'lanacionar';
UPDATE outlets SET feed_url = 'https://www.economist.com/latest/rss.xml' WHERE name = 'theeconomist';
UPDATE outlets SET feed_url = 'https://www.semana.com/arc/outboundfeeds/rss/?outputType=xml' WHERE name = 'semana';
UPDATE outlets SET feed_url = 'https://techcrunch.com/feed/' WHERE name = 'techcrunch';
UPDATE outlets SET feed_url = 'https://feeds.a.dj.com/rss/RSSWorldNews.xml' WHERE name = 'wsj';
UPDATE outlets SET feed_url = 'https://www.eltiempo.com/rss/colombia.xml' WHERE name = 'eltiempoco';
-- min_word_count only (short-form outlets, no working feed or feed not needed)
UPDATE outlets SET min_word_count = 25 WHERE name IN ('diariolibree','listindiario','acentodr','elcaribedr','reuters');
UPDATE outlets SET min_word_count = 30 WHERE name = 'animalpolitico';
COMMIT;
SELECT count(*) FILTER (WHERE feed_url IS NOT NULL) AS with_feed,
       count(*) FILTER (WHERE min_word_count IS NOT NULL) AS with_mwc
FROM outlets;
