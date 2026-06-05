# Словесность: дорожная карта RU + EN (v1)

**Статус:** канон потока после пилота (а/А, мама/кот/дом, probe 5/5). Lab: контраст **буква↔слово** — `run_grapheme_word_contrast.py` (подача, без правок sleep).

**Подача (hold):** корпус/shard слов — пауза; **исключение:** метаязык (`stage-07-meta-language`) и guided а/А — text tract, см. [CASA-literacy-class-v1.md](CASA-literacy-class-v1.md) § Guided attention.

| Стадия | lesson | Содержание |
|--------|--------|------------|
| `stage-07-meta-language` | `lesson-07-meta-language` | w1: буква, слово, заглавная, строчная |
| `stage-07b-meta-language-2` | `lesson-07-meta-language` | w2: не знаю, выбор, глагол, большая/маленькая, … |
| **meta pure (lab)** | — | `run_*_pure.py` — мета **без** `letter-*` в moment (канон 2026-06-03) |
| guided (lab) | — | vis + мета + grapheme — **не** единственный путь; а/А — шумный |
| **meta compare → measure → geom** | `visual-cards` | канон: [CASA-compare-greater-less-v1.md](CASA-compare-greater-less-v1.md) — nline gt/lt → meta → отрезки A/B (= / длиннее / короче) → длина на прямой → ширина на прямоугольниках → два круга → центр/радиус |
| **meta size (w2 текст)** | `lesson-07-meta-language` | `большая`/`маленькая` → `lang.meta.size.*`; **не** путь «круг больше» |

**Базовый протокол:** [CASA-literacy-class-v1.md](CASA-literacy-class-v1.md) · **общий принцип:** [CASA-learning-protocol-vis-math-v1.md](CASA-learning-protocol-vis-math-v1.md) § Vis↔lex

**Грамматика → связный текст:** [CASA-ADR-0030-grammar-literacy-coherent-text.md](CASA-ADR-0030-grammar-literacy-coherent-text.md) — L1 закрытый класс, L2 `lang.meta.grammar.*`, L3 согласование, J0 write.  
**Аналитическое чтение (слоги → слово, неологизмы):** [CASA-ADR-0032-analytic-syllable-reading.md](CASA-ADR-0032-analytic-syllable-reading.md) — R1 corpus bind, R2 «краш», R3 орфоварианты позже.  
**Lab ingest (педагогика):** [CASA-literacy-pedagogy-lab-v1.md](CASA-literacy-pedagogy-lab-v1.md) — порядок wordlist, probe, reinforce-tail.

| Стадия | lesson | Содержание |
|--------|--------|------------|
| `stage-08-meta-grammar-person` | `lesson-08-grammar-meta` | мета-лицо: `я`…`они` → `lang.meta.grammar.person.*` |
| `stage-07-closed-class` (план) | `lesson-07-closed-class` | служебные слова как `lang.word.*` |
| `stage-09-grammar-agreement-pilot` (план) | TBD | пары форм → `lang.meta.grammar.agreement.*` |

---

## Принцип (не меняется)

- **Read path** — импринт + emergent `vis.lum.frame.*` ↔ lexical; **без OCR**.
- **Слова** — целые знаки (`lang.word.*`); буквы и слоги — **инварианты**, не декодер в runtime.
- **Moment** — один vis + один lexical → **один sleep** (не batch из десятков пар).
- **Метаязык** — **отдельные** moment’ы на карточку-фразу; не смешивать с grapheme/буквой в том же sleep (lab: pure → probe **know** на фразе).
- **`concept_id`** — semantic EN; мета-оси `lang.meta.{category}.{facet}` (`meta_concepts.py`), не транслит RU.
- **Одна мета-категория** — много surface и языков (RU/EN фразы → один id); probe по категории, не по цитате. См. протокол § «Одна категория — много выражений».
- **Локали параллельны** — RU и EN те же стадии, разные lattice (`alphabet-ru` / `alphabet-en`, `lexicon-ru` / `lexicon-en`).

