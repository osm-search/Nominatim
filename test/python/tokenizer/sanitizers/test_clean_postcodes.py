# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the sanitizer that normalizes postcodes.
"""
import pytest

from nominatim.tokenizer.place_sanitizer import PlaceSanitizer
from nominatim.indexer.place_info import PlaceInfo
from nominatim.tools import country_info

@pytest.fixture
def sanitize(def_config, request):
    country_info.setup_country_config(def_config)
    sanitizer_args = {'step': 'clean-postcodes'}
    for mark in request.node.iter_markers(name="sanitizer_params"):
        sanitizer_args.update({k.replace('_', '-') : v for k,v in mark.kwargs.items()})

    def _run(country=None, **kwargs):
        pi = {'address': kwargs}
        if country is not None:
            pi['country_code'] = country

        _, address = PlaceSanitizer([sanitizer_args]).process_names(PlaceInfo(pi))

        return sorted([(p.kind, p.name) for p in address])

    return _run


@pytest.mark.parametrize("country", (None, 'ae'))
def test_postcode_no_country(sanitize, country):
    assert sanitize(country=country, postcode='23231') == [('unofficial_postcode', '23231')]


@pytest.mark.parametrize("country", (None, 'ae'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_no_country_drop(sanitize, country):
    assert sanitize(country=country, postcode='23231') == []


@pytest.mark.parametrize("postcode", ('12345', '  34009  '))
def test_postcode_pass_good_format(sanitize, postcode):
    assert sanitize(country='de', postcode=postcode) == [('postcode', postcode.strip())]


@pytest.mark.parametrize("postcode", ('123456', '', '   ', '.....'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_drop_bad_format(sanitize, postcode):
    assert sanitize(country='de', postcode=postcode) == []