"""
Name processor for tagging the langauge of the name
"""
import re

from nominatim.tools import country_info

class _AnalyzerByLanguage:
    """ Processor for tagging the language of names in a place.
    """

    def __init__(self, config):
        if 'filter-kind' in config:
            self.regexes = [re.compile(regex) for regex in config['filter-kind']]
        else:
            self.regexes = None

        self.use_defaults = config.get('use-defaults', 'no')
        if self.use_defaults not in ('mono', 'all'):
            self.use_defaults = False

        self.replace = config.get('mode', 'replace') != 'append'
        self.whitelist = config.get('whitelist')

        # Compute the languages to use when no suffix is given.
        self.deflangs = {}
        for ccode, prop in country_info.iterate():
            clangs = prop['languages']
            if len(clangs) == 1 or self.use_defaults == 'all':
                if self.whitelist:
                    self.deflangs[ccode] = [l for l in clangs if l in self.whitelist]
                else:
                    self.deflangs[ccode] = clangs



    def _kind_matches(self, kind):
        if self.regexes is None:
            return True

        return any(regex.search(kind) for regex in self.regexes)


    def _suffix_matches(self, suffix):
        if self.whitelist is None:
            return len(suffix) in (2, 3) and suffix.islower()

        return suffix in self.whitelist


    def __call__(self, obj):
        if not obj.names:
            return

        more_names = []

        for name in (n for n in obj.names
                     if not n.has_attr('analyzer') and self._kind_matches(n.kind)):
            if name.suffix:
                langs = [name.suffix] if self._suffix_matches(name.suffix) else None
            else:
                if self.use_defaults:
                    langs = self.deflangs.get(obj.place.country_code)
                    if self.use_defaults == 'mono' and len(langs) > 1:
                        langs = None

            if langs:
                if self.replace:
                    name.set_attr('analyzer', langs[0])
                else:
                    more_names.append(name.clone(attr={'analyzer': langs[0]}))

                more_names.extend(name.clone(attr={'analyzer': l}) for l in langs[1:])

        obj.names.extend(more_names)


def create(config):
    """ Create a function that sets the analyzer property depending on the
        language of the tag. The language is taken from the suffix.

        To restrict the set of languages that should be tagged, use
        'whitelist'. A list of acceptable suffixes. When unset, all 2- and
        3-letter codes are accepted.

        'use-defaults' configures what happens when the name has no suffix
        with a language tag. When set to 'all', a variant is created for
        each on the spoken languages in the country the feature is in. When
        set to 'mono', a variant is created, when only one language is spoken
        in the country. The default is, to do nothing with the default languages
        of a country.

        'mode' hay be 'replace' (the default) or 'append' and configures if
        the original name (without any analyzer tagged) is retained.

        With 'filter-kind' the set of names the sanitizer should be applied
        to can be retricted to the given patterns of 'kind'. It expects a
        list of regular expression to be matched against 'kind'.
    """
    return _AnalyzerByLanguage(config)