---

## Две оси curriculum

| Ось | Содержание |
|-----|------------|
| **Глубина** | буква (register) → face → слог → слово → face слова |
| **Язык** | **RU** (cyrl) и **EN** (latn) — зеркальные lesson_id, общий class `literacy-cards` |

Порядок стадий в журнале ≠ обязательный pipeline чтения. Слова корпуса и буквы алфавита можно вести **параллельными** micro-moment’ами.

---

## Русский (РЯ)

### 1. Алфавит, все регистры

| Стадия | lesson | Кадры | concept_id | lattice |
|--------|--------|-------|------------|---------|
| `stage-01-grapheme-cyrl` | `lesson-01-letters-cyrl` | 33×2, `face:sans` | `grapheme.cyrl.{cue}.{lower\|upper}` | `alphabet-ru` |

**Статус:** JPEG + manifest (66 кадров); ingest — micro по одной букве или батчами с **отдельным sleep на пару**.

**Cue:** латинский slug (`a`, `yo`, `zh`, …); **surface** на кадре — кириллица.

### 2. Буквы, разные начертания

| Стадия | lesson | Заметка |
|--------|--------|---------|
| `stage-02-grapheme-cyrl-faces` | `lesson-02-letters-faces` | те же `{cue, register}`, `face:serif`, `face:mono`, …; новый `frame_id`, тот же или связанный `concept_id` |

Контраст как круг/квадрат: не смешивать в один sleep шесть букв.

### 2b. Мета-фонология: гласная / согласная

| Стадия | lesson | Кадры | concept_id |
|--------|--------|-------|------------|
| `stage-04-meta-phonology-vowel-consonant` | `lesson-09-phonology-meta` | «гласная», «согласная» + буква с подписью категории | `lang.meta.phonology.vowel` / `.consonant` |

**Сборка:** `tools/build_phonology_meta_cards.py` (пилот 12 кадров или `--all-letters` 35). **Ingest:** `micro-literacy/run_phonology_meta_stage.py` (порядок `data/ru-phonology-ingest-order-v1.txt`). **Probe:** `probe_meta_phonology_quiz.py`. Между алфавитом (stage-01) и слогами (stage-05); один moment = один sleep.

### 3. Слоги (опционально, целые кадры)

| Стадия | lesson | concept_id | lattice |
|--------|--------|------------|---------|
| `stage-05-syllable-cyrl` | `lesson-05-syllables-cyrl` | `syllable.{surface}` (напр. `ма`, `ко`) | `syllables-ru` |

Не «собрать слово из слогов одним emergent predict» — на stage-05 отдельные узнаваемые формы; **композиция** на незнакомом целом кадре — [CASA-ADR-0032](CASA-ADR-0032-analytic-syllable-reading.md) (R1/R2).

**Пилот R1 (lab):** `data/literacy/analytic-segments-ru-pilot-v1.json` · `probe_analytic_read_corpus.py` · `micro-literacy/run_analytic_breakdown_pilot.py` · `casa/prisms/visual/analytic_read.py`.

### 4. Слова — современный корпус РЯ

| Стадия | lesson | Источник | concept_id |
|--------|--------|----------|------------|
| `stage-03-words-cyrl-core` | `lesson-03-words-cyrl` | пилот 8 слов | `lang.word.{slug}` |
| `stage-06-words-cyrl-corpus` | `lesson-06-words-cyrl-corpus` | частотный список | то же |

**Корпус (ingest, не runtime):**

- Леммы/формы из открытого частотного списка (напр. top-N по OpenCorpora / wordfreq-ru / срез RNC) — **авторинг**, не OCR.
- Один кадр = одно слово целиком; `cue` = нормализованная лемма; slug латиницей или NFC-хешем для `frame_id`.
- Большой N → **шарды** `lexicon-ru-00` … `lexicon-ru-NN` по ADR naming; lesson бьётся на части (500–2k слов на stage).
- Исключить на v1: имена, аббревиатуры, чистые цифры, слова длиннее K символов (напр. K≤12).

