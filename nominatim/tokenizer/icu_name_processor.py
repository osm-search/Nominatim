"""
Processor for names that are imported into the database based on the
ICU library.
"""
from collections import defaultdict
import itertools

from icu import Transliterator
import datrie

from nominatim.db.properties import set_property, get_property
from nominatim.tokenizer import icu_variants as variants

DBCFG_IMPORT_NORM_RULES = "tokenizer_import_normalisation"
DBCFG_IMPORT_TRANS_RULES = "tokenizer_import_transliteration"
DBCFG_IMPORT_REPLACEMENTS = "tokenizer_import_replacements"
DBCFG_SEARCH_STD_RULES = "tokenizer_search_standardization"


class ICUNameProcessorRules:
    """ Data object that saves the rules needed for the name processor.

        The rules can either be initialised through an ICURuleLoader or
        be loaded from a database when a connection is given.
    """
    def __init__(self, loader=None, conn=None):
        if loader is not None:
            self.norm_rules = loader.get_normalization_rules()
            self.trans_rules = loader.get_transliteration_rules()
            self.replacements = loader.get_replacement_pairs()
            self.search_rules = loader.get_search_rules()
        elif conn is not None:
            self.norm_rules = get_property(conn, DBCFG_IMPORT_NORM_RULES)
            self.trans_rules = get_property(conn, DBCFG_IMPORT_TRANS_RULES)
            self.replacements = \
                variants.unpickle_variant_set(get_property(conn, DBCFG_IMPORT_REPLACEMENTS))
            self.search_rules = get_property(conn, DBCFG_SEARCH_STD_RULES)
        else:
            assert False, "Parameter loader or conn required."


    def save_rules(self, conn):
        """ Save the rules in the property table of the given database.
            the rules can be loaded again by handing in a connection into
            the constructor of the class.
        """
        set_property(conn, DBCFG_IMPORT_NORM_RULES, self.norm_rules)
        set_property(conn, DBCFG_IMPORT_TRANS_RULES, self.trans_rules)
        set_property(conn, DBCFG_IMPORT_REPLACEMENTS,
                     variants.pickle_variant_set(self.replacements))
        set_property(conn, DBCFG_SEARCH_STD_RULES, self.search_rules)


class ICUNameProcessor:
    """ Collects the different transformation rules for normalisation of names
        and provides the functions to aply the transformations.
    """

    def __init__(self, rules):
        self.normalizer = Transliterator.createFromRules("icu_normalization",
                                                         rules.norm_rules)
        self.to_ascii = Transliterator.createFromRules("icu_to_ascii",
                                                       rules.trans_rules)
        self.search = Transliterator.createFromRules("icu_search",
                                                     rules.search_rules)

        # Intermediate reorder by source. Also compute required character set.
        immediate = defaultdict(list)
        chars = set()
        for variant in rules.replacements:
            immediate[variant.source].append(variant)
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
        while pos < len(baseform):
            full, repl = self.replacements.longest_prefix_item(baseform[pos:],
                                                               (None, None))
            if full is not None:
                done = baseform[startpos:pos]
                partials = [v + done + r.replacement
                            for v, r in itertools.product(partials, repl)]
                startpos = pos + len(full)
                pos = startpos
            else:
                pos += 1

        results = []

        if startpos == 0:
            trans_name = self.to_ascii.transliterate(norm_name).strip()
            if trans_name:
                results.append(trans_name)
        else:
            for variant in partials:
                name = variant[1:] + baseform[startpos:-1]
                trans_name = self.to_ascii.transliterate(name).strip()
                if trans_name:
                    results.append(trans_name)

        return results


    def get_search_normalized(self, name):
        """ Return the normalized version of the name (including transliteration)
            to be applied at search time.
        """
        return self.search.transliterate(' ' + name + ' ').strip()
