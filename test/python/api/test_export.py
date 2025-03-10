# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for export CLI function.
"""
import pytest

import nominatim_db.cli


@pytest.fixture
def run_export(tmp_path, capsys):
    def _exec(args):
        cli_args = ['export', '--project-dir', str(tmp_path)] + args
        assert 0 == nominatim_db.cli.nominatim(osm2pgsql_path='OSM2PGSQL NOT AVAILABLE',
                                               cli_args=cli_args)
        return capsys.readouterr().out.split('\r\n')

    return _exec


@pytest.fixture(autouse=True)
def setup_database_with_context(apiobj):
    apiobj.add_placex(place_id=332, osm_type='W', osm_id=4,
                      class_='highway', type='residential',  name='Street',
                      country_code='pl', postcode='55674',
                      rank_search=27, rank_address=26)
    apiobj.add_address_placex(332, fromarea=False, isaddress=False,
                              distance=0.0034,
                              place_id=1000, osm_type='N', osm_id=3333,
                              class_='place', type='suburb', name='Smallplace',
                              country_code='pl', admin_level=13,
                              rank_search=24, rank_address=23)
    apiobj.add_address_placex(332, fromarea=True, isaddress=True,
                              place_id=1001, osm_type='N', osm_id=3334,
                              class_='place', type='city', name='Bigplace',
                              country_code='pl',
                              rank_search=17, rank_address=16)


def test_export_default(run_export):
    csv = run_export([])

    assert csv == ['street,suburb,city,county,state,country', 'Street,,Bigplace,,,', '']


def test_export_output_type(run_export):
    csv = run_export(['--output-type', 'city'])

    assert csv == ['street,suburb,city,county,state,country', ',,Bigplace,,,', '']


def test_export_output_format(run_export):
    csv = run_export(['--output-format', 'placeid;street;nothing;postcode'])

    assert csv == ['placeid,street,nothing,postcode', '332,Street,,55674', '']


def test_export_restrict_to_node_good(run_export):
    csv = run_export(['--restrict-to-osm-node', '3334'])

    assert csv == ['street,suburb,city,county,state,country', 'Street,,Bigplace,,,', '']


def test_export_restrict_to_node_not_address(run_export):
    csv = run_export(['--restrict-to-osm-node', '3333'])

    assert csv == ['street,suburb,city,county,state,country', '']
