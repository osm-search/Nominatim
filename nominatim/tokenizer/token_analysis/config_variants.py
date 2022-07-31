# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Parser for configuration for variants.
"""
from typing import Any, Iterator, Tuple, List, Optional, Set, NamedTuple
from collections import defaultdict
import itertools
import re

from nominatim.config import flatten_config_list
from nominatim.errors import UsageError

class ICUVariant(NamedTuple):
    """ A single replacement rule for variant creation.
    """
    source: str
    replacement: str


def get_variant_config(in_rules: Any,
                       normalizer: Any) -> Tuple[List[Tuple[str, List[str]]], str]:
    """ Convert the variant definition from the configuration into
        replacement sets.

        Returns a tuple containing the replacement set and the list of characters
        used in the replacements.
    """
    immediate = defaultdict(list)
    chars: Set[str] = set()

    if in_rules:
        vset: Set[ICUVariant] = set()
        rules = flatten_config_list(in_rules, 'variants')

        vmaker = _VariantMaker(normalizer)

        for section in rules:
            for rule in (section.get('words') or []):
                vset.update(vmaker.compute(rule))

        # Intermediate reorder by source. Also compute required character set.
        for variant in vset:
            if variant.source[-1] == ' ' and variant.replacement[-1] == ' ':
                replstr = variant.replacement[:-1]
            else:
                replstr = variant.replacement
            immediate[variant.source].append(replstr)
            chars.update(variant.source)

    return list(immediate.items()), ''.join(chars)


class _VariantMaker:
    """ Generator for all necessary ICUVariants from a single variant rule.

        All text in rules is normalized to make sure the variants match later.
    """

    def __init__(self, normalizer: Any) -> None:
        self.norm = normalizer


    def compute(self, rule: Any) -> Iterator[ICUVariant]:
        """ Generator for all ICUVariant tuples from a single variant rule.
        """
        parts = re.split(r'(\|)?([=-])>', rule)
        if len(parts) != 4:
            raise UsageError(f"Syntax error in variant rule: {rule}")

        decompose = parts[1] is None
        src_terms = [self._parse_variant_word(t) for t in parts[0].split(',')]
        repl_terms = (self.norm.transliterate(t).strip() for t in parts[3].split(','))

        # If the source should be kept, add a 1:1 replacement
        if parts[2] == '-':
            for src in src_terms:
                if src:
                    for froms, tos in _create_variants(*src, src[0], decompose):
                        yield ICUVariant(froms, tos)

        for src, repl in itertools.product(src_terms, repl_terms):
            if src and repl:
                for froms, tos in _create_variants(*src, repl, decompose):
                    yield ICUVariant(froms, tos)


    def _parse_variant_word(self, name: str) -> Optional[Tuple[str, str, str]]:
        name = name.strip()
        match = re.fullmatch(r'([~^]?)([^~$^]*)([~$]?)', name)
        if match is None or (match.group(1) == '~' and match.group(3) == '~'):
            raise UsageError(f"Invalid variant word descriptor '{name}'")
        norm_name = self.norm.transliterate(match.group(2)).strip()
        if not norm_name:
            return None

        return norm_name, match.group(1), match.group(3)


_FLAG_MATCH = {'^': '^ ',
               '$': ' ^',
               '': ' '}


def _create_variants(src: str, preflag: str, postflag: str,
                     repl: str, decompose: bool) -> Iterator[Tuple[str, str]]:
    if preflag == '~':
        postfix = _FLAG_MATCH[postflag]
        # suffix decomposition
        src = src + postfix
        repl = repl + postfix

        yield src, repl
        yield ' ' + src, ' ' + repl

        if decompose:
            yield src, ' ' + repl
            yield ' ' + src, repl
    elif postflag == '~':
        # prefix decomposition
        prefix = _FLAG_MATCH[preflag]
        src = prefix + src
        repl = prefix + repl

        yield src, repl
        yield src + ' ', repl + ' '

        if decompose:
            yield src, repl + ' '
            yield src + ' ', repl
    else:
        prefix = _FLAG_MATCH[preflag]
        postfix = _FLAG_MATCH[postflag]

        yield prefix + src + postfix, prefix + repl + postfix
