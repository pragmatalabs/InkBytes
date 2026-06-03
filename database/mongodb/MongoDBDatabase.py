from Database.AbstractDatabase import AbstractDatabase
from pymongo import MongoClient


class MongoDBDatabase(AbstractDatabase):
    def __init__(self, config):
        self.config = config
        self.client = None
        self.db = None

    def connect(self):
        self.client = MongoClient(self.config['connection_string'])
        self.db = self.client[self.config['db_name']]

    def fetch(self, collection, query):
        return self.db[collection].find(query)

    def insert(self, collection, data):
        return self.db[collection].insert_one(data)

    def update(self, collection, query, new_data):
        return self.db[collection].update_one(query, new_data)

    def delete(self, collection, query):
        return self.db[collection].delete_one(query)

    def close(self):
        self.client.close()
