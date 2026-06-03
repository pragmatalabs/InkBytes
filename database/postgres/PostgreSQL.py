from abc import ABC

import psycopg2
from Database.AbstractDatabase import AbstractDatabase
from psycopg2 import sql


class PostgreSQLDatabase(AbstractDatabase, ABC):
    def __init__(self, config):
        self.config = config
        self.conn = None
        self.cur = None

    def connect(self):
        self.conn = psycopg2.connect(
            host=self.config['host'],
            port=self.config['port'],
            user=self.config['user'],
            password=self.config['password'],
            dbname=self.config['dbname']
        )
        self.cur = self.conn.cursor()

    def fetch(self, query):
        self.cur.execute(query)
        return self.cur.fetchall()

    def update(self, query, data):
        formatted_query = sql.SQL(query).format(*[sql.Identifier(i) for i in data])
        self.cur.execute(formatted_query)
        self.conn.commit()

    def close(self):
        if self.cur is not None:
            self.cur.close()
        if self.conn is not None:
            self.conn.close()
