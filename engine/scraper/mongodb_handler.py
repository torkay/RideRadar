from pymongo import MongoClient

class MongoDBHandler:
    def __init__(self, uri='mongodb://localhost:27017/', db_name='vehicle_database', collection_name='vehicle_listings'):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def insert_or_update(self, record):
        self.collection.update_one({'id': record['id']}, {'$set': record}, upsert=True)

    def delete_old_records(self, ids_in_json):
        self.collection.delete_many({'id': {'$nin': ids_in_json}})

    def close(self):
        self.client.close()
