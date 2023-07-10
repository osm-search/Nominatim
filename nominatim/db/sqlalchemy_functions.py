# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Custom functions and expressions for SQLAlchemy.
"""

import sqlalchemy as sa

def select_index_placex_geometry_reverse_lookuppolygon(table: str) -> 'sa.TextClause':
    """ Create an expression with the necessary conditions over a placex
        table that the index 'idx_placex_geometry_reverse_lookupPolygon'
        can be used.
    """
    return sa.text(f"ST_GeometryType({table}.geometry) in ('ST_Polygon', 'ST_MultiPolygon')"
                   f" AND {table}.rank_address between 4 and 25"
                   f" AND {table}.type != 'postcode'"
                   f" AND {table}.name is not null"
                   f" AND {table}.indexed_status = 0"
                   f" AND {table}.linked_place_id is null")

def select_index_placex_geometry_reverse_lookupplacenode(table: str) -> 'sa.TextClause':
    """ Create an expression with the necessary conditions over a placex
        table that the index 'idx_placex_geometry_reverse_lookupPlaceNode'
        can be used.
    """
    return sa.text(f"{table}.rank_address between 4 and 25"
                   f" AND {table}.type != 'postcode'"
                   f" AND {table}.name is not null"
                   f" AND {table}.linked_place_id is null"
                   f" AND {table}.osm_type = 'N'")
