import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, wait
from multiprocessing.connection import wait

import psycopg2
from sqlmodel import create_engine

sys.path.append("../../")
from tinydb import TinyDB
from Models.Article import Article
from Settings import Logger

# Configure your PGSQLDB connection
"""PGSQLDB_URL = 'postgresql://admin:admin@localhost:5342'
PGSQLDB_DATABASE_NAME = '/inkbytes_raw'
PGSQLDB_DATABASE_COLLECTION = 'news_articles'
engine = create_engine(PGSQLDB_URL + PGSQLDB_DATABASE_NAME)
Session = sessionmaker(bind=engine)"""
__name__ = 'PGSQLdb exporter'
logger = Logger.get_logger(__name__)
STORAGE_DIR = '../../scrapes'
FILES = files = os.listdir(STORAGE_DIR)
PGSQLDB_URL = 'postgresql://admin:deaf123456@127.0.0.1:5432/postgres'
PGSQLDB_DATABASE_NAME = '/postgres'
PGSQLDB_DATABASE_COLLECTION = 'inkbytes_raw'

conn = psycopg2.connect(
    host="localhost",
    database="postgres",
    user="admin",
    password="deaf123456")

# SessionLocal = sessionmaker(bind=engine, )
engine = create_engine(PGSQLDB_URL, echo=True)
# SQLModel.metadata.create_all(engine)

# Create a cursor

SQL = """
    INSERT INTO public.news_articles(
        id, uid, doc_id, publish_date, category, fetched_on, last_updated, cluster, factual, sentiment, 
        article_url, article_source, title, text, authors, summary, similars, related,  source_url, language, 
       combined, cluster_centroid
    )
    VALUES (
        %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    );"""

SQL2 = """INSERT INTO public.news_articles(id, uid,topics)VALUES ( %s, %s,%s,%s);"""
# Execute SQL commands
data = (
    '2aadfb1d-33d0-3e89-b02a-a7e2669d2c11',
    '2aadfb1d-33d0-3e89-b02a-a7e2669d2c11',
    123,
    '2023-08-23',
    'category_value',
    '2023-08-23 12:34:56',
    '2023-08-23 12:34:56',
    'cluster_value1',
    'factual_value',
    'sentiment_value',
    '{"type": "GPE", "name": "Spain", "links": []}',
    'article_url_value',
    'article_source_value',
    'title_value',
    'text_value',
    '["author1", "author2"]',
    'summary_value',
    '[]',
    '[]',
    '["topic1", "topic2"]',
    'source_url_value',
    'en',
    '["keyword1", "keyword2"]',
    '{}',
    'combined_value',
    1
)


def insert_data(data):
    for item in data:
        cur = conn.cursor()
        #item.pop('entities')
        #item.pop('topics')
        #item.pop('metadata')
        #item.pop('keywords')
        new_dict = list(value for key, value in item.items())
        new_dict = list(value for key, value in item.items())
        # Execute the INSERT statement
        try:
            print(item['topics'])
            cur.execute(SQL2, (item['id'],item['uid'], item['title'],f"{json.dumps(item['topics'])}"))
            conn.commit()
            # Close the cursor and connection
        except Exception as e:
            print(e)
            continue
    conn.close()
    #
    #conn.close()



def get_data(model):
    pass
    # session = SessionLocal()
    # rows = session.query(model).all()
    # session.close()
    # return rows


def update_data(id, new_data, model):
    pass
    # session = SessionLocal()
    # record = session.query(model).filter_by(id=id).first()
    # if record:
    #    for key, value in new_data.items():
    #        setattr(record, key, value)
    # session.commit()
    # session.close()


def export_to_PGSQLdb(file_name, model=Article, PERFORM_UPDATE=False):
    db = TinyDB(STORAGE_DIR + "/" + file_name)
    data = db.table('_default').all()
    insert_data(data)


# move_file_to_folder(TINYDB_JSON_FILE, '../scrapes/PGSQLDB')


def exec():
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(export_to_PGSQLdb, file_name)
                   for file_name in files if file_name.endswith('.db.csv')]
        # Wait for all futures to complete
        completed_futures, _ = wait(futures)
        # Check results of completed futures
        for future in completed_futures:
            try:
                result = future.result()
                print(f"Future completed successfully with result: {result}")
            except Exception as e:
                print(f"Future encountered an exception: {e}")


def csv_to_json():
    files = os.listdir(STORAGE_DIR)
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(export_to_PGSQLdb, file_name)
                   for file_name in files if file_name.endswith('.csv')]
        # Wait for all futures to complete
        completed_futures, _ = wait(futures)
        # Check results of completed futures
        for future in completed_futures:
            try:
                result = future.result()
                print(f"Future completed successfully with result: {result}")
                export_to_PGSQLdb(result, 'geocities')
            except Exception as e:
                print(f"Future encountered an exception: {e}")


def json_to_pgsql():
    files = os.listdir(STORAGE_DIR)
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(export_to_PGSQLdb, file_name)
                   for file_name in files if file_name.endswith('.json')]


json_to_pgsql()
