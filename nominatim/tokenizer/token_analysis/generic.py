# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Generic processor for names that creates abbreviation variants.
"""
import itertools

import datrie

from nominatim.tokenizer.token_analysis.config_variants import get_variant_config

### Configuration section

def configure(rules, normalization_rules):
    """ Extract and preprocess the configuration for this module.
    """
    config = {}

    config['replacements'], config['chars'] = get_variant_config(rules.get('variants'),
                                                                 normalization_rules)
    config['variant_only'] = rules.get('mode', '') == 'variant-only'

    return config


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
        results = set()
        for variant in self._generate_word_variants(norm_name):
            if not self.variant_only or variant.strip() != norm_name:
                trans_name = self.to_ascii.transliterate(variant).strip()
                if trans_name:
                    results.add(trans_name)

        return list(results)


    def _generate_word_variants(self, norm_name):
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
