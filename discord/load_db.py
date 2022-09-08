import pymongo
from load_secrets import secret

mongo = pymongo.MongoClient(f"mongodb://{secret['mongo_admin']}:{secret['mongo_pwd']}@mongodb")
db = mongo['maid-bot']

__all__ = ['db']