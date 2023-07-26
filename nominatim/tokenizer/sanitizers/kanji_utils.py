# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
This is a file for a function that converts Kanji (Japanese) numerals to Arabic numerals.
"""

def convert_kanji_sequence_to_number(sequence: str) -> str:
    """Converts Kanji numbers to Arabic numbers
    """
    kanji_map = {
      '零': '0',
      '一': '1',
      '二': '2',
      '三': '3',
      '四': '4',
      '五': '5',
      '六': '6',
      '七': '7',
      '八': '8',
      '九': '9'
    }
    converted = ''
    current_number = ''
    for char in sequence:
        if char in kanji_map:
            current_number += kanji_map[char]
        else:
            converted += current_number
            current_number = ''
            converted += char
    converted += current_number
    return converted
