# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
SQLAlchemy definitions for all tables used by the frontend.
"""
import sqlalchemy as sa

from .sqlalchemy_types import Geometry, KeyValueStore, IntArray


class SearchTables:
    """ Data class that holds the tables of the Nominatim database.

        This schema strictly reflects the read-access view of the database.
        Any data used for updates only will not be visible.
    """

    def __init__(self, meta: sa.MetaData) -> None:
        self.meta = meta

        self.import_status = sa.Table(
            'import_status', meta,
            sa.Column('lastimportdate', sa.DateTime(True), nullable=False),
            sa.Column('sequence_id', sa.Integer),
            sa.Column('indexed', sa.Boolean))

        self.properties = sa.Table(
            'nominatim_properties', meta,
            sa.Column('property', sa.Text, nullable=False),
            sa.Column('value', sa.Text))

        self.placex = sa.Table(
            'placex', meta,
            sa.Column('place_id', sa.BigInteger, nullable=False),
            sa.Column('parent_place_id', sa.BigInteger),
            sa.Column('linked_place_id', sa.BigInteger),
            sa.Column('importance', sa.Float),
            sa.Column('indexed_date', sa.DateTime),
            sa.Column('rank_address', sa.SmallInteger),
            sa.Column('rank_search', sa.SmallInteger),
            sa.Column('indexed_status', sa.SmallInteger),
            sa.Column('osm_type', sa.String(1), nullable=False),
            sa.Column('osm_id', sa.BigInteger, nullable=False),
            sa.Column('class', sa.Text, nullable=False, key='class_'),
            sa.Column('type', sa.Text, nullable=False),
            sa.Column('admin_level', sa.SmallInteger),
            sa.Column('name', KeyValueStore),
            sa.Column('address', KeyValueStore),
            sa.Column('extratags', KeyValueStore),
            sa.Column('geometry', Geometry, nullable=False),
            sa.Column('wikipedia', sa.Text),
            sa.Column('country_code', sa.String(2)),
            sa.Column('housenumber', sa.Text),
            sa.Column('postcode', sa.Text),
            sa.Column('centroid', Geometry))

        self.addressline = sa.Table(
            'place_addressline', meta,
            sa.Column('place_id', sa.BigInteger),
            sa.Column('address_place_id', sa.BigInteger),
            sa.Column('distance', sa.Float),
            sa.Column('fromarea', sa.Boolean),
            sa.Column('isaddress', sa.Boolean))

        self.postcode = sa.Table(
            'location_postcodes', meta,
            sa.Column('place_id', sa.BigInteger),
            sa.Column('parent_place_id', sa.BigInteger),
            sa.Column('osm_id', sa.BigInteger),
            sa.Column('rank_search', sa.SmallInteger),
            sa.Column('indexed_status', sa.SmallInteger),
            sa.Column('indexed_date', sa.DateTime),
            sa.Column('country_code', sa.String(2)),
            sa.Column('postcode', sa.Text),
            sa.Column('centroid', Geometry),
            sa.Column('geometry', Geometry))

        self.osmline = sa.Table(
            'location_property_osmline', meta,
            sa.Column('place_id', sa.BigInteger, nullable=False),
            sa.Column('osm_id', sa.BigInteger),
            sa.Column('parent_place_id', sa.BigInteger),
            sa.Column('indexed_date', sa.DateTime),
            sa.Column('startnumber', sa.Integer),
            sa.Column('endnumber', sa.Integer),
            sa.Column('step', sa.SmallInteger),
            sa.Column('indexed_status', sa.SmallInteger),
            sa.Column('linegeo', Geometry),
            sa.Column('address', KeyValueStore),
            sa.Column('postcode', sa.Text),
            sa.Column('country_code', sa.String(2)))

        self.country_name = sa.Table(
            'country_name', meta,
            sa.Column('country_code', sa.String(2)),
            sa.Column('name', KeyValueStore),
            sa.Column('derived_name', KeyValueStore),
            sa.Column('partition', sa.Integer))

        self.country_grid = sa.Table(
            'country_osm_grid', meta,
            sa.Column('country_code', sa.String(2)),
            sa.Column('area', sa.Float),
            sa.Column('geometry', Geometry))

        # The following tables are not necessarily present.
        self.search_name = sa.Table(
            'search_name', meta,
            sa.Column('place_id', sa.BigInteger),
            sa.Column('importance', sa.Float),
            sa.Column('search_rank', sa.SmallInteger),
            sa.Column('address_rank', sa.SmallInteger),
            sa.Column('name_vector', IntArray),
            sa.Column('nameaddress_vector', IntArray),
            sa.Column('country_code', sa.String(2)),
            sa.Column('centroid', Geometry))

        self.tiger = sa.Table(
            'location_property_tiger', meta,
            sa.Column('place_id', sa.BigInteger),
            sa.Column('parent_place_id', sa.BigInteger),
            sa.Column('startnumber', sa.Integer),
            sa.Column('endnumber', sa.Integer),
            sa.Column('step', sa.SmallInteger),
            sa.Column('linegeo', Geometry),
            sa.Column('postcode', sa.Text))

        self.placex_entrance = sa.Table(
            'placex_entrance', meta,
            sa.Column('place_id', sa.BigInteger),
            sa.Column('osm_id', sa.BigInteger),
            sa.Column('type', sa.Text),
            sa.Column('location', Geometry, nullable=False),
            sa.Column('extratags', KeyValueStore))
