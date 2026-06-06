# CASA: учебный план — русский язык (nositel′ v1)

**Статус:** рабочий учебный план (2026-06-06)  
**target_agent:** `von-neumann`  
**Active scope:** только RU, **письменный тракт** (visual + text); audio — вне v1.

**Не путать с:**
- [CASA-von-neumann-school-program-arc-v1.md](CASA-von-neumann-school-program-arc-v1.md) — macro-карта всей школы (draft)
- [CASA-von-neumann-class-ru-v1.md](CASA-von-neumann-class-ru-v1.md) — architecture класса, probes, waves

**Evidence (read-only):** `agent-notes/knowledge/worlds/pedagogy-russian-language/` (Castles, Ehri, NRP); neuro — rationale only ([bridge matrix](agent-notes path: `cognition-neurolinguistics/matrix-neurolinguistics-pedagogy-bridge-v1.md`)).

---

## Как читать этот документ

| Колонка | Смысл |
|---------|--------|
| **Блок** | Учебная единица с одной целью и одним gate |
| **Ориентир сессий** | Lab/teacher **moments** (Kolb-циклы), не календарные недели — темп задаёт **probe readiness** |
| **Teacher (1–4)** | Authoring: ingest, moment plan, held-out spec — [CASA-teacher-framework-v1.md](CASA-teacher-framework-v1.md) |
| **Agent (поле)** | predict → surprise → sleep → promote; без oracle на wake |
| **Gate** | Pass/fail только behavioral probe на store агента |

**Принципы подачи (pedagogy):** Rosenshine I→We→You; spaced practice между блоками; **whole-word — цель**, grapheme/syllable — bootstrap (Castles §1→§2→§3, Ehri OM).

---

## Сводная лента (12 блоков)

```text
Блок 1–2   CODE     grapheme + meta-phonology        → literacy-quiz
Блок 3     BRIDGE   syllable (fallback only)         → syllable-cyrl-quiz
Блок 4–5   WORDS    early whole + corpus             → literacy-corpus-quiz → skill.read.whole
── Phase I exit ──
Блок 6–7   META     closed class + grammar meta      → stage gates
Блок 8–9   PHRASE   agreement, possessive, numeral   → phrase-agent-store (held-out)
── Phase II exit ──
Блок 10    ORTHO    spelling in context              → probe_orthography_ru_v0
Блок 11    PUNCT    comma / что                      → probe_grammar_punct_ru_v0
Блок 12    DIALOG   written turn-taking              → dialogue tests + ADR-0049 acceptance
── nositel′ v0 ──
```

**Вне active RU v1 (не в ленте):** `stage-11-grapheme-latn`, EN mirror — после отдельного решения по SNL.

---

## Блок 1 — Буквы кириллицы (Castles §1, code)

| | |
|---|---|
| **Цель** | Узнавание **графем** lower/upper; bind `grapheme.cyrl.*` |
| **Stage** | `stage-01-grapheme-cyrl` |
| **Lesson** | `lessons/literacy-cards/lesson-01-letters-cyrl/` |
| **Ориентир** | 3–5 teacher moments (~15–25 frames/сессия) |
| **Evidence tag** | `lit.read.decode` · Castles §1 · Feng 2022 (VWFA at literacy onset — rationale) |

### Teacher (moment plan)

**Spec:** `lessons/literacy-cards/data/block-01-grapheme-cyrl-v1.json`  
**README / lab:** `lessons/literacy-cards/block-01-grapheme-cyrl/README.md`

1. **Goal:** «узнай букву на карточке» — vis cue → `grapheme.cyrl.{letter}.{case}`.
2. **Classify:** surface_class=letter, modality=vis.
3. **Methods:** I-do: wave 1 (a o m e n i lower); we-do: wave 2 register pairs; you-do: waves 3–5 batches; spacing: wave 6 revisit.
4. **Train / held-out:** 25 cues in waves; **8 cues never ingested** — `yo`, `zh`, `ts`, `ch`, `sch`, `hard`, `soft`, `eh` (16 frames).
5. **Ingest:** `run_block01_grapheme_pedagogy.py` (или `casa.cli.ingest_visual_class` по manifest).

```bash
python lab/visual-curriculum/micro-literacy/run_block01_grapheme_pedagogy.py --store von-neumann
python lab/visual-curriculum/probe_block01_grapheme_held_out.py --store von-neumann
```

### Agent (поле)

