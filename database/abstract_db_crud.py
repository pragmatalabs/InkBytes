from abc import ABC, abstractmethod


class AbstractDatabase(ABC):

    @abstractmethod
    def connect(self):
        """
        Connect to the database
        """
        pass

    @abstractmethod
    def fetch(self, query):
        """
        Fetch data from the database
        """
        pass

    @abstractmethod
    def insert(self, query, data):
        """
        Insert data into the database
        """
        pass

    @abstractmethod
    def update(self, query, data):
        """
        Update data in the database
        """
        pass

    @abstractmethod
    def delete(self, query):
        """
        Delete data from the database
        """
        pass

    @abstractmethod
    def close(self):
        """
        Close the connection to the database
        """
        pass

