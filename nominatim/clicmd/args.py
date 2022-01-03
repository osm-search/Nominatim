# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Provides custom functions over command-line arguments.
"""
import logging
from pathlib import Path

from nominatim.errors import UsageError

LOG = logging.getLogger()

class NominatimArgs:
    """ Customized namespace class for the nominatim command line tool
        to receive the command-line arguments.
    """

    def osm2pgsql_options(self, default_cache, default_threads):
        """ Return the standard osm2pgsql options that can be derived
            from the command line arguments. The resulting dict can be
            further customized and then used in `run_osm2pgsql()`.
        """
        return dict(osm2pgsql=self.config.OSM2PGSQL_BINARY or self.osm2pgsql_path,
                    osm2pgsql_cache=self.osm2pgsql_cache or default_cache,
                    osm2pgsql_style=self.config.get_import_style_file(),
                    threads=self.threads or default_threads,
                    dsn=self.config.get_libpq_dsn(),
                    flatnode_file=str(self.config.get_path('FLATNODE_FILE')),
                    tablespaces=dict(slim_data=self.config.TABLESPACE_OSM_DATA,
                                     slim_index=self.config.TABLESPACE_OSM_INDEX,
                                     main_data=self.config.TABLESPACE_PLACE_DATA,
                                     main_index=self.config.TABLESPACE_PLACE_INDEX
                                    )
                   )


    def get_osm_file_list(self):
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
