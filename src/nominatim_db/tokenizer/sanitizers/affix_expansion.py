# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Sanitizer which contracts or expands names based on the presence of
prefix and suffix tags.

The sanitizer can handle three kinds of prefix/suffix tags: The most simple
one is of the form `<kind>:<prefix-tag>`. It is presumed to refer to the
name tag `<kind>`. For example, the `name:prefix` tag will be recognised
as a prefix tag and paired with `name`, while `alt_name:suffix` is paired
with `alt_name`. For name tags that are of the form `<kind>:<suffix>`,
meaning that they have another suffix, for example a language suffix, to
notations for the prefix/suffix tag are accepted: `<kind>:<prefix-tag>:<suffix>`
and `<kind>:<suffix>:<prefix-tag>`. That means for a German name tag `name:de`
both `name:prefix:de` and `name:de:prefix` will work.

Arguments:
    prefix-tags: Specifies how to identify tags containing name prefixes.
                 This is a single string or a list of suffixes which identify
                 prefix names.
                 (default: prefix)
    prefix-tags: Specifies how to identify tags containing name suffixes.
                 This is a single string or a list of suffixes which identify
                 suffix names.
                 (default: suffix)
    mode: Defines how names are handled. _full-name_ means to only keep the
          expanded version of the name with prefix/suffix attached. _short-name_
          means to only keep the contracted version without prefix/suffix.
          Prefixes and suffixes are still added as partial terms to the index
          and are thus still searchable. _all-variants_ adds the expanded and
          contracted version of the name. _add_expanded_ adds the expanded
          version if it doesn't exist yet. If name contains the contracted
          name, then it will not be removed. _add_contracted_ add the contracted
          version if it doesn't exist yet. Any expanded version of the name
          that already exists will be kept.
"""
from typing import Optional, Sequence
from collections import defaultdict
from dataclasses import dataclass

from ...data.place_name import PlaceName, PlaceNames
from .base import ProcessInfo, SanitizerFunc
from .config import SanitizerConfig


class Mode:
    FULL_NAME = 1
    """ Only keep the name with prefix/suffix.
    """
    SHORT_NAME = 2
    """ Only keep the name without prefix/suffix. Add prefix/suffix as a partial.
    """
    ALL_VARIANTS = 3
    """ Add both variants with and without prefix/suffix as names.
    """
    ADD_EXPANDED = 5
    """ Add the variant with prefix/suffix if not already present.
    """
    ADD_CONTRACTED = 6
    """ Add the variant without prefix/suffix if not already present.
    """


StemTuple = tuple[str, Optional[str]]


@dataclass
class _AffixCollector:
    prefix: Optional[str] = None
    suffix: Optional[str] = None


class _AffixSanitizer:

    def __init__(self, config: SanitizerConfig) -> None:
        self.prefix_tags = config.get_string_list('prefix-tags', ['prefix'])
        self.suffix_tags = config.get_string_list('suffix-tags', ['suffix'])
        self.mode = config.get_choice('mode', Mode, Mode.ALL_VARIANTS)

    def __call__(self, obj: ProcessInfo) -> None:
        if not obj.names:
            return

        stem_names: PlaceNames = []
        affixes: dict[StemTuple, _AffixCollector] = defaultdict(_AffixCollector)
        for item in obj.names:
            if (stem := self.find_stem_kind(item, self.prefix_tags)) is not None:
                affixes[stem].prefix = item.name
            elif (stem := self.find_stem_kind(item, self.suffix_tags)) is not None:
                affixes[stem].suffix = item.name
            else:
                stem_names.append(item)

        if affixes:
            outnames: PlaceNames = []
            for item in stem_names:
                for stem, aff in affixes.items():
                    if item.kind == stem[0] and item.suffix == stem[1]:
                        self.add_names(outnames, item, aff)
                        break
                else:
                    outnames.append(item)

            obj.names = outnames

    def find_stem_kind(self, item: PlaceName, tags: Sequence[str]) -> Optional[StemTuple]:
        if item.suffix and tags:
            if item.suffix in tags:
                return item.kind, None

            parts = item.suffix.split(':', 1)
            if len(parts) == 2:
                if parts[0] in tags:
                    return item.kind, parts[1]
                if parts[1] in tags:
                    return item.kind, parts[0]
                parts = item.suffix.rsplit(':', 1)
                if parts[1] in tags:
                    return item.kind, parts[0]

        return None

    def add_names(self, outnames: PlaceNames, src: PlaceName,
                  affix: _AffixCollector) -> None:
        fn = src.name
        sn = src.name
        if affix.prefix is not None:
            prefix = affix.prefix + ' '
            if fn.startswith(prefix):
                sn = sn[len(prefix):]
            else:
                fn = prefix + fn
        if affix.suffix is not None:
            suffix = ' ' + affix.suffix
            if fn.endswith(suffix):
                sn = sn[:-len(suffix)]
            else:
                fn = fn + suffix

        if self.mode & 1:
            outnames.append(src.clone(name=fn))
            if self.mode & 4 and src.name != fn:
                outnames.append(src)
        if self.mode & 2:
            outnames.append(src.clone(name=sn))
            if self.mode & 4 and src.name != sn:
                outnames.append(src)
            elif self.mode == 2:
                if affix.prefix is not None:
                    outnames.append(PlaceName(affix.prefix, 'prefix', None,
                                              {'partial': 'yes'}))
                if affix.suffix is not None:
                    outnames.append(PlaceName(affix.suffix, 'suffix', None,
                                              {'partial': 'yes'}))


def create(config: SanitizerConfig) -> SanitizerFunc:
    """ Create the affix handler.
    """
    return _AffixSanitizer(config)
