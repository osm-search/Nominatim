# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for transliteration with the complex locales function
"""
import pytest

from nominatim_api.localization import TransliterateLocales
from nominatim_api.config import Configuration
from nominatim_db.data import lang_info


class MockResult:   # try and use address and result directly
    def __init__(self, address_rows):
        self.address_rows = address_rows
        self.country_code = 'cn'
        self.region_lang = ""


class MockAddressRow:
    def __init__(self, local_name, names, isaddress):
        self.local_name = local_name
        self.names = names
        self.isaddress = isaddress


def mock_hospital_results():
    """Factory function to create fresh mock hospital results so changes arent saved."""
    return [
        # https://nominatim.openstreetmap.org/ui/details.html?osmtype=W&osmid=1379522103&class=amenity
        MockResult([
            MockAddressRow(
                local_name="丹东市中医院",
                names={'name': '丹东市中医院'},
                isaddress=True
            ),
            MockAddressRow(
                local_name="锦山大街",
                names={
                    'ref': 'G331', 'name': '锦山大街', 'name:en': 'Jinshan Main Street',
                    'name:zh': '锦山大街', 'name:zh-Hant': '錦山大街'
                    },
                isaddress=True
            ),
            MockAddressRow(
                local_name="站前街道",
                names={
                    "name:zh-Hans": "站前街道",
                    "name:en": "Zhanqian Subdistrict",
                    },
                isaddress=True
            ),
            MockAddressRow(
                local_name="元宝区",
                names={
                    'name': '元宝区', 'name:en': 'Yuanbao', 'name:fr': 'Yuanbao', 'name:ja': '元宝区',
                    'name:ko': '위안바오구', 'name:zh': '元宝区', 'alt_name': '元宝', 'alt_name:en': 'Yuanbao'
                    ' District', 'alt_name:zh': '元宝', 'name:zh-Hans': '元宝区', 'name:zh-Hant': '元寶區'
                    },
                isaddress=True
            ),
            MockAddressRow(
                local_name="振兴区",
                names={
                    'name': '振兴区', 'name:en': 'Zhenxing', 'name:zh': '振兴区', 'alt_name': '振兴',
                    'alt_name:en': 'Zhenxing District', 'alt_name:zh': '振兴', 'name:zh-Hans': '振兴区',
                    'name:zh-Hant': '振興區', 'name:zh-Latn-pinyin': 'Zhènxīng Qū'
                    },
                isaddress=True
            ),
            MockAddressRow(
                local_name="118000",
                names={
                    "postcode": "118000",
                },
                isaddress=True
            ),
            MockAddressRow(
                local_name="中国",
                names={
                    "name:zh-Hans": "中国", "name:en": "China", "name:fr": "Chine",
                    "name:he": "סין", "name:ps": "چين"
                },
                isaddress=True
            ),
        ])
    ]


@pytest.mark.parametrize("header,expected_output", [
    ("zh-Hans", "丹东市中医院, 锦山大街, 站前街道, 元宝区, 振兴区, 118000, 中国"),
    (None, "Dan Dong Shi Zhong Yi Yuan, Jin Shan Da Jie, Zhan Qian Jie Dao,"
     " Yuan Bao Qu, Zhen Xing Qu, 118000, Zhong Guo"),
    ("en", "Dan Dong Shi Zhong Yi Yuan, Jinshan Main Street, Zhanqian"
     " Subdistrict, Yuanbao, Zhenxing, 118000, China"),
    ("he", "Dan Dong Shi Zhong Yi Yuan, Jin Shan Da Jie, Zhan Qian Jie Dao,"
     " Yuan Bao Qu, Zhen Xing Qu, 118000, סין"),
    ("ps", "Dan Dong Shi Zhong Yi Yuan, Jin Shan Da Jie, Zhan Qian"
     " Jie Dao, Yuan Bao Qu, Zhen Xing Qu, 118000, چين"),
    ("fr;q=0.8,en;q=0.2", "Dan Dong Shi Zhong Yi Yuan, Jinshan Main Street, Zhanqian Subdistrict,"
     " Yuanbao, Zhenxing, 118000, Chine")
])
def test_transliterate_hospital(header, expected_output):
    """Parameterized test for transliteration of hospitals in Dandong."""
    results = mock_hospital_results()
    if header:
        langs = TransliterateLocales().from_accept_languages(header).languages
        output = TransliterateLocales(langs).result_transliterate(results)[0]
    else:
        output = TransliterateLocales().result_transliterate(results)[0]

    assert output == expected_output


# def test_transliterate():
#     """ Base Transliteration Test """
#     variable = 'school in dandong'
#     results = asyncio.run(search(f"{variable}"))
#     print(results)  # not resulting:( pytest mocking for now, could maybe try a small import?
#     # set locale name here first, will probably need to further integrate with display name
#     SimpleLocales().localize_results(results)

#     output = TransliterateLocales().result_transliterate(results)[0]
#     assert output == (
#         "Dan Dong Shi Di Liu Zhong Xue, Qi Wei Lu, Zhan Qian Jie Dao, "
#         "Dan Dong Shi, Zhen Xing Qu, 118000, Zhong Guo"
#     )


# def test_transliterate_english():
#     """ Base Transliteration Test to English

#         Results should show that the result is transliterated to latin
#         Except for components that have English locales already set
#     """
#     variable = 'school in dandong'
#     results = asyncio.run(search(f"{variable}"))
#     output = TransliterateLocales(['en']).result_transliterate(results)[0]
#     assert output == (
#         "Dan Dong Shi Di Liu Zhong Xue, Qi Wei Lu, Zhanqian Subdistrict, "
#         "Dandong, Zhenxing, 118000, China"
#     )


# def test_parsing_transliterate():
#     """ Base HTML Header Parsing test + Transliteration
#         to see if it can properly concatanate and
#         extract the proper naming conventions

#         Checks if the prototype can differentiate between English Variants
#     """
#     test_header = "en-CA,en-GB;q=0.9,en-US;q=0.8,en;q=0.7"
#     variable = 'school in dandong'
#     results = asyncio.run(search(f"{variable}"))
#     output = TransliterateLocales(test_header).result_transliterate(results)[0]
#     assert output == (
#         "Dan Dong Shi Di Liu Zhong Xue, Qi Wei Lu, Zhanqian Subdistrict,"
#         " Dandong, Zhenxing, 118000, China"
#     )


def test_canto_transliterate():
    """ Cantonese transliteration to Latin test

        Tests to see if transliteration can accurately convert to
        Cantonese
    """
    test_str = "梁國雄"
    output = TransliterateLocales().decode_canto(test_str)
    assert output == "Leung Gwok Hung"


def test_load_languages():
    config = Configuration(None)
    lang_info.setup_lang_config(config)

    # Access language data
    for language_code, _ in lang_info.iterate():
        language = lang_info.get(language_code)
        latin = (language['written'] == 'lat')
        assert latin == language['latin']
