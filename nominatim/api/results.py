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
from typing import Optional, Tuple, Dict, Sequence, TypeVar, Type, List, Any, Union
import enum
import dataclasses
import datetime as dt

import sqlalchemy as sa

from nominatim.typing import SaSelect, SaRow, SaColumn
from nominatim.api.types import Point, Bbox, LookupDetails
from nominatim.api.connection import SearchConnection
from nominatim.api.logging import log
from nominatim.api.localization import Locales

# This file defines complex result data classes.
# pylint: disable=too-many-instance-attributes

def _mingle_name_tags(names: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """ Mix-in names from linked places, so that they show up
        as standard names where necessary.
    """
    if not names:
        return None

    out = {}
    for k, v in names.items():
        if k.startswith('_place_'):
            outkey = k[7:]
            out[k if outkey in names else outkey] = v
        else:
            out[k] = v

    return out


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

    local_name: Optional[str] = None


class AddressLines(List[AddressLine]):
    """ Sequence of address lines order in descending order by their rank.
    """

    def localize(self, locales: Locales) -> List[str]:
        """ Set the local name of address parts according to the chosen
            locale. Return the list of local names without duplications.

            Only address parts that are marked as isaddress are localized
            and returned.
        """
        label_parts: List[str] = []

        for line in self:
            if line.isaddress and line.names:
                line.local_name = locales.display_name(line.names)
                if not label_parts or label_parts[-1] != line.local_name:
                    label_parts.append(line.local_name)

        return label_parts



@dataclasses.dataclass
class WordInfo:
    """ Detailed information about a search term.
    """
    word_id: int
    word_token: str
    word: Optional[str] = None


WordInfos = Sequence[WordInfo]


@dataclasses.dataclass
class BaseResult:
    """ Data class collecting information common to all
        types of search results.
    """
    source_table: SourceTable
    category: Tuple[str, str]
    centroid: Point

    place_id : Optional[int] = None
    osm_object: Optional[Tuple[str, int]] = None

    locale_name: Optional[str] = None
    display_name: Optional[str] = None

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


    def localize(self, locales: Locales) -> None:
        """ Fill the locale_name and the display_name field for the
            place and, if available, its address information.
        """
        self.locale_name = locales.display_name(self.names)
        if self.address_rows:
            self.display_name = ', '.join(self.address_rows.localize(locales))
        else:
            self.display_name = self.locale_name



BaseResultT = TypeVar('BaseResultT', bound=BaseResult)

@dataclasses.dataclass
class DetailedResult(BaseResult):
    """ A search result with more internal information from the database
        added.
    """
    parent_place_id: Optional[int] = None
    linked_place_id: Optional[int] = None
    admin_level: int = 15
    indexed_date: Optional[dt.datetime] = None


@dataclasses.dataclass
class ReverseResult(BaseResult):
    """ A search result for reverse geocoding.
    """
    distance: Optional[float] = None
    bbox: Optional[Bbox] = None


class ReverseResults(List[ReverseResult]):
    """ Sequence of reverse lookup results ordered by distance.
        May be empty when no result was found.
    """


@dataclasses.dataclass
class SearchResult(BaseResult):
    """ A search result for forward geocoding.
    """
    bbox: Optional[Bbox] = None
    accuracy: float = 0.0


    @property
    def ranking(self) -> float:
        """ Return the ranking, a combined measure of accuracy and importance.
        """
        return (self.accuracy if self.accuracy is not None else 1) \
               - self.calculated_importance()


class SearchResults(List[SearchResult]):
    """ Sequence of forward lookup results ordered by relevance.
        May be empty when no result was found.
    """

    def localize(self, locales: Locales) -> None:
        """ Apply the given locales to all results.
        """
        for result in self:
            result.localize(locales)


def _filter_geometries(row: SaRow) -> Dict[str, str]:
    return {k[9:]: v for k, v in row._mapping.items() # pylint: disable=W0212
            if k.startswith('geometry_')}


def create_from_placex_row(row: Optional[SaRow],
                           class_type: Type[BaseResultT]) -> Optional[BaseResultT]:
    """ Construct a new result and add the data from the result row
        from the placex table. 'class_type' defines the type of result
        to return. Returns None if the row is None.
    """
    if row is None:
        return None

    return class_type(source_table=SourceTable.PLACEX,
                      place_id=row.place_id,
                      osm_object=(row.osm_type, row.osm_id),
                      category=(row.class_, row.type),
                      names=_mingle_name_tags(row.name),
                      address=row.address,
                      extratags=row.extratags,
                      housenumber=row.housenumber,
                      postcode=row.postcode,
                      wikipedia=row.wikipedia,
                      rank_address=row.rank_address,
                      rank_search=row.rank_search,
                      importance=row.importance,
                      country_code=row.country_code,
                      centroid=Point.from_wkb(row.centroid),
                      geometry=_filter_geometries(row))


def create_from_osmline_row(row: Optional[SaRow],
                            class_type: Type[BaseResultT]) -> Optional[BaseResultT]:
    """ Construct a new result and add the data from the result row
        from the address interpolation table osmline. 'class_type' defines
        the type of result to return. Returns None if the row is None.

        If the row contains a housenumber, then the housenumber is filled out.
        Otherwise the result contains the interpolation information in extratags.
    """
    if row is None:
        return None

    hnr = getattr(row, 'housenumber', None)

    res = class_type(source_table=SourceTable.OSMLINE,
                     place_id=row.place_id,
                     osm_object=('W', row.osm_id),
                     category=('place', 'houses' if hnr is None else 'house'),
                     address=row.address,
                     postcode=row.postcode,
                     country_code=row.country_code,
                     centroid=Point.from_wkb(row.centroid),
                     geometry=_filter_geometries(row))

    if hnr is None:
        res.extratags = {'startnumber': str(row.startnumber),
                         'endnumber': str(row.endnumber),
                         'step': str(row.step)}
    else:
        res.housenumber = str(hnr)

    return res


def create_from_tiger_row(row: Optional[SaRow],
                          class_type: Type[BaseResultT]) -> Optional[BaseResultT]:
    """ Construct a new result and add the data from the result row
        from the Tiger data interpolation table. 'class_type' defines
        the type of result to return. Returns None if the row is None.

        If the row contains a housenumber, then the housenumber is filled out.
        Otherwise the result contains the interpolation information in extratags.
    """
    if row is None:
        return None

    hnr = getattr(row, 'housenumber', None)

    res = class_type(source_table=SourceTable.TIGER,
                     place_id=row.place_id,
                     osm_object=(row.osm_type, row.osm_id),
                     category=('place', 'houses' if hnr is None else 'house'),
                     postcode=row.postcode,
                     country_code='us',
                     centroid=Point.from_wkb(row.centroid),
                     geometry=_filter_geometries(row))

    if hnr is None:
        res.extratags = {'startnumber': str(row.startnumber),
                         'endnumber': str(row.endnumber),
                         'step': str(row.step)}
    else:
        res.housenumber = str(hnr)

    return res


def create_from_postcode_row(row: Optional[SaRow],
                          class_type: Type[BaseResultT]) -> Optional[BaseResultT]:
    """ Construct a new result and add the data from the result row
        from the postcode table. 'class_type' defines
        the type of result to return. Returns None if the row is None.
    """
    if row is None:
        return None

    return class_type(source_table=SourceTable.POSTCODE,
                      place_id=row.place_id,
                      category=('place', 'postcode'),
                      names={'ref': row.postcode},
                      rank_search=row.rank_search,
                      rank_address=row.rank_address,
                      country_code=row.country_code,
                      centroid=Point.from_wkb(row.centroid),
                      geometry=_filter_geometries(row))


def create_from_country_row(row: Optional[SaRow],
                        class_type: Type[BaseResultT]) -> Optional[BaseResultT]:
    """ Construct a new result and add the data from the result row
        from the fallback country tables. 'class_type' defines
        the type of result to return. Returns None if the row is None.
    """
    if row is None:
        return None

    return class_type(source_table=SourceTable.COUNTRY,
                      category=('place', 'country'),
                      centroid=Point.from_wkb(row.centroid),
                      names=row.name,
                      rank_address=4, rank_search=4,
                      country_code=row.country_code)


async def add_result_details(conn: SearchConnection, results: List[BaseResultT],
                             details: LookupDetails) -> None:
    """ Retrieve more details from the database according to the
        parameters specified in 'details'.
    """
    if results:
        log().section('Query details for result')
        if details.address_details:
            log().comment('Query address details')
            await complete_address_details(conn, results)
        if details.linked_places:
            log().comment('Query linked places')
            for result in results:
                await complete_linked_places(conn, result)
        if details.parented_places:
            log().comment('Query parent places')
            for result in results:
                await complete_parented_places(conn, result)
        if details.keywords:
            log().comment('Query keywords')
            for result in results:
                await complete_keywords(conn, result)


def _result_row_to_address_row(row: SaRow) -> AddressLine:
    """ Create a new AddressLine from the results of a datbase query.
    """
    extratags: Dict[str, str] = getattr(row, 'extratags', {})
    if hasattr(row, 'place_type') and row.place_type:
        extratags['place'] = row.place_type

    names = _mingle_name_tags(row.name) or {}
    if getattr(row, 'housenumber', None) is not None:
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


def _get_housenumber_details(results: List[BaseResultT]) -> Tuple[List[int], List[int]]:
    places = []
    hnrs = []
    for result in results:
        if result.place_id:
            housenumber = -1
            if result.source_table in (SourceTable.TIGER, SourceTable.OSMLINE):
                if result.housenumber is not None:
                    housenumber = int(result.housenumber)
                elif result.extratags is not None and 'startnumber' in result.extratags:
                    # details requests do not come with a specific house number
                    housenumber = int(result.extratags['startnumber'])
            places.append(result.place_id)
            hnrs.append(housenumber)

    return places, hnrs


async def complete_address_details(conn: SearchConnection, results: List[BaseResultT]) -> None:
    """ Retrieve information about places that make up the address of the result.
    """
    places, hnrs = _get_housenumber_details(results)

    if not places:
        return

    def _get_addressdata(place_id: Union[int, SaColumn], hnr: Union[int, SaColumn]) -> Any:
        return sa.func.get_addressdata(place_id, hnr)\
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
                        sa.column('distance', type_=sa.Float),
                        joins_implicitly=True)


    if len(places) == 1:
        # Optimized case for exactly one result (reverse)
        sql = sa.select(_get_addressdata(places[0], hnrs[0]))\
                .order_by(sa.column('rank_address').desc(),
                          sa.column('isaddress').desc())

        alines = AddressLines()
        for row in await conn.execute(sql):
            alines.append(_result_row_to_address_row(row))

        for result in results:
            if result.place_id == places[0]:
                result.address_rows = alines
                return


    darray = sa.func.unnest(conn.t.types.to_array(places), conn.t.types.to_array(hnrs))\
                    .table_valued( # type: ignore[no-untyped-call]
                       sa.column('place_id', type_= sa.Integer),
                       sa.column('housenumber', type_= sa.Integer)
                    ).render_derived()

    sfn = _get_addressdata(darray.c.place_id, darray.c.housenumber)

    sql = sa.select(darray.c.place_id.label('result_place_id'), sfn)\
            .order_by(darray.c.place_id,
                      sa.column('rank_address').desc(),
                      sa.column('isaddress').desc())

    current_result = None
    for row in await conn.execute(sql):
        if current_result is None or row.result_place_id != current_result.place_id:
            for result in results:
                if result.place_id == row.result_place_id:
                    current_result = result
                    break
            else:
                assert False
            current_result.address_rows = AddressLines()
        current_result.address_rows.append(_result_row_to_address_row(row))


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


