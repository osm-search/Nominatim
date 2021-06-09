"""
Helper class to create ICU rules from a configuration file.
"""
import io
import logging
from collections import defaultdict
import itertools

import yaml
from icu import Transliterator

from nominatim.errors import UsageError

LOG = logging.getLogger()


class ICURuleLoader:
    """ Compiler for ICU rules from a tokenizer configuration file.
    """

    def __init__(self, configfile):
        self.configfile = configfile
        self.compound_suffixes = set()
        self.abbreviations = defaultdict()

        if configfile.suffix == '.yaml':
            self._load_from_yaml()
        else:
            raise UsageError("Unknown format of tokenizer configuration.")


    def get_search_rules(self):
        """ Return the ICU rules to be used during search.
            The rules combine normalization, compound decomposition (including
            abbreviated compounds) and transliteration.
        """
        # First apply the normalization rules.
        rules = io.StringIO()
        rules.write(self.normalization_rules)

        # For all compound suffixes: add them in their full and any abbreviated form.
        suffixes = set()
        for suffix in self.compound_suffixes:
            suffixes.add(suffix)
            suffixes.update(self.abbreviations.get(suffix, []))

        for suffix in sorted(suffixes, key=len, reverse=True):
            rules.write("'{0} ' > ' {0} ';".format(suffix))

        # Finally add transliteration.
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
        synonyms = defaultdict(set)

        for full, abbr in self.abbreviations.items():
            key = ' ' + full + ' '
            # Entries in the abbreviation list always apply to full words:
            synonyms[key].update((' ' + a + ' ' for a in abbr))
            # Replacements are optional, so add a noop
            synonyms[key].add(key)

        # Entries in the compound list expand to themselves and to
        # abbreviations.
        for suffix in self.compound_suffixes:
            keyset = synonyms[suffix + ' ']
            keyset.add(' ' + suffix + ' ')
            keyset.update((' ' + a + ' ' for a in self.abbreviations.get(suffix, [])))
            # The terms the entries are shortended to, need to be decompunded as well.
            for abbr in self.abbreviations.get(suffix, []):
                synonyms[abbr + ' '].add(' ' + abbr + ' ')

        # sort the resulting list by descending length (longer matches are prefered).
        sorted_keys = sorted(synonyms.keys(), key=len, reverse=True)

        return [(k, list(synonyms[k])) for k in sorted_keys]


    def _load_from_yaml(self):
        rules = yaml.load(self.configfile.read_text())

        self.normalization_rules = self._cfg_to_icu_rules(rules, 'normalization')
        self.transliteration_rules = self._cfg_to_icu_rules(rules, 'transliteration')
        self._parse_compound_suffix_list(self._get_section(rules, 'compound_suffixes'))
        self._parse_abbreviation_list(self._get_section(rules, 'abbreviations'))


    def _get_section(self, rules, section):
        """ Get the section named 'section' from the rules. If the section does
            not exist, raise a usage error with a meaningful message.
        """
        if section not in rules:
            LOG.fatal("Section '%s' not found in tokenizer config '%s'.",
                      section, str(self.configfile))
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

        if isinstance(content, str):
            return (self.configfile.parent / content).read_text().replace('\n', ' ')

        return ';'.join(content) + ';'


    def _parse_compound_suffix_list(self, rules):
        if not rules:
            self.compound_suffixes = set()
            return

        norm = Transliterator.createFromRules("rule_loader_normalization",
                                              self.normalization_rules)

        # Make sure all suffixes are in their normalised form.
        self.compound_suffixes = set((norm.transliterate(s) for s in rules))


    def _parse_abbreviation_list(self, rules):
        self.abbreviations = defaultdict(list)

        if not rules:
            return

        norm = Transliterator.createFromRules("rule_loader_normalization",
                                              self.normalization_rules)

        for rule in rules:
            parts = rule.split('=>')
            if len(parts) != 2:
                LOG.fatal("Syntax error in abbreviation section, line: %s", rule)
                raise UsageError("Syntax error in tokenizer configuration file.")

            # Make sure all terms match the normalised version.
            fullterms = (norm.transliterate(t.strip()) for t in parts[0].split(','))
            abbrterms = (norm.transliterate(t.strip()) for t in parts[1].split(','))

            for full, abbr in itertools.product(fullterms, abbrterms):
                self.abbreviations[full].append(abbr)
