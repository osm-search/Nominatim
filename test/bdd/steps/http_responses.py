# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Classes wrapping HTTP responses from the Nominatim API.
"""
import re
import json
import xml.etree.ElementTree as ET

from check_functions import Almost, OsmType, Field, check_for_attributes


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
        self.result = json.JSONDecoder().decode(code)
        if isinstance(self.result, dict):
            if 'error' in self.result:
                self.result = []
            else:
                self.result = [self.result]


    def _parse_geojson(self):
        self._parse_json()
        if self.result:
            geojson = self.result[0]
            # check for valid geojson
            check_for_attributes(geojson, 'type,features')
            assert geojson['type'] == 'FeatureCollection'
            assert isinstance(geojson['features'], list)

            self.result = []
            for result in geojson['features']:
                check_for_attributes(result, 'type,properties,geometry')
                assert result['type'] == 'Feature'
                new = result['properties']
                check_for_attributes(new, 'geojson', 'absent')
                new['geojson'] = result['geometry']
                if 'bbox' in result:
                    check_for_attributes(new, 'boundingbox', 'absent')
                    # bbox is  minlon, minlat, maxlon, maxlat
                    # boundingbox is minlat, maxlat, minlon, maxlon
                    new['boundingbox'] = [result['bbox'][1],
                                          result['bbox'][3],
                                          result['bbox'][0],
                                          result['bbox'][2]]
                for k, v in geojson.items():
                    if k not in ('type', 'features'):
                        check_for_attributes(new, '__' + k, 'absent')
                        new['__' + k] = v
                self.result.append(new)


    def _parse_geocodejson(self):
        self._parse_geojson()
        if self.result:
            for r in self.result:
                assert set(r.keys()) == {'geocoding', 'geojson', '__geocoding'}, \
                       f"Unexpected keys in result: {r.keys()}"
                check_for_attributes(r['geocoding'], 'geojson', 'absent')
                r |= r.pop('geocoding')


    def assert_subfield(self, idx, path, value):
        assert path

        field = self.result[idx]
        for p in path:
            assert isinstance(field, dict)
            assert p in field
            field = field[p]

        if isinstance(value, float):
            assert Almost(value) == float(field)
        elif value.startswith("^"):
            assert re.fullmatch(value, field)
        elif isinstance(field, dict):
            assert field, eval('{' + value + '}')
        else:
            assert str(field) == str(value)


    def assert_address_field(self, idx, field, value):
        """ Check that result rows`idx` has a field `field` with value `value`
            in its address. If idx is None, then all results are checked.
        """
        if idx is None:
            todo = range(len(self.result))
        else:
            todo = [int(idx)]

        for idx in todo:
            self.check_row(idx, 'address' in self.result[idx], "No field 'address'")

            address = self.result[idx]['address']
            self.check_row_field(idx, field, value, base=address)


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
                    self.check_row_field(i, 'osm_type', OsmType(value[0]))
                    self.check_row_field(i, 'osm_id', Field(value[1:]))
                elif name == 'centroid':
                    if ' ' in value:
                        lon, lat = value.split(' ')
                    elif context is not None:
                        lon, lat = context.osm.grid_node(int(value))
                    else:
                        raise RuntimeError("Context needed when using grid coordinates")
                    self.check_row_field(i, 'lat', Field(float(lat)))
                    self.check_row_field(i, 'lon', Field(float(lon)))
                elif '+' in name:
                    self.assert_subfield(i, name.split('+'), value)
                else:
                    self.check_row_field(i, name, Field(value))


    def property_list(self, prop):
        return [x[prop] for x in self.result]


    def check_row(self, idx, check, msg):
        """ Assert for the condition 'check' and print 'msg' on fail together
            with the contents of the failing result.
        """
        class _RowError:
            def __init__(self, row):
                self.row = row

            def __str__(self):
                return f"{msg}. Full row {idx}:\n" \
                       + json.dumps(self.row, indent=4, ensure_ascii=False)

        assert check, _RowError(self.result[idx])


    def check_row_field(self, idx, field, expected, base=None):
        """ Check field 'field' of result 'idx' for the expected value
            and print a meaningful error if the condition fails.
            When 'base' is set to a dictionary, then the field is checked
            in that base. The error message will still report the contents
            of the full result.
        """
        if base is None:
            base = self.result[idx]

        self.check_row(idx, field in base, f"No field '{field}'")
        value = base[field]

        self.check_row(idx, expected == value,
                       f"\nBad value for field '{field}'. Expected: {expected}, got: {value}")



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
