"""
Nominatim configuration accessor.
"""
import logging
import os
from pathlib import Path
import yaml

from dotenv import dotenv_values

from nominatim.errors import UsageError

LOG = logging.getLogger()


def flatten_config_list(content, section=''):
    """ Flatten YAML configuration lists that contain include sections
        which are lists themselves.
    """
    if not content:
        return []

    if not isinstance(content, list):
        raise UsageError(f"List expected in section '{section}'.")

    output = []
    for ele in content:
        if isinstance(ele, list):
            output.extend(flatten_config_list(ele, section))
        else:
            output.append(ele)

    return output


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

    def __init__(self, project_dir, config_dir, environ=None):
        self.environ = environ or os.environ
        self.project_dir = project_dir
        self.config_dir = config_dir
        self._config = dotenv_values(str((config_dir / 'env.defaults').resolve()))
        if project_dir is not None and (project_dir / '.env').is_file():
            self._config.update(dotenv_values(str((project_dir / '.env').resolve())))

        # Add defaults for variables that are left empty to set the default.
        # They may still be overwritten by environment variables.
        if not self._config['NOMINATIM_ADDRESS_LEVEL_CONFIG']:
            self._config['NOMINATIM_ADDRESS_LEVEL_CONFIG'] = \
                str(config_dir / 'address-levels.json')

        class _LibDirs:
            pass

        self.lib_dir = _LibDirs()

    def set_libdirs(self, **kwargs):
        """ Set paths to library functions and data.
        """
        for key, value in kwargs.items():
            setattr(self.lib_dir, key, Path(value).resolve())

    def __getattr__(self, name):
        name = 'NOMINATIM_' + name

        if name in self.environ:
            return self.environ[name]

        return self._config[name]

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
        except ValueError as exp:
            LOG.fatal("Invalid setting NOMINATIM_%s. Needs to be a number.", name)
            raise UsageError("Configuration error.") from exp


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


    def load_sub_configuration(self, filename, config=None):
        """ Load additional configuration from a file. `filename` is the name
            of the configuration file. The file is first searched in the
            project directory and then in the global settings dirctory.

            If `config` is set, then the name of the configuration file can
            be additionally given through a .env configuration option. When
            the option is set, then the file will be exclusively loaded as set:
            if the name is an absolute path, the file name is taken as is,
            if the name is relative, it is taken to be relative to the
            project directory.

            The format of the file is determined from the filename suffix.
            Currently only files with extension '.yaml' are supported.

            YAML files support a special '!include' construct. When the
            directive is given, the value is taken to be a filename, the file
            is loaded using this function and added at the position in the
            configuration tree.
        """
        assert Path(filename).suffix == '.yaml'

        configfile = self._find_config_file(filename, config)

        return self._load_from_yaml(configfile)


    def _find_config_file(self, filename, config=None):
        """ Resolve the location of a configuration file given a filename and
            an optional configuration option with the file name.
            Raises a UsageError when the file cannot be found or is not
            a regular file.
        """
        if config is not None:
            cfg_filename = self.__getattr__(config)
            if cfg_filename:
                cfg_filename = Path(cfg_filename)

                if cfg_filename.is_absolute():
                    cfg_filename = cfg_filename.resolve()

                    if not cfg_filename.is_file():
                        LOG.fatal("Cannot find config file '%s'.", cfg_filename)
                        raise UsageError("Config file not found.")

                    return cfg_filename

                filename = cfg_filename


        search_paths = [self.project_dir, self.config_dir]
        for path in search_paths:
            if path is not None and (path / filename).is_file():
                return path / filename

        LOG.fatal("Configuration file '%s' not found.\nDirectories searched: %s",
                  filename, search_paths)
        raise UsageError("Config file not found.")


    def _load_from_yaml(self, cfgfile):
        """ Load a YAML configuration file. This installs a special handler that
            allows to include other YAML files using the '!include' operator.
        """
        yaml.add_constructor('!include', self._yaml_include_representer,
                             Loader=yaml.SafeLoader)
        return yaml.safe_load(cfgfile.read_text(encoding='utf-8'))


    def _yaml_include_representer(self, loader, node):
        """ Handler for the '!include' operator in YAML files.

            When the filename is relative, then the file is first searched in the
            project directory and then in the global settings dirctory.
        """
        fname = loader.construct_scalar(node)

        if Path(fname).is_absolute():
            configfile = Path(fname)
        else:
            configfile = self._find_config_file(loader.construct_scalar(node))

        if configfile.suffix != '.yaml':
            LOG.fatal("Format error while reading '%s': only YAML format supported.",
                      configfile)
            raise UsageError("Cannot handle config file format.")

        return yaml.safe_load(configfile.read_text(encoding='utf-8'))
