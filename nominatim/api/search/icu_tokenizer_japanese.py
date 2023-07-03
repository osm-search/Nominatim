import MeCab

import re

def transliterate(text: str) -> str:
    #pattern = '''(...??[都道府県])((?:旭川|伊達|石狩|盛岡|奥州|田村|南相馬|那須塩原|東村山|武蔵村山|羽村|十日町|上越|富山|野々市|大町|蒲郡|四日市|姫路|大和郡山|廿日市|下松|岩国|田川|大村|宮古|富良野|別府|佐伯|黒部|小諸|塩尻|玉野|周南)市|(?:余市|高市|[^市]{2,3}?)郡(?:玉村|大町|.{1,5}?)[町村]|(?:.{1,4}市)?[^町]{1,4}?区|.{1,7}?[市町村])(.+)'''
    #result = re.match(pattern, text)
    pattern = r'''
            (...??[都道府県])            # [group1] prefecture
            (                           # [group2] municipalities (city/wards/towns/villages)
              (?:旭川|伊達|石狩|盛岡|奥州|田村|南相馬|那須塩原|東村山|武蔵村山|羽村|十日町|上越|富山|野々市|大町|蒲郡|四日市|姫路|大和郡山|廿日市|下松|岩国|田川|大村|宮古|富良野|別府|佐伯|黒部|小諸|塩尻|玉野|周南)市    
                                                                         # city (市)
              |(?:余市|高市|[^市]{2,3}?)郡(?:玉村|大町|.{1,5}?)[町村]    # towns villages (郡の町村)
              |(?:.{1,4}市)?[^町]{1,4}?区                                # city/wards (区)
              |.{1,7}?[市町村]                                           # other cities
            )
            (.+)                        # [group3] other words
            '''

    result = re.match(pattern, text, re.VERBOSE) # perform normalization using the pattern
    # this is for debug
    '''if result:
        print(result.group(1)) 
        print(result.group(2)) 
        print(result.group(3))''' 
    
    # split group 3 using the normalization library
    wakati = MeCab.Tagger("-Owakati")
    split_text = wakati.parse(result.group(3)).split()
    # print(text,split_text) # for debug
    # combine group 1 and group 2
    joined_group = ''.join([result.group(1),', ',result.group(2),','])
    # combine group 3 with spaces
    joined_group3 = ' '.join(split_text)
    # combine all the words
    joined_text = ' '.join([joined_group, joined_group3])
    return joined_text
# this is for debug
'''tmp = '東京都千代田区丸の内１－２'
print(transliterate(tmp))'''

