from typing import List

import numpy as np  # Replace with your vectorization library
# from langchain.document_loaders import JSONLoader
from langchain.docstore.document import Document
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.vectorstores import Chroma


class ChromaDBHandler:
    def __init__(self, collection_name):

    # self.client = chromadb.Client()
        self.collection = collection_name

    def add_documents(self, documents: List[Document]) -> object:
        # split it into chunks
        # text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        # docs = text_splitter.split_documents(_docs)
        embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
        db = Chroma.from_documents(documents, embedding_function,persist_directory='./data', collection_name=self.collection)
        db.persist()
        query = "Who is jeff bezzos"
        docs = db.search(query, "similarity", n_results=5)
        print(docs[0])

    def query_similar_documents(self, query_text, n_results=5):
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results


def vectorize_document(title, text, keywords, topics, category):
    # Replace this with your actual vectorization logic
    vector = np.random.rand(100)  # Example random vector
    return vector


def store_documents_in_chromadb(documents):
    handler = ChromaDBHandler("my-document-collection")
    doc_collection: List[Document] = []

    for doc in documents:
        _id = doc['id']
        page_content = str(doc['title']) + ' ' + str(doc['text']) + ' '
        metadata = {
            "_id": _id,
            "title": doc['title'],
            "keywords": ",".join(x for x in doc["keywords"]),
            "topics": ",".join(x for x in doc["topics"]),
            "category": doc['category'],
        }
        chromaDocument: Document = Document(id=_id, page_content=page_content, metadata=metadata)
        doc_collection.append(chromaDocument)
    handler.add_documents(doc_collection)


# Example usage
document1 = {
    "id": "0945jiwasdasdeirje9wriew9r",
    "title": "Shop Online",
    "text": "This is the content of document 1.",
    "keywords": ["keyword1", "keyword2"],
    "topics": ["topic1"],
    "category": "category1"
}
document2 = {
    "id": "adasd0934adsadewrewrwe",
    "title": "The owner of amazon",
    "text": "Bezzos is the owner of amazon",
    "keywords": ["Kindle", "Amazon"],
    "topics": ["Shopping"],
    "category": "category2"
}
document3 = {
    "id": "asdad0294302940293049",
    "title": "Amazon Prime",
    "text": "Amazon is owned by Jeff Bezos",
    "keywords": ["Amazon", "Prime"],
    "topics": ["Online"],
    "category": "category2"
}

documents_to_store = [document1, document2, document3]
store_documents_in_chromadb(documents_to_store)
