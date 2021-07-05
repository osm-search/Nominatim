"""
Helper class to create ICU rules from a configuration file.
"""
import io
import logging
import itertools
from pathlib import Path
import re

import yaml
from icu import Transliterator

from nominatim.errors import UsageError
import nominatim.tokenizer.icu_variants as variants

LOG = logging.getLogger()

def _flatten_yaml_list(content):
    if not content:
        return []

    if not isinstance(content, list):
        raise UsageError("List expected in ICU yaml configuration.")

    output = []
    for ele in content:
        if isinstance(ele, list):
            output.extend(_flatten_yaml_list(ele))
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

    def __init__(self, configfile):
        self.configfile = configfile
        self.variants = set()

        if configfile.suffix == '.yaml':
            self._load_from_yaml()
        else:
            raise UsageError("Unknown format of tokenizer configuration.")


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

    def _yaml_include_representer(self, loader, node):
        value = loader.construct_scalar(node)

        if Path(value).is_absolute():
            content = Path(value).read_text()
        else:
            content = (self.configfile.parent / value).read_text()

        return yaml.safe_load(content)


    def _load_from_yaml(self):
        yaml.add_constructor('!include', self._yaml_include_representer,
                             Loader=yaml.SafeLoader)
        rules = yaml.safe_load(self.configfile.read_text())

        self.normalization_rules = self._cfg_to_icu_rules(rules, 'normalization')
        self.transliteration_rules = self._cfg_to_icu_rules(rules, 'transliteration')
        self._parse_variant_list(self._get_section(rules, 'variants'))


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

        if content is None:
            return ''

        return ';'.join(_flatten_yaml_list(content)) + ';'


    def _parse_variant_list(self, rules):
        self.variants.clear()

        if not rules:
            return

        rules = _flatten_yaml_list(rules)

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
