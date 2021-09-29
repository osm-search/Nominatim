"""
Helper class to create ICU rules from a configuration file.
"""
import io
import json
import logging
import itertools
import re

from icu import Transliterator

from nominatim.db.properties import set_property, get_property
from nominatim.errors import UsageError
from nominatim.tokenizer.icu_name_processor import ICUNameProcessor
import nominatim.tokenizer.icu_variants as variants

LOG = logging.getLogger()

DBCFG_IMPORT_NORM_RULES = "tokenizer_import_normalisation"
DBCFG_IMPORT_TRANS_RULES = "tokenizer_import_transliteration"
DBCFG_IMPORT_ANALYSIS_RULES = "tokenizer_import_analysis_rules"


def _flatten_config_list(content):
    if not content:
        return []

    if not isinstance(content, list):
        raise UsageError("List expected in ICU configuration.")

    output = []
    for ele in content:
        if isinstance(ele, list):
            output.extend(_flatten_config_list(ele))
        else:
            output.append(ele)

    return output


class VariantRule:
    """ Saves a single variant expansion.

        An expansion consists of the normalized replacement term and
        a dicitonary of properties that describe when the expansion applies.
    """

    def __init__(self, replacement, properties):
        self.replacement = replacement
        self.properties = properties or {}


class ICURuleLoader:
    """ Compiler for ICU rules from a tokenizer configuration file.
    """

    def __init__(self, config):
        rules = config.load_sub_configuration('icu_tokenizer.yaml',
                                              config='TOKENIZER_CONFIG')

        self.variants = set()

        self.normalization_rules = self._cfg_to_icu_rules(rules, 'normalization')
        self.transliteration_rules = self._cfg_to_icu_rules(rules, 'transliteration')
        self.analysis_rules = self._get_section(rules, 'variants')
        self._parse_variant_list()


    def load_config_from_db(self, conn):
        """ Get previously saved parts of the configuration from the
            database.
        """
        self.normalization_rules = get_property(conn, DBCFG_IMPORT_NORM_RULES)
        self.transliteration_rules = get_property(conn, DBCFG_IMPORT_TRANS_RULES)
        self.analysis_rules = json.loads(get_property(conn, DBCFG_IMPORT_ANALYSIS_RULES))
        self._parse_variant_list()


    def save_config_to_db(self, conn):
        """ Save the part of the configuration that cannot be changed into
            the database.
        """
        set_property(conn, DBCFG_IMPORT_NORM_RULES, self.normalization_rules)
        set_property(conn, DBCFG_IMPORT_TRANS_RULES, self.transliteration_rules)
        set_property(conn, DBCFG_IMPORT_ANALYSIS_RULES, json.dumps(self.analysis_rules))


    def make_token_analysis(self):
        """ Create a token analyser from the reviouly loaded rules.
        """
        return ICUNameProcessor(self.normalization_rules,
                                self.transliteration_rules,
                                self.variants)


    def get_search_rules(self):
        """ Return the ICU rules to be used during search.
            The rules combine normalization and transliteration.
        """
        # First apply the normalization rules.
        rules = io.StringIO()
        rules.write(self.normalization_rules)

        # Then add transliteration.
        rules.write(self.transliteration_rules)
        return rules.getvalue()

    def get_normalization_rules(self):
        """ Return rules for normalisation of a term.
        """
        return self.normalization_rules

    def get_transliteration_rules(self):
        """ Return the rules for converting a string into its asciii representation.
        """
        return self.transliteration_rules

    def get_replacement_pairs(self):
        """ Return the list of possible compound decompositions with
            application of abbreviations included.
            The result is a list of pairs: the first item is the sequence to
            replace, the second is a list of replacements.
        """
        return self.variants


    @staticmethod
    def _get_section(rules, section):
        """ Get the section named 'section' from the rules. If the section does
            not exist, raise a usage error with a meaningful message.
        """
        if section not in rules:
            LOG.fatal("Section '%s' not found in tokenizer config.", section)
            raise UsageError("Syntax error in tokenizer configuration file.")

        return rules[section]


    def _cfg_to_icu_rules(self, rules, section):
        """ Load an ICU ruleset from the given section. If the section is a
            simple string, it is interpreted as a file name and the rules are
            loaded verbatim from the given file. The filename is expected to be
            relative to the tokenizer rule file. If the section is a list then
            each line is assumed to be a rule. All rules are concatenated and returned.
        """
        content = self._get_section(rules, section)

        if content is None:
            return ''

        return ';'.join(_flatten_config_list(content)) + ';'


    def _parse_variant_list(self):
        rules = self.analysis_rules

        self.variants.clear()

        if not rules:
            return

        rules = _flatten_config_list(rules)

        vmaker = _VariantMaker(self.normalization_rules)

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
                self.variants.update(vmaker.compute(rule, props))


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
