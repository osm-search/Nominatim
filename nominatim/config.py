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
        self._config.update(dotenv_values(str((project_dir / '.env').resolve())))

    def __getattr__(self, name):
        name = 'NOMINATIM_' + name

        return os.environ.get(name) or self._config[name]

    def get_os_env(self):
        """ Return a copy of the OS environment with the Nominatim configuration
            merged in.
        """
        env = dict(os.environ)
        env.update(self._config)

        return env
