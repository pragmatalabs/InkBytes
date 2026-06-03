import logging
from typing import Iterable, Mapping, List

import sysdictionary
import psycopg2
from UtilsPkg.Dates import current_time
from tinydb import TinyDB, Query, storages

logger = logging.getLogger(__name__)


class Database(TinyDB):
    def __init__(self, uri=SysDictionary.APP_GLOBAL_CONF.get("STORAGE_FILE"), storage=storages.JSONStorage):
        super().__init__(uri, storage=storage)

    def insert_multiple_objects(self, documents: Iterable[Mapping]) -> List[int]:
        try:
            return self.insert_multiple(documents)
        except ValueError as error:
            logger.error(error)

    def get_by_id(self, _id):
        return self.search(Query().id == _id)[0]


class DataHandler:
    _instance = None
    _data = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._db = Database()
            cls._data = cls._db.all()
        return cls._instance

    @property
    def data(self):
        return self._data

    def insert_multiple_objects(self, data):
        for i, item in enumerate(data):
            try:
                self._db.insert(item.to_json())
                logger.info(f"Inserting item {i}")
            except Exception as error:
                logger.error(error)

    def insert_multiple_articles_objects(self, data):
        for i, article in enumerate(data):
            try:
                article.last_updated = current_time()  # Define current_time() function as required
                self._db.insert(article.to_json())
                logger.info(f"Inserting article {i}")
            except Exception as error:
                logger.error(error)

    def upsert_multiple(self, data):
        doc = Query()
        for article in data:
            article.last_updated = current_time()  # Define current_time() function as required
            try:
                self._db.upsert(article.to_dict(), doc.id == article.id)
            except ValueError as error:
                logger.error(error)
                logger.error(f"Error upserting article {article.title} id:{article.id}")
                continue
            logger.info(f"Updated article {article.title} id:{article.id}")

    def upsert_multiple_articles(self, data):
        doc = Query()
        for article in data:
            article.last_updated = current_time()  # Define current_time() function as required
            try:
                self._db.upsert(article.to_dict(), doc.id == article.id)
            except ValueError as error:
                logger.error(error)
                logger.error(f"Error upserting article {article.title} id:{article.id}")
                continue
            logger.info(f"Updated article {article.title} id:{article.id}")

    def write_bulk(self, upd):
        try:
            logger.info("Writing")
            self.upsert_multiple(upd)
        except Exception as error:
            logger.error(f" found {error} error in write_bulk")

        return None


def fetch_data_from_postgresql(connection_string, table_name, row_id):
    # Fetch data from PostgreSQL and return the result
    try:
        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM {table_name} WHERE id = %s", (row_id,))
                result = cur.fetchone()
                if result:
                    return result
                else:
                    print(f"No data found for ID: {row_id}")
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
    return None