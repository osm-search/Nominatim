# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Test for loading dotenv configuration.
"""
from pathlib import Path
import pytest

from nominatim.config import Configuration, flatten_config_list
from nominatim.errors import UsageError

@pytest.fixture
def make_config(src_dir):
    """ Create a configuration object from the given project directory.
    """
    def _mk_config(project_dir=None):
        return Configuration(project_dir, src_dir / 'settings')

    return _mk_config

@pytest.fixture
def make_config_path(src_dir, tmp_path):
    """ Create a configuration object with project and config directories
        in a temporary directory.
    """
    def _mk_config():
        (tmp_path / 'project').mkdir()
        (tmp_path / 'config').mkdir()
        conf = Configuration(tmp_path / 'project', src_dir / 'settings')
        conf.config_dir = tmp_path / 'config'
        return conf

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


def test_prefer_os_environ_can_unset_project_setting(make_config, monkeypatch, tmp_path):
    envfile = tmp_path / '.env'
    envfile.write_text('NOMINATIM_DATABASE_WEBUSER=apache\n')

    monkeypatch.setenv('NOMINATIM_DATABASE_WEBUSER', '')

    config = make_config(tmp_path)

    assert config.DATABASE_WEBUSER == ''


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


def test_get_path_empty(make_config):
    config = make_config()

    assert config.DATABASE_MODULE_PATH == ''
    assert not config.get_path('DATABASE_MODULE_PATH')


def test_get_path_absolute(make_config, monkeypatch):
    config = make_config()

    monkeypatch.setenv('NOMINATIM_FOOBAR', '/dont/care')
    result = config.get_path('FOOBAR')

    assert isinstance(result, Path)
    assert str(result) == '/dont/care'


def test_get_path_relative(make_config, monkeypatch, tmp_path):
    config = make_config(tmp_path)

    monkeypatch.setenv('NOMINATIM_FOOBAR', 'an/oyster')
    result = config.get_path('FOOBAR')

    assert isinstance(result, Path)
    assert str(result) == str(tmp_path / 'an/oyster')


def test_get_import_style_intern(make_config, src_dir, monkeypatch):
    config = make_config()

    monkeypatch.setenv('NOMINATIM_IMPORT_STYLE', 'street')

    expected = src_dir / 'settings' / 'import-street.style'

    assert config.get_import_style_file() == expected


def test_get_import_style_extern_relative(make_config_path, monkeypatch):
    config = make_config_path()
    (config.project_dir / 'custom.style').write_text('x')

    monkeypatch.setenv('NOMINATIM_IMPORT_STYLE', 'custom.style')

    assert str(config.get_import_style_file()) == str(config.project_dir / 'custom.style')


def test_get_import_style_extern_absolute(make_config, tmp_path, monkeypatch):
    config = make_config()
    cfgfile = tmp_path / 'test.style'

    cfgfile.write_text('x')

    monkeypatch.setenv('NOMINATIM_IMPORT_STYLE', str(cfgfile))

    assert str(config.get_import_style_file()) == str(cfgfile)


def test_load_subconf_from_project_dir(make_config_path):
    config = make_config_path()

    testfile = config.project_dir / 'test.yaml'
    testfile.write_text('cow: muh\ncat: miau\n')

    testfile = config.config_dir / 'test.yaml'
    testfile.write_text('cow: miau\ncat: muh\n')

    rules = config.load_sub_configuration('test.yaml')

    assert rules == dict(cow='muh', cat='miau')


def test_load_subconf_from_settings_dir(make_config_path):
    config = make_config_path()

    testfile = config.config_dir / 'test.yaml'
    testfile.write_text('cow: muh\ncat: miau\n')

    rules = config.load_sub_configuration('test.yaml')

    assert rules == dict(cow='muh', cat='miau')


def test_load_subconf_empty_env_conf(make_config_path, monkeypatch):
    monkeypatch.setenv('NOMINATIM_MY_CONFIG', '')
    config = make_config_path()

    testfile = config.config_dir / 'test.yaml'
    testfile.write_text('cow: muh\ncat: miau\n')

    rules = config.load_sub_configuration('test.yaml', config='MY_CONFIG')

    assert rules == dict(cow='muh', cat='miau')


def test_load_subconf_env_absolute_found(make_config_path, monkeypatch, tmp_path):
    monkeypatch.setenv('NOMINATIM_MY_CONFIG', str(tmp_path / 'other.yaml'))
    config = make_config_path()

    (config.config_dir / 'test.yaml').write_text('cow: muh\ncat: miau\n')
    (tmp_path / 'other.yaml').write_text('dog: muh\nfrog: miau\n')

    rules = config.load_sub_configuration('test.yaml', config='MY_CONFIG')

    assert rules == dict(dog='muh', frog='miau')


def test_load_subconf_env_absolute_not_found(make_config_path, monkeypatch, tmp_path):
    monkeypatch.setenv('NOMINATIM_MY_CONFIG', str(tmp_path / 'other.yaml'))
    config = make_config_path()

    (config.config_dir / 'test.yaml').write_text('cow: muh\ncat: miau\n')

    with pytest.raises(UsageError, match='Config file not found.'):
        rules = config.load_sub_configuration('test.yaml', config='MY_CONFIG')


@pytest.mark.parametrize("location", ['project_dir', 'config_dir'])
def test_load_subconf_env_relative_found(make_config_path, monkeypatch, location):
    monkeypatch.setenv('NOMINATIM_MY_CONFIG', 'other.yaml')
    config = make_config_path()

    (config.config_dir / 'test.yaml').write_text('cow: muh\ncat: miau\n')
    (getattr(config, location) / 'other.yaml').write_text('dog: bark\n')

    rules = config.load_sub_configuration('test.yaml', config='MY_CONFIG')

    assert rules == dict(dog='bark')


def test_load_subconf_env_relative_not_found(make_config_path, monkeypatch):
    monkeypatch.setenv('NOMINATIM_MY_CONFIG', 'other.yaml')
    config = make_config_path()

    (config.config_dir / 'test.yaml').write_text('cow: muh\ncat: miau\n')

    with pytest.raises(UsageError, match='Config file not found.'):
        rules = config.load_sub_configuration('test.yaml', config='MY_CONFIG')


def test_load_subconf_json(make_config_path):
    config = make_config_path()

    (config.project_dir / 'test.json').write_text('{"cow": "muh", "cat": "miau"}')

    rules = config.load_sub_configuration('test.json')

    assert rules == dict(cow='muh', cat='miau')

def test_load_subconf_not_found(make_config_path):
    config = make_config_path()

    with pytest.raises(UsageError, match='Config file not found.'):
        config.load_sub_configuration('test.yaml')


def test_load_subconf_env_unknown_format(make_config_path):
    config = make_config_path()

    (config.project_dir / 'test.xml').write_text('<html></html>')

    with pytest.raises(UsageError, match='unknown format'):
        config.load_sub_configuration('test.xml')


def test_load_subconf_include_absolute(make_config_path, tmp_path):
    config = make_config_path()

    testfile = config.config_dir / 'test.yaml'
    testfile.write_text(f'base: !include {tmp_path}/inc.yaml\n')
    (tmp_path / 'inc.yaml').write_text('first: 1\nsecond: 2\n')

    rules = config.load_sub_configuration('test.yaml')

    assert rules == dict(base=dict(first=1, second=2))


@pytest.mark.parametrize("location", ['project_dir', 'config_dir'])
def test_load_subconf_include_relative(make_config_path, tmp_path, location):
    config = make_config_path()

    testfile = config.config_dir / 'test.yaml'
    testfile.write_text(f'base: !include inc.yaml\n')
    (getattr(config, location) / 'inc.yaml').write_text('first: 1\nsecond: 2\n')

    rules = config.load_sub_configuration('test.yaml')

    assert rules == dict(base=dict(first=1, second=2))


def test_load_subconf_include_bad_format(make_config_path):
    config = make_config_path()

    testfile = config.config_dir / 'test.yaml'
    testfile.write_text(f'base: !include inc.txt\n')
    (config.config_dir / 'inc.txt').write_text('first: 1\nsecond: 2\n')

    with pytest.raises(UsageError, match='Cannot handle config file format.'):
        rules = config.load_sub_configuration('test.yaml')


def test_load_subconf_include_not_found(make_config_path):
    config = make_config_path()

    testfile = config.config_dir / 'test.yaml'
    testfile.write_text(f'base: !include inc.txt\n')

    with pytest.raises(UsageError, match='Config file not found.'):
        rules = config.load_sub_configuration('test.yaml')


def test_load_subconf_include_recursive(make_config_path):
    config = make_config_path()

    testfile = config.config_dir / 'test.yaml'
    testfile.write_text(f'base: !include inc.yaml\n')
    (config.config_dir / 'inc.yaml').write_text('- !include more.yaml\n- upper\n')
    (config.config_dir / 'more.yaml').write_text('- the end\n')

    rules = config.load_sub_configuration('test.yaml')

    assert rules == dict(base=[['the end'], 'upper'])


@pytest.mark.parametrize("content", [[], None])
def test_flatten_config_list_empty(content):
    assert flatten_config_list(content) == []


@pytest.mark.parametrize("content", [{'foo': 'bar'}, 'hello world', 3])
def test_flatten_config_list_no_list(content):
    with pytest.raises(UsageError):
        flatten_config_list(content)


def test_flatten_config_list_allready_flat():
    assert flatten_config_list([1, 2, 456]) == [1, 2, 456]


def test_flatten_config_list_nested():
    content = [
        34,
        [{'first': '1st', 'second': '2nd'}, {}],
        [[2, 3], [45, [56, 78], 66]],
        'end'
    ]
    assert flatten_config_list(content) == \
               [34, {'first': '1st', 'second': '2nd'}, {},
                2, 3, 45, 56, 78, 66, 'end']
