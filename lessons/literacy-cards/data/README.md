# Данные для корпуса слов

Сюда кладутся **авторские** списки (не сырой dump с OCR):

- `ru-wordlist-v1.txt` — одна лемма на строку, NFC, нижний регистр для cue
- `en-wordlist-v1.txt` — то же для EN

Генерация (план): `tools/corpus_ru_wordlist.py` из открытого частотного источника + фильтры длины/символов.

`build_word_cards.py --wordlist data/ru-wordlist-v1.txt` → JPEG + frames в manifest.
