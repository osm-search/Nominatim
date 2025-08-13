# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
from typing import Optional, List
from .base import Locales
from ..results import AddressLine, BaseResultT, AddressLines
import yaml
import os
import re
from cantoroman import Cantonese  # type: ignore
from unidecode import unidecode
import opencc  # type: ignore


class ComplexLocales(Locales):
    """ Complex Helper class for localization of names.

        It takes a list of language prefixes in their order of preferred
        usage.
    """
    def __init__(self, langs: Optional[list[str]] = None):
        super().__init__(langs)

        # yaml information for now
        self.country_data = load_country_info()
        self.lang_data = load_lang_info()

    @staticmethod
    def from_accept_languages(langstr: str) -> 'ComplexLocales':
        """ Create a localization object from a language list in the
            format of HTTP accept-languages header.

            The functions tries to be forgiving of format errors by first splitting
            the string into comma-separated parts and then parsing each
            description separately. Badly formatted parts are then ignored.

            Using the additional normalization transliteration constraints,
            then returns the larguage in its normalized form, as well as the regional
            dialect, if applicable.

            The regional dialect always takes precedence

            Languages are returned in lowercase form
        """
        # split string into languages
        candidates = []
        for desc in langstr.split(','):
            m = re.fullmatch(r'\s*([a-z_-]+)(?:;\s*q\s*=\s*([01](?:\.\d+)?))?\s*',
                             desc, flags=re.I)
            if m:
                candidates.append((m[1], float(m[2] or 1.0)))

        # sort the results by the weight of each language (preserving order).
        candidates.sort(reverse=True, key=lambda e: e[1])

        # if a language has a region variant, ignore it
        # we want base transliteration language only
        languages = []
        for lid, _ in candidates:
            lid = lid

            if lid not in languages:
                languages.append(lid)

            normalized = ComplexLocales._normalize_lang(lid)
            for norm_lang in normalized:
                if norm_lang not in languages:
                    languages.append(norm_lang)
        return ComplexLocales(languages)

    def _get_languages(self, result: BaseResultT) -> List[str]:
        """ Given a result, returns the languages associated with the region

            Special handling is needed for Macau and Hong Kong (not in yaml)
        """
        if not self.country_data:
            self.country_data = load_country_info()
        country = self.country_data.get(str(result.country_code).lower())
        if country and 'languages' in country:
            return [lang.strip() for lang in country['languages'].split(',')]
        return []

    def _latin(self, language_code: str) -> bool:
        """ Using languages.yaml, returns if the
            given language is latin based or not.

            If the code does not exist in the yaml file, it
            will return false. This works as, due to normalization,
            we assume that the "prime" version of the code is also in
            the user languages, so it will eventually execute

            Will only work on two-letter ISO 639 language codes
            with the exception of yue, which is also included
        """
        if not self.lang_data:
            self.lang_data = load_lang_info()

        # when we safeload a yaml file, what comes out?
        # we also dont need to load in yaml file now right?
        # currently nominatim does not do so
        language = self.lang_data.get(language_code)
        return bool(language and language.get('written') == 'lat')

    @staticmethod
    def decode_canto(line: str) -> str:
        """ Takes in a string in Cantonese and returns the Latin
            transliterated version.
            Uses the cantoroman library, named as so to be homogenous
            with unidecode

            For cases with multiple pronounciation, the first is always taken
        """
        cantonese = Cantonese()  # perhaps make into global variable later
        cantonese_line = ""
        for char in line:
            cantonese_line += cantonese.getRoman(char)[0][0].capitalize()
            cantonese_line += ' '
        return cantonese_line.strip()

    @staticmethod
    def _normalize_lang(lang: str) -> List[str]:
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
        # For now, no dialect support
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

    def result_transliterate(self, results: List[BaseResultT]) -> List[str]:
        """ High level transliteration result wrapper

            Prints out the transliterated results
            Returns output as list
        """
        output = []
        for i, result in enumerate(results):
            address_parts = self.transliterate(result, self.languages)
            # print(address_parts)
            # print(f"{i + 1}. {', '.join(part.strip() for part in address_parts)}")
            # output.append(", ".join(part.strip() for part in address_parts))
            # print(", ".join(part.strip() for part in address_parts))
            output.append(address_parts)
        return output

    def _transliterate(self, line: AddressLine, locales: List[str], in_cantonese:
                       bool = False) -> str:
        """ Most granular transliteration component
            Performs raw transliteration based on locales

            Defaults to Latin
        """
        # in_cantonese is a placeholder for now until we determine HK and Macau mapping

        for locale in locales:
            # Need to replace to be a valid function
            _function = f"{locale.replace('-', '_')}_transliterate"
            if _function in globals():
                print(f"{locale} transliteration successful")
                return str(globals()[_function](line))
            elif self._latin(locale):
                print("latin based language detected, latin transliteration occuring")
                if not in_cantonese:
                    return unidecode(line.local_name) if line.local_name else ""
                else:
                    return self.decode_canto(line.local_name) if line.local_name else ""

        print("defaulting to latin based transliteration")
        if not in_cantonese:
            return unidecode(line.local_name) if line.local_name else ""
        else:
            return self.decode_canto(line.local_name) if line.local_name else ""

    @staticmethod
    def zh_Hans_transliterate(line: AddressLine) -> str:
        """ If in Traditional Chinese, convert to Simplified
            NOT TESTED, PROOF OF CONCEPT

            Else switch to standard Latin default transliteration
        """
        if line.local_name_lang == 'zh-hant':
            # t2s.json Traditional Chinese to Simplified Chinese 繁體到簡體
            converter = opencc.OpenCC('t2s.json')
            return str(converter.convert(line.local_name))
        return unidecode(line.local_name) if line.local_name else ""

    @staticmethod
    def zh_Hant_transliterate(line: AddressLine) -> str:
        """ If in Simplified Chinese, convert to Traditional

            Else switch to standard Latin default transliteration
        """
        if line.local_name_lang == 'zh-hans' or line.local_name_lang == 'zh-CN':
            # t2s.json Traditional Chinese to Simplified Chinese 繁體到簡體
            converter = opencc.OpenCC('s2t.json')
            return str(converter.convert(line.local_name)) if line.local_name else ""
        return unidecode(line.local_name) if line.local_name else ""

    @staticmethod
    def yue_transliterate(line: AddressLine) -> str:
        """ If in Simplified Chinese, convert to Traditional

            Else switch to standard Latin default transliteration
        """
        if line.local_name_lang == 'zh-hans' or line.local_name_lang == 'zh':
            # t2s.json Traditional Chinese to Simplified Chinese 繁體到簡體
            converter = opencc.OpenCC('s2t.json')
            return str(converter.convert(line.local_name))
        return unidecode(line.local_name) if line.local_name else ""

    def transliterate(self, result: BaseResultT, user_languages: List[str]) -> str:
        """ Based on Nominatim Localize and ISO regions
            Assumes the user does not know the local language

            Set the local name of address parts according to the chosen
            local, transliterating if not avaliable.
            Return the list of local names without duplicates.

            Only address parts that are marked as isaddress are localized
            and returned.
        """
        label_parts: List[str] = []
        iso = False

        if not result.address_rows:
            return ""

        local_languages = self._get_languages(result)

        if len(local_languages) == 1 and local_languages[0] in user_languages:
            iso = True
            result.region_lang = local_languages[0]  # can potentially do more with this

        for line in result.address_rows:
            if line.isaddress and line.names:
                if result.region_lang:
                    line.local_name_lang = result.region_lang

                if not iso:
                    # new identifier, local_name_lang
                    line.local_name, line.local_name_lang = (
                        self.display_name_with_locale(line.names)
                    )

                    # print(line.names) # For test cases, to see what names are avaliable
                    # dont use this function for Locales
                    # want to replace this

                # if not label_parts or label_parts[-1] != line.local_name:
                if line.local_name and (not label_parts or label_parts[-1] != line.local_name):
                    if iso or line.local_name_lang in user_languages:
                        print(f"no transliteration needed for {line.local_name}")
                        label_parts.append(line.local_name)
                    else:
                        label_parts.append(self._transliterate(line, user_languages))
        return ", ".join(part.strip() for part in label_parts)

    def localize(self, lines: AddressLines) -> None:
        """ Stand in localize """
        print(lines)

    def localize_results(self, results: List[BaseResultT]) -> None:
        """ Stand in localize_results """
        print(result.address_rows[0].local_name for result in results if result.address_rows)


