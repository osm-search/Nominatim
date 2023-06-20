# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Complex datatypes used by the Nominatim API.
"""
from typing import Optional, Union, Tuple, NamedTuple, TypeVar, Type, Dict, \
                   Any, List, Sequence
from collections import abc
import dataclasses
import enum
import math
from struct import unpack

from geoalchemy2 import WKTElement
import geoalchemy2.functions

from nominatim.errors import UsageError

# pylint: disable=no-member,too-many-boolean-expressions,too-many-instance-attributes

@dataclasses.dataclass
class PlaceID:
    """ Reference an object by Nominatim's internal ID.
    """
    place_id: int


@dataclasses.dataclass
class OsmID:
    """ Reference by the OSM ID and potentially the basic category.
    """
    osm_type: str
    osm_id: int
    osm_class: Optional[str] = None

    def __post_init__(self) -> None:
        if self.osm_type not in ('N', 'W', 'R'):
            raise ValueError(f"Illegal OSM type '{self.osm_type}'. Must be one of N, W, R.")


PlaceRef = Union[PlaceID, OsmID]


class Point(NamedTuple):
    """ A geographic point in WGS84 projection.
    """
    x: float
    y: float


    @property
    def lat(self) -> float:
        """ Return the latitude of the point.
        """
        return self.y


    @property
    def lon(self) -> float:
        """ Return the longitude of the point.
        """
        return self.x


    def to_geojson(self) -> str:
        """ Return the point in GeoJSON format.
        """
        return f'{{"type": "Point","coordinates": [{self.x}, {self.y}]}}'


    @staticmethod
    def from_wkb(wkb: bytes) -> 'Point':
        """ Create a point from EWKB as returned from the database.
        """
        if len(wkb) != 25:
            raise ValueError("Point wkb has unexpected length")
        if wkb[0] == 0:
            gtype, srid, x, y = unpack('>iidd', wkb[1:])
        elif wkb[0] == 1:
            gtype, srid, x, y = unpack('<iidd', wkb[1:])
        else:
            raise ValueError("WKB has unknown endian value.")

        if gtype != 0x20000001:
            raise ValueError("WKB must be a point geometry.")
        if srid != 4326:
            raise ValueError("Only WGS84 WKB supported.")

        return Point(x, y)


    @staticmethod
    def from_param(inp: Any) -> 'Point':
        """ Create a point from an input parameter. The parameter
            may be given as a point, a string or a sequence of
            strings or floats. Raises a UsageError if the format is
            not correct.
        """
        if isinstance(inp, Point):
            return inp

        seq: Sequence[str]
        if isinstance(inp, str):
            seq = inp.split(',')
        elif isinstance(inp, abc.Sequence):
            seq = inp

        if len(seq) != 2:
            raise UsageError('Point parameter needs 2 coordinates.')
        try:
            x, y = filter(math.isfinite, map(float, seq))
        except ValueError as exc:
            raise UsageError('Point parameter needs to be numbers.') from exc

        if x < -180.0 or x > 180.0 or y < -90.0 or y > 90.0:
            raise UsageError('Point coordinates invalid.')

        return Point(x, y)


    def sql_value(self) -> WKTElement:
        """ Create an SQL expression for the point.
        """
        return WKTElement(f'POINT({self.x} {self.y})', srid=4326)



AnyPoint = Union[Point, Tuple[float, float]]

WKB_BBOX_HEADER_LE = b'\x01\x03\x00\x00\x20\xE6\x10\x00\x00\x01\x00\x00\x00\x05\x00\x00\x00'
WKB_BBOX_HEADER_BE = b'\x00\x20\x00\x00\x03\x00\x00\x10\xe6\x00\x00\x00\x01\x00\x00\x00\x05'

class Bbox:
    """ A bounding box in WSG84 projection.

        The coordinates are available as an array in the 'coord'
        property in the order (minx, miny, maxx, maxy).
    """
    def __init__(self, minx: float, miny: float, maxx: float, maxy: float) -> None:
        self.coords = (minx, miny, maxx, maxy)


    @property
    def minlat(self) -> float:
        """ Southern-most latitude, corresponding to the minimum y coordinate.
        """
        return self.coords[1]


    @property
    def maxlat(self) -> float:
        """ Northern-most latitude, corresponding to the maximum y coordinate.
        """
        return self.coords[3]


    @property
    def minlon(self) -> float:
        """ Western-most longitude, corresponding to the minimum x coordinate.
        """
        return self.coords[0]


    @property
    def maxlon(self) -> float:
        """ Eastern-most longitude, corresponding to the maximum x coordinate.
        """
        return self.coords[2]


    @property
    def area(self) -> float:
        """ Return the area of the box in WGS84.
        """
        return (self.coords[2] - self.coords[0]) * (self.coords[3] - self.coords[1])


    def sql_value(self) -> Any:
        """ Create an SQL expression for the box.
        """
        return geoalchemy2.functions.ST_MakeEnvelope(*self.coords, 4326)


    def contains(self, pt: Point) -> bool:
        """ Check if the point is inside or on the boundary of the box.
        """
        return self.coords[0] <= pt[0] and self.coords[1] <= pt[1]\
               and self.coords[2] >= pt[0] and self.coords[3] >= pt[1]


    @staticmethod
    def from_wkb(wkb: Optional[bytes]) -> 'Optional[Bbox]':
        """ Create a Bbox from a bounding box polygon as returned by
            the database. Return s None if the input value is None.
        """
        if wkb is None:
            return None

        if len(wkb) != 97:
            raise ValueError("WKB must be a bounding box polygon")
        if wkb.startswith(WKB_BBOX_HEADER_LE):
            x1, y1, _, _, x2, y2 = unpack('<dddddd', wkb[17:65])
        elif wkb.startswith(WKB_BBOX_HEADER_BE):
            x1, y1, _, _, x2, y2 = unpack('>dddddd', wkb[17:65])
        else:
            raise ValueError("WKB has wrong header")

        return Bbox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


    @staticmethod
    def from_point(pt: Point, buffer: float) -> 'Bbox':
        """ Return a Bbox around the point with the buffer added to all sides.
        """
        return Bbox(pt[0] - buffer, pt[1] - buffer,
                    pt[0] + buffer, pt[1] + buffer)


    @staticmethod
    def from_param(inp: Any) -> 'Bbox':
        """ Return a Bbox from an input parameter. The box may be
            given as a Bbox, a string or a list or strings or integer.
            Raises a UsageError if the format is incorrect.
        """
        if isinstance(inp, Bbox):
            return inp

        seq: Sequence[str]
        if isinstance(inp, str):
            seq = inp.split(',')
        elif isinstance(inp, abc.Sequence):
            seq = inp

        if len(seq) != 4:
            raise UsageError('Bounding box parameter needs 4 coordinates.')
        try:
            x1, y1, x2, y2 = filter(math.isfinite, map(float, seq))
        except ValueError as exc:
            raise UsageError('Bounding box parameter needs to be numbers.') from exc

        if x1 < -180.0 or x1 > 180.0 or y1 < -90.0 or y1 > 90.0 \
           or x2 < -180.0 or x2 > 180.0 or y2 < -90.0 or y2 > 90.0:
            raise UsageError('Bounding box coordinates invalid.')

        if x1 == x2 or y1 == y2:
            raise UsageError('Bounding box with invalid parameters.')

        return Bbox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


class GeometryFormat(enum.Flag):
    """ Geometry output formats supported by Nominatim.
    """
    NONE = 0
    GEOJSON = enum.auto()
    KML = enum.auto()
    SVG = enum.auto()
    TEXT = enum.auto()


class DataLayer(enum.Flag):
    """ Layer types that can be selected for reverse and forward search.
    """
    POI = enum.auto()
    ADDRESS = enum.auto()
    RAILWAY = enum.auto()
    MANMADE = enum.auto()
    NATURAL = enum.auto()


def format_country(cc: Any) -> List[str]:
    """ Extract a list of country codes from the input which may be either
        a string or list of strings. Filters out all values that are not
        a two-letter string.
    """
    clist: Sequence[str]
    if isinstance(cc, str):
        clist = cc.split(',')
    elif isinstance(cc, abc.Sequence):
        clist = cc
    else:
        raise UsageError("Parameter 'country' needs to be a comma-separated list "
                         "or a Python list of strings.")

    return [cc.lower() for cc in clist if isinstance(cc, str) and len(cc) == 2]


def format_excluded(ids: Any) -> List[int]:
    """ Extract a list of place ids from the input which may be either
        a string or a list of strings or ints. Ignores empty value but
        throws a UserError on anything that cannot be converted to int.
    """
    plist: Sequence[str]
    if isinstance(ids, str):
        plist = [s.strip() for s in ids.split(',')]
    elif isinstance(ids, abc.Sequence):
        plist = ids
    else:
        raise UsageError("Parameter 'excluded' needs to be a comma-separated list "
                         "or a Python list of numbers.")
    if not all(isinstance(i, int) or
               (isinstance(i, str) and (not i or i.isdigit())) for i in plist):
        raise UsageError("Parameter 'excluded' only takes place IDs.")

    return [int(id) for id in plist if id]


def format_categories(categories: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """ Extract a list of categories. Currently a noop.
    """
    return categories

TParam = TypeVar('TParam', bound='LookupDetails') # pylint: disable=invalid-name

@dataclasses.dataclass
class LookupDetails:
    """ Collection of parameters that define the amount of details
        returned with a lookup or details result.
    """
    geometry_output: GeometryFormat = GeometryFormat.NONE
    """ Add the full geometry of the place to the result. Multiple
        formats may be selected. Note that geometries can become quite large.
    """
    address_details: bool = False
    """ Get detailed information on the places that make up the address
        for the result.
    """
    linked_places: bool = False
    """ Get detailed information on the places that link to the result.
    """
    parented_places: bool = False
    """ Get detailed information on all places that this place is a parent
        for, i.e. all places for which it provides the address details.
        Only POI places can have parents.
    """
    keywords: bool = False
    """ Add information about the search terms used for this place.
    """
    geometry_simplification: float = 0.0
    """ Simplification factor for a geometry in degrees WGS. A factor of
        0.0 means the original geometry is kept. The higher the value, the
        more the geometry gets simplified.
    """

    @classmethod
    def from_kwargs(cls: Type[TParam], kwargs: Dict[str, Any]) -> TParam:
        """ Load the data fields of the class from a dictionary.
            Unknown entries in the dictionary are ignored, missing ones
            get the default setting.

            The function supports type checking and throws a UsageError
            when the value does not fit.
        """
        def _check_field(v: Any, field: 'dataclasses.Field[Any]') -> Any:
            if v is None:
                return field.default_factory() \
                       if field.default_factory != dataclasses.MISSING \
                       else field.default
            if field.metadata and 'transform' in field.metadata:
                return field.metadata['transform'](v)
            if not isinstance(v, field.type):
                raise UsageError(f"Parameter '{field.name}' needs to be of {field.type!s}.")
            return v

        return cls(**{f.name: _check_field(kwargs[f.name], f)
                      for f in dataclasses.fields(cls) if f.name in kwargs})


@dataclasses.dataclass
class ReverseDetails(LookupDetails):
    """ Collection of parameters for the reverse call.
    """
    max_rank: int = dataclasses.field(default=30,
                                      metadata={'transform': lambda v: max(0, min(v, 30))}
                                     )
    """ Highest address rank to return.
    """
    layers: DataLayer = DataLayer.ADDRESS | DataLayer.POI
    """ Filter which kind of data to include.
    """

@dataclasses.dataclass
class SearchDetails(LookupDetails):
    """ Collection of parameters for the search call.
    """
    max_results: int = 10
    """ Maximum number of results to be returned. The actual number of results
        may be less.
    """
    min_rank: int = dataclasses.field(default=0,
                                      metadata={'transform': lambda v: max(0, min(v, 30))}
                                     )
    """ Lowest address rank to return.
    """
    max_rank: int = dataclasses.field(default=30,
                                      metadata={'transform': lambda v: max(0, min(v, 30))}
                                     )
    """ Highest address rank to return.
    """
    layers: Optional[DataLayer] = dataclasses.field(default=None,
                                                    metadata={'transform': lambda r : r})
    """ Filter which kind of data to include. When 'None' (the default) then
        filtering by layers is disabled.
    """
    countries: List[str] = dataclasses.field(default_factory=list,
                                             metadata={'transform': format_country})
    """ Restrict search results to the given countries. An empty list (the
        default) will disable this filter.
    """
    excluded: List[int] = dataclasses.field(default_factory=list,
                                            metadata={'transform': format_excluded})
    """ List of OSM objects to exclude from the results. Currenlty only
        works when the internal place ID is given.
        An empty list (the default) will disable this filter.
    """
    viewbox: Optional[Bbox] = dataclasses.field(default=None,
                                                metadata={'transform': Bbox.from_param})
    """ Focus the search on a given map area.
    """
    bounded_viewbox: bool = False
    """ Use 'viewbox' as a filter and restrict results to places within the
        given area.
    """
    near: Optional[Point] = dataclasses.field(default=None,
                                              metadata={'transform': Point.from_param})
    """ Order results by distance to the given point.
    """
    near_radius: Optional[float] = dataclasses.field(default=None,
                                              metadata={'transform': lambda r : r})
    """ Use near point as a filter and drop results outside the given
        radius. Radius is given in degrees WSG84.
    """
    categories: List[Tuple[str, str]] = dataclasses.field(default_factory=list,
                                                          metadata={'transform': format_categories})
    """ Restrict search to places with one of the given class/type categories.
        An empty list (the default) will disable this filter.
    """

    def __post_init__(self) -> None:
        if self.viewbox is not None:
            xext = (self.viewbox.maxlon - self.viewbox.minlon)/2
            yext = (self.viewbox.maxlat - self.viewbox.minlat)/2
            self.viewbox_x2 = Bbox(self.viewbox.minlon - xext, self.viewbox.minlat - yext,
                                   self.viewbox.maxlon + xext, self.viewbox.maxlat + yext)


    def restrict_min_max_rank(self, new_min: int, new_max: int) -> None:
        """ Change the min_rank and max_rank fields to respect the
            given boundaries.
        """
        assert new_min <= new_max
        self.min_rank = max(self.min_rank, new_min)
        self.max_rank = min(self.max_rank, new_max)


    def is_impossible(self) -> bool:
        """ Check if the parameter configuration is contradictionary and
            cannot yield any results.
        """
        return (self.min_rank > self.max_rank
                or (self.bounded_viewbox
                    and self.viewbox is not None and self.near is not None
                    and self.viewbox.contains(self.near))
                or self.layers is not None and not self.layers)


    def layer_enabled(self, layer: DataLayer) -> bool:
        """ Check if the given layer has been choosen. Also returns
            true when layer restriction has been disabled completely.
        """
        return self.layers is None or bool(self.layers & layer)
