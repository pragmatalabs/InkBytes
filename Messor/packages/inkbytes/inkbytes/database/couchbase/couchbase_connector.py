from couchbase.cluster import Cluster, ClusterOptions
from couchbase.auth import PasswordAuthenticator
from couchbase.collection import UpsertOptions
from couchbase.exceptions import UnAmbiguousTimeoutException, DocumentNotFoundException
from typing import Optional, Dict, Any
import time
import logging


class CouchbaseConnection:
    def __init__(
            self,
            connection_string: str,
            username: str,
            password: str,
            bucket_name: str,
            connection_timeout: int = 10000,  # milliseconds
            max_retries: int = 3,
            retry_delay: int = 2  # seconds
    ):
        self.connection_string = connection_string
        self.username = username
        self.password = password
        self.bucket_name = bucket_name
        self.connection_timeout = connection_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Initialize connection
        self.cluster = None
        self.bucket = None
        self.collection = None
        self.connect()

    def connect(self) -> bool:
        """Establishes connection to Couchbase server with retry mechanism"""
        for attempt in range(self.max_retries):
            try:
                auth = PasswordAuthenticator(self.username, self.password)
                options = ClusterOptions(auth)
                #options.connection_timeout = self.connection_timeout

                self.cluster = Cluster(self.connection_string, options)
                #self.cluster.wait_until_ready(timeout=self.connection_timeout / 1000)

                self.bucket = self.cluster.bucket(self.bucket_name)
                self.collection = self.bucket.default_collection()

                self.logger.info(f"Successfully connected to Couchbase cluster and bucket '{self.bucket_name}'")
                return True

            except UnAmbiguousTimeoutException as e:
                self.logger.warning(f"Timeout during connection attempt {attempt + 1}/{self.max_retries}: {str(e)}")
                if attempt < self.max_retries - 1:
                    self.logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error("Max retries reached. Could not establish connection.")
                    raise

            except Exception as e:
                self.logger.error(f"Unexpected error during connection: {str(e)}")
                raise

    def upsert_document(self, doc_id: str, document: Dict[str, Any], timeout: int = 5) -> bool:
        """
        Upsert a document with retry mechanism
        Returns: bool indicating success
        """
        try:
            self.collection.upsert(
                doc_id,
                document  # Convert to microseconds
            )
            self.logger.info(f"Successfully upserted document with ID: {doc_id}")
            return True
        except UnAmbiguousTimeoutException as e:
            self.logger.error(f"Timeout while upserting document {doc_id}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error upserting document {doc_id}: {str(e)}")
            raise

    def get_document(self, doc_id: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Retrieve a document by ID
        Returns: Document content as dictionary
        """
        try:
            result = self.collection.get(
                doc_id,
                timeout=timeout * 1000000  # Convert to microseconds
            )
            return result.content_as[dict]
        except DocumentNotFoundException:
            self.logger.warning(f"Document not found: {doc_id}")
            raise
        except UnAmbiguousTimeoutException as e:
            self.logger.error(f"Timeout while retrieving document {doc_id}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error retrieving document {doc_id}: {str(e)}")
            raise

    def delete_document(self, doc_id: str, timeout: int = 5) -> bool:
        """
        Delete a document by ID
        Returns: bool indicating success
        """
        try:
            self.collection.remove(
                doc_id,
                timeout=timeout * 1000000  # Convert to microseconds
            )
            self.logger.info(f"Successfully deleted document with ID: {doc_id}")
            return True
        except DocumentNotFoundException:
            self.logger.warning(f"Document not found for deletion: {doc_id}")
            raise
        except UnAmbiguousTimeoutException as e:
            self.logger.error(f"Timeout while deleting document {doc_id}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error deleting document {doc_id}: {str(e)}")
            raise

    def disconnect(self):
        """Safely close the Couchbase connection"""
        if self.cluster:
            try:
                self.cluster.close()
                self.logger.info("Disconnected from Couchbase cluster")
            except Exception as e:
                self.logger.error(f"Error during disconnect: {str(e)}")


# Example usage
if __name__ == "__main__":
    try:
        # Connection parameters
        connection_params = {
            "connection_string": "couchbase://localhost",
            "username": "your_username",
            "password": "your_password",
            "bucket_name": "your_bucket"
        }

        # Create connection
        cb = CouchbaseConnection(**connection_params)

        # Example document operations
        try:
            # Upsert a document
            doc = {"type": "test", "value": "hello world"}
            cb.upsert_document("test_doc", doc)

            # Retrieve the document
            retrieved_doc = cb.get_document("test_doc")
            print(f"Retrieved document: {retrieved_doc}")

            # Delete the document
            cb.delete_document("test_doc")

        finally:
            # Always disconnect when done
            cb.disconnect()

    except Exception as e:
        print(f"An error occurred: {str(e)}")