"""
Tests for setting up the website scripts.
"""
from pathlib import Path
import subprocess

import pytest

from nominatim.tools import refresh

@pytest.fixture
def envdir(tmpdir):
    (tmpdir / 'php').mkdir()
    (tmpdir / 'php' / 'website').mkdir()
    return tmpdir


@pytest.fixture
def test_script(envdir):
    def _create_file(code):
        outfile = envdir / 'php' / 'website' / 'reverse-only-search.php'
        outfile.write_text('<?php\n{}\n'.format(code), 'utf-8')

    return _create_file


def run_website_script(envdir, config, conn):
    config.lib_dir.php = envdir / 'php'
    config.project_dir = envdir
    refresh.setup_website(envdir, config, conn)

    proc = subprocess.run(['/usr/bin/env', 'php', '-Cq',
                           envdir / 'search.php'], check=False)

    return proc.returncode


@pytest.mark.parametrize("setting,retval", (('yes', 10), ('no', 20)))
def test_setup_website_check_bool(def_config, monkeypatch, envdir, test_script,
                                  setting, retval, temp_db_conn):
    monkeypatch.setenv('NOMINATIM_CORS_NOACCESSCONTROL', setting)

    test_script('exit(CONST_NoAccessControl ? 10 : 20);')

    assert run_website_script(envdir, def_config, temp_db_conn) == retval


@pytest.mark.parametrize("setting", (0, 10, 99067))
def test_setup_website_check_int(def_config, monkeypatch, envdir, test_script, setting,
                                 temp_db_conn):
    monkeypatch.setenv('NOMINATIM_LOOKUP_MAX_COUNT', str(setting))

    test_script('exit(CONST_Places_Max_ID_count == {} ? 10 : 20);'.format(setting))

    assert run_website_script(envdir, def_config, temp_db_conn) == 10


def test_setup_website_check_empty_str(def_config, monkeypatch, envdir, test_script,
                                       temp_db_conn):
    monkeypatch.setenv('NOMINATIM_DEFAULT_LANGUAGE', '')

    test_script('exit(CONST_Default_Language === false ? 10 : 20);')

    assert run_website_script(envdir, def_config, temp_db_conn) == 10


def test_setup_website_check_str(def_config, monkeypatch, envdir, test_script,
                                 temp_db_conn):
    monkeypatch.setenv('NOMINATIM_DEFAULT_LANGUAGE', 'ffde 2')

    test_script('exit(CONST_Default_Language === "ffde 2" ? 10 : 20);')

    assert run_website_script(envdir, def_config, temp_db_conn) == 10


