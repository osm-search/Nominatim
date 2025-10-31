# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the sanitizer that normalizes postcodes.
"""
import pytest

from nominatim_db.tokenizer.place_sanitizer import PlaceSanitizer
from nominatim_db.data.place_info import PlaceInfo
from nominatim_db.data import country_info


@pytest.fixture
def sanitize(def_config, request):
    country_info.setup_country_config(def_config)
    sanitizer_args = {'step': 'clean-postcodes'}
    for mark in request.node.iter_markers(name="sanitizer_params"):
        sanitizer_args.update({k.replace('_', '-'): v for k, v in mark.kwargs.items()})

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


@pytest.mark.parametrize("postcode", ('AD123', '123', 'AD 123', 'AD-123'))
def test_postcode_andorra_pass(sanitize, postcode):
    assert sanitize(country='ad', postcode=postcode) == [('postcode', 'AD123')]


@pytest.mark.parametrize("postcode", ('AD1234', 'AD AD123', 'XX123'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_andorra_fail(sanitize, postcode):
    assert sanitize(country='ad', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('AI-2640', '2640', 'AI 2640'))
def test_postcode_anguilla_pass(sanitize, postcode):
    assert sanitize(country='ai', postcode=postcode) == [('postcode', 'AI-2640')]


@pytest.mark.parametrize("postcode", ('AI-2000', 'AI US-2640', 'AI AI-2640'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_anguilla_fail(sanitize, postcode):
    assert sanitize(country='ai', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('BN1111', 'BN 1111', 'BN BN1111', 'BN BN 1111'))
def test_postcode_brunei_pass(sanitize, postcode):
    assert sanitize(country='bn', postcode=postcode) == [('postcode', 'BN1111')]


@pytest.mark.parametrize("postcode", ('BN-1111', 'BNN1111'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_brunei_fail(sanitize, postcode):
    assert sanitize(country='bn', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('IM1 1AA', 'IM11AA', 'IM IM11AA'))
def test_postcode_isle_of_man_pass(sanitize, postcode):
    assert sanitize(country='im', postcode=postcode) == [('postcode', 'IM1 1AA')]


@pytest.mark.parametrize("postcode", ('IZ1 1AA', 'IM1 AA'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_isle_of_man_fail(sanitize, postcode):
    assert sanitize(country='im', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('JE5 0LA', 'JE50LA', 'JE JE50LA', 'je JE5 0LA'))
def test_postcode_jersey_pass(sanitize, postcode):
    assert sanitize(country='je', postcode=postcode) == [('postcode', 'JE5 0LA')]


@pytest.mark.parametrize("postcode", ('gb JE5 0LA', 'IM50LA', 'IM5 012'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_jersey_fail(sanitize, postcode):
    assert sanitize(country='je', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('KY1-1234', '1-1234', 'KY 1-1234'))
def test_postcode_cayman_islands_pass(sanitize, postcode):
    assert sanitize(country='ky', postcode=postcode) == [('postcode', 'KY1-1234')]


@pytest.mark.parametrize("postcode", ('KY-1234', 'KZ1-1234', 'KY1 1234', 'KY1-123', 'KY KY1-1234'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_cayman_islands_fail(sanitize, postcode):
    assert sanitize(country='ky', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('LC11 222', '11 222', '11222', 'LC 11 222'))
def test_postcode_saint_lucia_pass(sanitize, postcode):
    assert sanitize(country='lc', postcode=postcode) == [('postcode', 'LC11 222')]


@pytest.mark.parametrize("postcode", ('11 2222', 'LC LC11 222'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_saint_lucia_fail(sanitize, postcode):
    assert sanitize(country='lc', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('LV-1111', '1111', 'LV 1111', 'LV1111',))
def test_postcode_latvia_pass(sanitize, postcode):
    assert sanitize(country='lv', postcode=postcode) == [('postcode', 'LV-1111')]


@pytest.mark.parametrize("postcode", ('111', '11111', 'LV LV-1111'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_latvia_fail(sanitize, postcode):
    assert sanitize(country='lv', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('MD-1111', '1111', 'MD 1111', 'MD1111'))
def test_postcode_moldova_pass(sanitize, postcode):
    assert sanitize(country='md', postcode=postcode) == [('postcode', 'MD-1111')]


@pytest.mark.parametrize("postcode", ("MD MD-1111", "MD MD1111", "MD MD 1111"))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_moldova_fail(sanitize, postcode):
    assert sanitize(country='md', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('VLT 1117', 'GDJ 1234', 'BZN 2222'))
def test_postcode_malta_pass(sanitize, postcode):
    assert sanitize(country='mt', postcode=postcode) == [('postcode', postcode)]


@pytest.mark.parametrize("postcode", ('MTF 1111', 'MT MTF 1111', 'MTF1111', 'MT MTF1111'))
def test_postcode_malta_mtarfa_pass(sanitize, postcode):
    assert sanitize(country='mt', postcode=postcode) == [('postcode', 'MTF 1111')]


@pytest.mark.parametrize("postcode", ('1111', 'MTMT 1111'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_malta_fail(sanitize, postcode):
    assert sanitize(country='mt', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('VC1111', '1111', 'VC-1111', 'VC 1111'))
def test_postcode_saint_vincent_pass(sanitize, postcode):
    assert sanitize(country='vc', postcode=postcode) == [('postcode', 'VC1111')]


@pytest.mark.parametrize("postcode", ('VC11', 'VC VC1111'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_saint_vincent_fail(sanitize, postcode):
    assert sanitize(country='vc', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('VG1111', '1111', 'VG 1111', 'VG-1111'))
def test_postcode_virgin_islands_pass(sanitize, postcode):
    assert sanitize(country='vg', postcode=postcode) == [('postcode', 'VG1111')]


@pytest.mark.parametrize("postcode", ('111', '11111', 'VG VG1111'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_virgin_islands_fail(sanitize, postcode):
    assert sanitize(country='vg', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('AB1', '123-456-7890', '1 as 44'))
@pytest.mark.sanitizer_params(default_pattern='[A-Z0-9- ]{3,12}')
def test_postcode_default_pattern_pass(sanitize, postcode):
    assert sanitize(country='an', postcode=postcode) == [('postcode', postcode.upper())]


@pytest.mark.parametrize("postcode", ('C', '12', 'ABC123DEF 456', '1234,5678', '11223;11224'))
@pytest.mark.sanitizer_params(convert_to_address=False, default_pattern='[A-Z0-9- ]{3,12}')
def test_postcode_default_pattern_fail(sanitize, postcode):
    assert sanitize(country='an', postcode=postcode) == []


@pytest.mark.parametrize("postcode", ('00000', '00-000', 'PL-00000', 'PL 00-000'))
@pytest.mark.sanitizer_params(convert_to_address=False)
def test_postcode_zeros(sanitize, postcode):
    assert sanitize(country='pl', postcode=postcode) == []
