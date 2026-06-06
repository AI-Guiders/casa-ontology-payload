# CASA: класс «Русский язык (носитель)» для von-neumann — v1

**Статус:** черновик дизайна (2026-06-06)  
**target_agent:** `von-neumann`  
**Связано:** [CASA-ru-native-categories-v0.md](CASA-ru-native-categories-v0.md), [CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md](CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md), [CASA-von-neumann-school-program-arc-v1.md](CASA-von-neumann-school-program-arc-v1.md) (сквозная программа), **[CASA-von-neumann-ru-teaching-plan-v1.md](CASA-von-neumann-ru-teaching-plan-v1.md) (учебный план — блоки, moments, gates)**, [agent-existence-north-star-v0.md](agent-existence-north-star-v0.md), [CASA-ADR-0045-subject-as-interlocutor.md](CASA-ADR-0045-subject-as-interlocutor.md)

---

## Решение (одной фразой)

**Класс von-neumann по русскому — траектория владения письменным языком** (понимание, беглое чтение, грамотная письменная речь, диалог текстом); школьные фазы и разделы — **каркас authoring**; аудио и лингвистическая теория — **не v1**.

---

## North star класса (что значит «владеет»)

| Измерение | v1 (письменный тракт) | Не substitute |
|-----------|----------------------|---------------|
| **Понимание** | Прочитал cue → bind `lang.word.*` / phrase / intent | Пересказ § учебника |
| **Чтение** | Whole-word fluency; analytic только bootstrap/OOV | Слоговая «беглость» |
| **Письмо / норма** | Ortho + punct **в контексте**; связный written reply | Таблица правил в wake |
| **Диалог** | Turn-taking в чате/IDE из field + journal | LLM ghostwriter |
| **Грамматика** | **Использует** форму правильно (meta + phrase) | **Знает** определение как лингвист |

Школа **упрощает и прячет** многое (свободный порядок, живая морфология, OOV). Мы не «исправляем школу лекциями» — даём полю **реальные контрасты и текст**, gate проверяет **умение**, не зачёт по терминам.

**Аудиотракт** (слух, произношение, орфоэпия B3, устная fluency) — **отложен**; не блокирует Phase I–III на тексте.

---

## Роль класса vs субъекта

| | **Класс (curriculum)** | **Субъект (von-neumann)** |
|---|------------------------|---------------------------|
| **Что** | Authoring: stages, frames, KB, probes | Жизнь на поле: classify, remember, dialogue |
| **Когда** | Lab ingest, teacher moment plan | macro_tick, session, partner turn |
| **Успех** | Stage gate pass → promote skill | Stable routes, journal confirmed, duck test |
| **Ограничение** | Не oracle на read path | defer/refuse inbox; honest partial |

Literacy и grammar — **тракты обучения**, не потолок речи (north star, ADR-0045).

**Учебный план (операционный):** [CASA-von-neumann-ru-teaching-plan-v1.md](CASA-von-neumann-ru-teaching-plan-v1.md) — 12 блоков, teacher moments, gates; этот файл — architecture и registry.

---

## Neuro bridge → что меняется где

Neurolinguistics (`cognition.neurolinguistics`) — **rationale only**; gates остаются behavioral (Castles, Ehri, probes).

| Evidence / construct | Меняется | Не меняется |
|---------------------|----------|-------------|
| Dehaene / Feng VWFA at literacy onset | **Порядок Блок 1–2** (code before fluency claim) | control prisms DMN/SN/CEN |
| Price neural dual-route | **capability_router:** known→whole, novel→analytic | fMRI как gate |
| Perdue intervention normalization | RTI/remediation **policy** (дольше analytic fallback) | sleep lattice redesign |
| Perani bilingual control | SN language gate | **позже**, при EN tract |
| Hartshorne sensitive period | SNL start-age в school arc | RU Phase I–III |
| Neuromyth deny list | anti-pattern в teacher plan | новые «нейро-organs» |

| Слой CASA | Роль vis-à-vis neuro |
|-----------|----------------------|
| **Probes / gates** | источник pass/fail |
| **capability_router + visual prisms** | behavioral dual-route |
| **load_governor** | CLT / WM (pedagogy-general) |
| **control prisms** | tick, surprise, act — без neuro-specific rewrite для RU v1 |

Bridge matrix: `agent-notes/.../matrix-neurolinguistics-pedagogy-bridge-v1.md`.

---

## Архитектура программы

