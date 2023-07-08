import MeCab
import re

def convert_kanji_sequence_to_number(sequence):
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

'''
def convert_zenkaku_sequence_to_number(sequence):
  zenkaku_map = {
    '１': '1',
    '２': '2',
    '３': '3',
    '４': '4',  
    '５': '5',
    '６': '6',
    '７': '7',
    '８': '8',
    '９': '9'
  }
  converted = ''
  current_number = ''
  for char in sequence:
    if char in zenkaku_map:
      current_number += zenkaku_map[char]
    else:
      converted += current_number
      current_number = ''
      converted += char
  converted += current_number
  return converted
'''

def transliterate(text: str) -> str:
    # split all words first using the normalization library
    text = convert_kanji_sequence_to_number(text)    
    # text = convert_zenkaku_sequence_to_number(text)
    wakati = MeCab.Tagger("-Owakati")
    split_text = wakati.parse(text).split()
    #trigger_words = ['都','道','府','県','市','区','町','村','群','丁目']
    trigger_words = ['都','道','府','県','市','区','町','村','群']
    for i in range(len(split_text)):
      if split_text[i] in trigger_words and i > 0:
        split_text[i-1] += split_text[i] + ','
        split_text[i] = ''
    combined_text = ' '.join(filter(None, split_text))
    return combined_text
# this is for debug
tmp = '東京都千代田区丸の内１－２'
print(transliterate(tmp))

