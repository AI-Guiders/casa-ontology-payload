# Lesson 03 — слова целиком

Один кадр = одно слово (цельный силуэт строки). Moment:

```json
{"visual_frame": "word-mama-sans"},
{"lexical": {
  "cue": "мама",
  "correct": "мама",
  "concept_id": "lang.word.mama",
  "lattice_id": "lexicon-ru"
}}
```

Probe: `predict_lex_for_vis_cue` → `lang.word.mama`, не разбор по буквам.

Сборка: `python lessons/literacy-cards/tools/build_word_cards.py`
