-- VALIDATED outlet additions from worldmonitor (newspaper3k-verified: title+body+date).
-- 27 outlets. Idempotent. Run on prod:
--   docker exec -i inkbytes-postgres psql -U inkbytes -d inkbytes < ib-outlet-insert-validated.sql

INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('theverge','theverge','The Verge','https://www.theverge.com/','global','en','tech',true,3,'https://www.theverge.com/rss/index.xml',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('arstechnica','arstechnica','Ars Technica','https://arstechnica.com/','global','en','tech',true,3,'https://feeds.arstechnica.com/arstechnica/technology-lab',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('engadget','engadget','Engadget','https://www.engadget.com/','global','en','tech',true,3,'https://www.engadget.com/rss.xml',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('zdnet','zdnet','ZDNet','https://www.zdnet.com/','global','en','tech',true,3,'https://www.zdnet.com/news/rss.xml',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('tomshardware','tomshardware','Tom''s Hardware','https://www.tomshardware.com/','global','en','tech',true,3,'https://www.tomshardware.com/feeds/all',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('thenextweb','thenextweb','The Next Web','https://thenextweb.com/','global','en','tech',true,3,'https://thenextweb.com/feed',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('technologyreview','technologyreview','MIT Technology Review','https://www.technologyreview.com/','global','en','tech',true,3,'https://www.technologyreview.com/feed/',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('coindesk','coindesk','CoinDesk','https://www.coindesk.com/','global','en','business',true,3,'https://www.coindesk.com/arc/outboundfeeds/rss/',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('cointelegraph','cointelegraph','Cointelegraph','https://cointelegraph.com/','global','en','business',true,3,'https://cointelegraph.com/rss',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('dwnews','dwnews','DW News','https://www.dw.com/','global','en','general',true,3,'https://rss.dw.com/xml/rss-en-all',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('euronewsen','euronewsen','Euronews','https://www.euronews.com/','global','en','general',true,3,'https://www.euronews.com/rss?format=xml',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('euronewses','euronewses','Euronews (Español)','https://es.euronews.com/','global','es','general',true,3,'https://es.euronews.com/rss?format=xml',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('scmp','scmp','South China Morning Post','https://www.scmp.com/','global','en','general',true,3,'https://www.scmp.com/rss/91/feed/',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('thediplomat','thediplomat','The Diplomat','https://thediplomat.com/','global','en','general',true,3,'https://thediplomat.com/feed/',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('foreignpolicy','foreignpolicy','Foreign Policy','https://foreignpolicy.com/','global','en','general',true,3,'https://foreignpolicy.com/feed/',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('thehindu','thehindu','The Hindu','https://www.thehindu.com/','global','en','general',true,3,'https://www.thehindu.com/news/national/feeder/default.rss',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('japantoday','japantoday','Japan Today','https://japantoday.com/','global','en','general',true,3,'https://japantoday.com/feed/atom',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('meduza','meduza','Meduza','https://meduza.io/','global','en','general',true,3,'https://meduza.io/rss/all',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('moscowtimes','moscowtimes','The Moscow Times','https://www.themoscowtimes.com/','global','en','general',true,3,'https://www.themoscowtimes.com/rss/news',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('cna','cna','Channel News Asia','https://www.channelnewsasia.com/','global','en','general',true,3,'https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('diezeit','diezeit','Die Zeit','https://www.zeit.de/','europe-de','de','general',true,3,'https://newsfeed.zeit.de/index',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('tagesschau','tagesschau','Tagesschau','https://www.tagesschau.de/','europe-de','de','general',true,3,'https://www.tagesschau.de/xml/rss2/',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('ansa','ansa','ANSA','https://www.ansa.it/','europe-it','it','general',true,3,'https://www.ansa.it/sito/notizie/topnews/topnews_rss.xml',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('nos','nos','NOS Nieuws','https://nos.nl/','europe-nl','nl','general',true,3,'https://feeds.nos.nl/nosnieuwsalgemeen',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('nrc','nrc','NRC','https://www.nrc.nl/','europe-nl','nl','general',true,3,'https://www.nrc.nl/rss/',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('lasillavacia','lasillavacia','La Silla Vacía','https://www.lasillavacia.com/','latam-co','es','general',true,3,'https://www.lasillavacia.com/rss',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
INSERT INTO outlets (id,name,display_name,url,region,language,vertical,active,priority,feed_url,pulse,created_at,updated_at)
VALUES ('mexiconewsdaily','mexiconewsdaily','Mexico News Daily','https://mexiconewsdaily.com/','latam-mx','en','general',true,3,'https://mexiconewsdaily.com/feed/',false,NOW(),NOW())
ON CONFLICT (id) DO NOTHING;
