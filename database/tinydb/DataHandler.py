import logging
from datetime import datetime

from tinydb import Query, where



__name__ = "DataHandler Class for TinyDB"

from inkbytes.database.tinydb.TinyDB import Database, get_tinydb_document_id

logger = logging.getLogger(__name__)


class DataHandler:
    def __init__(self, dbFilename=None):
        if dbFilename is not None:
            self._db = Database(dbFilename)
            self._dbFilename=dbFilename
        else:
            self._db = Database()
        self._data = self._db.all()

    @property
    def data(self):
        return self._data

    @property
    def filename(self):
        return self._dbFilename

    @property
    def db(self):
        return self._db

    def set_db(self, db: Database):
        self._db = db

    def insert_multiple(self, items: []):
        db = self._db
        insert_data = []
        batch_size = 100  # Set the batch size to 50
        for i, item in enumerate(items, start=1):
            if item is None:
                continue
            try:
                insert_data.append(item.to_dict())
                if i % batch_size == 0 or i == len(items):
                    db.insert_multiple(insert_data)
                    logger.info(f"Saved batch of {len(insert_data)} items")
                    insert_data = []  # Reset the update_data list for the next batch
            except ValueError as error:
                logger.error(error)
                logger.error(f"Error inserting item ")
                continue

    def update_multiple(self, data):
        logger.info(f"Updating {len(data)} items to {self._db.name}")
        for item in data:
            try:
                item.last_updated = str(datetime.now())
                doc = Query()
                docToUpdate, item = get_tinydb_document_id(item, self._db, doc)
                self.update_document(item, doc, docToUpdate)
            except ValueError as error:
                logger.error(error)
                logger.error(f"Error upserting article {item}")
                continue

    def delete_multiple(self, data):
        logger.info(f"Deleting {len(data)} items")
        for item in data:
            try:

                doc = Query()
                docToUpdate, item = get_tinydb_document_id(item, self._db, doc)
                # logger.info(f"Updating item {item.doc_id}  {item.title} id:{item.id}")
                # logger.info(f"Saving item {item.title} id:{item.id}")
                self.delete_document(item, doc, docToUpdate)
            except ValueError as error:
                logger.error(error)
                logger.error(f"Error deleting article {item}")
                continue

    def upsert_multiple(self, data):
        db = self._db
        doc = Query()
        update_data = []
        batch_size = 100  # Set the batch size to 50
        for i, item in enumerate(data, start=1):
            if item is None or 'id' not in item:
                logger.warning(f"Item {item} is without id")
                continue
            try:
                if 'last_updated' in item:
                    item.last_updated = str(datetime.now())

                doc_to_update, item = get_tinydb_document_id(item, db, doc)
                if doc_to_update is not None:
                    update_data.append((item.to_dict(), where("doc_id") == doc_to_update.doc_id))
                # Save the batch when the current index is a multiple of the batch size or it's the last item
                if i % batch_size == 0 or i == len(data):
                    db.update_multiple(update_data)
                    logger.info(f"Saved batch of {len(update_data)} articles")
                    update_data = []  # Reset the update_data list for the next batch
            except ValueError as error:
                logger.error(error)
                logger.error(f"Error upserting article {item.title} id:{item.id}")
                continue

    def update_document(self, article: object, doc, docToUpdate):
        try:
            article.last_updated = str(datetime.now())  # Define datetime.now() function as required
            doc = Query()
            result = self._db.update(article.to_dict(), doc['id'] == article.id)
            if not result:
                logger.error(f"No matching document found for article id: {article.id}")
        except ValueError as error:
            logger.error(error)

    def delete_document(self, article: object, doc, docToUpdate):
        try:
            doc = Query()
            result = self._db.remove(doc['doc_id'] == article.doc_id)
            if result:
                logger.info(f"Successfully deleted document: {result} {article.title}")
            else:
                logger.error(f"No matching document found for article id: {article.id}")
        except ValueError as error:
            logger.error(error)

    def write_bulk(self, upd):
        try:
            logger.info("Writing")
            self.upsert_multiple(upd)
        except Exception as error:
            logger.error(f" found {error} error in write_bulk")

        return None
