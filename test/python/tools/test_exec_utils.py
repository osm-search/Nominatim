# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for tools.exec_utils module.
"""
from pathlib import Path
import subprocess

import pytest

from nominatim.config import Configuration
import nominatim.tools.exec_utils as exec_utils
import nominatim.paths

class TestRunLegacyScript:

    @pytest.fixture(autouse=True)
    def setup_nominatim_env(self, tmp_path, monkeypatch):
        tmp_phplib_dir = tmp_path / 'phplib'
        tmp_phplib_dir.mkdir()
        (tmp_phplib_dir / 'admin').mkdir()

        monkeypatch.setattr(nominatim.paths, 'PHPLIB_DIR', tmp_phplib_dir)

        self.phplib_dir = tmp_phplib_dir
        self.config = Configuration(tmp_path)
        self.config.set_libdirs(module='.', osm2pgsql='default_osm2pgsql',
                                php=tmp_phplib_dir)


    def mk_script(self, code):
        codefile = self.phplib_dir / 'admin' / 't.php'
        codefile.write_text('<?php\n' + code + '\n')

        return 't.php'


    @pytest.mark.parametrize("return_code", (0, 1, 15, 255))
    def test_run_legacy_return_exit_code(self, return_code):
        fname = self.mk_script('exit({});'.format(return_code))
        assert return_code == \
                 exec_utils.run_legacy_script(fname, config=self.config)


    def test_run_legacy_return_throw_on_fail(self):
        fname = self.mk_script('exit(11);')
        with pytest.raises(subprocess.CalledProcessError):
            exec_utils.run_legacy_script(fname, config=self.config,
                                         throw_on_fail=True)


    def test_run_legacy_return_dont_throw_on_success(self):
        fname = self.mk_script('exit(0);')
        assert exec_utils.run_legacy_script(fname, config=self.config,
                                            throw_on_fail=True) == 0

    def test_run_legacy_use_given_module_path(self):
        fname = self.mk_script("exit($_SERVER['NOMINATIM_DATABASE_MODULE_PATH'] == '' ? 0 : 23);")

        assert exec_utils.run_legacy_script(fname, config=self.config) == 0


    def test_run_legacy_do_not_overwrite_module_path(self, monkeypatch):
        monkeypatch.setenv('NOMINATIM_DATABASE_MODULE_PATH', 'other')
        fname = self.mk_script(
            "exit($_SERVER['NOMINATIM_DATABASE_MODULE_PATH'] == 'other' ? 0 : 1);")

        assert exec_utils.run_legacy_script(fname, config=self.config) == 0


    def test_run_legacy_default_osm2pgsql_binary(self, monkeypatch):
        fname = self.mk_script("exit($_SERVER['NOMINATIM_OSM2PGSQL_BINARY'] == 'default_osm2pgsql' ? 0 : 23);")

        assert exec_utils.run_legacy_script(fname, config=self.config) == 0


    def test_run_legacy_override_osm2pgsql_binary(self, monkeypatch):
        monkeypatch.setenv('NOMINATIM_OSM2PGSQL_BINARY', 'somethingelse')

        fname = self.mk_script("exit($_SERVER['NOMINATIM_OSM2PGSQL_BINARY'] == 'somethingelse' ? 0 : 23);")

        assert exec_utils.run_legacy_script(fname, config=self.config) == 0


class TestRunApiScript:

    @staticmethod
    @pytest.fixture(autouse=True)
    def setup_project_dir(tmp_path):
        webdir = tmp_path / 'website'
        webdir.mkdir()
        (webdir / 'test.php').write_text("<?php\necho 'OK\n';")


    @staticmethod
    def test_run_api(tmp_path):
        assert exec_utils.run_api_script('test', tmp_path) == 0

    @staticmethod
    def test_run_api_execution_error(tmp_path):
        assert exec_utils.run_api_script('badname', tmp_path) != 0

    @staticmethod
    def test_run_api_with_extra_env(tmp_path):
        extra_env = dict(SCRIPT_FILENAME=str(tmp_path / 'website' / 'test.php'))
        assert exec_utils.run_api_script('badname', tmp_path, extra_env=extra_env) == 0

    @staticmethod
    def test_custom_phpcgi(tmp_path, capfd):
        assert exec_utils.run_api_script('test', tmp_path, phpcgi_bin='env',
                                         params={'q' : 'Berlin'}) == 0
        captured = capfd.readouterr()

        assert '?q=Berlin' in captured.out

    @staticmethod
    def test_fail_on_error_output(tmp_path):
        # Starting PHP 8 the PHP CLI no longer has STDERR defined as constant
        php = """
        <?php
        if(!defined('STDERR')) define('STDERR', fopen('php://stderr', 'wb'));
        fwrite(STDERR, 'WARNING'.PHP_EOL);
        """
        (tmp_path / 'website' / 'bad.php').write_text(php)

        assert exec_utils.run_api_script('bad', tmp_path) == 1

### run_osm2pgsql

def test_run_osm2pgsql(osm2pgsql_options):
    osm2pgsql_options['append'] = False
    osm2pgsql_options['import_file'] = 'foo.bar'
    osm2pgsql_options['tablespaces']['slim_data'] = 'extra'
    exec_utils.run_osm2pgsql(osm2pgsql_options)


def test_run_osm2pgsql_disable_jit(osm2pgsql_options):
    osm2pgsql_options['append'] = True
    osm2pgsql_options['import_file'] = 'foo.bar'
    osm2pgsql_options['disable_jit'] = True
    exec_utils.run_osm2pgsql(osm2pgsql_options)
