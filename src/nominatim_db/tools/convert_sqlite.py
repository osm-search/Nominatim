# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Exporting a Nominatim database to SQlite.
"""
from typing import Set, Any, Optional, Union
import datetime as dt
import logging
from pathlib import Path

import sqlalchemy as sa

import nominatim_api as napi
from nominatim_api.search.query_analyzer_factory import make_query_analyzer
from nominatim_api.typing import SaSelect, SaRow
from nominatim_api.sql.sqlalchemy_types import Geometry, IntArray

LOG = logging.getLogger()

async def convert(project_dir: Optional[Union[str, Path]],
                  outfile: Path, options: Set[str]) -> None:
    """ Export an existing database to sqlite. The resulting database
        will be usable against the Python frontend of Nominatim.
    """
    api = napi.NominatimAPIAsync(project_dir)

    try:
        outapi = napi.NominatimAPIAsync(project_dir,
                                        {'NOMINATIM_DATABASE_DSN': f"sqlite:dbname={outfile}",
                                         'NOMINATIM_DATABASE_RW': '1'})

        try:
            async with api.begin() as src, outapi.begin() as dest:
                writer = SqliteWriter(src, dest, options)
                await writer.write()
        finally:
            await outapi.close()
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
        LOG.warning('Setting up spatialite')
        await self.dest.execute(sa.select(sa.func.InitSpatialMetaData(True, 'WGS84')))

        await self.create_tables()
        await self.copy_data()
        if 'search' in self.options:
            await self.create_word_table()
        await self.create_indexes()


    async def create_tables(self) -> None:
        """ Set up the database tables.
        """
        LOG.warning('Setting up tables')
        if 'search' not in self.options:
            self.dest.t.meta.remove(self.dest.t.search_name)
        else:
            await self.create_class_tables()

        await self.dest.connection.run_sync(self.dest.t.meta.create_all)

        # Convert all Geometry columns to Spatialite geometries
        for table in self.dest.t.meta.sorted_tables:
            for col in table.c:
                if isinstance(col.type, Geometry):
                    await self.dest.execute(sa.select(
                        sa.func.RecoverGeometryColumn(table.name, col.name, 4326,
                                                      col.type.subtype.upper(), 'XY')))


    async def create_class_tables(self) -> None:
        """ Set up the table that serve class/type-specific geometries.
        """
        sql = sa.text("""SELECT tablename FROM pg_tables
                         WHERE tablename LIKE 'place_classtype_%'""")
        for res in await self.src.execute(sql):
            for db in (self.src, self.dest):
                sa.Table(res[0], db.t.meta,
                         sa.Column('place_id', sa.BigInteger),
                         sa.Column('centroid', Geometry))


    async def create_word_table(self) -> None:
        """ Create the word table.
            This table needs the property information to determine the
            correct format. Therefore needs to be done after all other
            data has been copied.
        """
        await make_query_analyzer(self.src)
        await make_query_analyzer(self.dest)
        src = self.src.t.meta.tables['word']
        dest = self.dest.t.meta.tables['word']

        await self.dest.connection.run_sync(dest.create)

        LOG.warning("Copying word table")
        async_result = await self.src.connection.stream(sa.select(src))

        async for partition in async_result.partitions(10000):
            data = [{k: getattr(r, k) for k in r._fields} for r in partition]
            await self.dest.execute(dest.insert(), data)

        await self.dest.connection.run_sync(sa.Index('idx_word_woken', dest.c.word_token).create)


    async def copy_data(self) -> None:
        """ Copy data for all registered tables.
        """
        def _getfield(row: SaRow, key: str) -> Any:
            value = getattr(row, key)
            if isinstance(value, dt.datetime):
                if value.tzinfo is not None:
                    value = value.astimezone(dt.timezone.utc)
            return value

        for table in self.dest.t.meta.sorted_tables:
            LOG.warning("Copying '%s'", table.name)
            async_result = await self.src.connection.stream(self.select_from(table.name))

            async for partition in async_result.partitions(10000):
                data = [{('class_' if k == 'class' else k): _getfield(r, k)
                         for k in r._fields}
                        for r in partition]
                await self.dest.execute(table.insert(), data)

        # Set up a minimal copy of pg_tables used to look up the class tables later.
        pg_tables = sa.Table('pg_tables', self.dest.t.meta,
                             sa.Column('schemaname', sa.Text, default='public'),
                             sa.Column('tablename', sa.Text))
        await self.dest.connection.run_sync(pg_tables.create)
        data = [{'tablename': t} for t in self.dest.t.meta.tables]
        await self.dest.execute(pg_tables.insert().values(data))


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
        await self.create_index('placex', 'parent_place_id')
        await self.create_index('placex', 'rank_address')
        await self.create_index('addressline', 'place_id')
        await self.create_index('postcode', 'place_id')
        await self.create_index('osmline', 'place_id')
        await self.create_index('tiger', 'place_id')

        if 'search' in self.options:
            await self.create_spatial_index('postcode', 'geometry')
            await self.create_spatial_index('search_name', 'centroid')
            await self.create_index('search_name', 'place_id')
            await self.create_index('osmline', 'parent_place_id')
            await self.create_index('tiger', 'parent_place_id')
            await self.create_search_index()

            for t in self.dest.t.meta.tables:
                if t.startswith('place_classtype_'):
                    await self.dest.execute(sa.select(
                      sa.func.CreateSpatialIndex(t, 'centroid')))


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


    async def create_search_index(self) -> None:
        """ Create the tables and indexes needed for word lookup.
        """
        LOG.warning("Creating reverse search table")
        rsn = sa.Table('reverse_search_name', self.dest.t.meta,
                       sa.Column('word', sa.Integer()),
                       sa.Column('column', sa.Text()),
                       sa.Column('places', IntArray))
        await self.dest.connection.run_sync(rsn.create)

        tsrc = self.src.t.search_name
        for column in ('name_vector', 'nameaddress_vector'):
            sql = sa.select(sa.func.unnest(getattr(tsrc.c, column)).label('word'),
                            sa.func.ArrayAgg(tsrc.c.place_id).label('places'))\
                    .group_by('word')

            async_result = await self.src.connection.stream(sql)
            async for partition in async_result.partitions(100):
                data = []
                for row in partition:
                    row.places.sort()
                    data.append({'word': row.word,
                                 'column': column,
                                 'places': row.places})
                await self.dest.execute(rsn.insert(), data)

        await self.dest.connection.run_sync(
            sa.Index('idx_reverse_search_name_word', rsn.c.word).create)


    def select_from(self, table: str) -> SaSelect:
        """ Create the SQL statement to select the source columns and rows.
        """
        columns = self.src.t.meta.tables[table].c

        if table == 'placex':
            # SQLite struggles with Geometries that are larger than 5MB,
            # so simplify those.
            return sa.select(*(c for c in columns if not isinstance(c.type, Geometry)),
                             sa.func.ST_AsText(columns.centroid).label('centroid'),
                             sa.func.ST_AsText(
                               sa.case((sa.func.ST_MemSize(columns.geometry) < 5000000,
                                        columns.geometry),
                                       else_=sa.func.ST_SimplifyPreserveTopology(
                                                columns.geometry, 0.0001)
                                )).label('geometry'))

        sql = sa.select(*(sa.func.ST_AsText(c).label(c.name)
                             if isinstance(c.type, Geometry) else c for c in columns))

        return sql
