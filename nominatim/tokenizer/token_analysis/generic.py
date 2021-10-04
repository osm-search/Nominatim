"""
Generic processor for names that creates abbreviation variants.
"""
from collections import defaultdict
import itertools

from icu import Transliterator
import datrie

### Analysis section

def create(norm_rules, trans_rules, config):
    """ Create a new token analysis instance for this module.
    """
    return GenericTokenAnalysis(norm_rules, trans_rules, config['variants'])


class GenericTokenAnalysis:
    """ Collects the different transformation rules for normalisation of names
        and provides the functions to apply the transformations.
    """

    def __init__(self, norm_rules, trans_rules, replacements):
        self.normalizer = Transliterator.createFromRules("icu_normalization",
                                                         norm_rules)
        self.to_ascii = Transliterator.createFromRules("icu_to_ascii",
                                                       trans_rules +
                                                       ";[:Space:]+ > ' '")
        self.search = Transliterator.createFromRules("icu_search",
                                                     norm_rules + trans_rules)

        # Intermediate reorder by source. Also compute required character set.
        immediate = defaultdict(list)
        chars = set()
        for variant in replacements:
            if variant.source[-1] == ' ' and variant.replacement[-1] == ' ':
                replstr = variant.replacement[:-1]
            else:
                replstr = variant.replacement
            immediate[variant.source].append(replstr)
            chars.update(variant.source)
        # Then copy to datrie
        self.replacements = datrie.Trie(''.join(chars))
        for src, repllist in immediate.items():
            self.replacements[src] = repllist


    def get_normalized(self, name):
        """ Normalize the given name, i.e. remove all elements not relevant
            for search.
        """
        return self.normalizer.transliterate(name).strip()

    def get_variants_ascii(self, norm_name):
        """ Compute the spelling variants for the given normalized name
            and transliterate the result.
        """
        baseform = '^ ' + norm_name + ' ^'
        partials = ['']

        startpos = 0
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
            trans_name = self.to_ascii.transliterate(norm_name).strip()
            return [trans_name] if trans_name else []

        return self._compute_result_set(partials, baseform[startpos:])


    def _compute_result_set(self, partials, prefix):
        results = set()

        for variant in partials:
            vname = variant + prefix
            trans_name = self.to_ascii.transliterate(vname[1:-1]).strip()
            if trans_name:
                results.add(trans_name)

        return list(results)


    def get_search_normalized(self, name):
        """ Return the normalized version of the name (including transliteration)
            to be applied at search time.
        """
        return self.search.transliterate(' ' + name + ' ').strip()
