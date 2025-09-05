# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of classes for API access via libraries.
"""
from typing import Mapping, Optional, Any, AsyncIterator, Dict, Sequence, List, \
                   Union, Tuple, cast
import asyncio
import sys
import contextlib
from pathlib import Path

if sys.version_info >= (3, 11):
    from asyncio import timeout_at
else:
    from async_timeout import timeout_at

import sqlalchemy as sa
import sqlalchemy.ext.asyncio as sa_asyncio

from .errors import UsageError
from .sql.sqlalchemy_schema import SearchTables
from .sql.async_core_library import PGCORE_LIB, PGCORE_ERROR
from .config import Configuration
from .sql import sqlite_functions, sqlalchemy_functions  # noqa
from .connection import SearchConnection
from .status import get_status, StatusResult
from .lookup import get_places, get_detailed_place
from .reverse import ReverseGeocoder
from .timeout import Timeout
from . import search as nsearch
from . import types as ntyp
from .results import DetailedResult, ReverseResult, SearchResults


class NominatimAPIAsync:
    """ The main frontend to the Nominatim database implements the
        functions for lookup, forward and reverse geocoding using
        asynchronous functions.

        This class shares most of the functions with its synchronous
        version. There are some additional functions or parameters,
        which are documented below.

        This class should usually be used as a context manager in 'with' context.
    """
    def __init__(self, project_dir: Optional[Union[str, Path]] = None,
                 environ: Optional[Mapping[str, str]] = None,
                 loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """ Initiate a new frontend object with synchronous API functions.

            Parameters:
              project_dir: Path to the
                  [project directory](../admin/Import.md#creating-the-project-directory)
                  of the local Nominatim installation.
              environ: Mapping of [configuration parameters](../customize/Settings.md).
                  When set, replaces any configuration via environment variables.
                  Settings in this mapping also have precedence over any
                  parameters found in the `.env` file of the project directory.
              loop: The asyncio event loop that will be used when calling
                  functions. Only needed, when a custom event loop is used
                  and the Python version is 3.9 or earlier.
        """
        self.config = Configuration(project_dir, environ)
        self.query_timeout = self.config.get_int('QUERY_TIMEOUT') \
            if self.config.QUERY_TIMEOUT else None
        self.request_timeout = self.config.get_int('REQUEST_TIMEOUT') \
            if self.config.REQUEST_TIMEOUT else None
        self.reverse_restrict_to_country_area = self.config.get_bool('SEARCH_WITHIN_COUNTRIES')
        self.server_version = 0

        if sys.version_info >= (3, 10):
            self._engine_lock = asyncio.Lock()
        else:
            self._engine_lock = asyncio.Lock(loop=loop)
        self._engine: Optional[sa_asyncio.AsyncEngine] = None
        self._tables: Optional[SearchTables] = None
        self._property_cache: Dict[str, Any] = {'DB:server_version': 0}

    async def setup_database(self) -> None:
        """ Set up the SQL engine and connections.

            This function will be implicitly called when the database is
            accessed for the first time. You may also call it explicitly to
            avoid that the first call is delayed by the setup.
        """
        async with self._engine_lock:
            if self._engine:
                return

            extra_args: Dict[str, Any] = {'future': True,
                                          'echo': self.config.get_bool('DEBUG_SQL')}

            if self.config.get_int('API_POOL_SIZE') == 0:
                extra_args['poolclass'] = sa.pool.NullPool
            else:
                extra_args['poolclass'] = sa.pool.AsyncAdaptedQueuePool
                extra_args['max_overflow'] = 0
                extra_args['pool_size'] = self.config.get_int('API_POOL_SIZE')

            is_sqlite = self.config.DATABASE_DSN.startswith('sqlite:')

            if is_sqlite:
                params = dict((p.split('=', 1)
                              for p in self.config.DATABASE_DSN[7:].split(';')))
                dburl = sa.engine.URL.create('sqlite+aiosqlite',
                                             database=params.get('dbname'))

                if not ('NOMINATIM_DATABASE_RW' in self.config.environ
                        and self.config.get_bool('DATABASE_RW')) \
                   and not Path(params.get('dbname', '')).is_file():
                    raise UsageError(f"SQlite database '{params.get('dbname')}' does not exist.")
            else:
                dsn = self.config.get_database_params()
                query = {k: str(v) for k, v in dsn.items()
                         if k not in ('user', 'password', 'dbname', 'host', 'port')}

                dburl = sa.engine.URL.create(
                           f'postgresql+{PGCORE_LIB}',
                           database=cast(str, dsn.get('dbname')),
                           username=cast(str, dsn.get('user')),
                           password=cast(str, dsn.get('password')),
                           host=cast(str, dsn.get('host')),
                           port=int(cast(str, dsn['port'])) if 'port' in dsn else None,
                           query=query)

            engine = sa_asyncio.create_async_engine(dburl, **extra_args)

            if is_sqlite:
                server_version = 0

                @sa.event.listens_for(engine.sync_engine, "connect")
                def _on_sqlite_connect(dbapi_con: Any, _: Any) -> None:
                    dbapi_con.run_async(lambda conn: conn.enable_load_extension(True))
                    sqlite_functions.install_custom_functions(dbapi_con)
                    cursor = dbapi_con.cursor()
                    cursor.execute("SELECT load_extension('mod_spatialite')")
                    cursor.execute('SELECT SetDecimalPrecision(7)')
                    dbapi_con.run_async(lambda conn: conn.enable_load_extension(False))
            else:
                try:
                    async with engine.begin() as conn:
                        result = await conn.scalar(sa.text('SHOW server_version_num'))
                        server_version = int(result)
                        await conn.execute(sa.text("SET jit_above_cost TO '-1'"))
                        await conn.execute(sa.text(
                                "SET max_parallel_workers_per_gather TO '0'"))
                except (PGCORE_ERROR, sa.exc.OperationalError):
                    server_version = 0

                @sa.event.listens_for(engine.sync_engine, "connect")
                def _on_connect(dbapi_con: Any, _: Any) -> None:
                    cursor = dbapi_con.cursor()
                    cursor.execute("SET jit_above_cost TO '-1'")
                    cursor.execute("SET max_parallel_workers_per_gather TO '0'")

            self._property_cache['DB:server_version'] = server_version

            self._tables = SearchTables(sa.MetaData())
            self._engine = engine

    async def close(self) -> None:
        """ Close all active connections to the database. The NominatimAPIAsync
            object remains usable after closing. If a new API functions is
            called, new connections are created.
        """
        if self._engine is not None:
            await self._engine.dispose()

    async def __aenter__(self) -> 'NominatimAPIAsync':
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    @contextlib.asynccontextmanager
    async def begin(self, abs_timeout: Optional[float] = None) -> AsyncIterator[SearchConnection]:
        """ Create a new connection with automatic transaction handling.

            This function may be used to get low-level access to the database.
            Refer to the documentation of SQLAlchemy for details how to use
            the connection object.

            You may optionally give an absolute timeout until when to wait
            for a connection to become available.
        """
        if self._engine is None:
            await self.setup_database()

        assert self._engine is not None
        assert self._tables is not None

        async with timeout_at(abs_timeout), self._engine.begin() as conn:
            yield SearchConnection(conn, self._tables, self._property_cache, self.config)

    async def status(self) -> StatusResult:
        """ Return the status of the database.
        """
        timeout = Timeout(self.request_timeout)
        try:
            async with self.begin(abs_timeout=timeout.abs) as conn:
                conn.set_query_timeout(self.query_timeout)
                status = await get_status(conn)
        except (PGCORE_ERROR, sa.exc.OperationalError):
            return StatusResult(700, 'Database connection failed')

        return status

    async def details(self, place: ntyp.PlaceRef, **params: Any) -> Optional[DetailedResult]:
        """ Get detailed information about a place in the database.

            Returns None if there is no entry under the given ID.
        """
        timeout = Timeout(self.request_timeout)
        details = ntyp.LookupDetails.from_kwargs(params)
        async with self.begin(abs_timeout=timeout.abs) as conn:
            conn.set_query_timeout(self.query_timeout)
            if details.keywords:
                await nsearch.make_query_analyzer(conn)
            return await get_detailed_place(conn, place, details)

    async def lookup(self, places: Sequence[ntyp.PlaceRef], **params: Any) -> SearchResults:
        """ Get simple information about a list of places.

            Returns a list of place information for all IDs that were found.
        """
        timeout = Timeout(self.request_timeout)
        details = ntyp.LookupDetails.from_kwargs(params)
        async with self.begin(abs_timeout=timeout.abs) as conn:
            conn.set_query_timeout(self.query_timeout)
            if details.keywords:
                await nsearch.make_query_analyzer(conn)
            return await get_places(conn, places, details)

    async def reverse(self, coord: ntyp.AnyPoint, **params: Any) -> Optional[ReverseResult]:
        """ Find a place by its coordinates. Also known as reverse geocoding.

            Returns the closest result that can be found or None if
            no place matches the given criteria.
        """
        # The following negation handles NaN correctly. Don't change.
        if not abs(coord[0]) <= 180 or not abs(coord[1]) <= 90:
            # There are no results to be expected outside valid coordinates.
            return None

        timeout = Timeout(self.request_timeout)
        details = ntyp.ReverseDetails.from_kwargs(params)
        async with self.begin(abs_timeout=timeout.abs) as conn:
            conn.set_query_timeout(self.query_timeout)
            if details.keywords:
                await nsearch.make_query_analyzer(conn)
            geocoder = ReverseGeocoder(conn, details,
                                       self.reverse_restrict_to_country_area)
            return await geocoder.lookup(coord)

    async def search(self, query: str, **params: Any) -> SearchResults:
        """ Find a place by free-text search. Also known as forward geocoding.
        """
        query = query.strip()
        if not query:
            raise UsageError('Nothing to search for.')

        timeout = Timeout(self.request_timeout)
        async with self.begin(abs_timeout=timeout.abs) as conn:
            conn.set_query_timeout(self.query_timeout)
            geocoder = nsearch.ForwardGeocoder(conn, ntyp.SearchDetails.from_kwargs(params),
                                               timeout)
            phrases = [nsearch.Phrase(nsearch.PHRASE_ANY, p.strip()) for p in query.split(',')]
            return await geocoder.lookup(phrases)

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
        timeout = Timeout(self.request_timeout)
        async with self.begin(abs_timeout=timeout.abs) as conn:
            conn.set_query_timeout(self.query_timeout)
            details = ntyp.SearchDetails.from_kwargs(params)

            phrases: List[nsearch.Phrase] = []

            if amenity:
                phrases.append(nsearch.Phrase(nsearch.PHRASE_AMENITY, amenity))
            if street:
                phrases.append(nsearch.Phrase(nsearch.PHRASE_STREET, street))
            if city:
                phrases.append(nsearch.Phrase(nsearch.PHRASE_CITY, city))
            if county:
                phrases.append(nsearch.Phrase(nsearch.PHRASE_COUNTY, county))
            if state:
                phrases.append(nsearch.Phrase(nsearch.PHRASE_STATE, state))
            if postalcode:
                phrases.append(nsearch.Phrase(nsearch.PHRASE_POSTCODE, postalcode))
            if country:
                phrases.append(nsearch.Phrase(nsearch.PHRASE_COUNTRY, country))

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

            if details.layers is None:
                details.layers = ntyp.DataLayer.ADDRESS
                if amenity:
                    details.layers |= ntyp.DataLayer.POI

            geocoder = nsearch.ForwardGeocoder(conn, details, timeout)
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

        timeout = Timeout(self.request_timeout)
        details = ntyp.SearchDetails.from_kwargs(params)
        async with self.begin(abs_timeout=timeout.abs) as conn:
            conn.set_query_timeout(self.query_timeout)
            if near_query:
                phrases = [nsearch.Phrase(nsearch.PHRASE_ANY, p) for p in near_query.split(',')]
            else:
                phrases = []
                if details.keywords:
                    await nsearch.make_query_analyzer(conn)

            geocoder = nsearch.ForwardGeocoder(conn, details, timeout)
            return await geocoder.lookup_pois(categories, phrases)


class NominatimAPI:
    """ This class provides a thin synchronous wrapper around the asynchronous
        Nominatim functions. It creates its own event loop and runs each
        synchronous function call to completion using that loop.

        This class should usually be used as a context manager in 'with' context.
    """

    def __init__(self, project_dir: Optional[Union[str, Path]] = None,
                 environ: Optional[Mapping[str, str]] = None) -> None:
        """ Initiate a new frontend object with synchronous API functions.

            Parameters:
              project_dir: Path to the
                  [project directory](../admin/Import.md#creating-the-project-directory)
                  of the local Nominatim installation.
              environ: Mapping of [configuration parameters](../customize/Settings.md).
                  When set, replaces any configuration via environment variables.
                  Settings in this mapping also have precedence over any
                  parameters found in the `.env` file of the project directory.
        """
        self._loop = asyncio.new_event_loop()
        self._async_api = NominatimAPIAsync(project_dir, environ, loop=self._loop)

    def close(self) -> None:
        """ Close all active connections to the database.

            This function also closes the asynchronous worker loop making
            the NominatimAPI object unusable.
        """
        if not self._loop.is_closed():
            self._loop.run_until_complete(self._async_api.close())
            self._loop.close()

    def __enter__(self) -> 'NominatimAPI':
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    @property
    def config(self) -> Configuration:
        """ Provide read-only access to the [configuration](Configuration.md)
            used by the API.
        """
        return self._async_api.config

    def status(self) -> StatusResult:
        """ Return the status of the database as a dataclass object
            with the fields described below.

            Returns:
              status(int): A status code as described on the status page.
              message(str): Either 'OK' or a human-readable message of the
                  problem encountered.
              software_version(tuple): A tuple with the version of the
                  Nominatim library consisting of (major, minor, patch, db-patch)
                  version.
              database_version(tuple): A tuple with the version of the library
                  which was used for the import or last migration.
                  Also consists of (major, minor, patch, db-patch).
              data_updated(datetime): Timestamp with the age of the data.
        """
        return self._loop.run_until_complete(self._async_api.status())

    def details(self, place: ntyp.PlaceRef, **params: Any) -> Optional[DetailedResult]:
        """ Get detailed information about a place in the database.

            The result is a dataclass object with the fields described below
            or `None` if the place could not be found in the database.

            Parameters:
              place: Description of the place to look up. See
                     [Place identification](Input-Parameter-Types.md#place-identification)
                     for the various ways to reference a place.

            Other parameters:
              geometry_output (enum): Add the full geometry of the place to the result.
                Multiple formats may be selected. Note that geometries can become
                quite large. (Default: none)
              geometry_simplification (float): Simplification factor to use on
                the geometries before returning them. The factor expresses
                the tolerance in degrees from which the geometry may differ.
                Topology is preserved. (Default: 0.0)
              address_details (bool): Add detailed information about the places
                that make up the address of the requested object. (Default: False)
              linked_places (bool): Add detailed information about the places
                that link to the result. (Default: False)
              parented_places (bool): Add detailed information about all places
                for which the requested object is a parent, i.e. all places for
                which the object provides the address details.
                Only POI places can have parents. (Default: False)
              keywords (bool): Add detailed information about the search terms
                used for this place.

            Returns:
              source_table (enum): Data source of the place. See below for possible values.
              category (tuple): A tuple of two strings with the primary OSM tag
                  and value.
              centroid (Point): Point position of the place.
              place_id (Optional[int]): Internal ID of the place. This ID may differ
                  for the same place between different installations.
              parent_place_id (Optional(int]): Internal ID of the parent of this
                  place. Only meaning full for POI-like objects (places with a
                  rank_address of 30).
              linked_place_id (Optional[int]): Internal ID of the place this object
                  links to. When this ID is set then there is no guarantee that
                  the rest of the result information is complete.
              admin_level (int): Value of the `admin_level` OSM tag. Only meaningful
                  for administrative boundary objects.
              indexed_date (datetime): Timestamp when the place was last updated.
              osm_object (Optional[tuple]): OSM type and ID of the place, if available.
              names (Optional[dict]): Dictionary of names of the place. Keys are
                  usually the corresponding OSM tag keys.
              address (Optional[dict]): Dictionary of address parts directly
                  attributed to the place. Keys are usually the corresponding
                  OSM tag keys with the `addr:` prefix removed.
              extratags (Optional[dict]): Dictionary of additional attributes for
                  the place. Usually OSM tag keys and values.
              housenumber (Optional[str]): House number of the place, normalised
                  for lookup. To get the house number in its original spelling,
                  use `address['housenumber']`.
              postcode (Optional[str]): Computed postcode for the place. To get
                  directly attributed postcodes, use `address['postcode']` instead.
              wikipedia (Optional[str]): Reference to a wikipedia site for the place.
                  The string has the format <language code>:<wikipedia title>.
              rank_address (int): [Address rank](../customize/Ranking.md#address-rank).
              rank_search (int): [Search rank](../customize/Ranking.md#search-rank).
              importance (Optional[float]): Relative importance of the place. This is a measure
                  how likely the place will be searched for.
              country_code (Optional[str]): Country the feature is in as
                  ISO 3166-1 alpha-2 country code.
              address_rows (Optional[AddressLines]): List of places that make up the
                  computed address. `None` when `address_details` parameter was False.
              linked_rows (Optional[AddressLines]): List of places that link to the object.
                  `None` when `linked_places` parameter was False.
              parented_rows (Optional[AddressLines]): List of direct children of the place.
                  `None` when `parented_places` parameter was False.
              name_keywords (Optional[WordInfos]): List of search words for the name of
                   the place. `None` when `keywords` parameter is set to False.
              address_keywords (Optional[WordInfos]): List of search word for the address of
                   the place. `None` when `keywords` parameter is set to False.
              geometry (dict): Dictionary containing the full geometry of the place
                   in the formats requested in the `geometry_output` parameter.
        """
        return self._loop.run_until_complete(self._async_api.details(place, **params))

    def lookup(self, places: Sequence[ntyp.PlaceRef], **params: Any) -> SearchResults:
        """ Get simple information about a list of places.

            Returns a list of place information for all IDs that were found.
            Each result is a dataclass with the fields detailed below.

            Parameters:
              places: List of descriptions of the place to look up. See
                      [Place identification](Input-Parameter-Types.md#place-identification)
                      for the various ways to reference a place.

            Other parameters:
              geometry_output (enum): Add the full geometry of the place to the result.
                Multiple formats may be selected. Note that geometries can become
                quite large. (Default: none)
              geometry_simplification (float): Simplification factor to use on
                the geometries before returning them. The factor expresses
                the tolerance in degrees from which the geometry may differ.
                Topology is preserved. (Default: 0.0)
              address_details (bool): Add detailed information about the places
                that make up the address of the requested object. (Default: False)
              linked_places (bool): Add detailed information about the places
                that link to the result. (Default: False)
              parented_places (bool): Add detailed information about all places
                for which the requested object is a parent, i.e. all places for
                which the object provides the address details.
                Only POI places can have parents. (Default: False)
              keywords (bool): Add detailed information about the search terms
                used for this place.

            Returns:
              source_table (enum): Data source of the place. See below for possible values.
              category (tuple): A tuple of two strings with the primary OSM tag
                  and value.
              centroid (Point): Point position of the place.
              place_id (Optional[int]): Internal ID of the place. This ID may differ
                  for the same place between different installations.
              osm_object (Optional[tuple]): OSM type and ID of the place, if available.
              names (Optional[dict]): Dictionary of names of the place. Keys are
                  usually the corresponding OSM tag keys.
              address (Optional[dict]): Dictionary of address parts directly
                  attributed to the place. Keys are usually the corresponding
                  OSM tag keys with the `addr:` prefix removed.
              extratags (Optional[dict]): Dictionary of additional attributes for
                  the place. Usually OSM tag keys and values.
              housenumber (Optional[str]): House number of the place, normalised
                  for lookup. To get the house number in its original spelling,
                  use `address['housenumber']`.
              postcode (Optional[str]): Computed postcode for the place. To get
                  directly attributed postcodes, use `address['postcode']` instead.
              wikipedia (Optional[str]): Reference to a wikipedia site for the place.
                  The string has the format <language code>:<wikipedia title>.
              rank_address (int): [Address rank](../customize/Ranking.md#address-rank).
              rank_search (int): [Search rank](../customize/Ranking.md#search-rank).
              importance (Optional[float]): Relative importance of the place. This is a measure
                  how likely the place will be searched for.
              country_code (Optional[str]): Country the feature is in as
                  ISO 3166-1 alpha-2 country code.
              address_rows (Optional[AddressLines]): List of places that make up the
                  computed address. `None` when `address_details` parameter was False.
              linked_rows (Optional[AddressLines]): List of places that link to the object.
                  `None` when `linked_places` parameter was False.
              parented_rows (Optional[AddressLines]): List of direct children of the place.
                  `None` when `parented_places` parameter was False.
              name_keywords (Optional[WordInfos]): List of search words for the name of
                   the place. `None` when `keywords` parameter is set to False.
              address_keywords (Optional[WordInfos]): List of search word for the address of
                   the place. `None` when `keywords` parameter is set to False.
              bbox (Bbox): Bounding box of the full geometry of the place.
                   If the place is a single point, then the size of the bounding
                   box is guessed according to the type of place.
              geometry (dict): Dictionary containing the full geometry of the place
                   in the formats requested in the `geometry_output` parameter.
        """
        return self._loop.run_until_complete(self._async_api.lookup(places, **params))

    def reverse(self, coord: ntyp.AnyPoint, **params: Any) -> Optional[ReverseResult]:
        """ Find a place by its coordinates. Also known as reverse geocoding.

            Returns the closest result that can be found or `None` if
            no place matches the given criteria. The result is a dataclass
            with the fields as detailed below.

            Parameters:
              coord: Coordinate to lookup the place for as a Point
                     or a tuple (x, y). Must be in WGS84 projection.

            Other parameters:
              max_rank (int): Highest address rank to return. Can be used to
                restrict search to streets or settlements.
              layers (enum): Defines the kind of data to take into account.
                See description of layers below. (Default: addresses and POIs)
              geometry_output (enum): Add the full geometry of the place to the result.
                Multiple formats may be selected. Note that geometries can become
                quite large. (Default: none)
              geometry_simplification (float): Simplification factor to use on
                the geometries before returning them. The factor expresses
                the tolerance in degrees from which the geometry may differ.
                Topology is preserved. (Default: 0.0)
              address_details (bool): Add detailed information about the places
                that make up the address of the requested object. (Default: False)
              linked_places (bool): Add detailed information about the places
                that link to the result. (Default: False)
              parented_places (bool): Add detailed information about all places
                for which the requested object is a parent, i.e. all places for
                which the object provides the address details.
                Only POI places can have parents. (Default: False)
              keywords (bool): Add detailed information about the search terms
                used for this place.

            Returns:
              source_table (enum): Data source of the place. See below for possible values.
              category (tuple): A tuple of two strings with the primary OSM tag
                  and value.
              centroid (Point): Point position of the place.
              place_id (Optional[int]): Internal ID of the place. This ID may differ
                  for the same place between different installations.
              osm_object (Optional[tuple]): OSM type and ID of the place, if available.
              names (Optional[dict]): Dictionary of names of the place. Keys are
                  usually the corresponding OSM tag keys.
              address (Optional[dict]): Dictionary of address parts directly
                  attributed to the place. Keys are usually the corresponding
                  OSM tag keys with the `addr:` prefix removed.
              extratags (Optional[dict]): Dictionary of additional attributes for
                  the place. Usually OSM tag keys and values.
              housenumber (Optional[str]): House number of the place, normalised
                  for lookup. To get the house number in its original spelling,
                  use `address['housenumber']`.
              postcode (Optional[str]): Computed postcode for the place. To get
                  directly attributed postcodes, use `address['postcode']` instead.
              wikipedia (Optional[str]): Reference to a wikipedia site for the place.
                  The string has the format <language code>:<wikipedia title>.
              rank_address (int): [Address rank](../customize/Ranking.md#address-rank).
              rank_search (int): [Search rank](../customize/Ranking.md#search-rank).
              importance (Optional[float]): Relative importance of the place. This is a measure
                  how likely the place will be searched for.
              country_code (Optional[str]): Country the feature is in as
                  ISO 3166-1 alpha-2 country code.
              address_rows (Optional[AddressLines]): List of places that make up the
                  computed address. `None` when `address_details` parameter was False.
              linked_rows (Optional[AddressLines]): List of places that link to the object.
                  `None` when `linked_places` parameter was False.
              parented_rows (Optional[AddressLines]): List of direct children of the place.
                  `None` when `parented_places` parameter was False.
              name_keywords (Optional[WordInfos]): List of search words for the name of
                   the place. `None` when `keywords` parameter is set to False.
              address_keywords (Optional[WordInfos]): List of search word for the address of
                   the place. `None` when `keywords` parameter is set to False.
              bbox (Bbox): Bounding box of the full geometry of the place.
                   If the place is a single point, then the size of the bounding
                   box is guessed according to the type of place.
              geometry (dict): Dictionary containing the full geometry of the place
                   in the formats requested in the `geometry_output` parameter.
              distance (Optional[float]): Distance in degree from the input point.
        """
        return self._loop.run_until_complete(self._async_api.reverse(coord, **params))

    def search(self, query: str, **params: Any) -> SearchResults:
        """ Find a place by free-text search. Also known as forward geocoding.

            Parameters:
              query: Free-form text query searching for a place.

            Other parameters:
              max_results (int): Maximum number of results to return. The
                actual number of results may be less. (Default: 10)
              min_rank (int): Lowest permissible rank for the result.
                For addressable places this is the minimum
                [address rank](../customize/Ranking.md#address-rank). For all
                other places the [search rank](../customize/Ranking.md#search-rank)
                is used.
              max_rank (int): Highest permissible rank for the result. See min_rank above.
              layers (enum): Defines the kind of data to take into account.
                See [layers section](Input-Parameter-Types.md#layers) for details.
                (Default: addresses and POIs)
              countries (list[str]): Restrict search to countries with the given
                ISO 3166-1 alpha-2 country code. An empty list (the default)
                disables this filter.
              excluded (list[int]): A list of internal IDs of places to exclude
                from the search.
              viewbox (Optional[Bbox]): Bounding box of an area to focus search on.
              bounded_viewbox (bool): Consider the bounding box given in `viewbox`
                as a filter and return only results within the bounding box.
              near (Optional[Point]): Focus search around the given point and
                return results ordered by distance to the given point.
              near_radius (Optional[float]): Restrict results to results within
                the given distance in degrees of `near` point. Ignored, when
                `near` is not set.
              categories (list[tuple]): Restrict search to places of the given
                categories. The category is the main OSM tag assigned to each
                place. An empty list (the default) disables this filter.
              geometry_output (enum): Add the full geometry of the place to the result.
                Multiple formats may be selected. Note that geometries can become
                quite large. (Default: none)
              geometry_simplification (float): Simplification factor to use on
                the geometries before returning them. The factor expresses
                the tolerance in degrees from which the geometry may differ.
                Topology is preserved. (Default: 0.0)
              address_details (bool): Add detailed information about the places
                that make up the address of the requested object. (Default: False)
              linked_places (bool): Add detailed information about the places
                that link to the result. (Default: False)
              parented_places (bool): Add detailed information about all places
                for which the requested object is a parent, i.e. all places for
                which the object provides the address details.
                Only POI places can have parents. (Default: False)
              keywords (bool): Add detailed information about the search terms
                used for this place.

            Returns:
              source_table (enum): Data source of the place. See below for possible values.
              category (tuple): A tuple of two strings with the primary OSM tag
                  and value.
              centroid (Point): Point position of the place.
              place_id (Optional[int]): Internal ID of the place. This ID may differ
                  for the same place between different installations.
              osm_object (Optional[tuple]): OSM type and ID of the place, if available.
              names (Optional[dict]): Dictionary of names of the place. Keys are
                  usually the corresponding OSM tag keys.
              address (Optional[dict]): Dictionary of address parts directly
                  attributed to the place. Keys are usually the corresponding
                  OSM tag keys with the `addr:` prefix removed.
              extratags (Optional[dict]): Dictionary of additional attributes for
                  the place. Usually OSM tag keys and values.
              housenumber (Optional[str]): House number of the place, normalised
                  for lookup. To get the house number in its original spelling,
                  use `address['housenumber']`.
              postcode (Optional[str]): Computed postcode for the place. To get
                  directly attributed postcodes, use `address['postcode']` instead.
              wikipedia (Optional[str]): Reference to a wikipedia site for the place.
                  The string has the format <language code>:<wikipedia title>.
              rank_address (int): [Address rank](../customize/Ranking.md#address-rank).
              rank_search (int): [Search rank](../customize/Ranking.md#search-rank).
              importance (Optional[float]): Relative importance of the place. This is a measure
                  how likely the place will be searched for.
              country_code (Optional[str]): Country the feature is in as
                  ISO 3166-1 alpha-2 country code.
              address_rows (Optional[AddressLines]): List of places that make up the
                  computed address. `None` when `address_details` parameter was False.
              linked_rows (Optional[AddressLines]): List of places that link to the object.
                  `None` when `linked_places` parameter was False.
              parented_rows (Optional[AddressLines]): List of direct children of the place.
                  `None` when `parented_places` parameter was False.
              name_keywords (Optional[WordInfos]): List of search words for the name of
                   the place. `None` when `keywords` parameter is set to False.
              address_keywords (Optional[WordInfos]): List of search word for the address of
                   the place. `None` when `keywords` parameter is set to False.
              bbox (Bbox): Bounding box of the full geometry of the place.
                   If the place is a single point, then the size of the bounding
                   box is guessed according to the type of place.
              geometry (dict): Dictionary containing the full geometry of the place
                   in the formats requested in the `geometry_output` parameter.
        """
        return self._loop.run_until_complete(
                   self._async_api.search(query, **params))

    def search_address(self, amenity: Optional[str] = None,
                       street: Optional[str] = None,
                       city: Optional[str] = None,
                       county: Optional[str] = None,
                       state: Optional[str] = None,
                       country: Optional[str] = None,
                       postalcode: Optional[str] = None,
                       **params: Any) -> SearchResults:
        """ Find an address using structured search.

            Parameters:
              amenity: Name of a POI.
              street: Street and optionally housenumber of the address. If the address
                does not have a street, then the place the housenumber references to.
              city: Postal city of the address.
              county: County equivalent of the address. Does not exist in all
                jurisdictions.
              state: State or province of the address.
              country: Country with its full name or its ISO 3166-1 alpha-2 country code.
                Do not use together with the country_code filter.
              postalcode: Post code or ZIP for the place.

            Other parameters:
              max_results (int): Maximum number of results to return. The
                actual number of results may be less. (Default: 10)
              min_rank (int): Lowest permissible rank for the result.
                For addressable places this is the minimum
                [address rank](../customize/Ranking.md#address-rank). For all
                other places the [search rank](../customize/Ranking.md#search-rank)
                is used.
              max_rank (int): Highest permissible rank for the result. See min_rank above.
              layers (enum): Defines the kind of data to take into account.
                See [layers section](Input-Parameter-Types.md#layers) for details.
                (Default: addresses and POIs)
              countries (list[str]): Restrict search to countries with the given
                ISO 3166-1 alpha-2 country code. An empty list (the default)
                disables this filter. Do not use, when the country parameter
                is used.
              excluded (list[int]): A list of internal IDs of places to exclude
                from the search.
              viewbox (Optional[Bbox]): Bounding box of an area to focus search on.
              bounded_viewbox (bool): Consider the bounding box given in `viewbox`
                as a filter and return only results within the bounding box.
              near (Optional[Point]): Focus search around the given point and
                return results ordered by distance to the given point.
              near_radius (Optional[float]): Restrict results to results within
                the given distance in degrees of `near` point. Ignored, when
                `near` is not set.
              categories (list[tuple]): Restrict search to places of the given
                categories. The category is the main OSM tag assigned to each
                place. An empty list (the default) disables this filter.
              geometry_output (enum): Add the full geometry of the place to the result.
                Multiple formats may be selected. Note that geometries can become
                quite large. (Default: none)
              geometry_simplification (float): Simplification factor to use on
                the geometries before returning them. The factor expresses
                the tolerance in degrees from which the geometry may differ.
                Topology is preserved. (Default: 0.0)
              address_details (bool): Add detailed information about the places
                that make up the address of the requested object. (Default: False)
              linked_places (bool): Add detailed information about the places
                that link to the result. (Default: False)
              parented_places (bool): Add detailed information about all places
                for which the requested object is a parent, i.e. all places for
                which the object provides the address details.
                Only POI places can have parents. (Default: False)
              keywords (bool): Add detailed information about the search terms
                used for this place.

            Returns:
              source_table (enum): Data source of the place. See below for possible values.
              category (tuple): A tuple of two strings with the primary OSM tag
                  and value.
              centroid (Point): Point position of the place.
              place_id (Optional[int]): Internal ID of the place. This ID may differ
                  for the same place between different installations.
              osm_object (Optional[tuple]): OSM type and ID of the place, if available.
              names (Optional[dict]): Dictionary of names of the place. Keys are
                  usually the corresponding OSM tag keys.
              address (Optional[dict]): Dictionary of address parts directly
                  attributed to the place. Keys are usually the corresponding
                  OSM tag keys with the `addr:` prefix removed.
              extratags (Optional[dict]): Dictionary of additional attributes for
                  the place. Usually OSM tag keys and values.
              housenumber (Optional[str]): House number of the place, normalised
                  for lookup. To get the house number in its original spelling,
                  use `address['housenumber']`.
              postcode (Optional[str]): Computed postcode for the place. To get
                  directly attributed postcodes, use `address['postcode']` instead.
              wikipedia (Optional[str]): Reference to a wikipedia site for the place.
                  The string has the format <language code>:<wikipedia title>.
              rank_address (int): [Address rank](../customize/Ranking.md#address-rank).
              rank_search (int): [Search rank](../customize/Ranking.md#search-rank).
              importance (Optional[float]): Relative importance of the place. This is a measure
                  how likely the place will be searched for.
              country_code (Optional[str]): Country the feature is in as
                  ISO 3166-1 alpha-2 country code.
              address_rows (Optional[AddressLines]): List of places that make up the
                  computed address. `None` when `address_details` parameter was False.
              linked_rows (Optional[AddressLines]): List of places that link to the object.
                  `None` when `linked_places` parameter was False.
              parented_rows (Optional[AddressLines]): List of direct children of the place.
                  `None` when `parented_places` parameter was False.
              name_keywords (Optional[WordInfos]): List of search words for the name of
                   the place. `None` when `keywords` parameter is set to False.
              address_keywords (Optional[WordInfos]): List of search word for the address of
                   the place. `None` when `keywords` parameter is set to False.
              bbox (Bbox): Bounding box of the full geometry of the place.
                   If the place is a single point, then the size of the bounding
                   box is guessed according to the type of place.
              geometry (dict): Dictionary containing the full geometry of the place
                   in the formats requested in the `geometry_output` parameter.
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

            Parameters:
              categories: Restrict search to places of the given
                categories. The category is the main OSM tag assigned to each
                place.
              near_query: Optional free-text query to define the are to
                restrict search to.

            Other parameters:
              max_results (int): Maximum number of results to return. The
                actual number of results may be less. (Default: 10)
              min_rank (int): Lowest permissible rank for the result.
                For addressable places this is the minimum
                [address rank](../customize/Ranking.md#address-rank). For all
                other places the [search rank](../customize/Ranking.md#search-rank)
                is used.
              max_rank (int): Highest permissible rank for the result. See min_rank above.
              layers (enum): Defines the kind of data to take into account.
                See [layers section](Input-Parameter-Types.md#layers) for details.
                (Default: addresses and POIs)
              countries (list[str]): Restrict search to countries with the given
                ISO 3166-1 alpha-2 country code. An empty list (the default)
                disables this filter.
              excluded (list[int]): A list of internal IDs of places to exclude
                from the search.
              viewbox (Optional[Bbox]): Bounding box of an area to focus search on.
              bounded_viewbox (bool): Consider the bounding box given in `viewbox`
                as a filter and return only results within the bounding box.
              near (Optional[Point]): Focus search around the given point and
                return results ordered by distance to the given point.
              near_radius (Optional[float]): Restrict results to results within
                the given distance in degrees of `near` point. Ignored, when
                `near` is not set.
              geometry_output (enum): Add the full geometry of the place to the result.
                Multiple formats may be selected. Note that geometries can become
                quite large. (Default: none)
              geometry_simplification (float): Simplification factor to use on
                the geometries before returning them. The factor expresses
                the tolerance in degrees from which the geometry may differ.
                Topology is preserved. (Default: 0.0)
              address_details (bool): Add detailed information about the places
                that make up the address of the requested object. (Default: False)
              linked_places (bool): Add detailed information about the places
                that link to the result. (Default: False)
              parented_places (bool): Add detailed information about all places
                for which the requested object is a parent, i.e. all places for
                which the object provides the address details.
                Only POI places can have parents. (Default: False)
              keywords (bool): Add detailed information about the search terms
                used for this place.

            Returns:
              source_table (enum): Data source of the place. See below for possible values.
              category (tuple): A tuple of two strings with the primary OSM tag
                  and value.
              centroid (Point): Point position of the place.
              place_id (Optional[int]): Internal ID of the place. This ID may differ
                  for the same place between different installations.
              osm_object (Optional[tuple]): OSM type and ID of the place, if available.
              names (Optional[dict]): Dictionary of names of the place. Keys are
                  usually the corresponding OSM tag keys.
              address (Optional[dict]): Dictionary of address parts directly
                  attributed to the place. Keys are usually the corresponding
                  OSM tag keys with the `addr:` prefix removed.
              extratags (Optional[dict]): Dictionary of additional attributes for
                  the place. Usually OSM tag keys and values.
              housenumber (Optional[str]): House number of the place, normalised
                  for lookup. To get the house number in its original spelling,
                  use `address['housenumber']`.
              postcode (Optional[str]): Computed postcode for the place. To get
                  directly attributed postcodes, use `address['postcode']` instead.
              wikipedia (Optional[str]): Reference to a wikipedia site for the place.
                  The string has the format <language code>:<wikipedia title>.
              rank_address (int): [Address rank](../customize/Ranking.md#address-rank).
              rank_search (int): [Search rank](../customize/Ranking.md#search-rank).
              importance (Optional[float]): Relative importance of the place. This is a measure
                  how likely the place will be searched for.
              country_code (Optional[str]): Country the feature is in as
                  ISO 3166-1 alpha-2 country code.
              address_rows (Optional[AddressLines]): List of places that make up the
                  computed address. `None` when `address_details` parameter was False.
              linked_rows (Optional[AddressLines]): List of places that link to the object.
                  `None` when `linked_places` parameter was False.
              parented_rows (Optional[AddressLines]): List of direct children of the place.
                  `None` when `parented_places` parameter was False.
              name_keywords (Optional[WordInfos]): List of search words for the name of
                   the place. `None` when `keywords` parameter is set to False.
              address_keywords (Optional[WordInfos]): List of search word for the address of
                   the place. `None` when `keywords` parameter is set to False.
              bbox (Bbox): Bounding box of the full geometry of the place.
                   If the place is a single point, then the size of the bounding
                   box is guessed according to the type of place.
              geometry (dict): Dictionary containing the full geometry of the place
                   in the formats requested in the `geometry_output` parameter.
        """
        return self._loop.run_until_complete(
                   self._async_api.search_category(categories, near_query, **params))