- Wake: predict on letter frames; surprise → hippo episode `bind_class: bindable_surprise`.
- Sleep: strengthen grapheme routes; **не** promote whole-word yet.
- Self-drive: `practice` только failed letters; **не** interleave dialogue.

### Gate

| Probe | Pass |
|-------|------|
| `probe_block01_grapheme_held_out` | held-out 8 cues (16 frames): ≥85% know, 0 empty, ≤10% ambiguous |

*(Pilot `literacy-quiz` на 5 frames — smoke only, не block exit.)*

### Типичные ошибки (teacher response)

| Ошибка | Не делать | Делать |
|--------|-----------|--------|
| Путает lower/upper | «это одна буква» лекцией | контрастная пара в одном moment |
| Spell-out слова буквами | считать fluency | отложить до Блок 4–5 |

---

## Блок 2 — Гласная / согласная (meta-phonology, B1)

| | |
|---|---|
| **Цель** | Операционно: «эта буква — гласная/согласная» для **decoding**, не лингвистика |
| **Stage** | `stage-04-meta-phonology-vowel-consonant` |
| **Lesson** | `lesson-09-phonology-meta` |
| **Ориентир** | 2–3 moments |
| **Evidence tag** | Ehri OM (phonological awareness → mapping) |

### Teacher

**Spec:** `lessons/literacy-cards/data/block-02-meta-phonology-cyrl-v1.json`  
**README:** `lessons/literacy-cards/block-02-meta-phonology-cyrl/README.md`

- Meta-cards: `lang.meta.phonology.vowel` / `consonant` на **знакомых** graphemes из Блок 1.
- Waves: category cards + a o m k → e i u y → spacing revisit.
- **Held-out (6):** eh, ya, yo, yu, s, t letter-class frames.

```bash
python lab/visual-curriculum/micro-literacy/run_block_pedagogy.py --block block-02-meta-phonology-cyrl
```

### Agent

- Vote meta category; journal confirm on held-out.
- Load governor: не смешивать с corpus words (WM ≤ threshold).

### Gate

| Probe | Pass |
|-------|------|
| `probe_block02_meta_phonology_held_out` | 100% know on held-out letter-class frames |

*(Smoke: `meta-phonology-quiz` на full stage — не block exit.)*

---

## Блок 3 — Слоги (analytic bootstrap, A2)

| | |
|---|---|
| **Цель** | Целый **слог** как vis unit; путь к R1, **не** финальная fluency |
| **Stage** | `stage-05-syllable-cyrl` |
| **Lesson** | `lesson-05-syllables-cyrl` |
| **Ориентир** | 2–4 moments |
| **Evidence tag** | Castles §2 · ADR-0032 R1 |

### Teacher

**Spec:** `lessons/literacy-cards/data/block-03-syllable-cyrl-v1.json`  
**README:** `lessons/literacy-cards/block-03-syllable-cyrl/README.md`

- Слоги из частых CV/VC шаблонов (ма, па, …); wave 3 — open/bound batch.
- **Held-out (11):** над, под, от, … -ость — prefix/affix syllables.
- Явно: syllable success **≠** promote `skill.read.whole`.

```bash
python lab/visual-curriculum/micro-literacy/run_block_pedagogy.py --block block-03-syllable-cyrl
```

### Agent

- `compose_analytic_read` на слоговых frames; promote `skill.read.analytic` только после `analytic-read-corpus-r1` held-out.

### Gate

| Probe | Pass |
|-------|------|
| `probe_block03_syllable_held_out` | ≥85% know on held-out syllable frames |

---

## Блок 4 — Первые слова целиком (A3 начало)

| | |
|---|---|
| **Цель** | Whole-word на **коротком** наборе (3–8 слов): мама, дом, кот… |
| **Stage** | `stage-03-words-cyrl` |
| **Lesson** | `lesson-03-words-cyrl` |
| **Ориентир** | 2–3 moments |
| **Evidence tag** | Ehri 2014 orthographic mapping · whole-word as unit |

### Teacher

**Spec:** `lessons/literacy-cards/data/block-04-early-words-cyrl-v1.json`  
**README:** `lessons/literacy-cards/block-04-early-words-cyrl/README.md`

- Frames: `word-{slug}-sans` → `lang.word.{lemma}`; waves 8 train + spacing revisit.
- **Held-out (2):** `word-apelsin-sans`, `word-apelsin_cap-sans`.
- Social «Привет» — `native_ru_bootstrap` (ADR-0049), **не** JPEG ingest в этом блоке.

```bash
python lab/visual-curriculum/micro-literacy/run_block_pedagogy.py --block block-04-early-words-cyrl
```

