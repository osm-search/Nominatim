# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Classes wrapping HTTP responses from the Nominatim API.
"""
from collections import OrderedDict
import re
import json
import xml.etree.ElementTree as ET

from check_functions import Almost

OSM_TYPE = {'N' : 'node', 'W' : 'way', 'R' : 'relation',
            'n' : 'node', 'w' : 'way', 'r' : 'relation',
            'node' : 'n', 'way' : 'w', 'relation' : 'r'}

def _geojson_result_to_json_result(geojson_result):
    result = geojson_result['properties']
    result['geojson'] = geojson_result['geometry']
    if 'bbox' in geojson_result:
        # bbox is  minlon, minlat, maxlon, maxlat
        # boundingbox is minlat, maxlat, minlon, maxlon
        result['boundingbox'] = [geojson_result['bbox'][1],
                                 geojson_result['bbox'][3],
                                 geojson_result['bbox'][0],
                                 geojson_result['bbox'][2]]
    return result

class BadRowValueAssert:
    """ Lazily formatted message for failures to find a field content.
    """

    def __init__(self, response, idx, field, value):
        self.idx = idx
        self.field = field
        self.value = value
        self.row = response.result[idx]

    def __str__(self):
        return "\nBad value for row {} field '{}'. Expected: {}, got: {}.\nFull row: {}"""\
                   .format(self.idx, self.field, self.value,
                           self.row[self.field], json.dumps(self.row, indent=4))


class GenericResponse:
    """ Common base class for all API responses.
    """
    def __init__(self, page, fmt, errorcode=200):
        fmt = fmt.strip()
        if fmt == 'jsonv2':
            fmt = 'json'

        self.page = page
        self.format = fmt
        self.errorcode = errorcode
        self.result = []
        self.header = dict()

        if errorcode == 200 and fmt != 'debug':
            getattr(self, '_parse_' + fmt)()

    def _parse_json(self):
        m = re.fullmatch(r'([\w$][^(]*)\((.*)\)', self.page)
        if m is None:
            code = self.page
        else:
            code = m.group(2)
            self.header['json_func'] = m.group(1)
        self.result = json.JSONDecoder(object_pairs_hook=OrderedDict).decode(code)
        if isinstance(self.result, OrderedDict):
            if 'error' in self.result:
                self.result = []
            else:
                self.result = [self.result]

    def _parse_geojson(self):
        self._parse_json()
        if self.result:
            self.result = list(map(_geojson_result_to_json_result, self.result[0]['features']))

    def _parse_geocodejson(self):
        self._parse_geojson()
        if self.result is not None:
            self.result = [r['geocoding'] for r in self.result]

    def assert_field(self, idx, field, value):
        """ Check that result row `idx` has a field `field` with value `value`.
            Float numbers are matched approximately. When the expected value
            starts with a carat, regular expression matching is used.
        """
        assert field in self.result[idx], \
               "Result row {} has no field '{}'.\nFull row: {}"\
                   .format(idx, field, json.dumps(self.result[idx], indent=4))

        if isinstance(value, float):
            assert Almost(value) == float(self.result[idx][field]), \
                   BadRowValueAssert(self, idx, field, value)
        elif value.startswith("^"):
            assert re.fullmatch(value, self.result[idx][field]), \
                   BadRowValueAssert(self, idx, field, value)
        elif isinstance(self.result[idx][field], OrderedDict):
            assert self.result[idx][field] == eval('{' + value + '}'), \
                   BadRowValueAssert(self, idx, field, value)
        else:
            assert str(self.result[idx][field]) == str(value), \
                   BadRowValueAssert(self, idx, field, value)

    def assert_address_field(self, idx, field, value):
        """ Check that result rows`idx` has a field `field` with value `value`
            in its address. If idx is None, then all results are checked.
        """
        if idx is None:
            todo = range(len(self.result))
        else:
            todo = [int(idx)]

        for idx in todo:
            assert 'address' in self.result[idx], \
                   "Result row {} has no field 'address'.\nFull row: {}"\
                       .format(idx, json.dumps(self.result[idx], indent=4))

            address = self.result[idx]['address']
            assert field in address, \
                   "Result row {} has no field '{}' in address.\nFull address: {}"\
                       .format(idx, field, json.dumps(address, indent=4))

            assert address[field] == value, \
                   "\nBad value for row {} field '{}' in address. Expected: {}, got: {}.\nFull address: {}"""\
                       .format(idx, field, value, address[field], json.dumps(address, indent=4))

    def match_row(self, row, context=None):
        """ Match the result fields against the given behave table row.
        """
        if 'ID' in row.headings:
            todo = [int(row['ID'])]
        else:
            todo = range(len(self.result))

        for i in todo:
            for name, value in zip(row.headings, row.cells):
                if name == 'ID':
                    pass
                elif name == 'osm':
                    assert 'osm_type' in self.result[i], \
                           "Result row {} has no field 'osm_type'.\nFull row: {}"\
                               .format(i, json.dumps(self.result[i], indent=4))
                    assert self.result[i]['osm_type'] in (OSM_TYPE[value[0]], value[0]), \
                           BadRowValueAssert(self, i, 'osm_type', value)
                    self.assert_field(i, 'osm_id', value[1:])
                elif name == 'osm_type':
                    assert self.result[i]['osm_type'] in (OSM_TYPE[value[0]], value[0]), \
                           BadRowValueAssert(self, i, 'osm_type', value)
                elif name == 'centroid':
                    if ' ' in value:
                        lon, lat = value.split(' ')
                    elif context is not None:
                        lon, lat = context.osm.grid_node(int(value))
                    else:
                        raise RuntimeError("Context needed when using grid coordinates")
                    self.assert_field(i, 'lat', float(lat))
                    self.assert_field(i, 'lon', float(lon))
                else:
                    self.assert_field(i, name, value)

    def property_list(self, prop):
        return [x[prop] for x in self.result]


