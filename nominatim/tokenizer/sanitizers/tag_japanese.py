from typing import Callable
import re

from nominatim.tokenizer.sanitizers.base import ProcessInfo
from nominatim.tokenizer.sanitizers.config import SanitizerConfig
from nominatim.data.place_name import PlaceName

def create(config):
    return tag_japanese

def convert_kanji_sequence_to_number(sequence):
    kanji_map = {
      '一': '1',
      '二': '2',
      '三': '3',
      '四': '4',
      '五': '5',
      '六': '6',
      '七': '7',
      '八': '8',
      '九': '9'
    }
    converted = ''
    current_number = ''
    for char in sequence:
      if char in kanji_map:
        current_number += kanji_map[char]
      else:
        converted += current_number
        current_number = ''
        converted += char
    converted += current_number
    return converted


def tag_japanese(obj: ProcessInfo) -> None:
    #print('!!!!!', obj)
    if obj.place.country_code != 'jp':
        #print('!!!',obj.place.country_code)
        return
    #print('!!!!!!',obj)
    tmp_housenumber = None
    tmp_blocknumber = None
    tmp_neighbourhood = None
    tmp_quarter = None

    new_address = []
    #print('herehere')
    #print(obj.names)
    
    for item in obj.names:
      item.name = convert_kanji_sequence_to_number(item.name) 
    #print(obj.names)


    for item in obj.address:
        item.name = convert_kanji_sequence_to_number(item.name)
        #print(item.name)
        if item.kind == 'housenumber':
            tmp_housenumber = item.name
        elif item.kind == 'block_number':
            tmp_blocknumber = item.name
        elif item.kind == 'neighbourhood':
            # this is temporary change
            #if item.name == '3丁目':
            #  tmp = '三丁目'
            #  tmp_neighbourhood = tmp
            #else:
            tmp_neighbourhood = item.name
            #print(tmp_neighbourhood)
        elif item.kind == 'quarter':
            tmp_quarter = item.name
            #print('quarter',tmp_quarter)
        else:
            new_address.append(item)
        #print(item)

    if tmp_blocknumber and tmp_housenumber:
        new_address.append(PlaceName(kind='housenumber', name=f'{tmp_blocknumber}-{tmp_housenumber}',suffix=''))
    elif tmp_blocknumber:
        new_address.append(PlaceName(kind='housenumber', name=f'{tmp_blocknumber}',suffix=''))
    elif tmp_housenumber:
        new_address.append(PlaceName(kind='housenumber', name=f'{tmp_housenumber}',suffix=''))

    if tmp_neighbourhood and tmp_quarter:
        new_address.append(PlaceName(kind='place', name=f'{tmp_quarter}{tmp_neighbourhood}',suffix=''))
        #print('new_address',new_address)
    elif tmp_neighbourhood:
        new_address.append(PlaceName(kind='place', name=f'{tmp_neighbourhood}',suffix=''))
    elif tmp_quarter:
        new_address.append(PlaceName(kind='place', name=f'{tmp_quarter}',suffix=''))

    obj.address = [item for item in new_address if item.name is not None]
    #print(obj.address)
