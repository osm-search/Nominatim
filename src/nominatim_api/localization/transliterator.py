# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
from typing import Optional, List

from .base import AbstractLocales
from ..results import AddressLine, BaseResultT
from ..data import lang_info, country_info

# optional dependencies
try:
    from unidecode import unidecode
except ImportError:
    unidecode = None
try:
    from cantoroman import Cantonese  # type: ignore
except ImportError:
    Cantonese = None
try:
    import opencc  # type: ignore
except ImportError:
    opencc = None


def latindecode(local_name: Optional[str]) -> str:
    if unidecode is None:
        raise ImportError('The unidecode library is required for Latin transliteration.')
    return unidecode(local_name) if local_name else ''


def chinesedecode(local_name: Optional[str], conversion: str) -> str:
    if opencc is None:
        raise ImportError('The opencc library is required for Latin transliteration.')
    converter = opencc.OpenCC(conversion)
    return str(converter.convert(local_name)) if local_name else ''


def cantodecode(line: str) -> str:
    """ Takes in a string in Cantonese and returns the Latin
        transliterated version.
        Uses the cantoroman library, named as so to be homogenous with unidecode

        For cases with multiple pronounciation, the first is always taken
    """
    if Cantonese is None:
        raise ImportError('The cantonese-romanisation library is'
                          'required for Cantonese transliteration.')
    cantonese = Cantonese()  # perhaps make into global variable later
    cantonese_line = ""
    for char in line:
        cantonese_line += cantonese.getRoman(char)[0][0].capitalize()
        cantonese_line += ' '
    return cantonese_line.strip()


