from load_db import db
from dcmaid.maid import Maid
from pymongo import ASCENDING
from types import MappingProxyType

# The maids information is loaded once per execution.
_maids = list(db['maid-list'].find("_id", ASCENDING))
_maids_list = list(Maid(m['name'], m['display_name'], m['avatar'].encode()) for m in _maids)
# This dict provides a way to retrieve maids by names.
# Also, with the features of dict, the maid order is kept.
maids: Dict[str, Maid] = MappingProxyType({m.name: m for m in _maids_list})

__all__ = ['maids']