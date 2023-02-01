# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Dataclasses for search results and helper functions to fill them.

Data classes are part of the public API while the functions are for
internal use only. That's why they are implemented as free-standing functions
instead of member functions.
"""
from typing import Optional, Tuple, Dict, Sequence, Any
import enum
import dataclasses
import datetime as dt

import sqlalchemy as sa

from nominatim.typing import SaSelect, SaRow
from nominatim.api.types import Point, LookupDetails
from nominatim.api.connection import SearchConnection

# This file defines complex result data classes.
# pylint: disable=too-many-instance-attributes

class SourceTable(enum.Enum):
    """ Enumeration of kinds of results.
    """
    PLACEX = 1
    OSMLINE = 2
    TIGER = 3
    POSTCODE = 4
    COUNTRY = 5


@dataclasses.dataclass
class AddressLine:
    """ Detailed information about a related place.
    """
    place_id: Optional[int]
    osm_object: Optional[Tuple[str, int]]
    category: Tuple[str, str]
    names: Dict[str, str]
    extratags: Optional[Dict[str, str]]

    admin_level: Optional[int]
    fromarea: bool
    isaddress: bool
    rank_address: int
    distance: float


AddressLines = Sequence[AddressLine]


@dataclasses.dataclass
class WordInfo:
    """ Detailed information about a search term.
    """
    word_id: int
    word_token: str
    word: Optional[str] = None


WordInfos = Sequence[WordInfo]


@dataclasses.dataclass
class SearchResult:
    """ Data class collecting all available information about a search result.
    """
    source_table: SourceTable
    category: Tuple[str, str]
    centroid: Point

    place_id : Optional[int] = None
    parent_place_id: Optional[int] = None
    linked_place_id: Optional[int] = None
    osm_object: Optional[Tuple[str, int]] = None
    admin_level: int = 15

    names: Optional[Dict[str, str]] = None
    address: Optional[Dict[str, str]] = None
    extratags: Optional[Dict[str, str]] = None

    housenumber: Optional[str] = None
    postcode: Optional[str] = None
    wikipedia: Optional[str] = None

    rank_address: int = 30
    rank_search: int = 30
    importance: Optional[float] = None

    country_code: Optional[str] = None

    indexed_date: Optional[dt.datetime] = None

    address_rows: Optional[AddressLines] = None
    linked_rows: Optional[AddressLines] = None
    parented_rows: Optional[AddressLines] = None
    name_keywords: Optional[WordInfos] = None
    address_keywords: Optional[WordInfos] = None

    geometry: Dict[str, str] = dataclasses.field(default_factory=dict)


    @property
    def lat(self) -> float:
        """ Get the latitude (or y) of the center point of the place.
        """
        return self.centroid[1]


    @property
    def lon(self) -> float:
        """ Get the longitude (or x) of the center point of the place.
        """
        return self.centroid[0]


    def calculated_importance(self) -> float:
        """ Get a valid importance value. This is either the stored importance
            of the value or an artificial value computed from the place's
            search rank.
        """
        return self.importance or (0.7500001 - (self.rank_search/40.0))


    # pylint: disable=consider-using-f-string
    def centroid_as_geojson(self) -> str:
        """ Get the centroid in GeoJSON format.
        """
        return '{"type": "Point","coordinates": [%f, %f]}' % self.centroid


def create_from_placex_row(row: SaRow) -> SearchResult:
    """ Construct a new SearchResult and add the data from the result row
        from the placex table.
    """
    result = SearchResult(source_table=SourceTable.PLACEX,
                          place_id=row.place_id,
                          parent_place_id=row.parent_place_id,
                          linked_place_id=row.linked_place_id,
                          osm_object=(row.osm_type, row.osm_id),
                          category=(row.class_, row.type),
                          admin_level=row.admin_level,
                          names=row.name,
                          address=row.address,
                          extratags=row.extratags,
                          housenumber=row.housenumber,
                          postcode=row.postcode,
                          wikipedia=row.wikipedia,
                          rank_address=row.rank_address,
                          rank_search=row.rank_search,
                          importance=row.importance,
                          country_code=row.country_code,
                          indexed_date=getattr(row, 'indexed_date'),
                          centroid=Point(row.x, row.y))

    result.geometry = {k[9:]: v for k, v in row._mapping.items() # pylint: disable=W0212
                       if k.startswith('geometry_')}

    return result


async def add_result_details(conn: SearchConnection, result: SearchResult,
                             details: LookupDetails) -> None:
    """ Retrieve more details from the database according to the
        parameters specified in 'details'.
    """
    if details.address_details:
        await complete_address_details(conn, result)
    if details.linked_places:
        await complete_linked_places(conn, result)
    if details.parented_places:
        await complete_parented_places(conn, result)
    if details.keywords:
        await complete_keywords(conn, result)


def _result_row_to_address_row(row: SaRow) -> AddressLine:
    """ Create a new AddressLine from the results of a datbase query.
    """
    extratags: Dict[str, str] = getattr(row, 'extratags', {})
    if 'place_type' in row:
        extratags['place_type'] = row.place_type

    names = row.name
    if getattr(row, 'housenumber', None) is not None:
        if names is None:
            names = {}
        names['housenumber'] = row.housenumber

    return AddressLine(place_id=row.place_id,
                       osm_object=None if row.osm_type is None else (row.osm_type, row.osm_id),
                       category=(getattr(row, 'class'), row.type),
                       names=names,
                       extratags=extratags,
                       admin_level=row.admin_level,
                       fromarea=row.fromarea,
                       isaddress=getattr(row, 'isaddress', True),
                       rank_address=row.rank_address,
                       distance=row.distance)


async def complete_address_details(conn: SearchConnection, result: SearchResult) -> None:
    """ Retrieve information about places that make up the address of the result.
    """
    housenumber = -1
    if result.source_table in (SourceTable.TIGER, SourceTable.OSMLINE):
        if result.housenumber is not None:
            housenumber = int(result.housenumber)
        elif result.extratags is not None and 'startnumber' in result.extratags:
            # details requests do not come with a specific house number
            housenumber = int(result.extratags['startnumber'])

    sfn = sa.func.get_addressdata(result.place_id, housenumber)\
            .table_valued( # type: ignore[no-untyped-call]
                sa.column('place_id', type_=sa.Integer),
                'osm_type',
                sa.column('osm_id', type_=sa.BigInteger),
                sa.column('name', type_=conn.t.types.Composite),
                'class', 'type', 'place_type',
                sa.column('admin_level', type_=sa.Integer),
                sa.column('fromarea', type_=sa.Boolean),
                sa.column('isaddress', type_=sa.Boolean),
                sa.column('rank_address', type_=sa.SmallInteger),
                sa.column('distance', type_=sa.Float))
    sql = sa.select(sfn).order_by(sa.column('rank_address').desc(),
                                  sa.column('isaddress').desc())

    result.address_rows = []
    for row in await conn.execute(sql):
        result.address_rows.append(_result_row_to_address_row(row))

# pylint: disable=consider-using-f-string
def _placex_select_address_row(conn: SearchConnection,
                               centroid: Point) -> SaSelect:
    t = conn.t.placex
    return sa.select(t.c.place_id, t.c.osm_type, t.c.osm_id, t.c.name,
                     t.c.class_.label('class'), t.c.type,
                     t.c.admin_level, t.c.housenumber,
                     sa.literal_column("""ST_GeometryType(geometry) in
                                        ('ST_Polygon','ST_MultiPolygon')""").label('fromarea'),
                     t.c.rank_address,
                     sa.literal_column(
                         """ST_DistanceSpheroid(geometry, 'SRID=4326;POINT(%f %f)'::geometry,
                              'SPHEROID["WGS 84",6378137,298.257223563, AUTHORITY["EPSG","7030"]]')
                         """ % centroid).label('distance'))


async def complete_linked_places(conn: SearchConnection, result: SearchResult) -> None:
    """ Retrieve information about places that link to the result.
    """
    result.linked_rows = []
    if result.source_table != SourceTable.PLACEX:
        return

    sql = _placex_select_address_row(conn, result.centroid)\
            .where(conn.t.placex.c.linked_place_id == result.place_id)

    for row in await conn.execute(sql):
        result.linked_rows.append(_result_row_to_address_row(row))


async def complete_keywords(conn: SearchConnection, result: SearchResult) -> None:
    """ Retrieve information about the search terms used for this place.
    """
    t = conn.t.search_name
    sql = sa.select(t.c.name_vector, t.c.nameaddress_vector)\
            .where(t.c.place_id == result.place_id)

    result.name_keywords = []
    result.address_keywords = []
    for name_tokens, address_tokens in await conn.execute(sql):
        t = conn.t.word
        sel = sa.select(t.c.word_id, t.c.word_token, t.c.word)

        for row in await conn.execute(sel.where(t.c.word_id == sa.any_(name_tokens))):
            result.name_keywords.append(WordInfo(*row))

        for row in await conn.execute(sel.where(t.c.word_id == sa.any_(address_tokens))):
            result.address_keywords.append(WordInfo(*row))


async def complete_parented_places(conn: SearchConnection, result: SearchResult) -> None:
    """ Retrieve information about places that the result provides the
        address for.
    """
    result.parented_rows = []
    if result.source_table != SourceTable.PLACEX:
        return

    sql = _placex_select_address_row(conn, result.centroid)\
            .where(conn.t.placex.c.parent_place_id == result.place_id)\
            .where(conn.t.placex.c.rank_search == 30)

    for row in await conn.execute(sql):
        result.parented_rows.append(_result_row_to_address_row(row))
