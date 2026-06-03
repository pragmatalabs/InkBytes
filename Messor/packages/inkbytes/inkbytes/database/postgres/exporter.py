"""
Module: Exporter.py
Author: julian.delarosa@icloud.com
Date: 2023-03-22
Version: 1.0
Description: This module contains a function to export data to a PostgreSQL database. Also
data can be exprted locally to tinydb json files
System: InkBytes v1.0
Language: Python 3.8.2
License: MIT License
Status: 1 - Planning
Usage: Call from heimdall.py or from another module
Notes: This is a work in progress. It is not ready for production use.
"""

import json
import logging

import sysdictionary
import psycopg2
from Database.TinyDB import DataHandler

__name__='TinyDB Abstraction'
logger = logging.getLogger(__name__)


def export_data_to_pgsql():
    data_handler = DataHandler()
    data = data_handler.data
    conn_params = SysDictionary.PGSQL_CONNECTION_PARAMS
    with psycopg2.connect(**conn_params) as conn:
        with conn.cursor() as cursor:
            commit_cnt = 0
            for item in data:
                commit_cnt += 1
                # Convert the Python dictionary to a JSON string
                json_data = json.dumps(item)
                
                # Insert the JSON data into the PostgreSQL database
                try:
                    cursor.execute(
                        'INSERT INTO "Grabit".articles (id, document) VALUES (%s, %s) '
                        'ON CONFLICT (id) DO UPDATE SET document = EXCLUDED.document;',
                        (item["id"], json_data)
                    )
                    logger.info("Inserted %s", item["id"])
                except psycopg2.Error as e:
                    logger.exception("Error inserting row: %s", e)
                    conn.rollback()
                    continue
                # Commit the changes in batches
                if commit_cnt % 100 == 0:
                    conn.commit()
                    logger.info("Committed %d rows", commit_cnt)
            # Commit any remaining changes
            if commit_cnt % 100 != 0:
                conn.commit()
                logger.info("Committed %d rows", commit_cnt)

    logger.info("Finished exporting data to PostgreSQL")


def export_similarity_matrix(self=None, data=[]):
    logger.info("Starting similarity matrix export")
    _matrix_data = None
    if data == None or len(data) == 0:
        with open(SysDictionary.APP_GLOBAL_CONF.get("BERT_SPACY_STORAGE_FILE"), 'r') as f:
            _matrix_data = json.load(f)
    else:
        _matrix_data = data

    conn_params = SysDictionary.PGSQL_CONNECTION_PARAMS
    batch_size = len(_matrix_data) // 100
    batch_records = len(_matrix_data) // batch_size
    logger.info(f"batch_size: {batch_size} batch_records: {batch_records}")
    with psycopg2.connect(**conn_params) as conn:
        with conn.cursor() as cursor:
            cnt = 0
            commit_cnt = 0

            for item in _matrix_data.items():
                cnt += 1
                entries = []
                for key, value in item[1].items():
                    entries.append({'id': key, 'percentage': value})
                # Insert the JSON data into the PostgreSQL database
                try:
                    docs = json.dumps(entries)
                    cursor.execute(
                        'INSERT INTO "Grabit".related_articles_matrix (id,document) '
                        'VALUES(%s,%s) ON CONFLICT (id) '
                        'DO UPDATE SET document = EXCLUDED.document;',
                        (item[0], docs))
                    # logger.info("Inserted %s", json_data["id"])
                except Exception as e:
                    logger.error(f"Error inserting row: {e}")
                    conn.rollback()
                    continue
                commit_cnt += 1
                if commit_cnt % 100 == 0:
                    conn.commit()
                    logger.info("Committed %d rows", commit_cnt)
            # Commit any remaining changes
            if commit_cnt % 100 != 0:
                conn.commit()
                logger.info("Finalizing Committed %d rows", commit_cnt)

    logger.info("Finished similarity matrix export of length %d", len(_matrix_data))
    return None
