# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
SQLAlchemy definitions for all tables used by the frontend.
"""
from typing import Any

import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import HSTORE, ARRAY, JSONB
from sqlalchemy.dialects.sqlite import JSON as sqlite_json

#pylint: disable=too-many-instance-attributes
class SearchTables:
    """ Data class that holds the tables of the Nominatim database.
    """

    def __init__(self, meta: sa.MetaData, engine_name: str) -> None:
        if engine_name == 'postgresql':
            Composite: Any = HSTORE
            Json: Any = JSONB
            IntArray: Any = ARRAY(sa.Integer()) #pylint: disable=invalid-name
        elif engine_name == 'sqlite':
            Composite = sqlite_json
            Json = sqlite_json
            IntArray = sqlite_json
        else:
            raise ValueError("Only 'postgresql' and 'sqlite' engines are supported.")

        self.meta = meta

        self.import_status = sa.Table('import_status', meta,
            sa.Column('lastimportdate', sa.DateTime(True), nullable=False),
            sa.Column('sequence_id', sa.Integer),
            sa.Column('indexed', sa.Boolean))

        self.properties = sa.Table('nominatim_properties', meta,
            sa.Column('property', sa.Text, nullable=False),
            sa.Column('value', sa.Text))

        self.placex = sa.Table('placex', meta,
            sa.Column('place_id', sa.BigInteger, nullable=False, unique=True),
            sa.Column('parent_place_id', sa.BigInteger),
            sa.Column('linked_place_id', sa.BigInteger),
            sa.Column('importance', sa.Float),
            sa.Column('indexed_date', sa.DateTime),
            sa.Column('rank_address', sa.SmallInteger),
            sa.Column('rank_search', sa.SmallInteger),
            sa.Column('partition', sa.SmallInteger),
            sa.Column('indexed_status', sa.SmallInteger),
            sa.Column('osm_type', sa.String(1), nullable=False),
            sa.Column('osm_id', sa.BigInteger, nullable=False),
            sa.Column('class', sa.Text, nullable=False, key='class_'),
            sa.Column('type', sa.Text, nullable=False),
            sa.Column('admin_level', sa.SmallInteger),
            sa.Column('name', Composite),
            sa.Column('address', Composite),
            sa.Column('extratags', Composite),
            sa.Column('geometry', Geometry(srid=4326), nullable=False),
            sa.Column('wikipedia', sa.Text),
            sa.Column('country_code', sa.String(2)),
            sa.Column('housenumber', sa.Text),
            sa.Column('postcode', sa.Text),
            sa.Column('centroid', Geometry(srid=4326, spatial_index=False)))

        self.addressline = sa.Table('place_addressline', meta,
            sa.Column('place_id', sa.BigInteger, index=True),
            sa.Column('address_place_id', sa.BigInteger, index=True),
            sa.Column('distance', sa.Float),
            sa.Column('cached_rank_address', sa.SmallInteger),
            sa.Column('fromarea', sa.Boolean),
            sa.Column('isaddress', sa.Boolean))

        self.postcode = sa.Table('location_postcode', meta,
            sa.Column('place_id', sa.BigInteger, unique=True),
            sa.Column('parent_place_id', sa.BigInteger),
            sa.Column('rank_search', sa.SmallInteger),
            sa.Column('rank_address', sa.SmallInteger),
            sa.Column('indexed_status', sa.SmallInteger),
            sa.Column('indexed_date', sa.DateTime),
            sa.Column('country_code', sa.String(2)),
            sa.Column('postcode', sa.Text, index=True),
            sa.Column('geometry', Geometry(srid=4326)))

        self.osmline = sa.Table('location_property_osmline', meta,
            sa.Column('place_id', sa.BigInteger, nullable=False, unique=True),
            sa.Column('osm_id', sa.BigInteger),
            sa.Column('parent_place_id', sa.BigInteger),
            sa.Column('indexed_date', sa.DateTime),
            sa.Column('startnumber', sa.Integer),
            sa.Column('endnumber', sa.Integer),
            sa.Column('step', sa.SmallInteger),
            sa.Column('partition', sa.SmallInteger),
            sa.Column('indexed_status', sa.SmallInteger),
            sa.Column('linegeo', Geometry(srid=4326)),
            sa.Column('address', Composite),
            sa.Column('postcode', sa.Text),
            sa.Column('country_code', sa.String(2)))

        self.word = sa.Table('word', meta,
            sa.Column('word_id', sa.Integer),
            sa.Column('word_token', sa.Text, nullable=False),
            sa.Column('type', sa.Text, nullable=False),
            sa.Column('word', sa.Text),
            sa.Column('info', Json))

        self.country_name = sa.Table('country_name', meta,
            sa.Column('country_code', sa.String(2)),
            sa.Column('name', Composite),
            sa.Column('derived_name', Composite),
            sa.Column('country_default_language_code', sa.Text),
            sa.Column('partition', sa.Integer))

        self.country_grid = sa.Table('country_osm_grid', meta,
            sa.Column('country_code', sa.String(2)),
            sa.Column('area', sa.Float),
            sa.Column('geometry', Geometry(srid=4326)))

        # The following tables are not necessarily present.
        self.search_name = sa.Table('search_name', meta,
            sa.Column('place_id', sa.BigInteger, index=True),
            sa.Column('importance', sa.Float),
            sa.Column('search_rank', sa.SmallInteger),
            sa.Column('address_rank', sa.SmallInteger),
            sa.Column('name_vector', IntArray, index=True),
            sa.Column('nameaddress_vector', IntArray, index=True),
            sa.Column('country_code', sa.String(2)),
            sa.Column('centroid', Geometry(srid=4326)))

        self.tiger = sa.Table('location_property_tiger', meta,
            sa.Column('place_id', sa.BigInteger),
            sa.Column('parent_place_id', sa.BigInteger),
            sa.Column('startnumber', sa.Integer),
            sa.Column('endnumber', sa.Integer),
            sa.Column('step', sa.SmallInteger),
            sa.Column('partition', sa.SmallInteger),
            sa.Column('linegeo', Geometry(srid=4326, spatial_index=False)),
            sa.Column('postcode', sa.Text))
