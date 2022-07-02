# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Nominatim configuration accessor.
"""
from typing import Dict, Any, List, Mapping, Optional
import logging
import os
from pathlib import Path
import json
import yaml

from dotenv import dotenv_values

from nominatim.typing import StrPath
from nominatim.errors import UsageError

LOG = logging.getLogger()
CONFIG_CACHE : Dict[str, Any] = {}

def flatten_config_list(content: Any, section: str = '') -> List[Any]:
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

    def __init__(self, project_dir: Path, config_dir: Path,
                 environ: Optional[Mapping[str, str]] = None) -> None:
        self.environ = environ or os.environ
        self.project_dir = project_dir
        self.config_dir = config_dir
        self._config = dotenv_values(str((config_dir / 'env.defaults').resolve()))
        if project_dir is not None and (project_dir / '.env').is_file():
            self._config.update(dotenv_values(str((project_dir / '.env').resolve())))

        class _LibDirs:
            pass

        self.lib_dir = _LibDirs()


    def set_libdirs(self, **kwargs: StrPath) -> None:
        """ Set paths to library functions and data.
        """
        for key, value in kwargs.items():
            setattr(self.lib_dir, key, Path(value).resolve())


    def __getattr__(self, name: str) -> str:
        name = 'NOMINATIM_' + name

        if name in self.environ:
            return self.environ[name]

        return self._config[name] or ''


    def get_bool(self, name: str) -> bool:
        """ Return the given configuration parameter as a boolean.
            Values of '1', 'yes' and 'true' are accepted as truthy values,
            everything else is interpreted as false.
        """
        return getattr(self, name).lower() in ('1', 'yes', 'true')


    def get_int(self, name: str) -> int:
        """ Return the given configuration parameter as an int.
        """
        try:
            return int(getattr(self, name))
        except ValueError as exp:
            LOG.fatal("Invalid setting NOMINATIM_%s. Needs to be a number.", name)
            raise UsageError("Configuration error.") from exp


    def get_str_list(self, name: str) -> Optional[List[str]]:
        """ Return the given configuration parameter as a list of strings.
            The values are assumed to be given as a comma-sparated list and
            will be stripped before returning them. On empty values None
            is returned.
        """
        raw = getattr(self, name)

        return [v.strip() for v in raw.split(',')] if raw else None


    def get_path(self, name: str) -> Optional[Path]:
        """ Return the given configuration parameter as a Path.
            If a relative path is configured, then the function converts this
            into an absolute path with the project directory as root path.
            If the configuration is unset, None is returned.
        """
        value = getattr(self, name)
        if not value:
            return None

        cfgpath = Path(value)

        if not cfgpath.is_absolute():
            cfgpath = self.project_dir / cfgpath

        return cfgpath.resolve()


    def get_libpq_dsn(self) -> str:
        """ Get configured database DSN converted into the key/value format
            understood by libpq and psycopg.
        """
        dsn = self.DATABASE_DSN

        def quote_param(param: str) -> str:
            key, val = param.split('=')
            val = val.replace('\\', '\\\\').replace("'", "\\'")
            if ' ' in val:
                val = "'" + val + "'"
            return key + '=' + val

        if dsn.startswith('pgsql:'):
            # Old PHP DSN format. Convert before returning.
            return ' '.join([quote_param(p) for p in dsn[6:].split(';')])

        return dsn


    def get_import_style_file(self) -> Path:
        """ Return the import style file as a path object. Translates the
            name of the standard styles automatically into a file in the
            config style.
        """
        style = getattr(self, 'IMPORT_STYLE')

        if style in ('admin', 'street', 'address', 'full', 'extratags'):
            return self.config_dir / f'import-{style}.style'

        return self.find_config_file('', 'IMPORT_STYLE')


    def get_os_env(self) -> Dict[str, Optional[str]]:
        """ Return a copy of the OS environment with the Nominatim configuration
            merged in.
        """
        env = dict(self._config)
        env.update(self.environ)

        return env


    def load_sub_configuration(self, filename: StrPath,
                               config: Optional[str] = None) -> Any:
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
        configfile = self.find_config_file(filename, config)

        if str(configfile) in CONFIG_CACHE:
            return CONFIG_CACHE[str(configfile)]

        if configfile.suffix in ('.yaml', '.yml'):
            result = self._load_from_yaml(configfile)
        elif configfile.suffix == '.json':
            with configfile.open('r', encoding='utf-8') as cfg:
                result = json.load(cfg)
        else:
            raise UsageError(f"Config file '{configfile}' has unknown format.")

        CONFIG_CACHE[str(configfile)] = result
        return result


    def find_config_file(self, filename: StrPath,
                         config: Optional[str] = None) -> Path:
        """ Resolve the location of a configuration file given a filename and
            an optional configuration option with the file name.
            Raises a UsageError when the file cannot be found or is not
            a regular file.
        """
        if config is not None:
            cfg_value = getattr(self, config)
            if cfg_value:
                cfg_filename = Path(cfg_value)

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


    def _load_from_yaml(self, cfgfile: Path) -> Any:
        """ Load a YAML configuration file. This installs a special handler that
            allows to include other YAML files using the '!include' operator.
        """
        yaml.add_constructor('!include', self._yaml_include_representer,
                             Loader=yaml.SafeLoader)
        return yaml.safe_load(cfgfile.read_text(encoding='utf-8'))


    def _yaml_include_representer(self, loader: Any, node: yaml.Node) -> Any:
        """ Handler for the '!include' operator in YAML files.

            When the filename is relative, then the file is first searched in the
            project directory and then in the global settings dirctory.
        """
        fname = loader.construct_scalar(node)

        if Path(fname).is_absolute():
            configfile = Path(fname)
        else:
            configfile = self.find_config_file(loader.construct_scalar(node))

        if configfile.suffix != '.yaml':
            LOG.fatal("Format error while reading '%s': only YAML format supported.",
                      configfile)
            raise UsageError("Cannot handle config file format.")

        return yaml.safe_load(configfile.read_text(encoding='utf-8'))
