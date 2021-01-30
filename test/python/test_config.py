"""
Test for loading dotenv configuration.
"""
from pathlib import Path
import tempfile

import pytest

from nominatim.config import Configuration
from nominatim.errors import UsageError

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


@pytest.mark.parametrize("val,expect", [('foo bar', "'foo bar'"),
                                        ("xy'z", "xy\\'z"),
                                       ])
def test_get_libpq_dsn_convert_php_special_chars(monkeypatch, val, expect):
    config = Configuration(None, DEFCFG_DIR)

    monkeypatch.setenv('NOMINATIM_DATABASE_DSN',
                       'pgsql:dbname=gis;password={}'.format(val))

    assert config.get_libpq_dsn() == "dbname=gis password={}".format(expect)


def test_get_libpq_dsn_convert_libpq(monkeypatch):
    config = Configuration(None, DEFCFG_DIR)

    monkeypatch.setenv('NOMINATIM_DATABASE_DSN', 
                       'host=localhost dbname=gis password=foo')

    assert config.get_libpq_dsn() == 'host=localhost dbname=gis password=foo'


@pytest.mark.parametrize("value,result",
                         [(x, True) for x in ('1', 'true', 'True', 'yes', 'YES')] +
                         [(x, False) for x in ('0', 'false', 'no', 'NO', 'x')])
def test_get_bool(monkeypatch, value, result):
    config = Configuration(None, DEFCFG_DIR)

    monkeypatch.setenv('NOMINATIM_FOOBAR', value)

    assert config.get_bool('FOOBAR') == result

def test_get_bool_empty():
    config = Configuration(None, DEFCFG_DIR)

    assert config.DATABASE_MODULE_PATH == ''
    assert config.get_bool('DATABASE_MODULE_PATH') == False


@pytest.mark.parametrize("value,result", [('0', 0), ('1', 1),
                                          ('85762513444', 85762513444)])
def test_get_int_success(monkeypatch, value, result):
    config = Configuration(None, DEFCFG_DIR)

    monkeypatch.setenv('NOMINATIM_FOOBAR', value)

    assert config.get_int('FOOBAR') == result


@pytest.mark.parametrize("value", ['1b', 'fg', '0x23'])
def test_get_int_bad_values(monkeypatch, value):
    config = Configuration(None, DEFCFG_DIR)

    monkeypatch.setenv('NOMINATIM_FOOBAR', value)

    with pytest.raises(UsageError):
        config.get_int('FOOBAR')


def test_get_int_empty():
    config = Configuration(None, DEFCFG_DIR)

    assert config.DATABASE_MODULE_PATH == ''

    with pytest.raises(UsageError):
        config.get_int('DATABASE_MODULE_PATH')


def test_get_import_style_intern(monkeypatch):
    config = Configuration(None, DEFCFG_DIR)

    monkeypatch.setenv('NOMINATIM_IMPORT_STYLE', 'street')

    expected = DEFCFG_DIR / 'import-street.style'

    assert config.get_import_style_file() == expected


@pytest.mark.parametrize("value", ['custom', '/foo/bar.stye'])
def test_get_import_style_intern(monkeypatch, value):
    config = Configuration(None, DEFCFG_DIR)

    monkeypatch.setenv('NOMINATIM_IMPORT_STYLE', value)

    assert str(config.get_import_style_file()) == value
