# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Test for loading extra Python modules.
"""
from pathlib import Path
import sys

import pytest

from nominatim.config import Configuration

@pytest.fixture
def test_config(src_dir, tmp_path):
    """ Create a configuration object with project and config directories
        in a temporary directory.
    """
    (tmp_path / 'project').mkdir()
    (tmp_path / 'config').mkdir()
    conf = Configuration(tmp_path / 'project', src_dir / 'settings')
    conf.config_dir = tmp_path / 'config'
    return conf


def test_load_default_module(test_config):
    module = test_config.load_plugin_module('version', 'nominatim')

    assert isinstance(module.NOMINATIM_VERSION, tuple)

def test_load_default_module_with_hyphen(test_config):
    module = test_config.load_plugin_module('place-info', 'nominatim.data')

    assert isinstance(module.PlaceInfo, object)


def test_load_plugin_module(test_config, tmp_path):
    (tmp_path / 'project' / 'testpath').mkdir()
    (tmp_path / 'project' / 'testpath' / 'mymod.py')\
        .write_text("def my_test_function():\n  return 'gjwitlsSG42TG%'")

    module = test_config.load_plugin_module('testpath/mymod.py', 'private.something')

    assert module.my_test_function() == 'gjwitlsSG42TG%'

    # also test reloading module
    (tmp_path / 'project' / 'testpath' / 'mymod.py')\
        .write_text("def my_test_function():\n  return 'hjothjorhj'")

    module = test_config.load_plugin_module('testpath/mymod.py', 'private.something')

    assert module.my_test_function() == 'gjwitlsSG42TG%'


def test_load_external_library_module(test_config, tmp_path, monkeypatch):
    MODULE_NAME = 'foogurenqodr4'
    pythonpath = tmp_path / 'priv-python'
    pythonpath.mkdir()
    (pythonpath / MODULE_NAME).mkdir()
    (pythonpath / MODULE_NAME / '__init__.py').write_text('')
    (pythonpath / MODULE_NAME / 'tester.py')\
        .write_text("def my_test_function():\n  return 'gjwitlsSG42TG%'")

    monkeypatch.syspath_prepend(pythonpath)

    module = test_config.load_plugin_module(f'{MODULE_NAME}.tester', 'private.something')

    assert module.my_test_function() == 'gjwitlsSG42TG%'

    # also test reloading module
    (pythonpath / MODULE_NAME / 'tester.py')\
        .write_text("def my_test_function():\n  return 'dfigjreigj'")

    module = test_config.load_plugin_module(f'{MODULE_NAME}.tester', 'private.something')

    assert module.my_test_function() == 'gjwitlsSG42TG%'

    del sys.modules[f'{MODULE_NAME}.tester']
