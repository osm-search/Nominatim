
import sys
from pykakasi import kakasi

def transliterate(text):
    kks = kakasi()
    kks.setMode("H", "a")  # Hiragana to ascii
    kks.setMode("K", "a")  # Katakana to ascii
    kks.setMode("J", "a")  # Kanji to ascii
    kks.setMode("r", "Hepburn")
    converter = kks.getConverter()
    result = converter.do(text)
    return result

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = sys.argv[1]
        print(transliterate(text))
