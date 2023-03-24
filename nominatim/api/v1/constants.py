# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Constants shared by all formats.
"""

import nominatim.api as napi

# pylint: disable=line-too-long
OSM_ATTRIBUTION = 'Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright'

OSM_TYPE_NAME = {
    'N': 'node',
    'W': 'way',
    'R': 'relation'
}

NODE_EXTENT = [25, 25, 25, 25,
               7,
               2.6, 2.6, 2.0, 1.0, 1.0,
               0.7, 0.7, 0.7,
               0.16, 0.16, 0.16, 0.16,
               0.04, 0.04,
               0.02, 0.02,
               0.01, 0.01, 0.01, 0.01, 0.01,
               0.015, 0.015, 0.015, 0.015,
               0.005]


def bbox_from_result(result: napi.ReverseResult) -> napi.Bbox:
    """ Compute a bounding box for the result. For ways and relations
        a given boundingbox is used. For all other object, a box is computed
        around the centroid according to dimensions dereived from the
        search rank.
    """
    if (result.osm_object and result.osm_object[0] == 'N') or result.bbox is None:
        return napi.Bbox.from_point(result.centroid, NODE_EXTENT[result.rank_search])

    return result.bbox
