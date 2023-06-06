from typing import Callable
import re

from nominatim.tokenizer.sanitizers.base import ProcessInfo
from nominatim.tokenizer.sanitizers.config import SanitizerConfig

def create(config):
    return tag_japanese

def tag_japanese(obj):
    if obj.place.country_code != 'ja':
        return
    for item in obj.address:
        if item.kind == 'housenumber':
            # item.kind = None
            # obj.name.kind ?
        elif item.kind == 'block_number':
            # item.kind = None
        elif item.kind == 'neighbourhood':
            # item.kind = None
