# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions for output of results in XML format.
"""
from typing import Mapping, Any, Optional
import datetime as dt
import xml.etree.ElementTree as ET

import nominatim.api as napi
from nominatim.api.v1.constants import OSM_ATTRIBUTION, OSM_TYPE_NAME, bbox_from_result
from nominatim.api.v1.classtypes import ICONS, get_label_tag

def _write_xml_address(root: ET.Element, address: napi.AddressLines,
                       country_code: Optional[str]) -> None:
    parts = {}
    for line in address:
        if line.isaddress and line.local_name:
            label = get_label_tag(line.category, line.extratags,
                                  line.rank_address, country_code)
            if label not in parts:
                parts[label] = line.local_name

    for k,v in parts.items():
        ET.SubElement(root, k).text = v

    if country_code:
        ET.SubElement(root, 'country_code').text = country_code


def _create_base_entry(result: napi.ReverseResult, #pylint: disable=too-many-branches
                       root: ET.Element, simple: bool,
                       locales: napi.Locales) -> ET.Element:
    if result.address_rows:
        label_parts = result.address_rows.localize(locales)
    else:
        label_parts = []

    place = ET.SubElement(root, 'result' if simple else 'place')
    if result.place_id is not None:
        place.set('place_id', str(result.place_id))
    if result.osm_object:
        osm_type = OSM_TYPE_NAME.get(result.osm_object[0], None)
        if osm_type is not None:
            place.set('osm_type', osm_type)
        place.set('osm_id', str(result.osm_object[1]))
    if result.names and 'ref' in result.names:
        place.set('place_id', result.names['ref'])
    place.set('lat', str(result.centroid.lat))
    place.set('lon', str(result.centroid.lon))

    bbox = bbox_from_result(result)
    place.set('boundingbox', ','.join(map(str, [bbox.minlat, bbox.maxlat,
                                                bbox.minlon, bbox.maxlon])))

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
        place.text = ', '.join(label_parts)
    else:
        place.set('display_name', ', '.join(label_parts))
        place.set('class', result.category[0])
        place.set('type', result.category[1])
        place.set('importance', str(result.calculated_importance()))

    return place


def format_base_xml(results: napi.ReverseResults,
                    options: Mapping[str, Any],
                    simple: bool, xml_root_tag: str,
                    xml_extra_info: Mapping[str, str]) -> str:
    """ Format the result into an XML response. With 'simple' exactly one
        result will be output, otherwise a list.
    """
    locales = options.get('locales', napi.Locales())

    root = ET.Element(xml_root_tag)
    root.set('timestamp', dt.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +00:00'))
    root.set('attribution', OSM_ATTRIBUTION)
    for k, v in xml_extra_info.items():
        root.set(k, v)

    if simple and not results:
        ET.SubElement(root, 'error').text = 'Unable to geocode'

    for result in results:
        place = _create_base_entry(result, root, simple, locales)

        if not simple and options.get('icon_base_url', None):
            icon = ICONS.get(result.category)
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