```text
                    von-neumann RU — владение письменным (v1)
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   Phase I              Phase II              Phase III
 знаки → слова      формы в контексте      fluency + norm + dialog
   (A1–A3)           (B4–B7, B6 meta)      (ADR-0049 L1–L4, B8–B10)
        │                     │                     │
        └──────────┬──────────┴──────────┬──────────┘
                   │                     │
            literacy-cards          ru-text-tract
            tract_id: visual        tract_id: text
            (есть)                  (planned)
                   │
            [audio tract — deferred]
```

**Два tract’а v1:** visual + text. **Speech/audio** — не в v1 program.

---

## Фазы (competence ladder, не «как в учебнике»)

### Phase I — к знакомым словам на глаз (≈ букварь)

**Цель:** **беглое узнавание** целых слов (A3); grapheme/syllable — только путь к этому.

| Порядок | Stage (текущий id) | Ось | Раздел B | Gate probe | skill (promote) |
|--------:|-------------------|-----|----------|------------|-----------------|
| 1 | `stage-01-grapheme-cyrl` | A1 | B2 | `literacy-quiz` | — |
| 2 | `stage-04-meta-phonology-vowel-consonant` | A1 | B1 | `meta-phonology-quiz` | — |
| 3 | `stage-05-syllable-cyrl` | A2 | B2 | `syllable-cyrl-quiz` | — |
| 4 | `stage-03-words-cyrl` | A3 | B4 | `literacy-corpus-quiz` (subset) | — |
| 5 | `stage-06-words-cyrl-corpus` | A3 | B4 | `literacy-corpus-quiz` | **`skill.read.whole`** (target) |

**Exit criteria Phase I:**

