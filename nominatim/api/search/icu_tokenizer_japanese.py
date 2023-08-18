# from nominatim.tokenizer.sanitizers.tag_japanese import convert_kanji_sequence_to_number

# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
This file divides Japanese addresses into three categories:
prefecture, municipality, and other.
The division is not strict but simple using these keywords.
Based on this division, icu_tokenizer.py inserts
a SOFT_PHRASE break between the divided words 
and penalizes the words with this SOFT_PHRASE
to lower the search priority.
"""
import re
from typing import List
from nominatim.api.search import query as qmod

def transliterate(text: str) -> str:
    """
    This function performs a division on the given text using a regular expression.
    """
    pattern_full = r'''
               (...??[都道府県])            # [group1] prefecture
               (.+?[市区町村])              # [group2] municipalities (city/wards/towns/villages)
               (.+)                         # [group3] other words
               '''
    pattern_1 = r'''
               (...??[都道府県])            # [group1] prefecture
               (.+)                         # [group3] other words
               '''
    pattern_2 = r'''
               (.+?[市区町村])              # [group2] municipalities (city/wards/towns/villages)
               (.+)                         # [group3] other words
               '''
    result_full = re.match(pattern_full, text, re.VERBOSE)
    result_1 = re.match(pattern_1, text, re.VERBOSE)
    result_2 = re.match(pattern_2, text, re.VERBOSE)
    if result_full is not None:
        joined_group = ''.join([
                                result_full.group(1),
                                ', ',
                                result_full.group(2),
                                ', ',
                                result_full.group(3)
                               ])
        return joined_group
    if result_1 is not None:
        joined_group = ''.join([result_1.group(1),', ',result_1.group(2)])
        return joined_group
    if result_2 is not None:
        joined_group = ''.join([result_2.group(1),', ',result_2.group(2)])
        return joined_group
    return text

def split_key_japanese_phrases(
    phrases: List[qmod.Phrase]
) -> List[qmod.Phrase]:
    """Split a Japanese address using japanese_tokenizer.
    """
    splited_address = list(filter(lambda p: p.text,
                            (qmod.Phrase(p.ptype, transliterate(p.text))
                            for p in phrases)))
    return splited_address
