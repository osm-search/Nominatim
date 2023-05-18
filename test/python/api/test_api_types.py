# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for loading of parameter dataclasses.
"""
import pytest

from nominatim.errors import UsageError
import nominatim.api.types as typ

def test_no_params_defaults():
    params = typ.LookupDetails.from_kwargs({})

    assert not params.parented_places
    assert params.geometry_simplification == 0.0


@pytest.mark.parametrize('k,v', [('geometry_output',  'a'),
                                 ('linked_places', 0),
                                 ('geometry_simplification', 'NaN')])
def test_bad_format_reverse(k, v):
    with pytest.raises(UsageError):
        params = typ.ReverseDetails.from_kwargs({k: v})


@pytest.mark.parametrize('rin,rout', [(-23, 0), (0, 0), (1, 1),
                                      (15, 15), (30, 30), (31, 30)])
def test_rank_params(rin, rout):
    params = typ.ReverseDetails.from_kwargs({'max_rank': rin})

    assert params.max_rank == rout
