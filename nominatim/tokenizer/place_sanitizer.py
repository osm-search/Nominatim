# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Handler for cleaning name and address tags in place information before it
is handed to the token analysis.
"""
import importlib

from nominatim.errors import UsageError
from nominatim.tokenizer.sanitizers.config import SanitizerConfig

class PlaceName:
    """ A searchable name for a place together with properties.
        Every name object saves the name proper and two basic properties:
        * 'kind' describes the name of the OSM key used without any suffixes
          (i.e. the part after the colon removed)
        * 'suffix' contains the suffix of the OSM tag, if any. The suffix
          is the part of the key after the first colon.
        In addition to that, the name may have arbitrary additional attributes.
        Which attributes are used, depends on the token analyser.
    """

    def __init__(self, name, kind, suffix):
        self.name = name
        self.kind = kind
        self.suffix = suffix
        self.attr = {}


    def __repr__(self):
        return f"PlaceName(name='{self.name}',kind='{self.kind}',suffix='{self.suffix}')"


    def clone(self, name=None, kind=None, suffix=None, attr=None):
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


    def set_attr(self, key, value):
        """ Add the given property to the name. If the property was already
            set, then the value is overwritten.
        """
        self.attr[key] = value


    def get_attr(self, key, default=None):
        """ Return the given property or the value of 'default' if it
            is not set.
        """
        return self.attr.get(key, default)


    def has_attr(self, key):
        """ Check if the given attribute is set.
        """
        return key in self.attr


class _ProcessInfo:
    """ Container class for information handed into to handler functions.
        The 'names' and 'address' members are mutable. A handler must change
        them by either modifying the lists place or replacing the old content
        with a new list.
    """

    def __init__(self, place):
        self.place = place
        self.names = self._convert_name_dict(place.name)
        self.address = self._convert_name_dict(place.address)


    @staticmethod
    def _convert_name_dict(names):
        """ Convert a dictionary of names into a list of PlaceNames.
            The dictionary key is split into the primary part of the key
            and the suffix (the part after an optional colon).
        """
        out = []

        if names:
            for key, value in names.items():
                parts = key.split(':', 1)
                out.append(PlaceName(value.strip(),
                                     parts[0].strip(),
                                     parts[1].strip() if len(parts) > 1 else None))

        return out


class PlaceSanitizer:
    """ Controller class which applies sanitizer functions on the place
        names and address before they are used by the token analysers.
    """

    def __init__(self, rules):
        self.handlers = []

        if rules:
            for func in rules:
                if 'step' not in func:
                    raise UsageError("Sanitizer rule is missing the 'step' attribute.")
                module_name = 'nominatim.tokenizer.sanitizers.' + func['step'].replace('-', '_')
                handler_module = importlib.import_module(module_name)
                self.handlers.append(handler_module.create(SanitizerConfig(func)))


    def process_names(self, place):
        """ Extract a sanitized list of names and address parts from the
            given place. The function returns a tuple
            (list of names, list of address names)
        """
        obj = _ProcessInfo(place)

        for func in self.handlers:
            func(obj)

        return obj.names, obj.address
