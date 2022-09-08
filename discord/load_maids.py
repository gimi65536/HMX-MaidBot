from load_db import db
from maid import Maid
from pymongo import ASCENDING

_maids = list(db['maid-list'].find("_id", ASCENDING))
maids = [Maid(m['name'], m['display_name'], m['avatar']) for m in _maids]

__all__ = ['maids']