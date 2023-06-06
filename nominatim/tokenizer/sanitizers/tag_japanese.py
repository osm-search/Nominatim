# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
This sanitizer maps OSM data to Japanese block addresses.
It replaces blocknumber and housenumber with housenumber,
and quarter and neighbourhood with place.
"""


from typing import Callable
from typing import List

from nominatim.tokenizer.sanitizers.base import ProcessInfo
from nominatim.tokenizer.sanitizers.config import SanitizerConfig
from nominatim.data.place_name import PlaceName

def create(_: SanitizerConfig) -> Callable[[ProcessInfo], None]:
#def create(config: SanitizerConfig) -> Callable[[ProcessInfo],None]:
    """Set up the sanitizer
    """
    return tag_japanese
    #return tag_japanese(config)

def convert_kanji_sequence_to_number(sequence: str) -> str:
    """Converts Kanji numbers to Arabic numbers
    """
    kanji_map = {
      '零': '0',
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

def reconbine_housenumber(
    new_address: List[PlaceName],
    tmp_housenumber: str | None,
    tmp_blocknumber: str | None
) -> List[PlaceName]:
    """ Recombine the tag of housenumber by using housenumber and blocknumber
    """
    if tmp_blocknumber and tmp_housenumber:
        new_address.append(
            PlaceName(
                kind='housenumber',
                name=f'{tmp_blocknumber}-{tmp_housenumber}',
                suffix=''
            )
        )
    elif tmp_blocknumber:
        new_address.append(
            PlaceName(
                kind='housenumber',
                name=f'{tmp_blocknumber}',
                suffix=''
            )
        )
    elif tmp_housenumber:
        new_address.append(
            PlaceName(
                kind='housenumber',
                name=f'{tmp_housenumber}',
                suffix=''
            )
        )
    return new_address
>>>>>>> 965beac7 (parent fc8caf720243b4d2116756f85bc20cae83280d53)

def reconbine_place(
    new_address: List[PlaceName],
    tmp_neighbourhood: str | None,
    tmp_quarter: str | None
) -> List[PlaceName]:
    """ Recombine the tag of place by using neighbourhood and quarter
    """
    if tmp_neighbourhood and tmp_quarter:
        new_address.append(
            PlaceName(
                kind='place',
                name=f'{tmp_quarter}{tmp_neighbourhood}',
                suffix=''
            )
        )
    elif tmp_neighbourhood:
        new_address.append(
            PlaceName(
                kind='place',
                name=f'{tmp_neighbourhood}',
                suffix=''
            )
        )
    elif tmp_quarter:
        new_address.append(
            PlaceName(
                kind='place',
                name=f'{tmp_quarter}',
                suffix=''
            )
        )
    return new_address
def tag_japanese(obj: ProcessInfo) -> None:
    """Recombine kind of address
    """
    if obj.place.country_code != 'jp':
        return
    tmp_housenumber = None
    tmp_blocknumber = None
    tmp_neighbourhood = None
    tmp_quarter = None

    new_address = []
    for item in obj.names:
        item.name = convert_kanji_sequence_to_number(item.name)

    for item in obj.address:
        item.name = convert_kanji_sequence_to_number(item.name)
        if item.kind == 'housenumber':
            tmp_housenumber = item.name
        elif item.kind == 'block_number':
            tmp_blocknumber = item.name
        elif item.kind == 'neighbourhood':
            tmp_neighbourhood = item.name
        elif item.kind == 'quarter':
            tmp_quarter = item.name
        else:
            new_address.append(item)

    new_address = reconbine_housenumber(new_address,tmp_housenumber,tmp_blocknumber)
    new_address = reconbine_place(new_address,tmp_neighbourhood,tmp_quarter)

    obj.address = [item for item in new_address if item.name is not None]
