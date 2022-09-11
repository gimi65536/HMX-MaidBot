import re
from load_db import db
from dcmaid.maid import Maid
from base64 import b64decode
from pymongo import ASCENDING
from types import MappingProxyType
from typing import Dict

def _data_base64_to_bytes(img):
	if (m := re.fullmatch(r'data:image/.*;base64,(.+)', img)):
		return b64decode(m.group(1))

# The maids information is loaded once per execution.
_maids = list(db['maid-list'].find().sort("_id", ASCENDING))
_maids_list = list(Maid(m['name'], m['display_name'], _data_base64_to_bytes(m['avatar'])) for m in _maids)
# This dict provides a way to retrieve maids by names.
# Also, with the features of dict, the maid order is kept.
maids: Dict[str, Maid] = MappingProxyType({m.name: m for m in _maids_list})

__all__ = ['maids']
