# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Module for forward search.
"""
from .geocoder import (ForwardGeocoder as ForwardGeocoder)
from .query import (Phrase as Phrase,
                    PHRASE_ANY as PHRASE_ANY,
                    PHRASE_AMENITY as PHRASE_AMENITY,
                    PHRASE_STREET as PHRASE_STREET,
                    PHRASE_CITY as PHRASE_CITY,
                    PHRASE_COUNTY as PHRASE_COUNTY,
                    PHRASE_STATE as PHRASE_STATE,
                    PHRASE_POSTCODE as PHRASE_POSTCODE,
                    PHRASE_COUNTRY as PHRASE_COUNTRY)
from .query_analyzer_factory import (make_query_analyzer as make_query_analyzer)