class TransliterateLocales(AbstractLocales):
    """ Complex Helper class for localization of names.

        It takes a list of language prefixes in their order of preferred
        usage.
    """
    def __init__(self, langs: Optional[list[str]] = None):
        super().__init__(langs)
        country_info.setup_country_config(self.config)
        lang_info.setup_lang_config(self.config)

    @staticmethod
    def is_latin(language_code: str) -> bool:
        """ Returns if the given language is latin based on the information in languanges.yaml

            If the code does not exist in the yaml file, it will return false.
            Due to normalization, the "prime" version of the code must also be in
            known languages, so it will eventually execute

            Will only work on two-letter ISO 639 language codes with the addition of yue
        """
        language = lang_info.get(language_code)
        return bool(language and language.get('written') == 'lat')

    @staticmethod
    def normalize_dict(lang: str) -> List[str]:
        """ Mock idea for language mapping dictionary

            Hoping to standardize certain names, i.e.
            zh and zh-cn will always map to zh-Hans
            zh-tw will always map to zh-Hant

            In the case of ambiguity, the largest number of
            languages will be added

            For all other languages, follow Nominatim precedent
            and just concatenate after the '-'

            Code assumes all language codes are in two letter format
            https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes
            with the exception of yue
        """
        # Potentially make this a global variable (or object field) to reduce compute
        # For zh-Latn-pinyin and zh-Latn, I did not include this as it is not a spoken language
        # and it would be in Latin anyways -> this could potentially be changed in the future
        lang_dict = {
            "zh": ["zh-Hans", "zh-Hant", "yue"],  # zh covers zh-Hans, zh-Hant, yue
            "zh-cn": ["zh-Hans"],  # only Simplfied
            "zh-tw": ["zh-Hant"],  # only Traditional Mandarin
            "zh-hans": ["zh-Hans"],
            "zh-hant": ["zh-Hant", "yue"],  # Traditional implies both canto & mando
            "zh-Hans-CN": ["zh-Hans"],  # only Simplfied
            "zh-cmn": ["zh-Hans"],  # only Simplified, cmn means Mandarin
            "zh-cmn-Hans": ["zh-Hans"],  # only Simplified, cmn means Mandarin
            "zh-cmn-Hant": ["zh-Hant"]  # only Traditional, cmn means Mandarin
        }

        if lang in lang_dict:
            # Ordering nessecary due to zh edge case (no '-')
            return lang_dict[lang]
        elif '-' not in lang:
            return [lang]
        return [lang.split('-')[0]]

    @staticmethod
    def zh_Hans_transliterate(line: AddressLine) -> str:
        """ If in Traditional Chinese, convert to Simplified
            NOT TESTED, PROOF OF CONCEPT

            Otherwise switch to standard Latin default transliteration
        """
        if line.local_name_lang == 'zh-hant':
            # t2s.json Traditional Chinese to Simplified Chinese 繁體到簡體
            return chinesedecode(line.local_name, 't2s.json')
        return latindecode(line.local_name)

    @staticmethod
    def zh_Hant_transliterate(line: AddressLine) -> str:
        """ If in Simplified Chinese, convert to Traditional
            Otherwise switch to standard Latin default transliteration
        """
        if line.local_name_lang == 'zh-hans' or line.local_name_lang == 'zh-CN':
            # t2s.json Traditional Chinese to Simplified Chinese 繁體到簡體
            return chinesedecode(line.local_name, 's2t.json')
        return latindecode(line.local_name)

    @staticmethod
    def yue_transliterate(line: AddressLine) -> str:
        """ If in Simplified Chinese, convert to Traditional
            Otherwise switch to standard Latin default transliteration
        """
        if line.local_name_lang == 'zh-hans' or line.local_name_lang == 'zh':
            # t2s.json Traditional Chinese to Simplified Chinese 繁體到簡體
            return chinesedecode(line.local_name, 's2t.json')
        return latindecode(line.local_name)

    def latin_transliterate(self, line: AddressLine) -> str:
        "Transliterates to latin, needs to take into account Han Re-Unification"
        if line.local_name_lang == 'yue':
            return cantodecode(line.local_name) if line.local_name else ''
        else:
            return latindecode(line.local_name)

    def transliterate(self, line: AddressLine) -> str:
        """ Most granular transliteration component that performs raw transliteration

            Defaults to Latin
        """
        for lang in self.languages:
            _function = f"{lang.replace('-', '_')}_transliterate"
            transliterate_function = getattr(self, _function, None)

            if transliterate_function:
                print(f"{lang} transliteration successful")
                return str(transliterate_function(line))
            elif self.is_latin(lang):
                print("latin based language detected, latin transliteration occuring")
                return self.latin_transliterate(line)

        print("defaulting to latin based transliteration")
        return self.latin_transliterate(line)

    def localize(self, result: BaseResultT) -> None:
        """ Sets the local name of address parts according to the chosen
            local, transliterating if not avaliable.

            Only address parts that are marked as isaddress are localized.
        """
        if not result.address_rows:
            return

        local_languages = country_info.get_lang(str(result.country_code))
        # would want to put cantonese here, i.e. use regions to detect
        if len(local_languages) == 1:
            region_lang = local_languages[0]

        for line in result.address_rows:
            if line.isaddress and line.names:
                if region_lang:
                    line.local_name_lang = region_lang

                if line.local_name_lang not in self.languages:
                    line.local_name, line.local_name_lang = (
                        self.display_name_with_locale(line.names)
                    )

                    if line.local_name_lang in self.languages:
                        print(f"no transliteration needed for {line.local_name}")
                    else:
                        line.local_name = self.transliterate(line).strip()

    @staticmethod
    def from_accept_languages(langstr: str) -> 'TransliterateLocales':
        """ Create a localization object from a language list in the
            format of HTTP accept-languages header.

            The functions tries to be forgiving of format errors by first splitting
            the string into comma-separated parts and then parsing each
            description separately. Badly formatted parts are then ignored.

            Using the additional normalization transliteration constraints,
            then returns the larguage in its normalized form, as well as the regional
            dialect, if applicable.
        """
        candidates = AbstractLocales.sort_languages(langstr)

        languages = []
        for lid, _ in candidates:
            if lid not in languages:
                languages.append(lid)

            normalized = TransliterateLocales.normalize_dict(lid)
            for norm_lang in normalized:
                if norm_lang not in languages:
                    languages.append(norm_lang)

        return TransliterateLocales(languages)
