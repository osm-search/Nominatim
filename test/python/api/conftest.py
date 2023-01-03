# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper fixtures for API call tests.
"""
from pathlib import Path
import pytest
import time

from nominatim.api import NominatimAPI

@pytest.fixture
def apiobj(temp_db):
    """ Create an asynchronous SQLAlchemy engine for the test DB.
    """
    api = NominatimAPI(Path('/invalid'), {})
    yield api
    api.close()
