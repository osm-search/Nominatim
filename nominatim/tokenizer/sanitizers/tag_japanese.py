from typing import Callable
import re

from nominatim.tokenizer.sanitizers.base import ProcessInfo
from nominatim.tokenizer.sanitizers.config import SanitizerConfig

def create(config):
    return tag_japanese

def tag_japanese(obj: ProcessInfo) -> None:
    if obj.place.country_code != 'ja':
        return
    tmp_housenumber = None
    tmp_blocknumber = None
    tmp_neighbourhood = None

    new_address = []
    for item in obj.address:
        if item.kind == 'housenumber':
            tmp_housenumber = item.name
        elif item.kind == 'block_number':
            tmp_blocknumber = item.name
        elif item.kind == 'neighbourhood':
            tmp_neighbourhood = item.name
        else:
            new_address.append(item)

    if tmp_blocknumber and tmp_housenumber:
        new_address.append(PlaceName(kind='housenumber', name=f'{tmp_blocknumber}-{tmp_housenumber}'))
    elif tmp_blocknumber:
        new_address.append(PlaceName(kind='housenumber', name=f'{tmp_blocknumber}'))
    elif tmp_housenumber:
        new_address.append(PlaceName(kind='housenumber', name=f'{tmp_housenumber}'))

    if tmp_neighbourhood:
        new_address.append(PlaceName(kind='place', name=tmp_neighbourhood))

    obj.address = [item for item in new_address if item.name is not None]
