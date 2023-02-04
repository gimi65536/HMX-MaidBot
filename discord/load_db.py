import pymongo
from load_secrets import secret

mongo: pymongo.MongoClient = pymongo.MongoClient(f"mongodb://{secret['mongo_admin']}:{secret['mongo_pwd']}@{secret['mongo_address']}")
db = mongo[secret['mongo_db']]

__all__ = ['db']