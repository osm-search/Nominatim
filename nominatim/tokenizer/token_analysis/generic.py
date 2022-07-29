# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Generic processor for names that creates abbreviation variants.
"""
from typing import Mapping, Dict, Any, Iterable, Iterator, Optional, List, cast
import itertools

import datrie

from nominatim.errors import UsageError
from nominatim.tokenizer.token_analysis.config_variants import get_variant_config
from nominatim.tokenizer.token_analysis.generic_mutation import MutationVariantGenerator

### Configuration section

def configure(rules: Mapping[str, Any], normalizer: Any, _: Any) -> Dict[str, Any]:
    """ Extract and preprocess the configuration for this module.
    """
    config: Dict[str, Any] = {}

    config['replacements'], config['chars'] = get_variant_config(rules.get('variants'),
                                                                 normalizer)
    config['variant_only'] = rules.get('mode', '') == 'variant-only'

    # parse mutation rules
    config['mutations'] = []
    for rule in rules.get('mutations', []):
        if 'pattern' not in rule:
            raise UsageError("Missing field 'pattern' in mutation configuration.")
        if not isinstance(rule['pattern'], str):
            raise UsageError("Field 'pattern' in mutation configuration "
                             "must be a simple text field.")
        if 'replacements' not in rule:
            raise UsageError("Missing field 'replacements' in mutation configuration.")
        if not isinstance(rule['replacements'], list):
            raise UsageError("Field 'replacements' in mutation configuration "
                             "must be a list of texts.")

        config['mutations'].append((rule['pattern'], rule['replacements']))

    return config


### Analysis section

def create(normalizer: Any, transliterator: Any,
           config: Mapping[str, Any]) -> 'GenericTokenAnalysis':
    """ Create a new token analysis instance for this module.
    """
    return GenericTokenAnalysis(normalizer, transliterator, config)


class GenericTokenAnalysis:
    """ Collects the different transformation rules for normalisation of names
        and provides the functions to apply the transformations.
    """

    def __init__(self, norm: Any, to_ascii: Any, config: Mapping[str, Any]) -> None:
        self.norm = norm
        self.to_ascii = to_ascii
        self.variant_only = config['variant_only']

        # Set up datrie
        if config['replacements']:
            self.replacements = datrie.Trie(config['chars'])
            for src, repllist in config['replacements']:
                self.replacements[src] = repllist
        else:
            self.replacements = None

        # set up mutation rules
        self.mutations = [MutationVariantGenerator(*cfg) for cfg in config['mutations']]


    def normalize(self, name: str) -> str:
        """ Return the normalized form of the name. This is the standard form
            from which possible variants for the name can be derived.
        """
        return cast(str, self.norm.transliterate(name)).strip()


    def get_variants_ascii(self, norm_name: str) -> List[str]:
        """ Compute the spelling variants for the given normalized name
            and transliterate the result.
        """
        variants = self._generate_word_variants(norm_name)

        for mutation in self.mutations:
            variants = mutation.generate(variants)

        return [name for name in self._transliterate_unique_list(norm_name, variants) if name]


    def _transliterate_unique_list(self, norm_name: str,
                                   iterable: Iterable[str]) -> Iterator[Optional[str]]:
        seen = set()
        if self.variant_only:
            seen.add(norm_name)

        for variant in map(str.strip, iterable):
            if variant not in seen:
                seen.add(variant)
                yield self.to_ascii.transliterate(variant).strip()


    def _generate_word_variants(self, norm_name: str) -> Iterable[str]:
        baseform = '^ ' + norm_name + ' ^'
        baselen = len(baseform)
        partials = ['']

        startpos = 0
        if self.replacements is not None:
            pos = 0
            force_space = False
            while pos < baselen:
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
            return (norm_name, )

        if startpos < baselen:
            return (part[1:] + baseform[startpos:-1] for part in partials)

        return (part[1:-1] for part in partials)
