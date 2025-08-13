# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Dataclasses for search results and helper functions to fill them.

Data classes are part of the public API while the functions are for
internal use only. That's why they are implemented as free-standing functions
instead of member functions.
"""
from typing import (
    Optional, Tuple, Dict, Sequence, TypeVar, Type, List,
    cast, Callable
)
import enum
import dataclasses
import datetime as dt

import sqlalchemy as sa

from .typing import SaSelect, SaRow
from .sql.sqlalchemy_types import Geometry
from .types import Point, Bbox, LookupDetails
from .connection import SearchConnection
from .logging import log

# This file defines complex result data classes.


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
    """ The `SourceTable` type lists the possible sources a result can have.
    """
    PLACEX = 1
    """ The placex table is the main source for result usually containing
        OSM data.
    """
    OSMLINE = 2
    """ The osmline table contains address interpolations from OSM data.
        Interpolation addresses are always approximate. The OSM id in the
        result refers to the OSM way with the interpolation line object.
    """
    TIGER = 3
    """ TIGER address data contains US addresses imported on the side,
        see [Installing TIGER data](../customize/Tiger.md).
        TIGER address are also interpolations. The addresses always refer
        to a street from OSM data. The OSM id in the result refers to
        that street.
    """
    POSTCODE = 4
    """ The postcode table contains artificial centroids for postcodes,
        computed from the postcodes available with address points. Results
        are always approximate.
    """
    COUNTRY = 5
    """ The country table provides a fallback, when country data is missing
        in the OSM data.
    """


@dataclasses.dataclass
class AddressLine:
    """ The `AddressLine` may contain the following fields about a related place
        and its function as an address object. Most fields are optional.
        Their presence depends on the kind and function of the address part.
    """
    category: Tuple[str, str]
    """ Main category of the place, described by a key-value pair.
    """
    names: Dict[str, str]
    """ All available names for the place including references, alternative
        names and translations.
    """
    fromarea: bool
    """ If true, then the exact area of the place is known. Without area
        information, Nominatim has to make an educated guess if an address
        belongs to one place or another.
    """
    isaddress: bool
    """ If true, this place should be considered for the final address display.
        Nominatim will sometimes include more than one candidate for
        the address in the list when it cannot reliably determine where the
        place belongs. It will consider names of all candidates when searching
        but when displaying the result, only the most likely candidate should
        be shown.
    """
    rank_address: int
    """ [Address rank](../customize/Ranking.md#address-rank) of the place.
    """
    distance: float
    """ Distance in degrees between the result place and this address part.
    """
    place_id: Optional[int] = None
    """ Internal ID of the place.
    """
    osm_object: Optional[Tuple[str, int]] = None
    """ OSM type and ID of the place, if such an object exists.
    """
    extratags: Optional[Dict[str, str]] = None
    """ Any extra information available about the place. This is a dictionary
        that usually contains OSM tag key-value pairs.
    """

    admin_level: Optional[int] = None
    """ The administrative level of a boundary as tagged in the input data.
        This field is only meaningful for places of the category
        (boundary, administrative).
    """

    local_name: Optional[str] = None
    """ Place holder for localization of this address part. See
        [Localization](Result-Handling.md#localization) below.
    """

    local_name_lang: Optional[str] = None
    """ Place holder for language of this address part, computed
        during localization
    """

    @property
    def display_name(self) -> Optional[str]:
        """ Dynamically compute the display name for the Address Line component
        """
        if self.local_name:
            return self.local_name
        elif 'name' in self.names:
            return self.names['name']
        elif self.names:
            return next(iter(self.names.values()), None)
        return None


class AddressLines(List[AddressLine]):
    """ A wrapper around a list of AddressLine objects."""


@dataclasses.dataclass
class WordInfo:
    """ Each entry in the list of search terms contains the
        following detailed information.
    """
    word_id: int
    """ Internal identifier for the word.
    """
    word_token: str
    """ Normalised and transliterated form of the word.
        This form is used for searching.
    """
    word: Optional[str] = None
    """ Untransliterated form, if available.
    """


WordInfos = Sequence[WordInfo]


@dataclasses.dataclass
class BaseResult:
    """ Data class collecting information common to all
        types of search results.
    """
    source_table: SourceTable
    category: Tuple[str, str]
    centroid: Point

    place_id: Optional[int] = None
    osm_object: Optional[Tuple[str, int]] = None
    parent_place_id: Optional[int] = None
    linked_place_id: Optional[int] = None
    admin_level: int = 15

    locale_name: Optional[str] = None
    region_lang: Optional[str] = None

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

    @property
    def display_name(self) -> Optional[str]:
        """ Dynamically compute the display name for the result place
            and, if available, its address information..
        """
        if self.address_rows:  # if this is true we need additional processing
            label_parts: List[str] = []

            for line in self.address_rows:  # assume locale_name is set by external formatter
                if line.isaddress and line.names:
                    address_name = line.display_name

                    if address_name and (not label_parts or label_parts[-1] != address_name):
                        label_parts.append(address_name)

            if label_parts:
                return ', '.join(label_parts)

        # Now adding additional information for reranking
        if self.locale_name:
            return self.locale_name
        elif self.names and 'name' in self.names:
            return self.names['name']
        elif self.names:
            return next(iter(self.names.values()))
        elif self.housenumber:
            return self.housenumber
        return None

    def calculated_importance(self) -> float:
        """ Get a valid importance value. This is either the stored importance
            of the value or an artificial value computed from the place's
            search rank.
        """
        return self.importance or (0.40001 - (self.rank_search/75.0))


BaseResultT = TypeVar('BaseResultT', bound=BaseResult)


@dataclasses.dataclass
class DetailedResult(BaseResult):
    """ A search result with more internal information from the database
        added.
    """
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


def _filter_geometries(row: SaRow) -> Dict[str, str]:
    return {k[9:]: v for k, v in row._mapping.items()
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
                      parent_place_id=row.parent_place_id,
                      linked_place_id=getattr(row, 'linked_place_id', None),
                      admin_level=getattr(row, 'admin_level', 15),
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
                     parent_place_id=row.parent_place_id,
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
                          class_type: Type[BaseResultT],
                          osm_type: Optional[str] = None,
                          osm_id: Optional[int] = None) -> Optional[BaseResultT]:
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
                     parent_place_id=row.parent_place_id,
                     osm_object=(osm_type or row.osm_type, osm_id or row.osm_id),
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
                      parent_place_id=row.parent_place_id,
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
                      country_code=row.country_code,
                      geometry=_filter_geometries(row))


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


def _result_row_to_address_row(row: SaRow, isaddress: Optional[bool] = None) -> AddressLine:
    """ Create a new AddressLine from the results of a database query.
    """
    extratags: Dict[str, str] = getattr(row, 'extratags', {}) or {}
    if 'linked_place' in extratags:
        extratags['place'] = extratags['linked_place']

    names = _mingle_name_tags(row.name) or {}
    if getattr(row, 'housenumber', None) is not None:
        names['housenumber'] = row.housenumber

    if isaddress is None:
        isaddress = getattr(row, 'isaddress', True)

    return AddressLine(place_id=row.place_id,
                       osm_object=None if row.osm_type is None else (row.osm_type, row.osm_id),
                       category=(getattr(row, 'class'), row.type),
                       names=names,
                       extratags=extratags,
                       admin_level=row.admin_level,
                       fromarea=row.fromarea,
                       isaddress=isaddress,
                       rank_address=row.rank_address,
                       distance=row.distance)


def _get_address_lookup_id(result: BaseResultT) -> int:
    assert result.place_id
    if result.source_table != SourceTable.PLACEX or result.rank_search > 27:
        return result.parent_place_id or result.place_id

    return result.linked_place_id or result.place_id


async def _finalize_entry(conn: SearchConnection, result: BaseResultT) -> None:
    assert result.address_rows is not None
    if result.category[0] not in ('boundary', 'place')\
       or result.category[1] not in ('postal_code', 'postcode'):
        postcode = result.postcode
        if not postcode and result.address:
            postcode = result.address.get('postcode')
        if postcode and ',' not in postcode and ';' not in postcode:
            result.address_rows.append(AddressLine(
                category=('place', 'postcode'),
                names={'ref': postcode},
                fromarea=False, isaddress=True, rank_address=5,
                distance=0.0))
    if result.country_code:
        async def _get_country_names() -> Optional[Dict[str, str]]:
            t = conn.t.country_name
            sql = sa.select(t.c.name, t.c.derived_name)\
                    .where(t.c.country_code == result.country_code)
            for cres in await conn.execute(sql):
                names = cast(Dict[str, str], cres[0])
                if cres[1]:
                    names.update(cast(Dict[str, str], cres[1]))
                return names
            return None

        country_names = await conn.get_cached_value('COUNTRY_NAME',
                                                    result.country_code,
                                                    _get_country_names)
        if country_names:
            result.address_rows.append(AddressLine(
                category=('place', 'country'),
                names=country_names,
                fromarea=False, isaddress=True, rank_address=4,
                distance=0.0))
        result.address_rows.append(AddressLine(
            category=('place', 'country_code'),
            names={'ref': result.country_code}, extratags={},
            fromarea=True, isaddress=False, rank_address=4,
            distance=0.0))


def _setup_address_details(result: BaseResultT) -> None:
    """ Retrieve information about places that make up the address of the result.
    """
    result.address_rows = AddressLines()
    if result.names:
        result.address_rows.append(AddressLine(
            place_id=result.place_id,
            osm_object=result.osm_object,
            category=result.category,
            names=result.names,
            extratags=result.extratags or {},
            admin_level=result.admin_level,
            fromarea=True, isaddress=True,
            rank_address=result.rank_address, distance=0.0))
    if result.source_table == SourceTable.PLACEX and result.address:
        housenumber = result.address.get('housenumber')\
                      or result.address.get('streetnumber')\
                      or result.address.get('conscriptionnumber')
    elif result.housenumber:
        housenumber = result.housenumber
    else:
        housenumber = None
    if housenumber:
        result.address_rows.append(AddressLine(
            category=('place', 'house_number'),
            names={'ref': housenumber},
            fromarea=True, isaddress=True, rank_address=28, distance=0))
    if result.address and '_unlisted_place' in result.address:
        result.address_rows.append(AddressLine(
            category=('place', 'locality'),
            names={'name': result.address['_unlisted_place']},
            fromarea=False, isaddress=True, rank_address=25, distance=0))


async def complete_address_details(conn: SearchConnection, results: List[BaseResultT]) -> None:
    """ Retrieve information about places that make up the address of the result.
    """
    for result in results:
        _setup_address_details(result)

    # Lookup entries from place_address line

    lookup_ids = [{'pid': r.place_id,
                   'lid': _get_address_lookup_id(r),
                   'names': list(r.address.values()) if r.address else [],
                   'c': ('SRID=4326;' + r.centroid.to_wkt()) if r.centroid else ''}
                  for r in results if r.place_id]

    if not lookup_ids:
        return

    ltab = sa.func.JsonArrayEach(sa.type_coerce(lookup_ids, sa.JSON))\
             .table_valued(sa.column('value', type_=sa.JSON))

    t = conn.t.placex
    taddr = conn.t.addressline

    sql = sa.select(ltab.c.value['pid'].as_integer().label('src_place_id'),
                    t.c.place_id, t.c.osm_type, t.c.osm_id, t.c.name,
                    t.c.class_, t.c.type, t.c.extratags,
                    t.c.admin_level, taddr.c.fromarea,
                    sa.case((t.c.rank_address == 11, 5),
                            else_=t.c.rank_address).label('rank_address'),
                    taddr.c.distance, t.c.country_code, t.c.postcode)\
            .join(taddr, sa.or_(taddr.c.place_id == ltab.c.value['pid'].as_integer(),
                                taddr.c.place_id == ltab.c.value['lid'].as_integer()))\
            .join(t, taddr.c.address_place_id == t.c.place_id)\
            .order_by('src_place_id')\
            .order_by(sa.column('rank_address').desc())\
            .order_by((taddr.c.place_id == ltab.c.value['pid'].as_integer()).desc())\
            .order_by(sa.case((sa.func.CrosscheckNames(t.c.name, ltab.c.value['names']), 2),
                              (taddr.c.isaddress, 0),
                              (sa.and_(taddr.c.fromarea,
                                       t.c.geometry.ST_Contains(
                                           sa.func.ST_GeomFromEWKT(
                                               ltab.c.value['c'].as_string()))), 1),
                              else_=-1).desc())\
            .order_by(taddr.c.fromarea.desc())\
            .order_by(taddr.c.distance.desc())\
            .order_by(t.c.rank_search.desc())

    current_result = None
    current_rank_address = -1
    for row in await conn.execute(sql):
        if current_result is None or row.src_place_id != current_result.place_id:
            current_result = next((r for r in results if r.place_id == row.src_place_id), None)
            assert current_result is not None
            current_rank_address = -1

        location_isaddress = row.rank_address != current_rank_address

        if current_result.country_code is None and row.country_code:
            current_result.country_code = row.country_code

        if row.type in ('postcode', 'postal_code') and location_isaddress:
            if not row.fromarea or \
               (current_result.address and 'postcode' in current_result.address):
                location_isaddress = False
            else:
                current_result.postcode = None

        assert current_result.address_rows is not None
        current_result.address_rows.append(_result_row_to_address_row(row, location_isaddress))
        current_rank_address = row.rank_address

    for result in results:
        await _finalize_entry(conn, result)

    # Finally add the record for the parent entry where necessary.

    parent_lookup_ids = list(filter(lambda e: e['pid'] != e['lid'], lookup_ids))
    if parent_lookup_ids:
        ltab = sa.func.JsonArrayEach(sa.type_coerce(parent_lookup_ids, sa.JSON))\
                 .table_valued(sa.column('value', type_=sa.JSON))
        sql = sa.select(ltab.c.value['pid'].as_integer().label('src_place_id'),
                        t.c.place_id, t.c.osm_type, t.c.osm_id, t.c.name,
                        t.c.class_, t.c.type, t.c.extratags,
                        t.c.admin_level,
                        t.c.rank_address)\
                .where(t.c.place_id == ltab.c.value['lid'].as_integer())

        for row in await conn.execute(sql):
            current_result = next((r for r in results if r.place_id == row.src_place_id), None)
            assert current_result is not None
            assert current_result.address_rows is not None

            current_result.address_rows.append(AddressLine(
                    place_id=row.place_id,
                    osm_object=(row.osm_type, row.osm_id),
                    category=(row.class_, row.type),
                    names=row.name, extratags=row.extratags or {},
                    admin_level=row.admin_level,
                    fromarea=True, isaddress=True,
                    rank_address=row.rank_address, distance=0.0))

    # Now sort everything
    def mk_sort_key(place_id: Optional[int]) -> Callable[[AddressLine], Tuple[bool, int, bool]]:
        return lambda a: (a.place_id != place_id, -a.rank_address, a.isaddress)

    for result in results:
        assert result.address_rows is not None
        result.address_rows.sort(key=mk_sort_key(result.place_id))


def _placex_select_address_row(conn: SearchConnection,
                               centroid: Point) -> SaSelect:
    t = conn.t.placex
    return sa.select(t.c.place_id, t.c.osm_type, t.c.osm_id, t.c.name,
                     t.c.class_.label('class'), t.c.type,
                     t.c.admin_level, t.c.housenumber,
                     t.c.geometry.is_area().label('fromarea'),
                     t.c.rank_address,
                     t.c.geometry.distance_spheroid(
                       sa.bindparam('centroid', value=centroid, type_=Geometry)).label('distance'))


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
        for row in await conn.execute(sel.where(t.c.word_id.in_(name_tokens))):
            result.name_keywords.append(WordInfo(*row))

        for row in await conn.execute(sel.where(t.c.word_id.in_(address_tokens))):
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
