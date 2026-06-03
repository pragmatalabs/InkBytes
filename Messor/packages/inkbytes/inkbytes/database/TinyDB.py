import logging
from typing import Iterable, Mapping, List


from tinydb import TinyDB, Query, storages

__name__ = "TinyDB scrapes System"
logger = logging.getLogger(__name__)


class Database(TinyDB):
    def __init__(self, uri="", storage=storages.JSONStorage):
        super().__init__(uri, storage=storage)

    def insert_multiple_objects(self, documents: Iterable[Mapping]) -> List[int]:
        try:
            return self.insert_multiple(documents)
        except ValueError as error:
            logger.error(error)

    def get_by_id(self, _id):
        return self.search(Query().id == _id)[0]


def get_tinydb_document_id(article, db, doc):
    try:
        idx = article.uid
        doc = Query()
        documents = db.search(doc['uid'] == idx)
        if not documents:
            logger.error(f"No document found for article id: {idx} in {db}")
            return None, article
        document = documents[0]
        if not article.doc_id:
            article.doc_id = document.doc_id
        return document, article
    except ValueError as error:
        logger.error(f"Error getting document id: {error}")
        return None, article
