"""
Nominatim configuration accessor.
"""
import os

from dotenv import dotenv_values

class Configuration:
    """ Load and manage the project configuration.

        Nominatim uses dotenv to configure the software. Configuration options
        are resolved in the following order:

         * from the OS environment
         * from the .env file in the project directory of the installation
         * from the default installation in the configuration directory

        All Nominatim configuration options are prefixed with 'NOMINATIM_' to
        avoid conflicts with other environment variables.
    """

    def __init__(self, project_dir, config_dir):
        self._config = dotenv_values(str((config_dir / 'env.defaults').resolve()))
        if project_dir is not None:
            self._config.update(dotenv_values(str((project_dir / '.env').resolve())))

        # Add defaults for variables that are left empty to set the default.
        # They may still be overwritten by environment variables.
        if not self._config['NOMINATIM_ADDRESS_LEVEL_CONFIG']:
            self._config['NOMINATIM_ADDRESS_LEVEL_CONFIG'] = \
                str(config_dir / 'address-levels.json')


    def __getattr__(self, name):
        name = 'NOMINATIM_' + name

        return os.environ.get(name) or self._config[name]

    def get_libpq_dsn(self):
        """ Get configured database DSN converted into the key/value format
            understood by libpq and psycopg.
        """
        dsn = self.DATABASE_DSN

        if dsn.startswith('pgsql:'):
            # Old PHP DSN format. Convert before returning.
            return dsn[6:].replace(';', ' ')

        return dsn

    def get_os_env(self):
        """ Return a copy of the OS environment with the Nominatim configuration
            merged in.
        """
        env = dict(self._config)
        env.update(os.environ)

        return env
