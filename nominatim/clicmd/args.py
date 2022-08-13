# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Provides custom functions over command-line arguments.
"""
from typing import Optional, List, Dict, Any, Sequence, Tuple
import argparse
import logging
from pathlib import Path

from nominatim.errors import UsageError
from nominatim.config import Configuration
from nominatim.typing import Protocol

LOG = logging.getLogger()

class Subcommand(Protocol):
    """
    Interface to be implemented by classes implementing a CLI subcommand.
    """

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        """
        Fill the given parser for the subcommand with the appropriate
        parameters.
        """

    def run(self, args: 'NominatimArgs') -> int:
        """
        Run the subcommand with the given parsed arguments.
        """


class NominatimArgs:
    """ Customized namespace class for the nominatim command line tool
        to receive the command-line arguments.
    """
    # Basic environment set by root program.
    config: Configuration
    project_dir: Path
    module_dir: Path
    osm2pgsql_path: Path
    phplib_dir: Path
    sqllib_dir: Path
    data_dir: Path
    config_dir: Path
    phpcgi_path: Path

    # Global switches
    version: bool
    subcommand: Optional[str]
    command: Subcommand

    # Shared parameters
    osm2pgsql_cache: Optional[int]
    socket_timeout: int

    # Arguments added to all subcommands.
    verbose: int
    threads: Optional[int]

    # Arguments to 'add-data'
    file: Optional[str]
    diff: Optional[str]
    node: Optional[int]
    way: Optional[int]
    relation: Optional[int]
    tiger_data: Optional[str]
    use_main_api: bool

    # Arguments to 'admin'
    warm: bool
    check_database: bool
    migrate: bool
    collect_os_info: bool
    analyse_indexing: bool
    target: Optional[str]
    osm_id: Optional[str]
    place_id: Optional[int]

    # Arguments to 'import'
    osm_file: List[str]
    continue_at: Optional[str]
    reverse_only: bool
    no_partitions: bool
    no_updates: bool
    offline: bool
    ignore_errors: bool
    index_noanalyse: bool

    # Arguments to 'index'
    boundaries_only: bool
    no_boundaries: bool
    minrank: int
    maxrank: int

    # Arguments to 'export'
    output_type: str
    output_format: str
    output_all_postcodes: bool
    language: Optional[str]
    restrict_to_country: Optional[str]
    restrict_to_osm_node: Optional[int]
    restrict_to_osm_way: Optional[int]
    restrict_to_osm_relation: Optional[int]

    # Arguments to 'refresh'
    postcodes: bool
    word_tokens: bool
    word_counts: bool
    address_levels: bool
    functions: bool
    wiki_data: bool
    importance: bool
    website: bool
    diffs: bool
    enable_debug_statements: bool
    data_object: Sequence[Tuple[str, int]]
    data_area: Sequence[Tuple[str, int]]

    # Arguments to 'replication'
    init: bool
    update_functions: bool
    check_for_updates: bool
    once: bool
    catch_up: bool
    do_index: bool

    # Arguments to 'serve'
    server: str

    # Arguments to 'special-phrases
    import_from_wiki: bool
    import_from_csv: Optional[str]
    no_replace: bool

    # Arguments to all query functions
    format: str
    addressdetails: bool
    extratags: bool
    namedetails: bool
    lang: Optional[str]
    polygon_output: Optional[str]
    polygon_threshold: Optional[float]

    # Arguments to 'search'
    query: Optional[str]
    street: Optional[str]
    city: Optional[str]
    county: Optional[str]
    state: Optional[str]
    country: Optional[str]
    postalcode: Optional[str]
    countrycodes: Optional[str]
    exclude_place_ids: Optional[str]
    limit: Optional[int]
    viewbox: Optional[str]
    bounded: bool
    dedupe: bool

    # Arguments to 'reverse'
    lat: float
    lon: float
    zoom: Optional[int]

    # Arguments to 'lookup'
    ids: Sequence[str]

    # Arguments to 'details'
    object_class: Optional[str]


    def osm2pgsql_options(self, default_cache: int,
                          default_threads: int) -> Dict[str, Any]:
        """ Return the standard osm2pgsql options that can be derived
            from the command line arguments. The resulting dict can be
            further customized and then used in `run_osm2pgsql()`.
        """
        return dict(osm2pgsql=self.config.OSM2PGSQL_BINARY or self.osm2pgsql_path,
                    osm2pgsql_cache=self.osm2pgsql_cache or default_cache,
                    osm2pgsql_style=self.config.get_import_style_file(),
                    threads=self.threads or default_threads,
                    dsn=self.config.get_libpq_dsn(),
                    flatnode_file=str(self.config.get_path('FLATNODE_FILE') or ''),
                    tablespaces=dict(slim_data=self.config.TABLESPACE_OSM_DATA,
                                     slim_index=self.config.TABLESPACE_OSM_INDEX,
                                     main_data=self.config.TABLESPACE_PLACE_DATA,
                                     main_index=self.config.TABLESPACE_PLACE_INDEX
                                    )
                   )


    def get_osm_file_list(self) -> Optional[List[Path]]:
        """ Return the --osm-file argument as a list of Paths or None
            if no argument was given. The function also checks if the files
            exist and raises a UsageError if one cannot be found.
        """
        if not self.osm_file:
            return None

        files = [Path(f) for f in self.osm_file]
        for fname in files:
            if not fname.is_file():
                LOG.fatal("OSM file '%s' does not exist.", fname)
                raise UsageError('Cannot access file.')

        return files
