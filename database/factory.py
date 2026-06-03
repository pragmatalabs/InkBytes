from mongodb.MongoDBDatabase import MongoDBDatabase
from postgres.PostgreSQL import PostgreSQLDatabase
from tinydb.TinyDBDatabase import TinyDBDatabase


class DatabaseFactory:
    @staticmethod
    def create_database(type, config):
        if type == 'postgresql':
            return PostgreSQLDatabase(config)
        elif type == 'tinydb':
            return TinyDBDatabase(config)
        elif type == 'mongodb':
            return MongoDBDatabase(config)
        else:
            raise ValueError('Invalid database type')
