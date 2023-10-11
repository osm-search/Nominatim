# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Exporting a Nominatim database to SQlite.
"""
from typing import Set
from pathlib import Path

import sqlalchemy as sa

import nominatim.api as napi

async def convert(project_dir: Path, outfile: Path, options: Set[str]) -> None:
    """ Export an existing database to sqlite. The resulting database
        will be usable against the Python frontend of Nominatim.
    """
    api = napi.NominatimAPIAsync(project_dir)

    try:
        outapi = napi.NominatimAPIAsync(project_dir,
                                        {'NOMINATIM_DATABASE_DSN': f"sqlite:dbname={outfile}"})

        async with api.begin() as inconn, outapi.begin() as outconn:
            pass
    finally:
        await api.close()