async def complete_linked_places(conn: SearchConnection, result: BaseResult) -> None:
    """ Retrieve information about places that link to the result.
    """
    result.linked_rows = AddressLines()
    if result.source_table != SourceTable.PLACEX:
        return

    sql = _placex_select_address_row(conn, result.centroid)\
            .where(conn.t.placex.c.linked_place_id == result.place_id)

    for row in await conn.execute(sql):
        result.linked_rows.append(_result_row_to_address_row(row))


async def complete_keywords(conn: SearchConnection, result: BaseResult) -> None:
    """ Retrieve information about the search terms used for this place.

        Requires that the query analyzer was initialised to get access to
        the word table.
    """
    t = conn.t.search_name
    sql = sa.select(t.c.name_vector, t.c.nameaddress_vector)\
            .where(t.c.place_id == result.place_id)

    result.name_keywords = []
    result.address_keywords = []

    t = conn.t.meta.tables['word']
    sel = sa.select(t.c.word_id, t.c.word_token, t.c.word)

    for name_tokens, address_tokens in await conn.execute(sql):
        for row in await conn.execute(sel.where(t.c.word_id == sa.any_(name_tokens))):
            result.name_keywords.append(WordInfo(*row))

        for row in await conn.execute(sel.where(t.c.word_id == sa.any_(address_tokens))):
            result.address_keywords.append(WordInfo(*row))


async def complete_parented_places(conn: SearchConnection, result: BaseResult) -> None:
    """ Retrieve information about places that the result provides the
        address for.
    """
    result.parented_rows = AddressLines()
    if result.source_table != SourceTable.PLACEX:
        return

    sql = _placex_select_address_row(conn, result.centroid)\
            .where(conn.t.placex.c.parent_place_id == result.place_id)\
            .where(conn.t.placex.c.rank_search == 30)

    for row in await conn.execute(sql):
        result.parented_rows.append(_result_row_to_address_row(row))
