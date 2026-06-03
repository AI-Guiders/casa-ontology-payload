# Lesson 01 — кириллица, одна гарнитура

Один кадр = одна буква (только глиф на JPEG). Moment: visual + **lexical** (не math):

```json
{"visual_frame": "letter-a-lower-sans"},
{"lexical": {"cue": "a", "correct": "а", "register": "lower", "concept_id": "grapheme.cyrl.a.lower"}}
```

| Поле | Смысл |
|------|--------|
| `cue` | латинский slug буквы (стабильный ключ) |
| `register` | `lower` \| `upper` |
| `correct` | символ на кадре |
| `concept_id` | `grapheme.cyrl.{cue}.{register}` |

Сборка: `python lessons/literacy-cards/tools/build_letter_cards.py`  
Lab: `lab/visual-curriculum/` — `CurriculumLabSession`, `lex_steps.lex_step` (общий vis↔lex); runners literacy: `micro-literacy/`  
Контраст регистра **а ↔ А** (после полного алфавита, если probe путает lower/upper):  
`python lab/visual-curriculum/micro-literacy/run_a_register_contrast.py`

Контраст регистра **другие cue → потом a** (если только а/А ambiguous):  
`python lab/visual-curriculum/micro-literacy/run_register_contrast_cues.py --rounds 2 --finale-a-rounds 6`

Контраст гранулярности **буква ↔ слово** (чередование grapheme / lang.word, богаче `correct` в episodic):  
`python lab/visual-curriculum/micro-literacy/run_grapheme_word_contrast.py`

**Метаязык + guided а/А** (text tract):  
`python lessons/literacy-cards/tools/build_meta_language_cards.py --wave 1`  
`python lessons/literacy-cards/tools/build_meta_language_cards.py --wave 2`  
`python lab/visual-curriculum/micro-literacy/run_meta_language_pilot.py`  
`python lab/visual-curriculum/micro-literacy/run_meta_language_wave2.py`  
`python lessons/literacy-cards/tools/build_register_phrase_cards.py`  
`python lab/visual-curriculum/micro-literacy/run_upper_register_contrast.py --cues b v --rounds 2`  
`python lab/visual-curriculum/micro-literacy/run_register_category.py --exemplar-cues b v --names-rounds 0`  
**Чистая категория** (без кадров букв в moment):  
`python lab/visual-curriculum/micro-literacy/run_register_category_pure.py --rounds 5`  
Мета «не знаю» (карточка ↔ `lang.word.ne_znayu`):  
`python lab/visual-curriculum/micro-literacy/run_meta_ne_znayu_pure.py --rounds 6`  
Переименование legacy id в store (без переучивания):  
`python tools/migrate_lex_concept_store.py` (сначала `--dry-run`)
