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
from nominatim.data.place_info import PlaceInfo
from nominatim.data import country_info

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

        _, address = PlaceSanitizer([sanitizer_args], def_config).process_names(PlaceInfo(pi))

        return sorted([(p.kind, p.name) for p in address])

    return _run


@pytest.mark.parametrize("country", (None, 'ae'))
def test_postcode_no_country(sanitize, country):
    assert sanitize(country=country, postcode='23231') == [('unofficial_postcode', '23231')]


@pytest.mark.parametrize("country", (None, 'ae'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_no_country_drop(sanitize, country):
    assert sanitize(country=country, postcode='23231') == []


@pytest.mark.parametrize("postcode", ('12345', '  12345  ', 'de 12345',
                                      'DE12345', 'DE 12345', 'DE-12345'))
def test_postcode_pass_good_format(sanitize, postcode):
    assert sanitize(country='de', postcode=postcode) == [('postcode', '12345')]


@pytest.mark.parametrize("postcode", ('123456', '', '   ', '.....',
                                      'DE  12345', 'DEF12345', 'CH 12345'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_drop_bad_format(sanitize, postcode):
    assert sanitize(country='de', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('1234', '9435', '99000'))
def test_postcode_cyprus_pass(sanitize, postcode):
    assert sanitize(country='cy', postcode=postcode) == [('postcode', postcode)]


@pytest.mark.parametrize("postcode", ('91234', '99a45', '567'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_cyprus_fail(sanitize, postcode):
    assert sanitize(country='cy', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('123456', 'A33F2G7'))
def test_postcode_kazakhstan_pass(sanitize, postcode):
    assert sanitize(country='kz', postcode=postcode) == [('postcode', postcode)]


@pytest.mark.parametrize("postcode", ('V34T6Y923456', '99345'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_kazakhstan_fail(sanitize, postcode):
    assert sanitize(country='kz', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('675 34', '67534', 'SE-675 34', 'SE67534'))
def test_postcode_sweden_pass(sanitize, postcode):
    assert sanitize(country='se', postcode=postcode) == [('postcode', '675 34')]


@pytest.mark.parametrize("postcode", ('67 345', '671123'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_sweden_fail(sanitize, postcode):
    assert sanitize(country='se', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('AB1', '123-456-7890', '1 as 44'))
@pytest.mark.sanitizer_params(default_pattern='[A-Z0-9- ]{3,12}')
def test_postcode_default_pattern_pass(sanitize, postcode):
    assert sanitize(country='an', postcode=postcode) == [('postcode', postcode.upper())]


@pytest.mark.parametrize("postcode", ('C', '12', 'ABC123DEF 456', '1234,5678', '11223;11224'))
@pytest.mark.sanitizer_params(convert_to_address=False, default_pattern='[A-Z0-9- ]{3,12}')
def test_postcode_default_pattern_fail(sanitize, postcode):
    assert sanitize(country='an', postcode=postcode) == []