def include_constructor(loader: yaml.SafeLoader, node:
                        yaml.ScalarNode) -> dict[str, dict[str, str]]:
    # Temporary file to get rid of !include error for yaml
    file_path = loader.construct_scalar(node)
    full_path = os.path.join(os.path.dirname(loader.name), file_path)
    with open(full_path, 'r') as file:
        return dict(yaml.safe_load(file))


def load_country_info(yaml_path: Optional[str] = None) -> dict[str, dict[str, str]]:
    """ Loads country_settings
        Yaml files from Nominatim blob/master/settings/country_settings.yaml
    """
    yaml.SafeLoader.add_constructor('!include', include_constructor)

    if yaml_path is None:
        current_dir = os.path.dirname(__file__)
        yaml_path = os.path.join(current_dir, "../../../", "settings/country_settings.yaml")
    with open(yaml_path, 'r') as file:
        yaml.SafeLoader.name = file.name  # Pass the file name to the loader
        return dict(yaml.safe_load(file))


def load_lang_info(yaml_path: Optional[str] = None) -> dict[str, dict[str, str]]:
    """ Loads language information on writing system

    Will only work on two-letter ISO 639 language codes
    with the exception of yue, which is also included
    """
    if yaml_path is None:
        current_dir = os.path.dirname(__file__)
        yaml_path = os.path.join(current_dir, "../../../", "settings/languages.yaml")

    with open(yaml_path, 'r') as file:
        return dict(yaml.safe_load(file))
