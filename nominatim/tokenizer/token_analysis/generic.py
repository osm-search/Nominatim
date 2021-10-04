"""
Generic processor for names that creates abbreviation variants.
"""
from collections import defaultdict
import itertools
import re

from icu import Transliterator
import datrie

from nominatim.config import flatten_config_list
from nominatim.errors import UsageError
import nominatim.tokenizer.icu_variants as variants

### Configuration section

def configure(rules, normalization_rules):
    """ Extract and preprocess the configuration for this module.
    """
    return {'variants': _parse_variant_list(rules.get('variants'),
                                            normalization_rules)}


def _parse_variant_list(rules, normalization_rules):
    vset = set()

    if rules:
        rules = flatten_config_list(rules, 'variants')

        vmaker = _VariantMaker(normalization_rules)

        properties = []
        for section in rules:
            # Create the property field and deduplicate against existing
            # instances.
            props = variants.ICUVariantProperties.from_rules(section)
            for existing in properties:
                if existing == props:
                    props = existing
                    break
            else:
                properties.append(props)

            for rule in (section.get('words') or []):
                vset.update(vmaker.compute(rule, props))

    return vset


class _VariantMaker:
    """ Generater for all necessary ICUVariants from a single variant rule.

        All text in rules is normalized to make sure the variants match later.
    """

    def __init__(self, norm_rules):
        self.norm = Transliterator.createFromRules("rule_loader_normalization",
                                                   norm_rules)


    def compute(self, rule, props):
        """ Generator for all ICUVariant tuples from a single variant rule.
        """
        parts = re.split(r'(\|)?([=-])>', rule)
        if len(parts) != 4:
            raise UsageError("Syntax error in variant rule: " + rule)

        decompose = parts[1] is None
        src_terms = [self._parse_variant_word(t) for t in parts[0].split(',')]
        repl_terms = (self.norm.transliterate(t.strip()) for t in parts[3].split(','))

        # If the source should be kept, add a 1:1 replacement
        if parts[2] == '-':
            for src in src_terms:
                if src:
                    for froms, tos in _create_variants(*src, src[0], decompose):
                        yield variants.ICUVariant(froms, tos, props)

        for src, repl in itertools.product(src_terms, repl_terms):
            if src and repl:
                for froms, tos in _create_variants(*src, repl, decompose):
                    yield variants.ICUVariant(froms, tos, props)


    def _parse_variant_word(self, name):
        name = name.strip()
        match = re.fullmatch(r'([~^]?)([^~$^]*)([~$]?)', name)
        if match is None or (match.group(1) == '~' and match.group(3) == '~'):
            raise UsageError("Invalid variant word descriptor '{}'".format(name))
        norm_name = self.norm.transliterate(match.group(2))
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
