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
