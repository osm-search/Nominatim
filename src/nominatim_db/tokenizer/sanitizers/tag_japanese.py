# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
This sanitizer maps OSM data to Japanese block addresses.
It replaces blocknumber and housenumber with housenumber,
and quarter and neighbourhood with place.
"""


from typing import Callable
from typing import List, Optional

from .base import ProcessInfo
from .config import SanitizerConfig
from ...data.place_name import PlaceName

def create(_: SanitizerConfig) -> Callable[[ProcessInfo], None]:
    """Set up the sanitizer
    """
    return tag_japanese

def reconbine_housenumber(
    new_address: List[PlaceName],
    tmp_housenumber: Optional[str],
    tmp_blocknumber: Optional[str]
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
                name=tmp_blocknumber,
                suffix=''
            )
        )
    elif tmp_housenumber:
        new_address.append(
            PlaceName(
                kind='housenumber',
                name=tmp_housenumber,
                suffix=''
            )
        )
    return new_address

def reconbine_place(
    new_address: List[PlaceName],
    tmp_neighbourhood: Optional[str],
    tmp_quarter: Optional[str]
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
                name=tmp_neighbourhood,
                suffix=''
            )
        )
    elif tmp_quarter:
        new_address.append(
            PlaceName(
                kind='place',
                name=tmp_quarter,
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
    for item in obj.address:
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

    new_address = reconbine_housenumber(new_address, tmp_housenumber, tmp_blocknumber)
    new_address = reconbine_place(new_address, tmp_neighbourhood, tmp_quarter)

    obj.address = [item for item in new_address if item.name is not None]
