# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Exporting a Nominatim database to SQlite.
"""
from typing import Set
import logging
from pathlib import Path

import sqlalchemy as sa

from nominatim.typing import SaSelect
from nominatim.db.sqlalchemy_types import Geometry
import nominatim.api as napi

LOG = logging.getLogger()

async def convert(project_dir: Path, outfile: Path, options: Set[str]) -> None:
    """ Export an existing database to sqlite. The resulting database
        will be usable against the Python frontend of Nominatim.
    """
    api = napi.NominatimAPIAsync(project_dir)

    try:
        outapi = napi.NominatimAPIAsync(project_dir,
                                        {'NOMINATIM_DATABASE_DSN': f"sqlite:dbname={outfile}"})

        async with api.begin() as src, outapi.begin() as dest:
            writer = SqliteWriter(src, dest, options)
            await writer.write()
    finally:
        await api.close()


class SqliteWriter:
    """ Worker class which creates a new SQLite database.
    """

    def __init__(self, src: napi.SearchConnection,
                 dest: napi.SearchConnection, options: Set[str]) -> None:
        self.src = src
        self.dest = dest
        self.options = options


    async def write(self) -> None:
        """ Create the database structure and copy the data from
            the source database to the destination.
        """
        await self.dest.execute(sa.select(sa.func.InitSpatialMetaData(True, 'WGS84')))

        await self.create_tables()
        await self.copy_data()
        await self.create_indexes()


    async def create_tables(self) -> None:
        """ Set up the database tables.
        """
        if 'search' not in self.options:
            self.dest.t.meta.remove(self.dest.t.search_name)

        await self.dest.connection.run_sync(self.dest.t.meta.create_all)

        # Convert all Geometry columns to Spatialite geometries
        for table in self.dest.t.meta.sorted_tables:
            for col in table.c:
                if isinstance(col.type, Geometry):
                    await self.dest.execute(sa.select(
                        sa.func.RecoverGeometryColumn(table.name, col.name, 4326,
                                                      col.type.subtype.upper(), 'XY')))


    async def copy_data(self) -> None:
        """ Copy data for all registered tables.
        """
        for table in self.dest.t.meta.sorted_tables:
            LOG.warning("Copying '%s'", table.name)
            async_result = await self.src.connection.stream(self.select_from(table.name))

            async for partition in async_result.partitions(10000):
                data = [{('class_' if k == 'class' else k): getattr(r, k) for k in r._fields}
                        for r in partition]
                await self.dest.execute(table.insert(), data)


    async def create_indexes(self) -> None:
        """ Add indexes necessary for the frontend.
        """
        # reverse place node lookup needs an extra table to simulate a
        # partial index with adaptive buffering.
        await self.dest.execute(sa.text(
            """ CREATE TABLE placex_place_node_areas AS
                  SELECT place_id, ST_Expand(geometry,
                                             14.0 * exp(-0.2 * rank_search) - 0.03) as geometry
                  FROM placex
                  WHERE rank_address between 5 and 25
                        and osm_type = 'N'
                        and linked_place_id is NULL """))
        await self.dest.execute(sa.select(
            sa.func.RecoverGeometryColumn('placex_place_node_areas', 'geometry',
                                          4326, 'GEOMETRY', 'XY')))
        await self.dest.execute(sa.select(sa.func.CreateSpatialIndex(
                                             'placex_place_node_areas', 'geometry')))

        # Remaining indexes.
        await self.create_spatial_index('country_grid', 'geometry')
        await self.create_spatial_index('placex', 'geometry')
        await self.create_spatial_index('osmline', 'linegeo')
        await self.create_spatial_index('tiger', 'linegeo')
        await self.create_index('placex', 'place_id')
        await self.create_index('placex', 'rank_address')
        await self.create_index('addressline', 'place_id')


    async def create_spatial_index(self, table: str, column: str) -> None:
        """ Create a spatial index on the given table and column.
        """
        await self.dest.execute(sa.select(
                  sa.func.CreateSpatialIndex(getattr(self.dest.t, table).name, column)))


    async def create_index(self, table_name: str, column: str) -> None:
        """ Create a simple index on the given table and column.
        """
        table = getattr(self.dest.t, table_name)
        await self.dest.connection.run_sync(
            sa.Index(f"idx_{table}_{column}", getattr(table.c, column)).create)


    def select_from(self, table: str) -> SaSelect:
        """ Create the SQL statement to select the source columns and rows.
        """
        columns = self.src.t.meta.tables[table].c

        sql = sa.select(*(sa.func.ST_AsText(c).label(c.name)
                             if isinstance(c.type, Geometry) else c for c in columns))

        return sql
