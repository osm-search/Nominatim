# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the streaming JSON writer.
"""
import json

import pytest

from nominatim.utils.json_writer import JsonWriter

@pytest.mark.parametrize("inval,outstr", [(None, 'null'),
                                          (True, 'true'), (False, 'false'),
                                          (23, '23'), (0, '0'), (-1.3, '-1.3'),
                                          ('g\nä', '"g\\nä"'), ('"', '"\\\""'),
                                          ({}, '{}'), ([], '[]')])
def test_simple_value(inval, outstr):
    writer = JsonWriter()
    writer.value(inval)

    assert writer() == outstr
    json.loads(writer())


def test_empty_array():
    writer = JsonWriter().start_array().end_array()

    assert writer() == '[]'
    json.loads(writer())


def test_array_with_single_value():
    writer = JsonWriter().start_array().value(None).end_array()

    assert writer() == '[null]'
    json.loads(writer())


@pytest.mark.parametrize("invals,outstr", [((1, ), '[1]'),
                                           (('a', 'b'), '["a","b"]')])
def test_array_with_data(invals, outstr):
    writer = JsonWriter()

    writer.start_array()
    for ival in invals:
        writer.value(ival).next()
    writer.end_array()

    assert writer() == outstr
    json.loads(writer())


def test_empty_object():
    writer = JsonWriter().start_object().end_object()

    assert writer() == '{}'
    json.loads(writer())


def test_object_single_entry():
    writer = JsonWriter()\
                .start_object()\
                    .key('something')\
                    .value(5)\
                .end_object()

    assert writer() == '{"something":5}'
    json.loads(writer())

def test_object_many_values():
    writer = JsonWriter()\
                .start_object()\
                    .keyval('foo', None)\
                    .keyval('bar', {})\
                    .keyval('baz', 'b\taz')\
                .end_object()

    assert writer() == '{"foo":null,"bar":{},"baz":"b\\taz"}'
    json.loads(writer())

def test_object_many_values_without_none():
    writer = JsonWriter()\
                .start_object()\
                    .keyval_not_none('foo', 0)\
                    .keyval_not_none('bar', None)\
                    .keyval_not_none('baz', '')\
                    .keyval_not_none('eve', False,
                                     transform = lambda v: 'yes' if v else 'no')\
                .end_object()

    assert writer() == '{"foo":0,"baz":"","eve":"no"}'
    json.loads(writer())


def test_raw_output():
    writer = JsonWriter()\
                .start_array()\
                    .raw('{ "nicely": "formatted here" }').next()\
                    .value(1)\
                .end_array()

    assert writer() == '[{ "nicely": "formatted here" },1]'
