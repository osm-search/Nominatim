# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the sanitizer that normalizes housenumbers.
"""
import pytest

from nominatim.tokenizer.place_sanitizer import PlaceSanitizer
from nominatim.indexer.place_info import PlaceInfo

@pytest.fixture
def sanitize(request):
    sanitizer_args = {'step': 'clean-housenumbers'}
    for mark in request.node.iter_markers(name="sanitizer_params"):
        sanitizer_args.update({k.replace('_', '-') : v for k,v in mark.kwargs.items()})

    def _run(**kwargs):
        place = PlaceInfo({'address': kwargs})
        _, address = PlaceSanitizer([sanitizer_args]).process_names(place)

        return sorted([(p.kind, p.name) for p in address])

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
