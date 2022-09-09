from load_db import db
from maid import Maid
from pymongo import ASCENDING
from types import MappingProxyType

# The maids information is loaded once per execution.
_maids = list(db['maid-list'].find("_id", ASCENDING))
maids = tuple(Maid(m['name'], m['display_name'], m['avatar']) for m in _maids)
# This dict provides a way to retrieve maids by names.
# Also, with the features of dict, the maid order is kept.
maids_dict = MappingProxyType({m.name: m for m in maids})

__all__ = ['maids', 'maids_dict']