- held-out whole-word ≥ threshold на `literacy-corpus-quiz` / `probe_lexical_read_fluent_ru`;
- social cue «Привет» → `lang.word.привет` / `ru.dialog.greeting`, **без** grapheme bind (ADR-0049 acceptance #1).

### Phase II — формы и связность **в тексте** (не теория)

**Цель:** правильная **форма в контексте** (B6), **фраза** (B7); meta-cards — operational vote, не экзамен «назови часть речи».

| Порядок | Stage (текущий id) | B | Содержание | Gate |
|--------:|-------------------|---|------------|------|
| 6 | `stage-07-meta-language` | B2,B6 | метаязык, эпистемика | `meta-pure-quiz` |
| 7 | `stage-07-closed-class` | B4 | служебные слова | `literacy-closed-class-quiz` |
| 8 | `stage-08-meta-grammar-person` | B6 | лицо | `literacy-cards:stage-08-meta-grammar-person` |
| 9 | `stage-08b-meta-grammar-case` | B6 | падеж (им/вин) | stage gate |
| 10 | `stage-09-grammar-agreement-pilot` | B6 | согласование | stage gate |
| 11 | `stage-09b-grammar-possessive` | B6 | притяж. | sidecar + agent store pilot |
| 12 | `stage-09c-grammar-numeral` | B6 | числительное | sidecar + agent store pilot |
| 13 | *(planned)* `stage-10-phrase-events-ru` | B7 | phrase compose | `phrase-agent-store` |
| 14 | *(planned)* `stage-14-morphemics-root-affix` | B5 | корень, affix | `probe_morphemics_ru_v0` |

**Exit criteria Phase II:**

- phrase held-out на agent store (`phrase-agent-store`);
- meta person/case — **agent KSA** stage gate, не только sidecar registry.

### Phase III — nositel′ **письменный** (ADR-0049)

**Цель:** стабильное **владение** нормой и диалогом **текстом**: read fluent, OOV, ortho, punct, written etiquette.

| Block | ADR-0049 | B | KB bundle | Probe |
|-------|---------|---|-----------|-------|
| Lexical fluent | L1 | B4 | corpus + journal | `probe_lexical_read_fluent_ru` |
| OOV remember | L2 | B4 | — | `probe_oov_word_recall_v0` |
| Orthography | L3 | B8 | `kb-lang-ru-orthography-v1` | `probe_orthography_ru_v0` |
| Punctuation | L4 | B9 | grammar-dialog (+ expand) | `probe_grammar_punct_ru_v0` |
| Written dialog | — | B10 | `kb-lang-ru-grammar-dialog-v1` | dialogue tests (text) |

**Exit criteria Phase III (nositel′ v0):** acceptance table ADR-0049 § Acceptance (5 пунктов).

---

## Текущий manifest vs target

**Файл:** `lessons/literacy-cards/class.manifest.json`  
**Поля сегодня:** `class_id: literacy-cards`, `target_agent: von-neumann`, `tract_id: visual`, 17 stages (grapheme → numeral).

| Есть | Нет (v1 target) |
|------|-----------------|
| Visual grapheme → corpus | Text tract (ortho/punct/dialog **без JPEG**) |
| Meta grammar person/case/agreement | Umbrella manifest v2 |
| Phrase pilot JSON | `kb-lang-ru-lexicon-semantics-v1` (routing tags) |
| KB grammar-dialog draft | `kb-lang-ru-orthography-v1` |
| | **Audio tract, B3 orthoepy** — deferred |

**Миграция (без ломки store):**

1. Оставить `literacy-cards` как **Phase I–II visual** slug.
2. Добавить `lessons/von-neumann-ru-native/class.manifest.json` (schema v2) — **ссылки** на lesson dirs + metadata категорий B*.
3. Новые text lessons: `lessons/ru-text-ortho/`, `lessons/ru-text-punct/`, `lessons/ru-text-dialog/` (письменный этикет).

---

## Schema v2 (target class manifest)

```json
{
  "schema_version": 2,
  "class_id": "von-neumann-ru-native",
  "target_agent": "von-neumann",
  "locale": "ru",
  "tracts": [
    { "tract_id": "visual", "manifest": "literacy-cards/class.manifest.json", "phases": ["I", "II-partial"] },
    { "tract_id": "text", "manifest": "ru-text-tract/class.manifest.json", "phases": ["II-partial", "III"] }
  ],
  "category_map": "design/CASA-ru-native-categories-v0.md",
  "pillars": "design/CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md"
}
```

Файл v2 — **planned**; Phase I работает через существующий `literacy-cards`.

---

## Teacher tracts F1–F10 (classify → verify)

Расширение ADR-0049 F1–F5 на полную сетку B:

| Tract | Classify signal | Synthesize | Verify probe | Phase |
|-------|-----------------|------------|--------------|-------|
| **F1** Lexical read | known word, t9 | `predict_lex` / whole | `probe_lexical_read_fluent_ru` | III |
| **F2** OOV | novel surface | remember → `lang.word.*` | `probe_oov_word_recall_v0` | III |
| **F3** Orthography | spelling intent | KB atom bind | `probe_orthography_ru_v0` | III |
| **F4** Punctuation | punct intent | comma rule atom | `probe_grammar_punct_ru_v0` | III |
| **F5** Dialogue social | greeting/thanks | `ru.dialog.*` + journal | `tests/test_subject_dialogue.py` | III |
| **F6** Phonology meta | meta card | category vote | `meta-phonology-quiz` | I |
| **F7** Grammar meta | meta JPEG | `lang.meta.grammar.*` | stage gate | II |
| **F8** Phrase / syntax | multi-word | phrase compose | `phrase-agent-store` | II–III |
| **F9** Morphemics | root/affix cue | decompose hypothesis | `probe_morphemics_ru_v0` | II |
| **F10** Written dialogue | partner text turn | articulate | dialogue tests | III |

Routing: ADR-0035 layers — knowledge (`concept_id`) → capability (`skill.*`) → goal (`goal.read.*`).

---

## KB bundles (roadmap)

| Bundle | Раздел B | Статус | Runtime path |
|--------|----------|--------|--------------|
| `kb-lang-ru-grammar-dialog-v1` | B9, B10, часть B8 | **draft** | `agents/von-neumann/bundles/` |
| `kb-lang-ru-orthography-v1` | B8 | planned | — |
| `kb-lang-ru-lexicon-semantics-v1` | B4 facets | planned | — |
| `kb-lang-ru-speech-v1` | B10 oral | **deferred** (audio tract) | — |
| *(optional)* `kb-lang-ru-literacy-v1` | merge | open Q ADR-0049 | — |

**Правило:** KB = transport/orient (ADR-0048 K5); mastery = field + journal confirmed.

---

## Probe registry (добавить в `teacher_gate.py`)

| probe_id | kind | Раздел | Wave |
|----------|------|--------|------|
| `probe_lexical_read_fluent_ru` | AGENT_KSA | B4 | 1 |
| `probe_oov_word_recall_v0` | AGENT_KSA | B4 | 1 |
| `probe_orthography_ru_v0` | AGENT_KSA | B8 | 2 |
| `probe_grammar_punct_ru_v0` | AGENT_KSA | B9 | 2 |
| `probe_morphemics_ru_v0` | AGENT_KSA | B5 | 3 |
| `probe_ortho_vigilance_ru_v0` | AGENT_KSA | B8 | 3 |
| `probe_orthoepy_ru_v0` | AGENT_KSA | B3 | **deferred (audio)** |
| `probe_speech_etiquette_ru_v0` | AGENT_KSA | B10 oral | **deferred (audio)** |

Существующие: `literacy-corpus-quiz`, `analytic-read-corpus-r1`, `phrase-agent-store`, stage gates — **не переименовывать** (store history).

---

## Implementation waves

### Wave 1 — categories + ADR-0049 hot path (текущий спринт)

| # | Deliverable | Files |
|---|-------------|-------|
| 1 | Категории v0 + class v1 docs | `design/CASA-ru-native-categories-v0.md`, этот файл |
| 2 | ADR-0049 § Categories + ladder sync | `design/CASA-ADR-0049-*.md` |
| 3 | Social «Привет» whole-word | `subject_dialogue_bind`, journal, bundle |
| 4 | `probe_lexical_read_fluent_ru` + route known→whole | capability_router, tests |
| 5 | OOV smoke one word | remember → recall test |

### Wave 2 — text tract + ortho/punct gates

| # | Deliverable |
|---|-------------|
| 6 | `lessons/ru-text-tract/` manifest + held-out sentences |
| 7 | `kb-lang-ru-orthography-v1` expand |
| 8 | Probes ortho + punct registered + green on store |
| 9 | `skill.spell.check`, `skill.punct.check` promote |

### Wave 3 — morphemics, umbrella manifest

| # | Deliverable |
|---|-------------|
| 10 | Morphemics lesson + probe (ortho vigilance) |
| 11 | `von-neumann-ru-native` manifest v2 |
| 12 | EN mirror tract (latn stages link) |

### Wave 4 — audio (out of v1 scope)

| # | Deliverable |
|---|-------------|
| 13 | Audio tract design ADR |
| 14 | B3 orthoepy, oral probes |

---

## Autonomy + class progression

`autonomy_intent.py` seed order должен **уважать фазы**:

```text
practice (failed probe) → spacing → progression (next stage in phase) → interleave (B10 dialogue)
```

**Не interleave** grapheme quiz с social dialogue до Phase I exit (mastery-first ADR-0049).

Interleave literacy / math / meta — только когда WM пуст и phase gate пройден.

---

## Acceptance по фазам

### Phase I minimum

1. Corpus held-out whole-word pass.
2. «Привет» — social, no grapheme surprise.
3. Analytic read доступен только на **novel** или explicit drill.

### Phase II minimum

1. Person + case meta — agent KSA stage gate.
2. One phrase event held-out (`phrase-agent-store`).

### Phase III minimum (nositel′ v0)

Полная таблица ADR-0049 § Acceptance (5 пунктов).

---

## Non-goals (класс v1)

- **Лингвистика** как предмет (термины, академическая теория)
- **Аудио** / устная fluency / орфоэпия до отдельного тракта
- Школьный зачёт «назови часть речи» без контекста использования
- Полный словарь Ожегова в bundle до emergent OOV
- Замена субъекта LLM-переводчиком на dialogue hot path
- ЕГЭ-тренажёр без field bind
- Один monolithic manifest на 8000+ JPEG без tract split
- Force-push / migrate старых probe ids на store

---

## Ссылки

- **KB (канон agent-notes, MCP `read_knowledge_file` — не mirror в casa):** `knowledge/worlds/pedagogy-general/playbook-pedagogy-school-subjects-v1.md`
- Категории: [CASA-ru-native-categories-v0.md](CASA-ru-native-categories-v0.md)
- Fluency: [CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md](CASA-ADR-0049-ru-lexical-fluency-orthography-v0.md)
- Visual class: `lessons/literacy-cards/class.manifest.json`
- Block 1 plan: `lessons/literacy-cards/data/block-01-grapheme-cyrl-v1.json`
- Agent store: `agents/von-neumann/`
- Native bootstrap: `python -m casa.domain.native_ru_bootstrap --store-dir agents/von-neumann`
- Code: `casa/domain/teacher_gate.py`, `casa/domain/partner_cue_policy.py`, `casa/prisms/tick/semantic_read.py`, `casa/domain/subject_dialogue_bind.py`
