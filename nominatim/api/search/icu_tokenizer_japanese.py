import MeCab
import re

def transliterate(text: str) -> str:
    wakati = MeCab.Tagger("-Owakati")
    
    pattern = '''(...??[都道府県])((?:旭川|伊達|石狩|盛岡|奥州|田村|南相馬|那須塩原|東村山|武蔵村山|羽村|十日町|上越|富山|野々市|大町|蒲郡|四日市|姫路|大和郡山|廿日市|下松|岩国|田川|大村|宮古|富良野|別府|佐伯|黒部|小諸|塩尻|玉野|周南)市|(?:余市|高市|[^市]{2,3}?)郡(?:玉村|大町|.{1,5}?)[町村]|(?:.{1,4}市)?[^町]{1,4}?区|.{1,7}?[市町村])(.+)'''
    result = re.match(pattern, text)
    #if result:
        #print(result.group(1)) 
        #print(result.group(2)) 
        #print(result.group(3)) 

    split_text = wakati.parse(result.group(3)).split()
    #print(text,split_text)
    joined_group = ''.join([result.group(1),', ',result.group(2),','])
    joined_group3 = ' '.join(split_text)
    joined_text = ' '.join([joined_group, joined_group3])
    return joined_text
tmp = '東京都千代田区丸の内１－２'
print(transliterate(tmp))
