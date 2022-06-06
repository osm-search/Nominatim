# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for centroid computation.
"""
import pytest

from nominatim.utils.centroid import PointsCentroid

def test_empty_set():
    c = PointsCentroid()

    with pytest.raises(ValueError, match='No points'):
        c.centroid()


@pytest.mark.parametrize("centroid", [(0,0), (-1, 3), [0.0000032, 88.4938]])
def test_one_point_centroid(centroid):
    c = PointsCentroid()

    c += centroid

    assert len(c.centroid()) == 2
    assert c.centroid() == (pytest.approx(centroid[0]), pytest.approx(centroid[1]))


def test_multipoint_centroid():
    c = PointsCentroid()

    c += (20.0, -10.0)
    assert c.centroid() == (pytest.approx(20.0), pytest.approx(-10.0))
    c += (20.2, -9.0)
    assert c.centroid() == (pytest.approx(20.1), pytest.approx(-9.5))
    c += (20.2, -9.0)
    assert c.centroid() == (pytest.approx(20.13333), pytest.approx(-9.333333))


def test_manypoint_centroid():
    c = PointsCentroid()

    for _ in range(10000):
        c += (4.564732, -0.000034)

    assert c.centroid() == (pytest.approx(4.564732), pytest.approx(-0.000034))


@pytest.mark.parametrize("param", ["aa", None, 5, [1, 2, 3], (3, None), ("a", 3.9)])
def test_add_non_tuple(param):
    c = PointsCentroid()

    with pytest.raises(ValueError, match='2-element tuples'):
        c += param
