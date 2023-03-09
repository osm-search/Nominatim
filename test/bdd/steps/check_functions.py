# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Collection of assertion functions used for the steps.
"""
import json

class Almost:
    """ Compares a float value with a certain jitter.
    """
    def __init__(self, value, offset=0.00001):
        self.value = value
        self.offset = offset

    def __eq__(self, other):
        return abs(other - self.value) < self.offset

class Bbox:
    """ Comparator for bounding boxes.
    """
    def __init__(self, bbox_string):
        self.coord = [float(x) for x in bbox_string.split(',')]

    def __contains__(self, item):
        if isinstance(item, str):
            item = item.split(',')
        item = list(map(float, item))

        if len(item) == 2:
            return self.coord[0] <= item[0] <= self.coord[2] \
                   and self.coord[1] <= item[1] <= self.coord[3]

        if len(item) == 4:
            return item[0] >= self.coord[0] and item[1] <= self.coord[1] \
                   and item[2] >= self.coord[2] and item[3] <= self.coord[3]

        raise ValueError("Not a coordinate or bbox.")

    def __str__(self):
        return str(self.coord)



def check_for_attributes(obj, attrs, presence='present'):
    """ Check that the object has the given attributes. 'attrs' is a
        string with a comma-separated list of attributes. If 'presence'
        is set to 'absent' then the function checks that the attributes do
        not exist for the object
    """
    def _dump_json():
        return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False)

    for attr in attrs.split(','):
        attr = attr.strip()
        if presence == 'absent':
            assert attr not in obj, \
                   f"Unexpected attribute {attr}. Full response:\n{_dump_json()}"
        else:
            assert attr in obj, \
                   f"No attribute '{attr}'. Full response:\n{_dump_json()}"

