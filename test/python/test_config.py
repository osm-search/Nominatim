"""
Test for loading dotenv configuration.
"""
from pathlib import Path
import tempfile
import os

import pytest

from nominatim.config import Configuration

DEFCFG_DIR = Path(__file__) / '..' / '..' / '..' / 'settings'

def test_no_project_dir():
    config = Configuration(None, DEFCFG_DIR)

    assert config.DATABASE_WEBUSER == 'www-data'

def test_prefer_project_setting_over_default():
    with tempfile.TemporaryDirectory() as project_dir:
        with open(project_dir + '/.env', 'w') as envfile:
            envfile.write('NOMINATIM_DATABASE_WEBUSER=apache\n')

        config = Configuration(Path(project_dir), DEFCFG_DIR)

        assert config.DATABASE_WEBUSER == 'apache'

def test_prefer_os_environ_over_project_setting():
    with tempfile.TemporaryDirectory() as project_dir:
        with open(project_dir + '/.env', 'w') as envfile:
            envfile.write('NOMINATIM_DATABASE_WEBUSER=apache\n')

        os.environ['NOMINATIM_DATABASE_WEBUSER'] = 'nobody'

        config = Configuration(Path(project_dir), DEFCFG_DIR)

        assert config.DATABASE_WEBUSER == 'nobody'

        del os.environ['NOMINATIM_DATABASE_WEBUSER']

def test_get_os_env_add_defaults():
    config = Configuration(None, DEFCFG_DIR)

    if 'NOMINATIM_DATABASE_WEBUSER' in os.environ:
        del os.environ['NOMINATIM_DATABASE_WEBUSER']

    assert config.get_os_env()['NOMINATIM_DATABASE_WEBUSER'] == 'www-data'

def test_get_os_env_prefer_os_environ():
    config = Configuration(None, DEFCFG_DIR)

    os.environ['NOMINATIM_DATABASE_WEBUSER'] = 'nobody'

    assert config.get_os_env()['NOMINATIM_DATABASE_WEBUSER'] == 'nobody'

    del os.environ['NOMINATIM_DATABASE_WEBUSER']
