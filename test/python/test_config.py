"""
Test for loading dotenv configuration.
"""
from pathlib import Path
import tempfile

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

def test_prefer_os_environ_over_project_setting(monkeypatch):
    with tempfile.TemporaryDirectory() as project_dir:
        with open(project_dir + '/.env', 'w') as envfile:
            envfile.write('NOMINATIM_DATABASE_WEBUSER=apache\n')

        monkeypatch.setenv('NOMINATIM_DATABASE_WEBUSER', 'nobody')

        config = Configuration(Path(project_dir), DEFCFG_DIR)

        assert config.DATABASE_WEBUSER == 'nobody'

def test_get_os_env_add_defaults(monkeypatch):
    config = Configuration(None, DEFCFG_DIR)

    monkeypatch.delenv('NOMINATIM_DATABASE_WEBUSER', raising=False)

    assert config.get_os_env()['NOMINATIM_DATABASE_WEBUSER'] == 'www-data'

def test_get_os_env_prefer_os_environ(monkeypatch):
    config = Configuration(None, DEFCFG_DIR)

    monkeypatch.setenv('NOMINATIM_DATABASE_WEBUSER', 'nobody')

    assert config.get_os_env()['NOMINATIM_DATABASE_WEBUSER'] == 'nobody'

def test_get_libpq_dsn_convert_default():
    config = Configuration(None, DEFCFG_DIR)

    assert config.get_libpq_dsn() == 'dbname=nominatim'

def test_get_libpq_dsn_convert_php(monkeypatch):
    config = Configuration(None, DEFCFG_DIR)

    monkeypatch.setenv('NOMINATIM_DATABASE_DSN',
                       'pgsql:dbname=gis;password=foo;host=localhost')

    assert config.get_libpq_dsn() == 'dbname=gis password=foo host=localhost'

def test_get_libpq_dsn_convert_libpq(monkeypatch):
    config = Configuration(None, DEFCFG_DIR)

    monkeypatch.setenv('NOMINATIM_DATABASE_DSN', 
                       'host=localhost dbname=gis password=foo')

    assert config.get_libpq_dsn() == 'host=localhost dbname=gis password=foo'
