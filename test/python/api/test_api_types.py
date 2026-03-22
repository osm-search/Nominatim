# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for loading of parameter dataclasses.
"""
import pytest

from nominatim_api.errors import UsageError
import nominatim_api.types as typ


def test_no_params_defaults():
    params = typ.LookupDetails.from_kwargs({})

    assert not params.parented_places
    assert params.geometry_simplification == 0.0


@pytest.mark.parametrize('k,v', [('geometry_output',  'a'),
                                 ('linked_places', 0),
                                 ('geometry_simplification', 'NaN')])
def test_bad_format_reverse(k, v):
    with pytest.raises(UsageError):
        typ.ReverseDetails.from_kwargs({k: v})


@pytest.mark.parametrize('rin,rout', [(-23, 0), (0, 0), (1, 1),
                                      (15, 15), (30, 30), (31, 30)])
def test_rank_params(rin, rout):
    params = typ.ReverseDetails.from_kwargs({'max_rank': rin})

    assert params.max_rank == rout


class TestFormatExcluded:

    @pytest.mark.parametrize('inp', ['', None])
    def test_empty_value(self, inp):
        assert typ.format_excluded(inp) == []

    @pytest.mark.parametrize('inp,expected', [
        ('123', [typ.PlaceID(123)]),
        ('123,456', [typ.PlaceID(123), typ.PlaceID(456)]),
        ('N100', [typ.OsmID('N', 100)]),
        ('W101', [typ.OsmID('W', 101)]),
        ('R102', [typ.OsmID('R', 102)]),
        ('N100,W101,R102', [typ.OsmID('N', 100), typ.OsmID('W', 101), typ.OsmID('R', 102)]),
        ('n100', [typ.OsmID('N', 100)]),
        ('123,N456,W789', [typ.PlaceID(123), typ.OsmID('N', 456), typ.OsmID('W', 789)]),
        (' 123 , N456 ', [typ.PlaceID(123), typ.OsmID('N', 456)]),
        ('123,,456', [typ.PlaceID(123), typ.PlaceID(456)]),
        ('0', []),
        ('N0', []),
        ('000123', [typ.PlaceID(123)])
    ])
    def test_valid_exclude_ids(self, inp, expected):
        assert typ.format_excluded(inp) == expected

    @pytest.mark.parametrize('inp, bad_id', [
        ('abc', 'abc'),
        ('X999', 'X999'),
        ('-540', '-540'),
        ('N-100', 'N-100'),
        ('123,abc,456', 'abc'),
        ('N:100', 'N:100')
        ])
    def test_invalid_exclude_ids(self, inp, bad_id):
        with pytest.raises(UsageError, match=f"Invalid exclude ID: {bad_id}"):
            typ.format_excluded(inp)

    @pytest.mark.parametrize('inp', [[12.5], [{'key': 'value'}], [[123, 456]]])
    def test_invalid_list_element_type(self, inp):
        with pytest.raises(UsageError, match="Parameter 'excluded' contains invalid types."):
            typ.format_excluded(inp)
