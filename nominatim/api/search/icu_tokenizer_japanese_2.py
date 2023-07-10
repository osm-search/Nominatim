import MeCab
import re

def convert_kanji_sequence_to_number(sequence):
  kanji_map = {
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
    # wakati = MeCab.Tagger("-Owakati")
    wakati = MeCab.Tagger('-Owakati -d /var/lib/mecab/dic/debian -u /home/miku/mecab/addr.dic')
    split_text = wakati.parse(text).split()
    #print(split_text)    
    combined_text = ', '.join(split_text[:3]) + ' ' + ' '.join(split_text[3:])
    return combined_text
# this is for debug
tmp = '東京都千代田区丸の内１－２'
print(transliterate(tmp))