**Инструменты (план):**

- `tools/corpus_ru_wordlist.py` — скачать/отфильтровать список → `data/literacy/ru-wordlist-v1.txt`
- `tools/build_word_cards.py --corpus data/...` — JPEG + дополнение manifest
- `lab/visual-curriculum/micro-literacy/run_word_shard.py` — micro-moment по слову, один sleep

### 5. Слова, разные шрифты

| Стадия | lesson |
|--------|--------|
| `stage-04-words-cyrl-faces` | `lesson-04-words-faces` — top-1k корпуса в serif/mono |

---

## English (EN) — зеркало

| RU | EN |
|----|-----|
| `grapheme.cyrl.*` | `grapheme.latn.*` |
| `alphabet-ru` | `alphabet-en` |
| `syllables-ru` | `syllables-en` |
| `lexicon-ru` | `lexicon-en` |
| `lesson-01-letters-cyrl` | `lesson-11-letters-latn` |
| `lesson-02-letters-faces` (ru) | `lesson-12-letters-latn-faces` |
| `lesson-05-syllables-cyrl` | `lesson-15-syllables-latn` |
| `lesson-06-words-cyrl-corpus` | `lesson-16-words-en-corpus` |

**EN алфавит:** `a`–`z` + register `lower` / `upper` (52 кадра на face).  
**EN слоги:** CV, CVC по частотному списку (опционально).  
**EN корпус:** wordfreq-en / SUBTLEX-US top-N → `lang.word.{slug}` на `lexicon-en`.

`ensure_lexical_lattices` расширить: при EN-moment поднимать `alphabet-en` + `lexicon-en`.

---

## Probe / отчёты учителя

| Probe | held-out |
|-------|----------|
| `probe_grapheme_quiz.py` | буквы + пилот-слова |
| `probe_word_quiz.py` (план) | срез корпуса, не входивший в последний ingest |
| `probe_syllable_quiz.py` (план) | слоги |

Hints только в JSON отчёта; runtime без manifest-oracle.

---

## Очередь реализации (инженерия)

0. **Мета-лицо (ADR-0030)** — `build_grammar_meta_cards.py` → `run_meta_grammar_person_pure.py` → `probe_meta_grammar_person_quiz.py`.
1. **RU ingest алфавита** — micro-runner по всем 66 кадрам (ночной прогон, один persist в конце).
2. **RU corpus v1** — wordlist 1k–5k + `build_word_cards --corpus`.
3. **Faces** — generator + stage-02 / stage-04.
4. **Слоги** — `build_syllable_cards.py` + stage-05.
5. **EN** — `build_letter_cards_latn.py`, bootstrap EN lattices, пилот `a/A`, corpus EN.
6. Статья / серия `casa-literacy` (по аналогии с vis-math).

---

## Уже в репо

- `lessons/literacy-cards/` — 66 букв RU, 52 буквы EN, 56 слогов, **331** слово корпуса RU, 8 слов пилот
- `tools/` — `build_*`, `corpus_wordlist.py`, `literacy_render.py`
- `lab/visual-curriculum/micro-literacy/run_micro_stage.py` — ingest по stage
- Математика lesson-15: **6/6** geom-lex (закрыто)

## Ingest (lab)

```powershell
python lab/visual-curriculum/micro-literacy/run_micro_stage.py --stage stage-01-grapheme-cyrl
python lab/visual-curriculum/micro-literacy/run_micro_stage.py --stage stage-05-syllable-cyrl
python lab/visual-curriculum/micro-literacy/run_micro_stage.py --stage stage-06-words-cyrl-corpus --limit 50  # пачками
python lab/visual-curriculum/micro-literacy/run_micro_stage.py --stage stage-11-grapheme-latn
```
