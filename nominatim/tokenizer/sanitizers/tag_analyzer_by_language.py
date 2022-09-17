# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
This sanitizer sets the `analyzer` property depending on the
language of the tag. The language is taken from the suffix of the name.
If a name already has an analyzer tagged, then this is kept.

Arguments:

    filter-kind: Restrict the names the sanitizer should be applied to
                 to the given tags. The parameter expects a list of
                 regular expressions which are matched against 'kind'.
                 Note that a match against the full string is expected.
    whitelist: Restrict the set of languages that should be tagged.
               Expects a list of acceptable suffixes. When unset,
               all 2- and 3-letter lower-case codes are accepted.
    use-defaults:  Configure what happens when the name has no suffix.
                   When set to 'all', a variant is created for
                   each of the default languages in the country
                   the feature is in. When set to 'mono', a variant is
                   only created, when exactly one language is spoken
                   in the country. The default is to do nothing with
                   the default languages of a country.
    mode: Define how the variants are created and may be 'replace' or
          'append'. When set to 'append' the original name (without
          any analyzer tagged) is retained. (default: replace)

"""
from typing import Callable, Dict, Optional, List

from nominatim.data import country_info
from nominatim.tokenizer.sanitizers.base import ProcessInfo
from nominatim.tokenizer.sanitizers.config import SanitizerConfig

class _AnalyzerByLanguage:
    """ Processor for tagging the language of names in a place.
    """

    def __init__(self, config: SanitizerConfig) -> None:
        self.filter_kind = config.get_filter_kind()
        self.replace = config.get('mode', 'replace') != 'append'
        self.whitelist = config.get('whitelist')

        self._compute_default_languages(config.get('use-defaults', 'no'))


    def _compute_default_languages(self, use_defaults: str) -> None:
        self.deflangs: Dict[Optional[str], List[str]] = {}

        if use_defaults in ('mono', 'all'):
            for ccode, clangs in country_info.iterate('languages'):
                if len(clangs) == 1 or use_defaults == 'all':
                    if self.whitelist:
                        self.deflangs[ccode] = [l for l in clangs if l in self.whitelist]
                    else:
                        self.deflangs[ccode] = clangs


    def _suffix_matches(self, suffix: str) -> bool:
        if self.whitelist is None:
            return len(suffix) in (2, 3) and suffix.islower()

        return suffix in self.whitelist


    def __call__(self, obj: ProcessInfo) -> None:
        if not obj.names:
            return

        more_names = []

        for name in (n for n in obj.names
                     if not n.has_attr('analyzer') and self.filter_kind(n.kind)):
            if name.suffix:
                langs = [name.suffix] if self._suffix_matches(name.suffix) else None
            else:
                langs = self.deflangs.get(obj.place.country_code)


            if langs:
                if self.replace:
                    name.set_attr('analyzer', langs[0])
                else:
                    more_names.append(name.clone(attr={'analyzer': langs[0]}))

                more_names.extend(name.clone(attr={'analyzer': l}) for l in langs[1:])

        obj.names.extend(more_names)


def create(config: SanitizerConfig) -> Callable[[ProcessInfo], None]:
    """ Create a function that sets the analyzer property depending on the
        language of the tag.
    """
    return _AnalyzerByLanguage(config)
