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
from nominatim_api.data import lang_info
from nominatim_api.results import AddressLine, SearchResult


def hospital_result():
    result = SearchResult(
        source_table=None,
        category=('place', 'city'),
        centroid=(0.0, 0.0)
    )

    result.country_code = 'cn'
    result.address_rows = [
        AddressLine(
            category=('amenity', 'hospital'),
            names={'name': '丹东市中医院'},
            fromarea=True,
            isaddress=True,
            rank_address=30,
            distance=0.0,
            place_id=100109,
            osm_object=('N', 12112291499),
            extratags={},
            admin_level=15,
            local_name='丹东市中医院'
        ),
        AddressLine(
            category=('highway', 'trunk'),
            names={'ref': 'G331', 'name': '锦山大街', 'name:en': 'Jinshan Main Street',
                   'name:zh': '锦山大街', 'name:zh-Hant': '錦山大街'},
            fromarea=True, isaddress=True, rank_address=26,
            distance=0.0, place_id=100287, osm_object=('W', 1209291912),
            extratags={'oneway': 'yes', 'surface': 'asphalt'},
            admin_level=15, local_name=None),
        AddressLine(
            category=('boundary', 'administrative'),
            names={'name': '广济街道', 'name:en': 'Guangji Subdistrict', 'name:ko': '위안바오 구',
                   'name:zh': '广济街道', 'alt_name': 'Guangji;广济', 'official_name': '广济街道',
                   '_place_name:en': 'Guangji', '_place_alt_name': 'Guangji Subdistrict;广济',
                   'name:zh-Hans': '广济街道', 'name:zh-Hant': '廣濟街道', 'name:zh-Latn-pinyin':
                   'Yuánbăo Qū'},
            fromarea=True, isaddress=False, rank_address=20, distance=2.085130332117237e-08,
            place_id=100168, osm_object=('R', 9660093), admin_level=8, local_name=None),
        AddressLine(
            category=('boundary', 'administrative'),
            names={'name': '兴东街道', 'name:en': 'Xingdong Subdistrict', 'name:zh': '兴东街道',
                   'alt_name': 'Xingdong;兴东', 'official_name': '兴东街道', '_place_name:en':
                   'Xingdong', 'name:ja': '興東街道', '_place_alt_name': 'Xingdong Subdistrict;兴东',
                   'name:zh-Hans': '兴东街道', 'name:zh-Hant': '興東街道'},
            fromarea=True, isaddress=False, rank_address=20, distance=0.003425476071486737,
            place_id=100222, osm_object=('R', 9660099), admin_level=8, local_name=None),
        AddressLine(
            category=('boundary', 'administrative'),
            names={'name': '六道口街道', 'name:en': 'Liudaokou Subdistrict', 'name:zh': '六道口街道',
                   'alt_name': 'Liudaokou;六道口', 'official_name': '六道口街道',
                   'name:ja': '六道口街道', '_place_alt_name': 'Liudaokou Subdistrict;六道口',
                   'name:zh-Hans': '六道口街道', 'name:zh-Hant': '六道口街道'},
            fromarea=True, isaddress=False, rank_address=20, distance=0.0008695703526356822,
            place_id=100332, osm_object=('R', 9660097), admin_level=8, local_name=None),
        AddressLine(
            category=('boundary', 'administrative'),
            names={'name': '站前街道', 'name:en': 'Zhanqian Subdistrict', 'name:zh': '站前街道',
                   'alt_name': 'Zhanqian;站前', 'official_name': '站前街道', '_place_name:en':
                   'Zhanqian', 'name:ja': '駅前街道', '_place_alt_name': 'Zhanqian Subdistrict;站前',
                   'name:zh-Hans': '站前街道', 'name:zh-Hant': '站前街道'},
            fromarea=True, isaddress=True, rank_address=20, distance=0.0035797314418621385,
            place_id=100044, admin_level=8, local_name=None),
        AddressLine(
            category=('place', 'city'),
            names={'name': '振兴区', 'name:en': 'Zhenxing', 'name:fr': 'Zhenxing', 'name:ja': '振興区',
                   'name:ko': '전싱구', 'name:zh': '振兴区', 'alt_name': '振兴', 'alt_name:zh': '振兴',
                   'name:zh-Hans': '振兴区', 'name:zh-Hant': '振興區'},
            fromarea=False, isaddress=False, rank_address=16, distance=0.034584735617470413,
            place_id=101842, osm_object=('N', 6416739765), admin_level=15, local_name=None),
        AddressLine(
            category=('place', 'city'),
            names={'name': '丹东市', 'name:ar': 'داندونغ', 'name:az': 'Dandun', 'name:bg': 'Дандун',
                   'name:cs': 'Tan-tung', 'name:de': 'Dandong', 'name:en': 'Dandong', 'name:et':
                   'Dandong', 'name:eu': 'Dandong', 'name:fi': 'Dandong', 'name:fr': 'Dandong',
                   'name:hi': 'डेन्डोंग', 'name:hr': 'Dandong', 'name:ja': '丹東市', 'name:ko': '단둥시',
                   'name:ru': 'Даньдун', 'name:sv': 'Dandong', 'name:vi': 'Đan Đông', 'name:zh':
                   '丹东市', 'int_name': 'Dandong', 'old_name': '安东市', 'short_name': '丹东',
                   'alt_name:en': 'Dandong City', 'alt_name:ko': '단동시', 'old_name:en':
                   'Andong;Antung', 'old_name:ja': '安東市', 'old_name:ko': '안둥시', 'old_name:zh':
                   '安东市', 'name:zh-Hans': '丹东市', 'name:zh-Hant': '丹東市', 'short_name:ja':
                   '丹東', 'short_name:ko': '단둥;단동', 'short_name:zh': '丹东',
                   'name:zh-Latn-pinyin': 'Dāndōng Shì'},
            fromarea=False, isaddress=False, rank_address=16, distance=0.002896152207101176,
            place_id=100418, osm_object=('N', 244078242), admin_level=15, local_name=None),
        AddressLine(
            category=('place', 'city'),
            names={'name': '元宝区', 'name:en': 'Yuanbao', 'name:fr': 'Yuanbao', 'name:ja':
                   '元宝区', 'name:ko': '위안바오구', 'name:zh': '元宝区', 'alt_name': '元宝',
                   'alt_name:en': 'Yuanbao District', 'alt_name:zh': '元宝', 'name:zh-Hans':
                   '元宝区', 'name:zh-Hant': '元寶區'},
            fromarea=False, isaddress=True, rank_address=16, distance=0.0014780993108928506,
            place_id=100117, osm_object=('N', 6416739764), admin_level=15, local_name=None),
        AddressLine(
            category=('place', 'district'),
            names={'name': '振兴区', 'name:en': 'Zhenxing', 'name:zh': '振兴区', 'alt_name': '振兴',
                   'alt_name:en': 'Zhenxing District', 'alt_name:zh': '振兴', 'name:zh-Hans': '振兴区',
                   'name:zh-Hant': '振興區', 'name:zh-Latn-pinyin': 'Zhènxīng Qū'},
            fromarea=False, isaddress=True, rank_address=12, distance=0.100276398631487,
            place_id=101581, osm_object=('N', 244084848), admin_level=15, local_name=None),
        AddressLine(
            category=('place', 'postcode'), names={'ref': '118000'}, fromarea=False, isaddress=True,
            rank_address=5, distance=0.0, place_id=None, osm_object=None, extratags=None,
            admin_level=None, local_name='118000'),
        AddressLine(
            category=('place', 'country_code'),
            names={'ref': 'cn'}, fromarea=True, isaddress=False, rank_address=4, distance=0.0,
            place_id=None, osm_object=None, extratags={}, admin_level=None, local_name=None),
        AddressLine(
            category=('place', 'country'),
            names={'name': '中国', 'name:ab': 'Чынҭ', 'name:af': 'China', 'name:ak': 'China',
                   'name:am': 'የቻይና', 'name:an': 'China', 'name:ar': 'الصين', 'name:as': 'চীন',
                   'name:av': 'Чин', 'name:ay': 'China', 'name:az': 'Çin', 'name:ba': 'Ҡытай',
                   'name:be': 'Кітай', 'name:bg': 'Китай', 'name:bh': 'चीन', 'name:bi': 'Jaena',
                   'name:bm': 'China', 'name:bn': 'গণচীন', 'name:bo': 'ཀྲུང་གོ།', 'name:br': 'Sina',
                   'name:bs': 'Kina', 'name:ca': 'Xina', 'name:ce': 'Цийн-мохк', 'name:ch': 'China',
                   'name:co': 'China', 'name:cs': 'Čína', 'name:cu': 'Срѣдинꙗнє', 'name:cv':
                   'Китай', 'name:cy': 'Tsieina', 'name:da': 'Kina', 'name:de': 'China', 'name:dv':
                   'ސީނުކަރަ', 'name:dz': 'རྒྱ་ནག', 'name:ee': 'China', 'name:el': 'Κίνα',
                   'name:en': 'China', 'name:eo': 'Ĉinio', 'name:es': 'China', 'name:et': 'Hiina',
                   'name:eu': 'Txina', 'name:fa': 'چین', 'name:ff': 'Ciina', 'name:fi': 'Kiina',
                   'name:fj': 'Jaina', 'name:fo': 'Kina', 'name:fr': 'Chine', 'name:fy': 'Sina',
                   'name:ga': 'Síne', 'name:gd': 'Sìona', 'name:gl': 'China', 'name:gn': 'Chína',
                   'name:gu': 'ચીન', 'name:gv': 'Sheen', 'name:ha': 'Sin', 'name:he': 'סין',
                   'name:hi': 'चीनी', 'name:hr': 'Kina', 'name:ht': 'Chin', 'name:hu': 'Kína',
                   'name:hy': 'Չինաստան', 'name:ia': 'China', 'name:id': 'Tiongkok', 'name:ie':
                   'China', 'name:ig': 'Chaina', 'name:ik': 'China', 'name:io': 'Chinia', 'name:is':
                   'Kína', 'name:it': 'Cina', 'name:iu': 'ᓴᐃᓇ', 'name:ja': '中国', 'name:jv': 'Cina',
                   'name:ka': 'ჩინეთი', 'name:kg': 'Sina', 'name:ki': 'China', 'name:kk': 'Қытай',
                   'name:kl': 'Kina', 'name:km': 'ចិន', 'name:kn': 'ಚೀನಿ', 'name:ko': '중국',
                   'name:ks': 'چیٖن', 'name:ku': 'Çîn', 'name:kv': 'Китай', 'name:kw': 'China',
                   'name:ky': 'Кытай', 'name:la': 'Sinae', 'name:lb': 'China', 'name:lg': 'Cayina',
                   'name:li': 'China', 'name:ln': 'Sína', 'name:lo': 'ປະເທດຈີນ',
                   'name:lv': 'Ķīna', 'name:mg': 'Sina', 'name:mi': 'Haina', 'name:mk': 'Кина',
                   'name:ml': 'ചീന', 'name:mn': 'Хятад', 'name:mr': 'चीन', 'name:ms': 'China',
                   'name:mt': 'Ċina', 'name:my': 'တရုတ်', 'name:na': 'Tsiene', 'name:nb': 'Kina',
                   'name:ne': 'चीन', 'name:nl': 'China', 'name:nn': 'Kina', 'name:no': 'Kina',
                   'name:nv': 'Tsiiʼyishbizhí Dineʼé Bikéyah', 'name:ny': 'China',
                   'name:oc': 'China', 'name:om': 'Chaayinaan', 'name:or': 'ଚୀନ', 'name:os':
                   'Китай', 'name:pa': 'ਚੀਨ', 'name:pl': 'Chiny', 'name:ps': 'چين', 'name:pt':
                   'China', 'name:qu': 'Chunkuk', 'name:rm': 'China', 'name:rn':
                   'Ubushinwa', 'name:ro': 'China', 'name:ru': 'Китай', 'name:rw':
                   'Ubushinwa', 'name:sc': 'Cina', 'name:sd': 'چين', 'name:se': 'Kiinná',
                   'name:sg': 'Sînä', 'name:sh': 'Kina', 'name:si': 'චීනය', 'name:sk': 'Čína',
                   'name:sl': 'Kitájska', 'name:sm': 'Saina', 'name:sn': 'China', 'name:so':
                   'Shiinaha', 'name:sq': 'Kina', 'name:sr': 'Кина', 'name:ss': 'iShayina',
                   'name:st': 'Tjhaena', 'name:su': 'Tiongkok', 'name:sv': 'Kina',
                   'name:sw': 'China', 'name:ta': 'சீனா', 'name:te': 'చైనా', 'name:tg':
                   'Хито́й', 'name:th': 'ประเทศจีน', 'name:ti': 'የቻይና', 'name:tk': 'Hytaý',
                   'name:tl': 'Tsina', 'name:tn': 'China', 'name:to': 'Siaina', 'name:tr':
                   'Çin', 'name:ts': 'Chayina', 'name:tt': 'Кытай', 'name:tw': 'China',
                   'name:ty': 'Tinitō', 'name:ug': 'جۇڭخۇا خەلق جۇمھۇرىيىتى', 'name:uk':
                   'Кита́йська', 'name:ur': 'چین', 'name:uz': 'Xitoy', 'name:ve': 'China',
                   'name:vi': 'Trung Quốc', 'name:vo': 'Tsyinän', 'name:wo': 'Siin',
                   'name:xh': 'IShayina', 'name:yi': 'כינע', 'name:yo': 'Ṣáínà',
                   'name:za': 'Cunghgoz', 'name:zh': '中国', 'name:zu': 'IShayina'},
            fromarea=False, isaddress=True, rank_address=4, distance=0.0, place_id=None,
            osm_object=None, extratags=None, admin_level=None, local_name=None)
        ]
    return result


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
     " Yuanbao, Zhenxing, 118000, Chine"),
    ("zh", "丹东市中医院, 锦山大街, 站前街道, 元宝区, 振兴区, 118000, 中国"),
])
def test_transliterate_hospital(header, expected_output):
    """Parameterized test for transliteration of hospitals in Dandong."""
    results = [hospital_result()]
    if header:
        langs = TransliterateLocales().from_accept_languages(header).languages
        print(langs)
        print(results[0].display_name)
        TransliterateLocales(langs).localize_results(results)
    else:
        TransliterateLocales().localize_results(results)

    assert results[0].display_name == expected_output


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
    output = TransliterateLocales().cantodecode(test_str)
    assert output == "Leung Gwok Hung"


def test_load_languages():
    config = Configuration(None)
    lang_info.setup_lang_config(config)

    # Access language data
    for language_code, _ in lang_info.iterate():
        language = lang_info.get(language_code)
        latin = (language['written'] == 'lat')
        assert latin == language['latin']
