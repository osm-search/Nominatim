# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions for output of results in XML format.
"""
from typing import Mapping, Any, Optional, Union
import datetime as dt
import xml.etree.ElementTree as ET

import nominatim.api as napi
import nominatim.api.v1.classtypes as cl

#pylint: disable=too-many-branches

def _write_xml_address(root: ET.Element, address: napi.AddressLines,
                       country_code: Optional[str]) -> None:
    parts = {}
    for line in address:
        if line.isaddress:
            if line.local_name:
                label = cl.get_label_tag(line.category, line.extratags,
                                         line.rank_address, country_code)
                if label not in parts:
                    parts[label] = line.local_name
            if line.names and 'ISO3166-2' in line.names and line.admin_level:
                parts[f"ISO3166-2-lvl{line.admin_level}"] = line.names['ISO3166-2']

    for k,v in parts.items():
        ET.SubElement(root, k).text = v

    if country_code:
        ET.SubElement(root, 'country_code').text = country_code


def _create_base_entry(result: Union[napi.ReverseResult, napi.SearchResult],
                       root: ET.Element, simple: bool) -> ET.Element:
    place = ET.SubElement(root, 'result' if simple else 'place')
    if result.place_id is not None:
        place.set('place_id', str(result.place_id))
    if result.osm_object:
        osm_type = cl.OSM_TYPE_NAME.get(result.osm_object[0], None)
        if osm_type is not None:
            place.set('osm_type', osm_type)
        place.set('osm_id', str(result.osm_object[1]))
    if result.names and 'ref' in result.names:
        place.set('ref', result.names['ref'])
    elif result.locale_name:
        # bug reproduced from PHP
        place.set('ref', result.locale_name)
    place.set('lat', f"{result.centroid.lat:.7f}")
    place.set('lon', f"{result.centroid.lon:.7f}")

    bbox = cl.bbox_from_result(result)
    place.set('boundingbox',
              f"{bbox.minlat:.7f},{bbox.maxlat:.7f},{bbox.minlon:.7f},{bbox.maxlon:.7f}")

    place.set('place_rank', str(result.rank_search))
    place.set('address_rank', str(result.rank_address))

    if result.geometry:
        for key in ('text', 'svg'):
            if key in result.geometry:
                place.set('geo' + key, result.geometry[key])
        if 'kml' in result.geometry:
            ET.SubElement(root if simple else place, 'geokml')\
              .append(ET.fromstring(result.geometry['kml']))
        if 'geojson' in result.geometry:
            place.set('geojson', result.geometry['geojson'])

    if simple:
        place.text = result.display_name or ''
    else:
        place.set('display_name', result.display_name or '')
        place.set('class', result.category[0])
        place.set('type', result.category[1])
        place.set('importance', str(result.calculated_importance()))

    return place


def format_base_xml(results: Union[napi.ReverseResults, napi.SearchResults],
                    options: Mapping[str, Any],
                    simple: bool, xml_root_tag: str,
                    xml_extra_info: Mapping[str, str]) -> str:
    """ Format the result into an XML response. With 'simple' exactly one
        result will be output, otherwise a list.
    """
    root = ET.Element(xml_root_tag)
    root.set('timestamp', dt.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +00:00'))
    root.set('attribution', cl.OSM_ATTRIBUTION)
    for k, v in xml_extra_info.items():
        root.set(k, v)

    if simple and not results:
        ET.SubElement(root, 'error').text = 'Unable to geocode'

    for result in results:
        place = _create_base_entry(result, root, simple)

        if not simple and options.get('icon_base_url', None):
            icon = cl.ICONS.get(result.category)
            if icon:
                place.set('icon', icon)

        if options.get('addressdetails', False) and result.address_rows:
            _write_xml_address(ET.SubElement(root, 'addressparts') if simple else place,
                               result.address_rows, result.country_code)

        if options.get('extratags', False):
            eroot = ET.SubElement(root if simple else place, 'extratags')
            if result.extratags:
                for k, v in result.extratags.items():
                    ET.SubElement(eroot, 'tag', attrib={'key': k, 'value': v})

        if options.get('namedetails', False):
            eroot = ET.SubElement(root if simple else place, 'namedetails')
            if result.names:
                for k,v in result.names.items():
                    ET.SubElement(eroot, 'name', attrib={'desc': k}).text = v

    return '<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(root, encoding='unicode')
