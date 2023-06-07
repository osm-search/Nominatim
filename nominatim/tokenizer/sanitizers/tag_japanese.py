from typing import Callable
import re

from nominatim.tokenizer.sanitizers.base import ProcessInfo
from nominatim.tokenizer.sanitizers.config import SanitizerConfig

def create(config):
    return tag_japanese

def tag_japanese(obj):
    if obj.place.country_code != 'ja':
        return
    flag_house = 0
    flag_block = 0
    for item in obj.address:
        if item.kind == 'housenumber' and flag_block == 1:
            # if both house and block exist, add them to name
            obj.names.append(item.clone(kind=))
        elif item.kind == 'housenumber':
            flag_house = 1
            # item.kind = None
        elif item.kind == 'block_number' and flag_house ==1:
            # same as above
            # ? obj.names.append(item.clone(kind=))
        elif item.kind == 'block_number':
            flag_block = 1
        elif item.kind == 'neighbourhood':
            obj.names.append(item.clone(kind='place'))
            # item.kind = Nonne
    if flag_house == 1 or flag_block == 1:
        # if only one of the two is available, the value is assigned as it is.
        obj.names.appned(item.clone(kind=))
