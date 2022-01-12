# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for creating a tokenizer or initialising the right one for an
existing database.

A tokenizer is something that is bound to the lifetime of a database. It
can be choosen and configured before the intial import but then needs to
be used consistently when querying and updating the database.

This module provides the functions to create and configure a new tokenizer
as well as instanciating the appropriate tokenizer for updating an existing
database.

A tokenizer usually also includes PHP code for querying. The appropriate PHP
normalizer module is installed, when the tokenizer is created.
"""
import logging
import importlib
from pathlib import Path

from ..errors import UsageError
from ..db import properties
from ..db.connection import connect

LOG = logging.getLogger()

def _import_tokenizer(name):
    """ Load the tokenizer.py module from project directory.
    """
    src_file = Path(__file__).parent / (name + '_tokenizer.py')
    if not src_file.is_file():
        LOG.fatal("No tokenizer named '%s' available. "
                  "Check the setting of NOMINATIM_TOKENIZER.", name)
        raise UsageError('Tokenizer not found')

    return importlib.import_module('nominatim.tokenizer.' + name + '_tokenizer')


def create_tokenizer(config, init_db=True, module_name=None):
    """ Create a new tokenizer as defined by the given configuration.

        The tokenizer data and code is copied into the 'tokenizer' directory
        of the project directory and the tokenizer loaded from its new location.
    """
    if module_name is None:
        module_name = config.TOKENIZER

    # Create the directory for the tokenizer data
    basedir = config.project_dir / 'tokenizer'
    if not basedir.exists():
        basedir.mkdir()
    elif not basedir.is_dir():
        LOG.fatal("Tokenizer directory '%s' cannot be created.", basedir)
        raise UsageError("Tokenizer setup failed.")

    # Import and initialize the tokenizer.
    tokenizer_module = _import_tokenizer(module_name)

    tokenizer = tokenizer_module.create(config.get_libpq_dsn(), basedir)
    tokenizer.init_new_db(config, init_db=init_db)

    with connect(config.get_libpq_dsn()) as conn:
        properties.set_property(conn, 'tokenizer', module_name)

    return tokenizer


def get_tokenizer_for_db(config):
    """ Instantiate a tokenizer for an existing database.

        The function looks up the appropriate tokenizer in the database
        and initialises it.
    """
    basedir = config.project_dir / 'tokenizer'
    if not basedir.is_dir():
        LOG.fatal("Cannot find tokenizer data in '%s'.", basedir)
        raise UsageError('Cannot initialize tokenizer.')

    with connect(config.get_libpq_dsn()) as conn:
        name = properties.get_property(conn, 'tokenizer')

    if name is None:
        LOG.fatal("Tokenizer was not set up properly. Database property missing.")
        raise UsageError('Cannot initialize tokenizer.')

    tokenizer_module = _import_tokenizer(name)

    tokenizer = tokenizer_module.create(config.get_libpq_dsn(), basedir)
    tokenizer.init_from_project(config)

    return tokenizer
