# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of the 'freeze' subcommand.
"""
import argparse

from nominatim.db.connection import connect
from nominatim.clicmd.args import NominatimArgs

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to avoid eventually unused imports.
# pylint: disable=E0012,C0415

class SetupFreeze:
    """\
    Make database read-only.

    About half of data in the Nominatim database is kept only to be able to
    keep the data up-to-date with new changes made in OpenStreetMap. This
    command drops all this data and only keeps the part needed for geocoding
    itself.

    This command has the same effect as the `--no-updates` option for imports.
    """

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        pass # No options


    def run(self, args: NominatimArgs) -> int:
        from ..tools import freeze

        with connect(args.config.get_libpq_dsn()) as conn:
            freeze.drop_update_tables(conn)
        freeze.drop_flatnode_file(args.config.get_path('FLATNODE_FILE'))

        return 0
