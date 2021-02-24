"""
Provides custom functions over command-line arguments.
"""


class NominatimArgs: # pylint: disable=too-few-public-methods
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
                    flatnode_file=self.config.FLATNODE_FILE,
                    tablespaces=dict(slim_data=self.config.TABLESPACE_OSM_DATA,
                                     slim_index=self.config.TABLESPACE_OSM_INDEX,
                                     main_data=self.config.TABLESPACE_PLACE_DATA,
                                     main_index=self.config.TABLESPACE_PLACE_INDEX
                                    )
                    )
