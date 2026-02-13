# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.

from nominatim_db.tools.special_phrases.sp_importer import SPImporter


# Testing Database Class Pair Retrival using Conftest.py and placex
def test_get_classtype_pair_data(placex_row, def_config, temp_db_conn):
    for _ in range(100):
        placex_row(cls='highway', typ='motorway')  # edge case 100

    for _ in range(99):
        placex_row(cls='amenity', typ='prison')  # edge case 99

    for _ in range(150):
        placex_row(cls='tourism', typ='hotel')

    importer = SPImporter(config=def_config, conn=temp_db_conn, sp_loader=None)

    result = importer.get_classtype_pairs(min=100)

    assert result == {
        ("highway", "motorway"),
        ("tourism", "hotel")
    }


def test_get_classtype_pair_data_more(placex_row, def_config, temp_db_conn):
    for _ in range(99):
        placex_row(cls='emergency', typ='firehydrant')  # edge case 99, not included

    for _ in range(199):
        placex_row(cls='amenity', typ='prison')

    for _ in range(3478):
        placex_row(cls='tourism', typ='hotel')

    importer = SPImporter(config=def_config, conn=temp_db_conn, sp_loader=None)

    result = importer.get_classtype_pairs(min=100)

    assert result == {
        ("amenity", "prison"),
        ("tourism", "hotel")
    }


def test_get_classtype_pair_data_default(placex_row, def_config, temp_db_conn):
    for _ in range(1):
        placex_row(cls='emergency', typ='firehydrant')

    for _ in range(199):
        placex_row(cls='amenity', typ='prison')

    for _ in range(3478):
        placex_row(cls='tourism', typ='hotel')

    importer = SPImporter(config=def_config, conn=temp_db_conn, sp_loader=None)

    result = importer.get_classtype_pairs()

    assert result == {
        ("amenity", "prison"),
        ("tourism", "hotel"),
        ("emergency", "firehydrant")
    }
