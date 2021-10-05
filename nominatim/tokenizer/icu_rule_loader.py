"""
Helper class to create ICU rules from a configuration file.
"""
import importlib
import io
import json
import logging

from nominatim.config import flatten_config_list
from nominatim.db.properties import set_property, get_property
from nominatim.errors import UsageError
from nominatim.tokenizer.place_sanitizer import PlaceSanitizer
from nominatim.tokenizer.icu_token_analysis import ICUTokenAnalysis

LOG = logging.getLogger()

DBCFG_IMPORT_NORM_RULES = "tokenizer_import_normalisation"
DBCFG_IMPORT_TRANS_RULES = "tokenizer_import_transliteration"
DBCFG_IMPORT_ANALYSIS_RULES = "tokenizer_import_analysis_rules"


def _get_section(rules, section):
    """ Get the section named 'section' from the rules. If the section does
        not exist, raise a usage error with a meaningful message.
    """
    if section not in rules:
        LOG.fatal("Section '%s' not found in tokenizer config.", section)
        raise UsageError("Syntax error in tokenizer configuration file.")

    return rules[section]


class ICURuleLoader:
    """ Compiler for ICU rules from a tokenizer configuration file.
    """

    def __init__(self, config):
        rules = config.load_sub_configuration('icu_tokenizer.yaml',
                                              config='TOKENIZER_CONFIG')

        self.normalization_rules = self._cfg_to_icu_rules(rules, 'normalization')
        self.transliteration_rules = self._cfg_to_icu_rules(rules, 'transliteration')
        self.analysis_rules = _get_section(rules, 'token-analysis')
        self._setup_analysis()

        # Load optional sanitizer rule set.
        self.sanitizer_rules = rules.get('sanitizers', [])


    def load_config_from_db(self, conn):
        """ Get previously saved parts of the configuration from the
            database.
        """
        self.normalization_rules = get_property(conn, DBCFG_IMPORT_NORM_RULES)
        self.transliteration_rules = get_property(conn, DBCFG_IMPORT_TRANS_RULES)
        self.analysis_rules = json.loads(get_property(conn, DBCFG_IMPORT_ANALYSIS_RULES))
        self._setup_analysis()


    def save_config_to_db(self, conn):
        """ Save the part of the configuration that cannot be changed into
            the database.
        """
        set_property(conn, DBCFG_IMPORT_NORM_RULES, self.normalization_rules)
        set_property(conn, DBCFG_IMPORT_TRANS_RULES, self.transliteration_rules)
        set_property(conn, DBCFG_IMPORT_ANALYSIS_RULES, json.dumps(self.analysis_rules))


    def make_sanitizer(self):
        """ Create a place sanitizer from the configured rules.
        """
        return PlaceSanitizer(self.sanitizer_rules)


    def make_token_analysis(self):
        """ Create a token analyser from the reviouly loaded rules.
        """
        return ICUTokenAnalysis(self.normalization_rules,
                                self.transliteration_rules, self.analysis)


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


    def _setup_analysis(self):
        """ Process the rules used for creating the various token analyzers.
        """
        self.analysis = {}

        if not isinstance(self.analysis_rules, list):
            raise UsageError("Configuration section 'token-analysis' must be a list.")

        for section in self.analysis_rules:
            name = section.get('id', None)
            if name in self.analysis:
                if name is None:
                    LOG.fatal("ICU tokenizer configuration has two default token analyzers.")
                else:
                    LOG.fatal("ICU tokenizer configuration has two token "
                              "analyzers with id '%s'.", name)
                UsageError("Syntax error in ICU tokenizer config.")
            self.analysis[name] = TokenAnalyzerRule(section, self.normalization_rules)


    @staticmethod
    def _cfg_to_icu_rules(rules, section):
        """ Load an ICU ruleset from the given section. If the section is a
            simple string, it is interpreted as a file name and the rules are
            loaded verbatim from the given file. The filename is expected to be
            relative to the tokenizer rule file. If the section is a list then
            each line is assumed to be a rule. All rules are concatenated and returned.
        """
        content = _get_section(rules, section)

        if content is None:
            return ''

        return ';'.join(flatten_config_list(content, section)) + ';'


class TokenAnalyzerRule:
    """ Factory for a single analysis module. The class saves the configuration
        and creates a new token analyzer on request.
    """

    def __init__(self, rules, normalization_rules):
        # Find the analysis module
        module_name = 'nominatim.tokenizer.token_analysis.' \
                      + _get_section(rules, 'analyzer').replace('-', '_')
        analysis_mod = importlib.import_module(module_name)
        self.create = analysis_mod.create

        # Load the configuration.
        self.config = analysis_mod.configure(rules, normalization_rules)
