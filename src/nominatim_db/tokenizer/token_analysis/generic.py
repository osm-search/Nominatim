# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Generic processor for names that creates abbreviation variants.
"""
from typing import Mapping, Dict, Any, Iterable, Optional, List, cast, Tuple
import itertools

from ...errors import UsageError
from ...data.place_name import PlaceName
from .config_variants import get_variant_config
from .generic_mutation import MutationVariantGenerator
from .simple_trie import SimpleTrie

# Configuration section


def configure(rules: Mapping[str, Any], normalizer: Any, _: Any) -> Dict[str, Any]:
    """ Extract and preprocess the configuration for this module.
    """
    config: Dict[str, Any] = {}

    config['replacements'], _ = get_variant_config(rules.get('variants'), normalizer)
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


# Analysis section

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
        self.replacements: Optional[SimpleTrie[List[str]]] = \
            SimpleTrie(config['replacements']) if config['replacements'] else None

        # set up mutation rules
        self.mutations = [MutationVariantGenerator(*cfg) for cfg in config['mutations']]

    def get_canonical_id(self, name: PlaceName) -> str:
        """ Return the normalized form of the name. This is the standard form
            from which possible variants for the name can be derived.
        """
        return cast(str, self.norm.transliterate(name.name)).strip()

    def compute_variants(self, norm_name: str) -> Tuple[List[str], List[str]]:
        """ Compute the spelling variants for the given normalized name
            and transliterate the result.
        """
        variants = self._generate_word_variants(norm_name)

        for mutation in self.mutations:
            variants = mutation.generate(variants)

        varset = set(map(str.strip, variants))
        if self.variant_only:
            varset.discard(norm_name)

        trans = []
        norm = []

        for var in varset:
            t = self.to_ascii.transliterate(var).strip()
            if t:
                trans.append(t)
                norm.append(var)

        return trans, norm

    def _generate_word_variants(self, norm_name: str) -> Iterable[str]:
        baseform = '^ ' + norm_name + ' ^'
        baselen = len(baseform)
        partials = ['']

        startpos = 0
        if self.replacements is not None:
            pos = 0
            force_space = False
            while pos < baselen:
                frm = pos
                repl, pos = self.replacements.longest_prefix(baseform, pos)
                if repl is not None:
                    done = baseform[startpos:frm]
                    partials = [v + done + r
                                for v, r in itertools.product(partials, repl)
                                if not force_space or r.startswith(' ')]
                    if len(partials) > 128:
                        # If too many variants are produced, they are unlikely
                        # to be helpful. Only use the original term.
                        startpos = 0
                        break
                    if baseform[pos - 1] == ' ':
                        pos -= 1
                        force_space = True
                    startpos = pos
                else:
                    pos += 1
                    force_space = False

        # No variants detected? Fast return.
        if startpos == 0:
            return (norm_name, )

        if startpos < baselen:
            return (part[1:] + baseform[startpos:-1] for part in partials)

        return (part[1:-1] for part in partials)