class SearchResponse(GenericResponse):
    """ Specialised class for search and lookup responses.
        Transforms the xml response in a format similar to json.
    """

    def _parse_xml(self):
        xml_tree = ET.fromstring(self.page)

        self.header = dict(xml_tree.attrib)

        for child in xml_tree:
            assert child.tag == "place"
            self.result.append(dict(child.attrib))

            address = {}
            for sub in child:
                if sub.tag == 'extratags':
                    self.result[-1]['extratags'] = {}
                    for tag in sub:
                        self.result[-1]['extratags'][tag.attrib['key']] = tag.attrib['value']
                elif sub.tag == 'namedetails':
                    self.result[-1]['namedetails'] = {}
                    for tag in sub:
                        self.result[-1]['namedetails'][tag.attrib['desc']] = tag.text
                elif sub.tag == 'geokml':
                    self.result[-1][sub.tag] = True
                else:
                    address[sub.tag] = sub.text

            if address:
                self.result[-1]['address'] = address


class ReverseResponse(GenericResponse):
    """ Specialised class for reverse responses.
        Transforms the xml response in a format similar to json.
    """

    def _parse_xml(self):
        xml_tree = ET.fromstring(self.page)

        self.header = dict(xml_tree.attrib)
        self.result = []

        for child in xml_tree:
            if child.tag == 'result':
                assert not self.result, "More than one result in reverse result"
                self.result.append(dict(child.attrib))
            elif child.tag == 'addressparts':
                address = {}
                for sub in child:
                    address[sub.tag] = sub.text
                self.result[0]['address'] = address
            elif child.tag == 'extratags':
                self.result[0]['extratags'] = {}
                for tag in child:
                    self.result[0]['extratags'][tag.attrib['key']] = tag.attrib['value']
            elif child.tag == 'namedetails':
                self.result[0]['namedetails'] = {}
                for tag in child:
                    self.result[0]['namedetails'][tag.attrib['desc']] = tag.text
            elif child.tag == 'geokml':
                self.result[0][child.tag] = True
            else:
                assert child.tag == 'error', \
                       "Unknown XML tag {} on page: {}".format(child.tag, self.page)


class StatusResponse(GenericResponse):
    """ Specialised class for status responses.
        Can also parse text responses.
    """

    def _parse_text(self):
        pass
