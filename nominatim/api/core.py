# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of classes for API access via libraries.
"""
from typing import Mapping, Optional, Any, AsyncIterator, Dict, Sequence, List, Tuple
import asyncio
import contextlib
from pathlib import Path

import sqlalchemy as sa
import sqlalchemy.ext.asyncio as sa_asyncio

from nominatim.errors import UsageError
from nominatim.db.sqlalchemy_schema import SearchTables
from nominatim.db.async_core_library import PGCORE_LIB, PGCORE_ERROR
from nominatim.config import Configuration
from nominatim.api.connection import SearchConnection
from nominatim.api.status import get_status, StatusResult
from nominatim.api.lookup import get_detailed_place, get_simple_place
from nominatim.api.reverse import ReverseGeocoder
from nominatim.api.search import ForwardGeocoder, Phrase, PhraseType, make_query_analyzer
import nominatim.api.types as ntyp
from nominatim.api.results import DetailedResult, ReverseResult, SearchResults


class NominatimAPIAsync:
    """ API loader asynchornous version.
    """
    def __init__(self, project_dir: Path,
                 environ: Optional[Mapping[str, str]] = None) -> None:
        self.config = Configuration(project_dir, environ)
        self.server_version = 0

        self._engine_lock = asyncio.Lock()
        self._engine: Optional[sa_asyncio.AsyncEngine] = None
        self._tables: Optional[SearchTables] = None
        self._property_cache: Dict[str, Any] = {'DB:server_version': 0}


    async def setup_database(self) -> None:
        """ Set up the engine and connection parameters.

            This function will be implicitly called when the database is
            accessed for the first time. You may also call it explicitly to
            avoid that the first call is delayed by the setup.
        """
        async with self._engine_lock:
            if self._engine:
                return

            dsn = self.config.get_database_params()

            query = {k: v for k, v in dsn.items()
                      if k not in ('user', 'password', 'dbname', 'host', 'port')}

            dburl = sa.engine.URL.create(
                       f'postgresql+{PGCORE_LIB}',
                       database=dsn.get('dbname'),
                       username=dsn.get('user'), password=dsn.get('password'),
                       host=dsn.get('host'), port=int(dsn['port']) if 'port' in dsn else None,
                       query=query)
            engine = sa_asyncio.create_async_engine(dburl, future=True,
                                                    echo=self.config.get_bool('DEBUG_SQL'))

            try:
                async with engine.begin() as conn:
                    result = await conn.scalar(sa.text('SHOW server_version_num'))
                    server_version = int(result)
            except (PGCORE_ERROR, sa.exc.OperationalError):
                server_version = 0

            if server_version >= 110000:
                @sa.event.listens_for(engine.sync_engine, "connect")
                def _on_connect(dbapi_con: Any, _: Any) -> None:
                    cursor = dbapi_con.cursor()
                    cursor.execute("SET jit_above_cost TO '-1'")
                    cursor.execute("SET max_parallel_workers_per_gather TO '0'")
                # Make sure that all connections get the new settings
                await self.close()

            self._property_cache['DB:server_version'] = server_version

            self._tables = SearchTables(sa.MetaData(), engine.name) # pylint: disable=no-member
            self._engine = engine


    async def close(self) -> None:
        """ Close all active connections to the database. The NominatimAPIAsync
            object remains usable after closing. If a new API functions is
            called, new connections are created.
        """
        if self._engine is not None:
            await self._engine.dispose()


    @contextlib.asynccontextmanager
    async def begin(self) -> AsyncIterator[SearchConnection]:
        """ Create a new connection with automatic transaction handling.

            This function may be used to get low-level access to the database.
            Refer to the documentation of SQLAlchemy for details how to use
            the connection object.
        """
        if self._engine is None:
            await self.setup_database()

        assert self._engine is not None
        assert self._tables is not None

        async with self._engine.begin() as conn:
            yield SearchConnection(conn, self._tables, self._property_cache)


    async def status(self) -> StatusResult:
        """ Return the status of the database.
        """
        try:
            async with self.begin() as conn:
                status = await get_status(conn)
        except (PGCORE_ERROR, sa.exc.OperationalError):
            return StatusResult(700, 'Database connection failed')

        return status


    async def details(self, place: ntyp.PlaceRef, **params: Any) -> Optional[DetailedResult]:
        """ Get detailed information about a place in the database.

            Returns None if there is no entry under the given ID.
        """
        details = ntyp.LookupDetails.from_kwargs(params)
        async with self.begin() as conn:
            if details.keywords:
                await make_query_analyzer(conn)
            return await get_detailed_place(conn, place, details)


    async def lookup(self, places: Sequence[ntyp.PlaceRef], **params: Any) -> SearchResults:
        """ Get simple information about a list of places.

            Returns a list of place information for all IDs that were found.
        """
        details = ntyp.LookupDetails.from_kwargs(params)
        async with self.begin() as conn:
            if details.keywords:
                await make_query_analyzer(conn)
            return SearchResults(filter(None,
                                        [await get_simple_place(conn, p, details) for p in places]))


    async def reverse(self, coord: ntyp.AnyPoint, **params: Any) -> Optional[ReverseResult]:
        """ Find a place by its coordinates. Also known as reverse geocoding.

            Returns the closest result that can be found or None if
            no place matches the given criteria.
        """
        # The following negation handles NaN correctly. Don't change.
        if not abs(coord[0]) <= 180 or not abs(coord[1]) <= 90:
            # There are no results to be expected outside valid coordinates.
            return None

        details = ntyp.ReverseDetails.from_kwargs(params)
        async with self.begin() as conn:
            if details.keywords:
                await make_query_analyzer(conn)
            geocoder = ReverseGeocoder(conn, details)
            return await geocoder.lookup(coord)


    async def search(self, query: str, **params: Any) -> SearchResults:
        """ Find a place by free-text search. Also known as forward geocoding.
        """
        query = query.strip()
        if not query:
            raise UsageError('Nothing to search for.')

        async with self.begin() as conn:
            geocoder = ForwardGeocoder(conn, ntyp.SearchDetails.from_kwargs(params))
            phrases = [Phrase(PhraseType.NONE, p.strip()) for p in query.split(',')]
            return await geocoder.lookup(phrases)


    # pylint: disable=too-many-arguments,too-many-branches
    async def search_address(self, amenity: Optional[str] = None,
                             street: Optional[str] = None,
                             city: Optional[str] = None,
                             county: Optional[str] = None,
                             state: Optional[str] = None,
                             country: Optional[str] = None,
                             postalcode: Optional[str] = None,
                             **params: Any) -> SearchResults:
        """ Find an address using structured search.
        """
        async with self.begin() as conn:
            details = ntyp.SearchDetails.from_kwargs(params)

            phrases: List[Phrase] = []

            if amenity:
                phrases.append(Phrase(PhraseType.AMENITY, amenity))
            if street:
                phrases.append(Phrase(PhraseType.STREET, street))
            if city:
                phrases.append(Phrase(PhraseType.CITY, city))
            if county:
                phrases.append(Phrase(PhraseType.COUNTY, county))
            if state:
                phrases.append(Phrase(PhraseType.STATE, state))
            if postalcode:
                phrases.append(Phrase(PhraseType.POSTCODE, postalcode))
            if country:
                phrases.append(Phrase(PhraseType.COUNTRY, country))

            if not phrases:
                raise UsageError('Nothing to search for.')

            if amenity or street:
                details.restrict_min_max_rank(26, 30)
            elif city:
                details.restrict_min_max_rank(13, 25)
            elif county:
                details.restrict_min_max_rank(10, 12)
            elif state:
                details.restrict_min_max_rank(5, 9)
            elif postalcode:
                details.restrict_min_max_rank(5, 11)
            else:
                details.restrict_min_max_rank(4, 4)

            if 'layers' not in params:
                details.layers = ntyp.DataLayer.ADDRESS
                if amenity:
                    details.layers |= ntyp.DataLayer.POI

            geocoder = ForwardGeocoder(conn, details)
            return await geocoder.lookup(phrases)


    async def search_category(self, categories: List[Tuple[str, str]],
                              near_query: Optional[str] = None,
                              **params: Any) -> SearchResults:
        """ Find an object of a certain category near another place.
            The near place may either be given as an unstructured search
            query in itself or as coordinates.
        """
        if not categories:
            return SearchResults()

        details = ntyp.SearchDetails.from_kwargs(params)
        async with self.begin() as conn:
            if near_query:
                phrases = [Phrase(PhraseType.NONE, p) for p in near_query.split(',')]
            else:
                phrases = []
                if details.keywords:
                    await make_query_analyzer(conn)

            geocoder = ForwardGeocoder(conn, details)
            return await geocoder.lookup_pois(categories, phrases)



class NominatimAPI:
    """ API loader, synchronous version.
    """

    def __init__(self, project_dir: Path,
                 environ: Optional[Mapping[str, str]] = None) -> None:
        self._loop = asyncio.new_event_loop()
        self._async_api = NominatimAPIAsync(project_dir, environ)


    def close(self) -> None:
        """ Close all active connections to the database. The NominatimAPIAsync
            object remains usable after closing. If a new API functions is
            called, new connections are created.
        """
        self._loop.run_until_complete(self._async_api.close())
        self._loop.close()


    @property
    def config(self) -> Configuration:
        """ Return the configuration used by the API.
        """
        return self._async_api.config

    def status(self) -> StatusResult:
        """ Return the status of the database.
        """
        return self._loop.run_until_complete(self._async_api.status())


    def details(self, place: ntyp.PlaceRef, **params: Any) -> Optional[DetailedResult]:
        """ Get detailed information about a place in the database.
        """
        return self._loop.run_until_complete(self._async_api.details(place, **params))


    def lookup(self, places: Sequence[ntyp.PlaceRef], **params: Any) -> SearchResults:
        """ Get simple information about a list of places.

            Returns a list of place information for all IDs that were found.
        """
        return self._loop.run_until_complete(self._async_api.lookup(places, **params))


    def reverse(self, coord: ntyp.AnyPoint, **params: Any) -> Optional[ReverseResult]:
        """ Find a place by its coordinates. Also known as reverse geocoding.

            Returns the closest result that can be found or None if
            no place matches the given criteria.
        """
        return self._loop.run_until_complete(self._async_api.reverse(coord, **params))


    def search(self, query: str, **params: Any) -> SearchResults:
        """ Find a place by free-text search. Also known as forward geocoding.
        """
        return self._loop.run_until_complete(
                   self._async_api.search(query, **params))


    # pylint: disable=too-many-arguments
    def search_address(self, amenity: Optional[str] = None,
                       street: Optional[str] = None,
                       city: Optional[str] = None,
                       county: Optional[str] = None,
                       state: Optional[str] = None,
                       country: Optional[str] = None,
                       postalcode: Optional[str] = None,
                       **params: Any) -> SearchResults:
        """ Find an address using structured search.
        """
        return self._loop.run_until_complete(
                   self._async_api.search_address(amenity, street, city, county,
                                                  state, country, postalcode, **params))


    def search_category(self, categories: List[Tuple[str, str]],
                        near_query: Optional[str] = None,
                        **params: Any) -> SearchResults:
        """ Find an object of a certain category near another place.
            The near place may either be given as an unstructured search
            query in itself or as a geographic area through the
            viewbox or near parameters.
        """
        return self._loop.run_until_complete(
                   self._async_api.search_category(categories, near_query, **params))
