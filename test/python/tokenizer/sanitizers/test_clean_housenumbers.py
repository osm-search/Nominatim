# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the sanitizer that normalizes housenumbers.
"""
import pytest

from nominatim_db.tokenizer.place_sanitizer import PlaceSanitizer
from nominatim_db.data.place_info import PlaceInfo


@pytest.fixture
def sanitize(request, def_config):
    sanitizer_args = {'step': 'clean-housenumbers'}
    for mark in request.node.iter_markers(name="sanitizer_params"):
        sanitizer_args.update({k.replace('_', '-'): v for k, v in mark.kwargs.items()})

    def _run(**kwargs):
        place = PlaceInfo({'address': kwargs})
        PlaceSanitizer([sanitizer_args], def_config).process_names(place)

        return sorted([(p.kind, p.name) for p in place.searchable_address])

    return _run


def test_simple_number(sanitize):
    assert sanitize(housenumber='34') == [('housenumber', '34')]


@pytest.mark.parametrize('number', ['1;2;3', '1,2,3', '1; 3 ,2',
                                    '2,,3,1', '1;2;3;;', ';3;2;1'])
def test_housenumber_lists(sanitize, number):
    assert sanitize(housenumber=number) == \
           [('housenumber', '1'), ('housenumber', '2'), ('housenumber', '3')]


@pytest.mark.sanitizer_params(filter_kind=('number', 'streetnumber'))
def test_filter_kind(sanitize):
    assert sanitize(housenumber='34', number='4', badnumber='65') == \
            [('badnumber', '65'), ('housenumber', '34'), ('housenumber', '4')]


@pytest.mark.parametrize('number', ('6523', 'n/a', '4'))
def test_convert_to_name_converted(def_config, number):
    sanitizer_args = {'step': 'clean-housenumbers',
                      'convert-to-name': (r'\d+', 'n/a')}

    place = PlaceInfo({'address': {'housenumber': number}})
    PlaceSanitizer([sanitizer_args], def_config).process_names(place)

    assert ('housenumber', number) in set((p.kind, p.name) for p in place.searchable_names)
    assert 'housenumber' not in set(p.kind for p in place.searchable_address)


@pytest.mark.parametrize('number', ('a54', 'n.a', 'bow'))
def test_convert_to_name_unconverted(def_config, number):
    sanitizer_args = {'step': 'clean-housenumbers',
                      'convert-to-name': (r'\d+', 'n/a')}

    place = PlaceInfo({'address': {'housenumber': number}})
    PlaceSanitizer([sanitizer_args], def_config).process_names(place)

    assert 'housenumber' not in set(p.kind for p in place.searchable_names)
    assert ('housenumber', number) in set((p.kind, p.name) for p in place.searchable_address)


@pytest.mark.parametrize('hnr,itype,out', [
                            ('1-5', 'all', (1, 2, 3, 4, 5)),
                            ('1-5', 'odd', (1, 3, 5)),
                            ('1-5', 'even', (2, 4)),
                            ('6-9', '1', (6, 7, 8, 9)),
                            ('6-9', '2', (6, 8)),
                            ('6-9', '3', (6, 9)),
                            ('6-9', '5', (6,)),
                            ('6-9', 'odd', (7, 9)),
                            ('6-9', 'even', (6, 8)),
                            ('6-22', 'even', (6, 8, 10, 12, 14, 16, 18, 20, 22))
                            ])
def test_convert_interpolations(sanitize, hnr, itype, out):
    assert set(sanitize(housenumber=hnr, interpolation=itype)) \
            == {('housenumber', str(i)) for i in out}


@pytest.mark.parametrize('hnr', ('23', '23-', '3z-f', '1-10', '5-1', '1-4-5'))
def test_ignore_interpolation_with_bad_housenumber(sanitize, hnr):
    assert sanitize(housenumber=hnr, interpolation='all') == [('housenumber', hnr)]
