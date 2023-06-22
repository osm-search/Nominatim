# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper function for parsing parameters and and outputting data
specifically for the v1 version of the API.
"""
from typing import Tuple, Optional, Any, Dict, Iterable
from itertools import chain
import re

from nominatim.api.results import SearchResult, SearchResults, SourceTable
from nominatim.api.types import SearchDetails, GeometryFormat

REVERSE_MAX_RANKS = [2, 2, 2,   # 0-2   Continent/Sea
                     4, 4,      # 3-4   Country
                     8,         # 5     State
                     10, 10,    # 6-7   Region
                     12, 12,    # 8-9   County
                     16, 17,    # 10-11 City
                     18,        # 12    Town
                     19,        # 13    Village/Suburb
                     22,        # 14    Hamlet/Neighbourhood
                     25,        # 15    Localities
                     26,        # 16    Major Streets
                     27,        # 17    Minor Streets
                     30         # 18    Building
                    ]


def zoom_to_rank(zoom: int) -> int:
    """ Convert a zoom parameter into a rank according to the v1 API spec.
    """
    return REVERSE_MAX_RANKS[max(0, min(18, zoom))]


FEATURE_TYPE_TO_RANK: Dict[Optional[str], Any] = {
    'country': (4, 4),
    'state': (8, 8),
    'city': (14, 16),
    'settlement': (8, 20)
}


def feature_type_to_rank(feature_type: Optional[str]) -> Tuple[int, int]:
    """ Convert a feature type parameter to a tuple of
        feature type name, minimum rank and maximum rank.
    """
    return FEATURE_TYPE_TO_RANK.get(feature_type, (0, 30))


#pylint: disable=too-many-arguments,too-many-branches
def extend_query_parts(queryparts: Dict[str, Any], details: Dict[str, Any],
                       feature_type: Optional[str],
                       namedetails: bool, extratags: bool,
                       excluded: Iterable[str]) -> None:
    """ Add parameters from details dictionary to the query parts
        dictionary which is suitable as URL parameter dictionary.
    """
    parsed = SearchDetails.from_kwargs(details)
    if parsed.geometry_output != GeometryFormat.NONE:
        if GeometryFormat.GEOJSON in parsed.geometry_output:
            queryparts['polygon_geojson'] = '1'
        if GeometryFormat.KML in parsed.geometry_output:
            queryparts['polygon_kml'] = '1'
        if GeometryFormat.SVG in parsed.geometry_output:
            queryparts['polygon_svg'] = '1'
        if GeometryFormat.TEXT in parsed.geometry_output:
            queryparts['polygon_text'] = '1'
    if parsed.address_details:
        queryparts['addressdetails'] = '1'
    if namedetails:
        queryparts['namedetails'] = '1'
    if extratags:
        queryparts['extratags'] = '1'
    if parsed.geometry_simplification > 0.0:
        queryparts['polygon_threshold'] = f"{parsed.geometry_simplification:.6g}"
    if parsed.max_results != 10:
        queryparts['limit'] = str(parsed.max_results)
    if parsed.countries:
        queryparts['countrycodes'] = ','.join(parsed.countries)
    queryparts['exclude_place_ids'] = \
        ','.join(chain(excluded, map(str, parsed.excluded)))
    if parsed.viewbox:
        queryparts['viewbox'] = ','.join(f"{c:.7g}" for c in parsed.viewbox.coords)
    if parsed.bounded_viewbox:
        queryparts['bounded'] = '1'
    if not details['dedupe']:
        queryparts['dedupe'] = '0'
    if feature_type in FEATURE_TYPE_TO_RANK:
        queryparts['featureType'] = feature_type


def deduplicate_results(results: SearchResults, max_results: int) -> SearchResults:
    """ Remove results that look like duplicates.

        Two results are considered the same if they have the same OSM ID
        or if they have the same category, display name and rank.
    """
    osm_ids_done = set()
    classification_done = set()
    deduped = SearchResults()
    for result in results:
        if result.source_table == SourceTable.POSTCODE:
            assert result.names and 'ref' in result.names
            if any(_is_postcode_relation_for(r, result.names['ref']) for r in results):
                continue
        classification = (result.osm_object[0] if result.osm_object else None,
                          result.category,
                          result.display_name,
                          result.rank_address)
        if result.osm_object not in osm_ids_done \
           and classification not in classification_done:
            deduped.append(result)
        osm_ids_done.add(result.osm_object)
        classification_done.add(classification)
        if len(deduped) >= max_results:
            break

    return deduped


def _is_postcode_relation_for(result: SearchResult, postcode: str) -> bool:
    return result.source_table == SourceTable.PLACEX \
           and result.osm_object is not None \
           and result.osm_object[0] == 'R' \
           and result.category == ('boundary', 'postal_code') \
           and result.names is not None \
           and result.names.get('ref') == postcode


def _deg(axis:str) -> str:
    return f"(?P<{axis}_deg>\\d+\\.\\d+)°?"

def _deg_min(axis: str) -> str:
    return f"(?P<{axis}_deg>\\d+)[°\\s]+(?P<{axis}_min>[\\d.]+)?[′']*"

def _deg_min_sec(axis: str) -> str:
    return f"(?P<{axis}_deg>\\d+)[°\\s]+(?P<{axis}_min>\\d+)[′'\\s]+(?P<{axis}_sec>[\\d.]+)?[\"″]*"

COORD_REGEX = [re.compile(r'(?:(?P<pre>.*?)\s+)??' + r + r'(?:\s+(?P<post>.*))?') for r in (
    r"(?P<ns>[NS])\s*" + _deg('lat') + r"[\s,]+" + r"(?P<ew>[EW])\s*" + _deg('lon'),
    _deg('lat') + r"\s*(?P<ns>[NS])[\s,]+" + _deg('lon') + r"\s*(?P<ew>[EW])",
    r"(?P<ns>[NS])\s*" + _deg_min('lat') + r"[\s,]+" + r"(?P<ew>[EW])\s*" + _deg_min('lon'),
    _deg_min('lat') + r"\s*(?P<ns>[NS])[\s,]+" + _deg_min('lon') + r"\s*(?P<ew>[EW])",
    r"(?P<ns>[NS])\s*" + _deg_min_sec('lat') + r"[\s,]+" + r"(?P<ew>[EW])\s*" + _deg_min_sec('lon'),
    _deg_min_sec('lat') + r"\s*(?P<ns>[NS])[\s,]+" + _deg_min_sec('lon') + r"\s*(?P<ew>[EW])",
    r"\[?(?P<lat_deg>[+-]?\d+\.\d+)[\s,]+(?P<lon_deg>[+-]?\d+\.\d+)\]?"
)]

def extract_coords_from_query(query: str) -> Tuple[str, Optional[float], Optional[float]]:
    """ Look for something that is formated like a coordinate at the
        beginning or end of the query. If found, extract the coordinate and
        return the remaining query (or the empty string if the query
        consisted of nothing but a coordinate).

        Only the first match will be returned.
    """
    for regex in COORD_REGEX:
        match = regex.fullmatch(query)
        if match is None:
            continue
        groups = match.groupdict()
        if not groups['pre'] or not groups['post']:
            x = float(groups['lon_deg']) \
                + float(groups.get('lon_min', 0.0)) / 60.0 \
                + float(groups.get('lon_sec', 0.0)) / 3600.0
            if groups.get('ew') == 'W':
                x = -x
            y = float(groups['lat_deg']) \
                + float(groups.get('lat_min', 0.0)) / 60.0 \
                + float(groups.get('lat_sec', 0.0)) / 3600.0
            if groups.get('ns') == 'S':
                y = -y
            return groups['pre'] or groups['post'] or '', x, y

    return query, None, None


CATEGORY_REGEX = re.compile(r'(?P<pre>.*?)\[(?P<cls>[a-zA-Z_]+)=(?P<typ>[a-zA-Z_]+)\](?P<post>.*)')

def extract_category_from_query(query: str) -> Tuple[str, Optional[str], Optional[str]]:
    """ Extract a hidden category specification of the form '[key=value]' from
        the query. If found, extract key and value  and
        return the remaining query (or the empty string if the query
        consisted of nothing but a category).

        Only the first match will be returned.
    """
    match = CATEGORY_REGEX.search(query)
    if match is not None:
        return (match.group('pre').strip() + ' ' + match.group('post').strip()).strip(), \
               match.group('cls'), match.group('typ')

    return query, None, None
