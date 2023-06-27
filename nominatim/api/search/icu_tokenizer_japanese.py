import MeCab

def transliterate(text: str) -> str:
    wakati = MeCab.Tagger("-Owakati")
    split_text = wakati.parse(text).split()
    #print(text,split_text)
    joined_text = ' '.join(split_text)
    return joined_text
#tmp = "西新宿3丁目"
#print(transliterate(tmp))
