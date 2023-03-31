# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Complex datatypes used by the Nominatim API.
"""
from typing import Optional, Union, Tuple, NamedTuple
import dataclasses
import enum
from struct import unpack

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


class GeometryFormat(enum.Flag):
    """ Geometry output formats supported by Nominatim.
    """
    NONE = 0
    GEOJSON = enum.auto()
    KML = enum.auto()
    SVG = enum.auto()
    TEXT = enum.auto()


@dataclasses.dataclass
class LookupDetails:
    """ Collection of parameters that define the amount of details
        returned with a search result.
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


class DataLayer(enum.Flag):
    """ Layer types that can be selected for reverse and forward search.
    """
    POI = enum.auto()
    ADDRESS = enum.auto()
    RAILWAY = enum.auto()
    MANMADE = enum.auto()
    NATURAL = enum.auto()