### Agent

- `predict_lex` whole; known → `skill.read.whole` route (partial — full promote после Блок 5).
- Dialogue bind: greeting → `ru.dialog.greeting` if journal confirms.

### Gate

| Probe | Pass |
|-------|------|
| `probe_block04_early_words_held_out` | 100% know on held-out lesson-03 words |

---

## Блок 5 — Корпус частотных слов (Phase I exit)

| | |
|---|---|
| **Цель** | **Lexical fluency** на частотном корпусе; exit Phase I |
| **Stage** | `stage-06-words-cyrl-corpus` |
| **Lesson** | `lesson-06-words-cyrl-corpus` |
| **Ориентир** | 4–8 moments (batch ingest + spacing) |
| **Evidence tag** | Castles §2→§3 · Stalega deny PA-only |

### Teacher

**Spec:** `lessons/literacy-cards/data/block-05-corpus-cyrl-v1.json`  
**README:** `lessons/literacy-cards/block-05-corpus-cyrl/README.md`

- Corpus ingest: 331 lemmas (`ru-wordlist-v1.txt`) → 4 batch waves (265 train).
- **Held-out:** offset 265, limit 66 (20%) — never in block ingest.
- Spacing: revisit Блок 1–3 failures only if probe red.
- **После Phase I:** новые слова — OOV (L2), не расширение corpus teacher'ом (см. § Corpus bootstrap vs emergent).

```bash
python lab/visual-curriculum/micro-literacy/run_block_pedagogy.py --block block-05-corpus-cyrl
python lab/visual-curriculum/probe_block_held_out.py --block block-05-corpus-cyrl
```

### Agent

- Promote **`skill.read.whole`** after corpus gate green.
- Capability route: `novel=false` → whole; `novel=true` → analytic/OOV.
- OOV smoke: one novel word remember→recall (prep Блок 10+).

### Gate (Phase I exit — все три)

