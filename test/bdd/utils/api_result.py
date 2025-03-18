# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Wrapper for results from the API
"""
import json
import xml.etree.ElementTree as ET


class APIResult:

    def __init__(self, fmt, endpoint, body):
        getattr(self, '_parse_' + fmt)(endpoint, body)

    def is_simple(self):
        return not isinstance(self.result, list)

    def __len__(self):
        return 1 if self.is_simple() else len(self.result)

    def __str__(self):
        return json.dumps({'meta': self.meta, 'result': self.result}, indent=2)

    def _parse_json(self, _, body):
        self.meta = {}
        self.result = json.loads(body)

    def _parse_xml(self, endpoint, body):
        xml_tree = ET.fromstring(body)

        self.meta = dict(xml_tree.attrib)

        if xml_tree.tag == 'reversegeocode':
            self._parse_xml_simple(xml_tree)
        elif xml_tree.tag == 'searchresults':
            self._parse_xml_multi(xml_tree)
        elif xml_tree.tag == 'error':
            self.result = {'error': {sub.tag: sub.text for sub in xml_tree}}

    def _parse_xml_simple(self, xml):
        self.result = {}

        for child in xml:
            if child.tag == 'result':
                assert not self.result, "More than one result in reverse result"
                self.result.update(child.attrib)
                assert 'display_name' not in self.result
                self.result['display_name'] = child.text
            elif child.tag == 'addressparts':
                assert 'address' not in self.result
                self.result['address'] = {sub.tag: sub.text for sub in child}
            elif child.tag == 'extratags':
                assert 'extratags' not in self.result
                self.result['extratags'] = {tag.attrib['key']: tag.attrib['value'] for tag in child}
            elif child.tag == 'namedetails':
                assert 'namedetails' not in self.result
                self.result['namedetails'] = {tag.attrib['desc']: tag.text for tag in child}
            elif child.tag == 'geokml':
                assert 'geokml' not in self.result
                self.result['geokml'] = ET.tostring(child, encoding='unicode')
            elif child.tag == 'error':
                assert not self.result
                self.result['error'] = child.text
            else:
                assert False, f"Unknown XML tag {child.tag} on page: {self.page}"

    def _parse_xml_multi(self, xml):
        self.result = []

        for child in xml:
            assert child.tag == "place"
            res = dict(child.attrib)

            address = {}
            for sub in child:
                if sub.tag == 'extratags':
                    assert 'extratags' not in res
                    res['extratags'] = {tag.attrib['key']: tag.attrib['value'] for tag in sub}
                elif sub.tag == 'namedetails':
                    assert 'namedetails' not in res
                    res['namedetails'] = {tag.attrib['desc']: tag.text for tag in sub}
                elif sub.tag == 'geokml':
                    res['geokml'] = ET.tostring(sub, encoding='utf-8')
                else:
                    address[sub.tag] = sub.text

            if address:
                res['address'] = address

            self.result.append(res)

    def _parse_geojson(self, _, body):
        geojson = json.loads(body)

        assert geojson.get('type') == 'FeatureCollection'
        assert isinstance(geojson.get('features'), list)

        self.meta = {k: v for k, v in geojson.items() if k not in ('type', 'features')}
        self.result = []

        for obj in geojson['features']:
            assert isinstance(obj, dict)
            assert obj.get('type') == 'Feature'

            assert isinstance(obj.get('properties'), dict)
            result = obj['properties']
            assert 'geojson' not in result
            result['geojson'] = obj['geometry']
            if 'bbox' in obj:
                assert 'boundingbox' not in result
                # bbox is  minlon, minlat, maxlon, maxlat
                # boundingbox is minlat, maxlat, minlon, maxlon
                result['boundingbox'] = [obj['bbox'][1], obj['bbox'][3],
                                         obj['bbox'][0], obj['bbox'][2]]
            self.result.append(result)

    def _parse_geocodejson(self, endpoint, body):
        self._parse_geojson(endpoint, body)

        assert set(self.meta.keys()) == {'geocoding'}
        assert isinstance(self.meta['geocoding'], dict)
        self.meta = self.meta['geocoding']

        for r in self.result:
            assert set(r.keys()) == {'geocoding', 'geojson'}
            inner = r.pop('geocoding')
            assert isinstance(inner, dict)
            assert 'geojson' not in inner
            r.update(inner)
