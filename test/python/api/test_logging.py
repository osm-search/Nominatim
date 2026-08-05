# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the HTML debug logger.

The debug output is served as ``text/html``, so values that come from user input
or database should be HTML-escaped, while the markup the logger emits itself
should remain intact.
"""
from types import SimpleNamespace

import nominatim_api.logging as loglib

# A value containing HTML-significant characters (&, <, >).
HTML_VALUE = 'H-T-M-L & <b>BoldValue</b>'


def _fake_result(**kwargs):
    """ Build a minimal object with the attributes result_dump() reads. """
    defaults = dict(source_table=SimpleNamespace(name='PLACEX'),
                    names={'name': 'a place'},
                    housenumber=None,
                    category=('place', 'hamlet'),
                    rank_address=16,
                    osm_object=('N', 123),
                    country_code='ad',
                    importance=0.5)
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_result_dump_escapes_html_in_values():
    logger = loglib.HTMLLogger()
    res = _fake_result(names={'name': HTML_VALUE}, country_code='a<b')
    logger.result_dump('Results', iter([(0.0, res)]))
    out = logger.get_buffer()

    assert '<b>BoldValue</b>' not in out
    assert '&lt;b&gt;BoldValue&lt;/b&gt;' in out
    assert 'a&lt;b' in out


def test_result_dump_preserves_own_markup():
    logger = loglib.HTMLLogger()
    logger.result_dump('Results', iter([(0.0, _fake_result())]))
    out = logger.get_buffer()

    # The OSM link the logger builds itself must not be escaped away.
    assert '<a href="https://www.openstreetmap.org/node/123">N123</a>' in out
