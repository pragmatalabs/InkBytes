
from Database.AbstractDatabase import AbstractDatabase
from tinydb import TinyDB, Query


class TinyDBDatabase(AbstractDatabase):
    def __init__(self, config):
        self.config = config
        self.db = None

    def connect(self):
        self.db = TinyDB(self.config['path'])

    def fetch(self, query):
        User = Query()
        return self.db.search(User.name == query)

    def insert(self, query, data):
        self.db.insert(data)

    def update(self, query, data):
        User = Query()
        self.db.update(data, User.name == query)

    def delete(self, query):
        User = Query()
        self.db.remove(User.name == query)

    def close(self):
        self.db.close()
