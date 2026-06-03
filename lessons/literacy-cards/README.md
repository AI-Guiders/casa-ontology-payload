# literacy-cards — класс словесности

Один **visual** tract (`retinal_lrgb`) + **lexical** episodic (`alphabet-*`, `syllables-*`, `lexicon-*`).  
Полный поток: [design/CASA-literacy-roadmap-v1.md](../../design/CASA-literacy-roadmap-v1.md).

## Сейчас

| Lesson | Содержание |
|--------|------------|
| `lesson-01-letters-cyrl` | 33×2 буквы RU |
| `lesson-03-words-cyrl` | 8 слов пилот |
| `lesson-05-syllables-cyrl` | 56 слогов |
| `lesson-06-words-cyrl-corpus` | 331 слово (seed; wordfreq опционально) |
| `lesson-11-letters-latn` | 26×2 EN |

## Сборка

```powershell
python lessons/literacy-cards/tools/build_letter_cards.py
python lessons/literacy-cards/tools/build_syllable_cards.py
python lessons/literacy-cards/tools/build_letter_cards_latn.py
python lessons/literacy-cards/tools/corpus_wordlist.py --lang ru -n 500
python lessons/literacy-cards/tools/build_word_cards.py --wordlist lessons/literacy-cards/data/ru-wordlist-v1.txt --limit 500
```

## Lab (von-neumann)

```powershell
python lab/visual-curriculum/micro-literacy/run_micro_stage.py --stage stage-01-grapheme-cyrl
python lab/visual-curriculum/probe_grapheme_quiz.py
```

Корпус слов — пачками: `--limit 50 --offset 0` (один sleep на слово).

## Дальше (RU + EN)

1. Ingest всех букв RU (micro, sleep на пару).
2. Слоги RU — целые кадры на `syllables-ru`.
3. Слова корпуса РЯ — частотный список → `lesson-06-words-cyrl-corpus`.
4. Шрифты (faces) для букв и слов.
5. Зеркало **EN**: `lesson-11-letters-latn`, corpus на `lexicon-en`.
