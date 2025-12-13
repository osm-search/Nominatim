# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of the 'freeze' subcommand.
"""
import argparse

from .args import NominatimArgs
from ..tools import freeze


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
        pass  # No options

    def run(self, args: NominatimArgs) -> int:
        freeze.freeze(args.config)
        return 0
