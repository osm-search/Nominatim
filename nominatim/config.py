"""
Nominatim configuration accessor.
"""
import logging
import os
from pathlib import Path

from dotenv import dotenv_values

from .errors import UsageError

LOG = logging.getLogger()

class Configuration:
    """ Load and manage the project configuration.

        Nominatim uses dotenv to configure the software. Configuration options
        are resolved in the following order:

         * from the OS environment (or the dirctionary given in `environ`
         * from the .env file in the project directory of the installation
         * from the default installation in the configuration directory

        All Nominatim configuration options are prefixed with 'NOMINATIM_' to
        avoid conflicts with other environment variables.
    """

    def __init__(self, project_dir, config_dir, environ=os.environ):
        self.environ = environ
        self.project_dir = project_dir
        self.config_dir = config_dir
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

        return self.environ.get(name) or self._config[name]

    def get_bool(self, name):
        """ Return the given configuration parameter as a boolean.
            Values of '1', 'yes' and 'true' are accepted as truthy values,
            everything else is interpreted as false.
        """
        return self.__getattr__(name).lower() in ('1', 'yes', 'true')


    def get_int(self, name):
        """ Return the given configuration parameter as an int.
        """
        try:
            return int(self.__getattr__(name))
        except ValueError:
            LOG.fatal("Invalid setting NOMINATIM_%s. Needs to be a number.", name)
            raise UsageError("Configuration error.")


    def get_libpq_dsn(self):
        """ Get configured database DSN converted into the key/value format
            understood by libpq and psycopg.
        """
        dsn = self.DATABASE_DSN

        def quote_param(param):
            key, val = param.split('=')
            val = val.replace('\\', '\\\\').replace("'", "\\'")
            if ' ' in val:
                val = "'" + val + "'"
            return key + '=' + val

        if dsn.startswith('pgsql:'):
            # Old PHP DSN format. Convert before returning.
            return ' '.join([quote_param(p) for p in dsn[6:].split(';')])

        return dsn


    def get_import_style_file(self):
        """ Return the import style file as a path object. Translates the
            name of the standard styles automatically into a file in the
            config style.
        """
        style = self.__getattr__('IMPORT_STYLE')

        if style in ('admin', 'street', 'address', 'full', 'extratags'):
            return self.config_dir / 'import-{}.style'.format(style)

        return Path(style)


    def get_os_env(self):
        """ Return a copy of the OS environment with the Nominatim configuration
            merged in.
        """
        env = dict(self._config)
        env.update(self.environ)

        return env
