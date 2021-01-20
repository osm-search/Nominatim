"""
Tests for tools.exec_utils module.
"""
from pathlib import Path
import subprocess
import tempfile

import pytest

from nominatim.config import Configuration
import nominatim.tools.exec_utils as exec_utils

@pytest.fixture
def tmp_phplib_dir():
    with tempfile.TemporaryDirectory() as phpdir:
        (Path(phpdir) / 'admin').mkdir()

        yield Path(phpdir)

@pytest.fixture
def nominatim_env(tmp_phplib_dir):
    class _NominatimEnv:
        config = Configuration(None, Path(__file__) / '..' / '..' / '..' / 'settings')
        phplib_dir = tmp_phplib_dir
        data_dir = Path('data')
        project_dir = Path('.')
        module_dir = 'module'
        osm2pgsql_path = 'osm2pgsql'

    return _NominatimEnv

@pytest.fixture
def test_script(nominatim_env):
    def _create_file(code):
        with (nominatim_env.phplib_dir / 'admin' / 't.php').open(mode='w') as fd:
            fd.write('<?php\n')
            fd.write(code + '\n')

        return 't.php'

    return _create_file

@pytest.fixture(params=[0, 1, 15, 255])
def return_code(request):
    return request.param

### run_legacy_script

def test_run_legacy_return_exit_code(nominatim_env, test_script, return_code):
    fname = test_script('exit({});'.format(return_code))
    assert return_code == exec_utils.run_legacy_script(fname,
                                                       nominatim_env=nominatim_env)


def test_run_legacy_return_throw_on_fail(nominatim_env, test_script):
    fname = test_script('exit(11);')
    with pytest.raises(subprocess.CalledProcessError):
        exec_utils.run_legacy_script(fname, nominatim_env=nominatim_env,
                                     throw_on_fail=True)


def test_run_legacy_return_dont_throw_on_success(nominatim_env, test_script):
    fname = test_script('exit(0);')
    assert 0 == exec_utils.run_legacy_script(fname, nominatim_env=nominatim_env,
                                             throw_on_fail=True)

def test_run_legacy_use_given__module_path(nominatim_env, test_script):
    fname = test_script("exit($_SERVER['NOMINATIM_DATABASE_MODULE_PATH'] == 'module' ? 0 : 23);")

    assert 0 == exec_utils.run_legacy_script(fname, nominatim_env=nominatim_env)


def test_run_legacy_do_not_overwrite_module_path(nominatim_env, test_script, monkeypatch):
    monkeypatch.setenv('NOMINATIM_DATABASE_MODULE_PATH', 'other')
    fname = test_script("exit($_SERVER['NOMINATIM_DATABASE_MODULE_PATH'] == 'other' ? 0 : 1);")

    assert 0 == exec_utils.run_legacy_script(fname, nominatim_env=nominatim_env)

### run_api_script

@pytest.fixture
def tmp_project_dir():
    with tempfile.TemporaryDirectory() as tempd:
        project_dir = Path(tempd)
        webdir = project_dir / 'website'
        webdir.mkdir()

        with (webdir / 'test.php').open(mode='w') as fd:
            fd.write("<?php\necho 'OK\n';")

        yield project_dir

def test_run_api(tmp_project_dir):
    assert 0 == exec_utils.run_api_script('test', tmp_project_dir)

def test_run_api_execution_error(tmp_project_dir):
    assert 0 != exec_utils.run_api_script('badname', tmp_project_dir)

def test_run_api_with_extra_env(tmp_project_dir):
    extra_env = dict(SCRIPT_FILENAME=str(tmp_project_dir / 'website' / 'test.php'))
    assert 0 == exec_utils.run_api_script('badname', tmp_project_dir,
                                          extra_env=extra_env)
