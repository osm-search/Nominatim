"""
Test for loading dotenv configuration.
"""
import pytest

from nominatim.config import Configuration
from nominatim.errors import UsageError

@pytest.fixture
def make_config(src_dir):
    """ Create a configuration object from the given project directory.
    """
    def _mk_config(project_dir=None):
        return Configuration(project_dir, src_dir / 'settings')

    return _mk_config


def test_no_project_dir(make_config):
    config = make_config()

    assert config.DATABASE_WEBUSER == 'www-data'


@pytest.mark.parametrize("val", ('apache', '"apache"'))
def test_prefer_project_setting_over_default(make_config, val, tmp_path):
    envfile = tmp_path / '.env'
    envfile.write_text('NOMINATIM_DATABASE_WEBUSER={}\n'.format(val))

    config = make_config(tmp_path)

    assert config.DATABASE_WEBUSER == 'apache'


def test_prefer_os_environ_over_project_setting(make_config, monkeypatch, tmp_path):
    envfile = tmp_path / '.env'
    envfile.write_text('NOMINATIM_DATABASE_WEBUSER=apache\n')

    monkeypatch.setenv('NOMINATIM_DATABASE_WEBUSER', 'nobody')

    config = make_config(tmp_path)

    assert config.DATABASE_WEBUSER == 'nobody'


def test_get_os_env_add_defaults(make_config, monkeypatch):
    config = make_config()

    monkeypatch.delenv('NOMINATIM_DATABASE_WEBUSER', raising=False)

    assert config.get_os_env()['NOMINATIM_DATABASE_WEBUSER'] == 'www-data'


def test_get_os_env_prefer_os_environ(make_config, monkeypatch):
    config = make_config()

    monkeypatch.setenv('NOMINATIM_DATABASE_WEBUSER', 'nobody')

    assert config.get_os_env()['NOMINATIM_DATABASE_WEBUSER'] == 'nobody'


def test_get_libpq_dsn_convert_default(make_config):
    config = make_config()

    assert config.get_libpq_dsn() == 'dbname=nominatim'


def test_get_libpq_dsn_convert_php(make_config, monkeypatch):
    config = make_config()

    monkeypatch.setenv('NOMINATIM_DATABASE_DSN',
                       'pgsql:dbname=gis;password=foo;host=localhost')

    assert config.get_libpq_dsn() == 'dbname=gis password=foo host=localhost'


@pytest.mark.parametrize("val,expect", [('foo bar', "'foo bar'"),
                                        ("xy'z", "xy\\'z"),
                                       ])
def test_get_libpq_dsn_convert_php_special_chars(make_config, monkeypatch, val, expect):
    config = make_config()

    monkeypatch.setenv('NOMINATIM_DATABASE_DSN',
                       'pgsql:dbname=gis;password={}'.format(val))

    assert config.get_libpq_dsn() == "dbname=gis password={}".format(expect)


def test_get_libpq_dsn_convert_libpq(make_config, monkeypatch):
    config = make_config()

    monkeypatch.setenv('NOMINATIM_DATABASE_DSN',
                       'host=localhost dbname=gis password=foo')

    assert config.get_libpq_dsn() == 'host=localhost dbname=gis password=foo'


@pytest.mark.parametrize("value,result",
                         [(x, True) for x in ('1', 'true', 'True', 'yes', 'YES')] +
                         [(x, False) for x in ('0', 'false', 'no', 'NO', 'x')])
def test_get_bool(make_config, monkeypatch, value, result):
    config = make_config()

    monkeypatch.setenv('NOMINATIM_FOOBAR', value)

    assert config.get_bool('FOOBAR') == result

def test_get_bool_empty(make_config):
    config = make_config()

    assert config.DATABASE_MODULE_PATH == ''
    assert not config.get_bool('DATABASE_MODULE_PATH')


@pytest.mark.parametrize("value,result", [('0', 0), ('1', 1),
                                          ('85762513444', 85762513444)])
def test_get_int_success(make_config, monkeypatch, value, result):
    config = make_config()

    monkeypatch.setenv('NOMINATIM_FOOBAR', value)

    assert config.get_int('FOOBAR') == result


@pytest.mark.parametrize("value", ['1b', 'fg', '0x23'])
def test_get_int_bad_values(make_config, monkeypatch, value):
    config = make_config()

    monkeypatch.setenv('NOMINATIM_FOOBAR', value)

    with pytest.raises(UsageError):
        config.get_int('FOOBAR')


def test_get_int_empty(make_config):
    config = make_config()

    assert config.DATABASE_MODULE_PATH == ''

    with pytest.raises(UsageError):
        config.get_int('DATABASE_MODULE_PATH')


def test_get_import_style_intern(make_config, src_dir, monkeypatch):
    config = make_config()

    monkeypatch.setenv('NOMINATIM_IMPORT_STYLE', 'street')

    expected = src_dir / 'settings' / 'import-street.style'

    assert config.get_import_style_file() == expected


@pytest.mark.parametrize("value", ['custom', '/foo/bar.stye'])
def test_get_import_style_extern(make_config, monkeypatch, value):
    config = make_config()

    monkeypatch.setenv('NOMINATIM_IMPORT_STYLE', value)

    assert str(config.get_import_style_file()) == value
