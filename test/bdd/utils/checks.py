# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions to compare expected values.
"""
import json
import re

COMPARATOR_TERMS = {
    'exactly': lambda exp, act: exp == act,
    'more than': lambda exp, act: act > exp,
    'less than': lambda exp, act: act < exp,
}


def _pretty(obj):
    return json.dumps(obj, sort_keys=True, indent=2)


def within_box(value, expect):
    coord = [float(x) for x in expect.split(',')]

    if isinstance(value, str):
        value = value.split(',')
    value = list(map(float, value))

    if len(value) == 2:
        return coord[0] <= value[0] <= coord[2] \
               and coord[1] <= value[1] <= coord[3]

    if len(value) == 4:
        return value[0] >= coord[0] and value[1] <= coord[1] \
               and value[2] >= coord[2] and value[3] <= coord[3]

    raise ValueError("Not a coordinate or bbox.")


COMPARISON_FUNCS = {
    None: lambda val, exp: str(val) == exp,
    'i': lambda val, exp: str(val).lower() == exp.lower(),
    'fm': lambda val, exp: re.fullmatch(exp, val) is not None,
    'in_box': within_box
}

OSM_TYPE = {'node': 'n', 'way': 'w', 'relation': 'r'}


class ResultAttr:
    """ Returns the given attribute as a string.

        The key parameter determines how the value is formatted before
        returning. To refer to sub attributes, use '+' to add more keys
        (e.g. 'name+ref' will access obj['name']['ref']). A '!' introduces
        a formatting suffix. If no suffix is given, the value will be
        converted using the str() function.

        Available formatters:

        !:... - use a formatting expression according to Python Mini Format Spec
        !i    - make case-insensitive comparison
        !fm   - consider comparison string a regular expression and match full value
    """

    def __init__(self, obj, key):
        self.obj = obj
        if '!' in key:
            self.key, self.fmt = key.rsplit('!', 1)
        else:
            self.key = key
            self.fmt = None

        if self.key == 'object':
            assert 'osm_id' in obj
            assert 'osm_type' in obj
            self.subobj = OSM_TYPE[obj['osm_type']] + str(obj['osm_id'])
            self.fmt = 'i'
        else:
            done = ''
            self.subobj = self.obj
            for sub in self.key.split('+'):
                done += f"[{sub}]"
                assert sub in self.subobj, \
                    f"Missing attribute {done}. Full object:\n{_pretty(self.obj)}"
                self.subobj = self.subobj[sub]

    def __eq__(self, other):
        if not isinstance(other, str):
            raise NotImplementedError()

        # work around bad quoting by pytest-bdd
        other = other.replace(r'\\', '\\')

        if self.fmt in COMPARISON_FUNCS:
            return COMPARISON_FUNCS[self.fmt](self.subobj, other)

        if self.fmt.startswith(':'):
            return other == f"{{{self.fmt}}}".format(self.subobj)

        raise RuntimeError(f"Unknown format string '{self.fmt}'.")

    def __repr__(self):
        k = self.key.replace('+', '][')
        if self.fmt:
            k += '!' + self.fmt
        return f"result[{k}]({self.subobj})"
