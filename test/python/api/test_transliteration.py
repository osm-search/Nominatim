# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for transliteration with the complex locales function
"""
import asyncio

from nominatim_api.localization.complex import ComplexLocales, load_lang_info
from nominatim_api.localization.simple import SimpleLocales
import nominatim_api as napi


async def search(query):
    """ Nominatim Search Query
    """
    async with napi.NominatimAPIAsync() as api:
        return await api.search(query, address_details=True)


def test_transliterate():
    """ Base Transliteration Test """
    variable = 'school in dandong'
    results = asyncio.run(search(f"{variable}"))
    print(results)
    # set locale name here first, will probably need to further integrate with display name
    SimpleLocales().localize_results(results)

    output = ComplexLocales().result_transliterate(results)[0]
    assert output == (
        "Dan Dong Shi Di Liu Zhong Xue, Qi Wei Lu, Zhan Qian Jie Dao, "
        "Dan Dong Shi, Zhen Xing Qu, 118000, Zhong Guo"
    )


def test_transliterate_english():
    """ Base Transliteration Test to English

        Results should show that the result is transliterated to latin
        Except for components that have English locales already set
    """
    variable = 'school in dandong'
    results = asyncio.run(search(f"{variable}"))
    output = ComplexLocales(['en']).result_transliterate(results)[0]
    assert output == (
        "Dan Dong Shi Di Liu Zhong Xue, Qi Wei Lu, Zhanqian Subdistrict, "
        "Dandong, Zhenxing, 118000, China"
    )


def test_transliterate_local():
    """ Base Transliteration Test where the user knows the local language

        Results should show that the result is in the orginal locale
    """
    variable = 'hospital in dandong'
    results = asyncio.run(search(f"{variable}"))
    output = ComplexLocales(['zh-Hans']).result_transliterate(results)[0]
    assert output == "丹东市中医院, 锦山大街, 站前街道, 元宝区, 振兴区, 118000, 中国"


def test_transliterate_ps():
    """ Base transliteration test where the user does not know the local language
        and only knows a non-latin language

        Results should show that the result is transliterated to latin (for now)
        but all aspects in the users non latin locale sould be not in latin

        ISSUE RIGHT NOW: langdetect detects ps (Afghanistan) as ur (Pakistan)
        FIXED: With locale key search
    """
    variable = 'hospital in dandong'
    results = asyncio.run(search(f"{variable}"))
    output = ComplexLocales(['ps']).result_transliterate(results)[0]
    assert output == (
        "Dan Dong Shi Zhong Yi Yuan, Jin Shan Da Jie, Zhan Qian"
        " Jie Dao, Yuan Bao Qu, Zhen Xing Qu, 118000, چين"
    )


def test_transliterate_he():
    """ Base transliteration test where the user does not know the local language
        and only knows a non-latin language

        Results should show that the result is transliterated to latin (for now)
        but all aspects in the users non latin locale should be not in latin

        ISSUE RIGHT NOW: Hebrew is somehow flipped in the script
        FIXED: With locale key search
    """
    variable = 'hospital in dandong'
    results = asyncio.run(search(f"{variable}"))
    output = ComplexLocales(['he']).result_transliterate(results)[0]
    assert output == (
        "Dan Dong Shi Zhong Yi Yuan, Jin Shan Da Jie, Zhan Qian Jie Dao,"
        " Yuan Bao Qu, Zhen Xing Qu, 118000, סין"
    )


def test_transliterate_km():
    """ Base transliteration test where the user does not know the local language
        and only knows a non-latin language

        Results should show that the result is transliterated to latin (for now)
        but all aspects in the users non latin locale should be not in latin

        ISSUE RIGHT NOW: langdetect does not detect Cambodian
        FIXED: With locale key search
    """
    variable = 'hospital in dandong'
    results = asyncio.run(search(f"{variable}"))
    output = ComplexLocales(['km']).result_transliterate(results)[0]
    assert output == (
        "Dan Dong Shi Zhong Yi Yuan, Jin Shan Da Jie, Zhan Qian Jie Dao,"
        " Yuan Bao Qu, Zhen Xing Qu, 118000, ចិន"
    )


def test_transliterate_two():
    """ Base transliteration test where the user does not know the local language
        and only knows two latin languages (French and English), but the browser
        gives region-specific language (en-US).
    """
    variable = 'hospital in dandong'
    results = asyncio.run(search(f"{variable}"))
    output = ComplexLocales(['fr', 'en']).result_transliterate(results)[0]
    assert output == (
        "Dan Dong Shi Zhong Yi Yuan, Jinshan Main Street, Zhanqian Subdistrict,"
        " Yuanbao, Zhenxing, 118000, Chine"
    )


def test_transliterate_region():
    """ Base transliteration test where the user does not know the local language
        and only knows two latin languages (French and English), but the browser gives
        region specific language (en-US)

        Result is shown in French and English, with preference for French
        All non-latin components should then be translated to Latin
    """
    variable = 'hospital in dandong'
    test_header = "fr,en-GB;q=0.9,en-US;q=0.8,en;q=0.7"

    results = asyncio.run(search(f"{variable}"))
    output = ComplexLocales(test_header).result_transliterate(results)[0]
    assert output == (
        "Dan Dong Shi Zhong Yi Yuan, Jinshan Main Street, Zhanqian Subdistrict,"
        " Yuanbao, Zhenxing, 118000, Chine"
    )


def test_parsing_transliterate():
    """ Base HTML Header Parsing test + Transliteration
        to see if it can properly concatanate and
        extract the proper naming conventions

        Checks if the prototype can differentiate between English Variants
    """
    test_header = "en-CA,en-GB;q=0.9,en-US;q=0.8,en;q=0.7"
    variable = 'school in dandong'
    results = asyncio.run(search(f"{variable}"))
    output = ComplexLocales(test_header).result_transliterate(results)[0]
    assert output == (
        "Dan Dong Shi Di Liu Zhong Xue, Qi Wei Lu, Zhanqian Subdistrict,"
        " Dandong, Zhenxing, 118000, China"
    )


def test_canto_transliterate():
    """ Cantonese transliteration to Latin test

        Tests to see if transliteration can accurately convert to
        Cantonese
    """
    test_str = "梁國雄"
    output = ComplexLocales().decode_canto(test_str)
    assert output == "Leung Gwok Hung"


def test_load_languages():
    lang_data = load_lang_info()
    for language_code in lang_data:
        language = lang_data.get(language_code)
        latin = (language['written'] == 'lat')
        assert latin == language['latin']
