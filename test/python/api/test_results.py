# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for result datatype helper functions.
"""
import struct
from binascii import hexlify

import pytest
import pytest_asyncio
import sqlalchemy as sa


from nominatim.api import SourceTable, DetailedResult, Point
import nominatim.api.results as nresults

def mkpoint(x, y):
    return hexlify(struct.pack("=biidd", 1, 0x20000001, 4326, x, y)).decode('utf-8')

class FakeRow:
    def __init__(self, **kwargs):
        if 'parent_place_id' not in kwargs:
            kwargs['parent_place_id'] = None
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._mapping = kwargs


def test_minimal_detailed_result():
    res = DetailedResult(SourceTable.PLACEX,
                         ('amenity', 'post_box'),
                         Point(23.1, 0.5))

    assert res.lon == 23.1
    assert res.lat == 0.5
    assert res.calculated_importance() == pytest.approx(0.0000001)

def test_detailed_result_custom_importance():
    res = DetailedResult(SourceTable.PLACEX,
                         ('amenity', 'post_box'),
                         Point(23.1, 0.5),
                         importance=0.4563)

    assert res.calculated_importance() == 0.4563


@pytest.mark.parametrize('func', (nresults.create_from_placex_row,
                                  nresults.create_from_osmline_row,
                                  nresults.create_from_tiger_row,
                                  nresults.create_from_postcode_row))
def test_create_row_none(func):
    assert func(None, DetailedResult) is None


@pytest.mark.parametrize('func', (nresults.create_from_osmline_row,
                                  nresults.create_from_tiger_row))
def test_create_row_with_housenumber(func):
    row = FakeRow(place_id=2345, osm_type='W', osm_id=111, housenumber=4,
                  address=None, postcode='99900', country_code='xd',
                  centroid=mkpoint(0, 0))

    res = func(row, DetailedResult)

    assert res.housenumber == '4'
    assert res.extratags is None
    assert res.category == ('place', 'house')


@pytest.mark.parametrize('func', (nresults.create_from_osmline_row,
                                  nresults.create_from_tiger_row))
def test_create_row_without_housenumber(func):
    row = FakeRow(place_id=2345, osm_type='W', osm_id=111,
                  startnumber=1, endnumber=11, step=2,
                  address=None, postcode='99900', country_code='xd',
                  centroid=mkpoint(0, 0))

    res = func(row, DetailedResult)

    assert res.housenumber is None
    assert res.extratags == {'startnumber': '1', 'endnumber': '11', 'step': '2'}
    assert res.category == ('place', 'houses')
