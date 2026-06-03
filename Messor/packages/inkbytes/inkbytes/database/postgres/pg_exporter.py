import os
import sys
from concurrent.futures import ThreadPoolExecutor, wait
from multiprocessing.connection import wait

import psycopg2
from sqlalchemy import create_engine
from sqlmodel import Session

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
session = Session(engine)
# Create a cursor
cur = conn.cursor()
SQL =  """
    INSERT INTO public.news_articles(
        id, uid, doc_id, publish_date, category, fetched_on, last_updated, cluster, factual, sentiment, entities, 
        article_url, article_source, title, text, authors, summary, similars, related, topics, source_url, language, 
        keywords, metadata, combined, cluster_centroid
    )
    VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    );
"""


def insert_data(data):
    for item in data:

        # print(article.to_dict())
        try:

            article=Article(**item).to_dict()
            print(article.values())
            session.execute(SQL,[article.values()])
            session.commit()
            print(len(item))
            # print(item)
            # article = Article(**item)
            #article = list(item.values())
            # article=item
            #print(article)
            #cur.execute(SQL,article)
            #conn.commit()
            # Close the cursor and connection
            #cur.close()
            conn.close()
        except Exception as e:
            print(e)


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
    # print(data)
    insert_data(data[:1])


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
