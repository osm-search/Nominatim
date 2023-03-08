# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Data class for a single name of a place.
"""
from typing import Optional, Dict, Mapping

class PlaceName:
    """ Each name and address part of a place is encapsulated in an object of
        this class. It saves not only the name proper but also describes the
        kind of name with two properties:

        * `kind` describes the name of the OSM key used without any suffixes
          (i.e. the part after the colon removed)
        * `suffix` contains the suffix of the OSM tag, if any. The suffix
          is the part of the key after the first colon.

        In addition to that, a name may have arbitrary additional attributes.
        How attributes are used, depends on the sanitizers and token analysers.
        The exception is the 'analyzer' attribute. This attribute determines
        which token analysis module will be used to finalize the treatment of
        names.
    """

    def __init__(self, name: str, kind: str, suffix: Optional[str]):
        self.name = name
        self.kind = kind
        self.suffix = suffix
        self.attr: Dict[str, str] = {}


    def __repr__(self) -> str:
        return f"PlaceName(name='{self.name}',kind='{self.kind}',suffix='{self.suffix}')"


    def clone(self, name: Optional[str] = None,
              kind: Optional[str] = None,
              suffix: Optional[str] = None,
              attr: Optional[Mapping[str, str]] = None) -> 'PlaceName':
        """ Create a deep copy of the place name, optionally with the
            given parameters replaced. In the attribute list only the given
            keys are updated. The list is not replaced completely.
            In particular, the function cannot to be used to remove an
            attribute from a place name.
        """
        newobj = PlaceName(name or self.name,
                           kind or self.kind,
                           suffix or self.suffix)

        newobj.attr.update(self.attr)
        if attr:
            newobj.attr.update(attr)

        return newobj


    def set_attr(self, key: str, value: str) -> None:
        """ Add the given property to the name. If the property was already
            set, then the value is overwritten.
        """
        self.attr[key] = value


    def get_attr(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """ Return the given property or the value of 'default' if it
            is not set.
        """
        return self.attr.get(key, default)


    def has_attr(self, key: str) -> bool:
        """ Check if the given attribute is set.
        """
        return key in self.attr