| # | Criterion |
|---|-----------|
| 1 | `probe_block05_corpus_held_out` — 20% held-out ≥85% know |
| 2 | `probe_lexical_read_fluent_ru` (same held-out slice) green |
| 3 | «Привет» → social bind, **no** grapheme surprise (ADR-0049 #1) |

---

## Блок 6 — Метаязык и служебные слова (B2, B4)

| | |
|---|---|
| **Цель** | Регистр, эпистемика; closed-class для phrase |
| **Stages** | `stage-07-meta-language`, `stage-07b`, `stage-07c-register-phrases`, `stage-07-closed-class` |
| **Lessons** | `lesson-07-meta-language`, `lesson-07-closed-class` |
| **Ориентир** | 3–5 moments |

### Teacher

**Closed-class spec:** `lessons/literacy-cards/data/block-06-closed-class-cyrl-v1.json`  
**README:** `lessons/literacy-cards/block-06-closed-class-cyrl/README.md`

- Text + vis meta (`lesson-07-meta-language`) — **не** exam «назови часть речи».
- Closed class: 52 function words → 3 batch waves; held-out last 10 (`ru-closed-class-v1.txt`).

```bash
python lab/visual-curriculum/micro-literacy/run_block_pedagogy.py --block block-06-closed-class-cyrl
```

### Agent

- Meta votes operational; closed-class on whole-word path.

### Gate

| Probe | Pass |
|-------|------|
| `probe_block06_closed_class_held_out` | ≥85% know on held-out closed-class |
| `meta-pure-quiz` | meta language cards (отдельный tract) |

---

## Блок 7 — Грамматическая форма в контексте (B6, Phase II)

| | |
|---|---|
| **Цель** | Лицо, падеж (им/вин) — **правильная форма на карточке**, не определение |
| **Stages** | `stage-08-meta-grammar-person`, `stage-08b-meta-grammar-case` |
| **Lessons** | `lesson-08-grammar-meta`, `lesson-08b-grammar-case-meta` |
| **Ориентир** | 4–6 moments |
| **Evidence tag** | ADR-0036 emergent morph · operational meta |

### Teacher

- JPEG pairs: «она мыла» / «*она мыл» — contrast, не lecture.
- Agent KSA stage gate spec in manifest.

### Agent

- Paradigm pilot on store; sidecar registry ≠ mastery.

### Gate

| Probe | Pass |
|-------|------|
| `literacy-cards:stage-08-*` stage gates | agent KSA on held-out forms |

---

## Блок 8 — Согласование и словоформы (B6–B7)

| | |
|---|---|
| **Цель** | Agreement, possessive, numeral+noun — **phrase-level** |
| **Stages** | `stage-09-grammar-agreement-pilot`, `stage-09b`, `stage-09c` |
| **Lessons** | `lesson-09-*-meta` |
| **Ориентир** | 5–7 moments |

### Teacher

- Phrase events sidecar: slots + grammeme tags.
- Ingest phrase compose pilot JSON.

### Agent

- `phrase_compose` / `phrase-agent-store` events; sleep on high-value phrase errors.

### Gate (Phase II partial)

| Probe | Pass |
|-------|------|
| stage-09* gates | held-out agreement pairs |

---

## Блок 9 — Фраза и morphemics (B7, B5) — Phase II exit

| | |
|---|---|
| **Цель** | Held-out **phrase event**; корень/affix для ortho vigilance |
| **Stages** | `stage-10-phrase-events-ru` (planned), `stage-14-morphemics-root-affix` (planned) |
| **Ориентир** | 3–5 moments |

### Teacher

- Phrase held-out: 6 events min (phrase-agent-store spec).
- Morphemics: 10–15 root/affix contrasts for B8 prep.

### Agent

- Promote `skill.read.phrase` after phrase gate.

### Gate (Phase II exit)

| # | Criterion |
|---|-----------|
| 1 | `phrase-agent-store` held-out pass |
| 2 | Person+case — agent KSA, not sidecar only |

---

## Блок 9b — Связное понимание (Castles §3, SVR C)

| | |
|---|---|
| **Цель** | **Discourse C:** прочитал короткий passage → ответ по смыслу (не пересказ §) |
| **Tract** | `lessons/ru-text-tract/data/passage-comprehend-pilot-v1.json` |
| **Ориентир** | 2–4 moments (text); после phrase gate, до ortho |
| **Evidence tag** | Castles §3 · Hoover–Gough SVR · Hwang 2021 (passage in context) |

### Teacher

- Passage + вопрос в одном turn: «Маша купила хлеб… / Что купила Маша?»
- Held-out: events **не** из phrase-agent-store pilot.
- **Не gate:** three-cueing, «перескажи абзац учебника».

### Agent

- `semantic_read` → recall/general; bind journal + known `lang.word.*`.
- `compose_subject_utterance` — duck test: ответ содержит target token из passage.

### Gate

| Probe | Pass |
|-------|------|
| `probe_passage_comprehend_ru_v0` | all held-out cases: `expect_in_reply` in articulate |

```bash
python lab/visual-curriculum/probe_passage_comprehend_ru_v0.py
```

**Статус v0:** spec + probe wired; green на store — после corpus/journal coverage (волна 2).

---

## Блок 10 — Орфография в контексте (B8, L3)

| | |
|---|---|
| **Цель** | Правильная **форма в предложении** |
| **Tract** | `lessons/ru-text-ortho/` (planned) + KB |
| **Bundle** | `kb-lang-ru-orthography-v1` (planned), grammar-dialog draft |
| **Ориентир** | 4–6 moments (text tract) |
| **Evidence tag** | Graham writing-to-learn (explain) · ortho atoms |

### Teacher

- Text cues: «в течение дня», «по-русски», «также» — held-out sentences.
- KB = orient only; gate on field bind.

### Agent

- `skill.spell.check`; articulate compare forms; honest partial if no atom.

### Gate

| Probe | Pass |
|-------|------|
| `probe_orthography_ru_v0` | held-out spelling in context |

---

## Блок 11 — Пунктуация (B9, L4)

| | |
|---|---|
| **Цель** | Запятая перед «что»; прямая речь (minimal v1) |
| **Tract** | `lessons/ru-text-punct/` (planned) |
| **Bundle** | `kb-lang-ru-grammar-dialog-v1` § punct |
| **Ориентир** | 3–4 moments |

### Teacher

- Intent cues: «проверь запятые», «верно ли».
- Separate from ortho: **structure**, not graphemes.

### Agent

- `skill.punct.check`; semantic_read grammar intent.

### Gate

| Probe | Pass |
|-------|------|
| `probe_grammar_punct_ru_v0` | held-out comma + что |

---

## Блок 12 — Письменный диалог (B10, nositel′ v0)

| | |
|---|---|
| **Цель** | Turn-taking в чате/IDE; этикет; связный written reply |
| **Tract** | `lessons/ru-text-dialog/` + `lessons/lang-ru-grammar-dialog/` |
| **Bundle** | `agents/von-neumann/bundles/kb-lang-ru-grammar-dialog-v1.bundle.json` |
| **Ориентир** | 4–8 moments + life dialogue |
| **Evidence tag** | ADR-0045 subject-as-interlocutor |

### Teacher

- Scenarios: greeting, thanks, simple question-answer, norm check request.
- OOV in dialogue → remember tract (L2).

### Agent

- Field-mastery-first articulate; defer/refuse if partial.
- Interleave dialogue **only after** Phase I exit (autonomy_intent).

### Gate (nositel′ v0 — ADR-0049 acceptance)

| # | Acceptance |
|---|------------|
| 1 | Known word → whole-word read (no grapheme drill) |
| 2 | OOV → remember → recall |
| 3 | Ortho held-out in reply context |
| 4 | Punct held-out |
| 5 | Partner turn → coherent written response (duck test) |

---

## Corpus bootstrap vs emergent lexicon

| Режим | Когда | Кто | Как |
|-------|-------|-----|-----|
| **Bootstrap corpus** | Blocks 4–5, Phase I | Teacher | `ru-wordlist-v1` + held-out gate; цель — `skill.read.whole` |
| **Domain packs** | Phase II (6–9) | Teacher точечно | closed-class, phrase events, morphemics — не «ещё 5000 слов» |
| **Emergent / OOV** | Phase I exit+ | **Агент** | partner/text → remember → `lang.word.*`; optional KB promote |
| **Life reading** | Phase III+ | **Агент** | dialogue, passages, periphery — Block 9b, Blocks 10–12 |

**Инвариант:** частотный corpus — **потолок teacher ingest**, не весь язык. Полный словарь в bundle до OOV — non-goal (ADR-0049).

---

## OOV (сквозной тракт L2)

Не отдельный блок — **в каждом блоке после Блок 4**:

```text
partner/text surface → classify OOV
  → agent_remember (hypothesis)
  → verify recall cue
  → journal confirmed → sleep → lang.word.*
```

Gate: `probe_oov_word_recall_v0` (Блок 10+).

---

## Ритм и нагрузка

| Правило | Источник |
|---------|----------|
| Mastery-first: следующий блок только после gate | ADR-0049, Rosenshine |
| Spacing: 1–2 revisit moments прошлого блока | Kolb / sleep |
| WM overload → defer low-priority goals | `load_governor.py`, CLT |
| Sleep when surprise value high or overload + hippo pending | ADR-0010 value, ADR-0036 |
| **Не** interleave grapheme + dialogue до Phase I exit | class-ru-v1 |

**Ориентир macro-времени (human child analog, не жёстко для агента):**

| Phase | Блоки | Школьный аналог |
|-------|-------|-----------------|
| I | 1–5 | букварь → первое чтение |
| II | 6–9 | 2–3 класс: форма в тексте |
| III | 10–12 | 3–4 класс: норма + dialog |

Агент может пройти быстрее/медленнее — **gates**, не календарь.

---

## Материалы (authoring checklist)

| Блок | Manifest / path | Status |
|------|-------------------|--------|
| 1 | `data/block-01-grapheme-cyrl-v1.json` | **done** |
| 2 | `data/block-02-meta-phonology-cyrl-v1.json` | **done** |
| 3 | `data/block-03-syllable-cyrl-v1.json` | **done** |
| 4 | `data/block-04-early-words-cyrl-v1.json` | **done** |
| 5 | `data/block-05-corpus-cyrl-v1.json` | **done** |
| 6 | `data/block-06-closed-class-cyrl-v1.json` | **done** (closed-class tract) |
| 7–9 | `lessons/literacy-cards/class.manifest.json` | **exists** |
| 9b | `ru-text-tract/data/passage-comprehend-pilot-v1.json` | **draft** |
| 10–12 text | `lessons/ru-text-tract/data/*.json` | **draft** |
| KB dialog | `lessons/lang-ru-grammar-dialog/README.md` | draft |
| Store | `agents/von-neumann/` | active lab |

---

## Связанные документы

- Architecture: [CASA-von-neumann-class-ru-v1.md](CASA-von-neumann-class-ru-v1.md)
- Fluency ADR: [CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md](CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md)
- Categories: [CASA-ru-native-categories-v0.md](CASA-ru-native-categories-v0.md)
- Teacher protocol: [CASA-teacher-framework-v1.md](CASA-teacher-framework-v1.md)
- Macro map (all subjects): [CASA-von-neumann-school-program-arc-v1.md](CASA-von-neumann-school-program-arc-v1.md)

*Версия: v1.0 · 2026-06-06 · status: active teaching plan*
