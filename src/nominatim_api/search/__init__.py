# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Module for forward search.
"""
# pylint: disable=useless-import-alias

from .geocoder import (ForwardGeocoder as ForwardGeocoder)
from .query import (Phrase as Phrase,
                    PhraseType as PhraseType)
from .query_analyzer_factory import (make_query_analyzer as make_query_analyzer)
