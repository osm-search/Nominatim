# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for language parsing with the complex locales function
"""
from nominatim_api.localization.complex import ComplexLocales


def test_parsing_en():
    """ Base HTML Header Parsing test to see if it can properly concatanate and
        extract the proper naming conventions

        Checks if the prototype can differentiate between English Variants
    """
    test_header = "en-CA,en-GB;q=0.9,en-US;q=0.8,en;q=0.7"
    output = ComplexLocales().from_accept_languages(test_header).languages
    assert output == ['en-CA', 'en', 'en-GB', 'en-US']


def test_parsing_zh():
    """ Base HTML Header Parsing test to see if it can properly concatanate and
        extract the proper naming conventions

        Checks if the prototype can differentiate between Chinese Variants
    """
    test_header = "zh;q=0.9,zh-cn;q=0.8,zh-Hans-CN;q=0.7"
    output = ComplexLocales().from_accept_languages(test_header).languages
    assert output == ['zh', 'zh-Hans', 'zh-Hant', 'yue', 'zh-cn', 'zh-Hans-CN']


def test_parsing_zh_en():
    """ Base HTML Header Parsing test to see if it can properly concatanate and
        extract the proper naming conventions

        Checks if the prototype can differentiate between Chinese Variants and English Variants
    """
    test_header = "zh;q=0.4, en-US, zh-cn;q=0.8,zh-Hans-CN;q=0.7, en-UK;q=0.1"
    output = ComplexLocales().from_accept_languages(test_header).languages
    assert output == ['en-US', 'en', 'zh-cn', 'zh-Hans', 'zh-Hans-CN',
                      'zh', 'zh-Hant', 'yue', 'en-UK']
