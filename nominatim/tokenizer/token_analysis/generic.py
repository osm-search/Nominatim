# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Generic processor for names that creates abbreviation variants.
"""
from collections import defaultdict, namedtuple
import itertools
import re

from icu import Transliterator
import datrie

from nominatim.config import flatten_config_list
from nominatim.errors import UsageError

### Configuration section

ICUVariant = namedtuple('ICUVariant', ['source', 'replacement'])

def configure(rules, normalization_rules):
    """ Extract and preprocess the configuration for this module.
    """
    config = {}

    config['replacements'], config['chars'] = _get_variant_config(rules.get('variants'),
                                                                  normalization_rules)
    config['variant_only'] = rules.get('mode', '') == 'variant-only'

    return config


def _get_variant_config(rules, normalization_rules):
    """ Convert the variant definition from the configuration into
        replacement sets.
    """
    immediate = defaultdict(list)
    chars = set()

    if rules:
        vset = set()
        rules = flatten_config_list(rules, 'variants')

        vmaker = _VariantMaker(normalization_rules)

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
    """ Generater for all necessary ICUVariants from a single variant rule.

        All text in rules is normalized to make sure the variants match later.
    """

    def __init__(self, norm_rules):
        self.norm = Transliterator.createFromRules("rule_loader_normalization",
                                                   norm_rules)


    def compute(self, rule):
        """ Generator for all ICUVariant tuples from a single variant rule.
        """
        parts = re.split(r'(\|)?([=-])>', rule)
        if len(parts) != 4:
            raise UsageError("Syntax error in variant rule: " + rule)

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


    def _parse_variant_word(self, name):
        name = name.strip()
        match = re.fullmatch(r'([~^]?)([^~$^]*)([~$]?)', name)
        if match is None or (match.group(1) == '~' and match.group(3) == '~'):
            raise UsageError("Invalid variant word descriptor '{}'".format(name))
        norm_name = self.norm.transliterate(match.group(2)).strip()
        if not norm_name:
            return None

        return norm_name, match.group(1), match.group(3)


_FLAG_MATCH = {'^': '^ ',
               '$': ' ^',
               '': ' '}


def _create_variants(src, preflag, postflag, repl, decompose):
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


### Analysis section

def create(transliterator, config):
    """ Create a new token analysis instance for this module.
    """
    return GenericTokenAnalysis(transliterator, config)


class GenericTokenAnalysis:
    """ Collects the different transformation rules for normalisation of names
        and provides the functions to apply the transformations.
    """

    def __init__(self, to_ascii, config):
        self.to_ascii = to_ascii
        self.variant_only = config['variant_only']

        # Set up datrie
        if config['replacements']:
            self.replacements = datrie.Trie(config['chars'])
            for src, repllist in config['replacements']:
                self.replacements[src] = repllist
        else:
            self.replacements = None


    def get_variants_ascii(self, norm_name):
        """ Compute the spelling variants for the given normalized name
            and transliterate the result.
        """
        baseform = '^ ' + norm_name + ' ^'
        partials = ['']

        startpos = 0
        if self.replacements is not None:
            pos = 0
            force_space = False
            while pos < len(baseform):
                full, repl = self.replacements.longest_prefix_item(baseform[pos:],
                                                                   (None, None))
                if full is not None:
                    done = baseform[startpos:pos]
                    partials = [v + done + r
                                for v, r in itertools.product(partials, repl)
                                if not force_space or r.startswith(' ')]
                    if len(partials) > 128:
                        # If too many variants are produced, they are unlikely
                        # to be helpful. Only use the original term.
                        startpos = 0
                        break
                    startpos = pos + len(full)
                    if full[-1] == ' ':
                        startpos -= 1
                        force_space = True
                    pos = startpos
                else:
                    pos += 1
                    force_space = False

        # No variants detected? Fast return.
        if startpos == 0:
            if self.variant_only:
                return []

            trans_name = self.to_ascii.transliterate(norm_name).strip()
            return [trans_name] if trans_name else []

        return self._compute_result_set(partials, baseform[startpos:],
                                        norm_name if self.variant_only else '')


    def _compute_result_set(self, partials, prefix, exclude):
        results = set()

        for variant in partials:
            vname = (variant + prefix)[1:-1].strip()
            if vname != exclude:
                trans_name = self.to_ascii.transliterate(vname).strip()
                if trans_name:
                    results.add(trans_name)

        return list(results)
