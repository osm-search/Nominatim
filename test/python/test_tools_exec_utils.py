"""
Tests for tools.exec_utils module.
"""
from pathlib import Path
import subprocess

import pytest

import nominatim.tools.exec_utils as exec_utils

class TestRunLegacyScript:

    @pytest.fixture(autouse=True)
    def setup_nominatim_env(self, tmp_path, def_config):
        tmp_phplib_dir = tmp_path / 'phplib'
        tmp_phplib_dir.mkdir()
        (tmp_phplib_dir / 'admin').mkdir()

        class _NominatimEnv:
            config = def_config
            phplib_dir = tmp_phplib_dir
            data_dir = Path('data')
            project_dir = Path('.')
            sqllib_dir = Path('lib-sql')
            config_dir = Path('settings')
            module_dir = 'module'
            osm2pgsql_path = 'osm2pgsql'

        self.testenv = _NominatimEnv


    def mk_script(self, code):
        codefile = self.testenv.phplib_dir / 'admin' / 't.php'
        codefile.write_text('<?php\n' + code + '\n')

        return 't.php'


    @pytest.mark.parametrize("return_code", (0, 1, 15, 255))
    def test_run_legacy_return_exit_code(self, return_code):
        fname = self.mk_script('exit({});'.format(return_code))
        assert return_code == \
                 exec_utils.run_legacy_script(fname, nominatim_env=self.testenv)


    def test_run_legacy_return_throw_on_fail(self):
        fname = self.mk_script('exit(11);')
        with pytest.raises(subprocess.CalledProcessError):
            exec_utils.run_legacy_script(fname, nominatim_env=self.testenv,
                                         throw_on_fail=True)


    def test_run_legacy_return_dont_throw_on_success(self):
        fname = self.mk_script('exit(0);')
        assert 0 == exec_utils.run_legacy_script(fname, nominatim_env=self.testenv,
                                                 throw_on_fail=True)

    def test_run_legacy_use_given_module_path(self):
        fname = self.mk_script("exit($_SERVER['NOMINATIM_DATABASE_MODULE_PATH'] == '' ? 0 : 23);")

        assert 0 == exec_utils.run_legacy_script(fname, nominatim_env=self.testenv)


    def test_run_legacy_do_not_overwrite_module_path(self, monkeypatch):
        monkeypatch.setenv('NOMINATIM_DATABASE_MODULE_PATH', 'other')
        fname = self.mk_script("exit($_SERVER['NOMINATIM_DATABASE_MODULE_PATH'] == 'other' ? 0 : 1);")

        assert 0 == exec_utils.run_legacy_script(fname, nominatim_env=self.testenv)


class TestRunApiScript:

    @pytest.fixture(autouse=True)
    def setup_project_dir(self, tmp_path):
        webdir = tmp_path / 'website'
        webdir.mkdir()
        (webdir / 'test.php').write_text("<?php\necho 'OK\n';")


    def test_run_api(self, tmp_path):
        assert 0 == exec_utils.run_api_script('test', tmp_path)

    def test_run_api_execution_error(self, tmp_path):
        assert 0 != exec_utils.run_api_script('badname', tmp_path)

    def test_run_api_with_extra_env(self, tmp_path):
        extra_env = dict(SCRIPT_FILENAME=str(tmp_path / 'website' / 'test.php'))
        assert 0 == exec_utils.run_api_script('badname', tmp_path,
                                              extra_env=extra_env)


### run_osm2pgsql

def test_run_osm2pgsql(osm2pgsql_options):
    osm2pgsql_options['append'] = False
    osm2pgsql_options['import_file'] = 'foo.bar'
    osm2pgsql_options['tablespaces']['osm_data'] = 'extra'
    exec_utils.run_osm2pgsql(osm2pgsql_options)


def test_run_osm2pgsql_disable_jit(osm2pgsql_options):
    osm2pgsql_options['append'] = True
    osm2pgsql_options['import_file'] = 'foo.bar'
    osm2pgsql_options['disable_jit'] = True
    exec_utils.run_osm2pgsql(osm2pgsql_options)
