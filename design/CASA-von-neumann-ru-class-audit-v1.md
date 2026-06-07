# CASA: аудит класса «Русский» von-neumann — v1

**Статус:** рабочий аудит (2026-06-07)  
**Основание:** канон design/, lessons/, lab probes, agent-notes pedagogy (Castles 2018, SVR, Stalega deny PA-only).  
**Связано:** [CASA-von-neumann-class-ru-v1.md](CASA-von-neumann-class-ru-v1.md), [CASA-von-neumann-ru-teaching-plan-v1.md](CASA-von-neumann-ru-teaching-plan-v1.md), [CASA-ru-native-categories-v0.md](CASA-ru-native-categories-v0.md), [CASA-cefr-gate-ru-v1.md](CASA-cefr-gate-ru-v1.md), [CASA-ADR-0053-type0-written-meaning-graph-v1.md](CASA-ADR-0053-type0-written-meaning-graph-v1.md), **[CASA-von-neumann-curriculum-review-v1.md](CASA-von-neumann-curriculum-review-v1.md)**

---

## Резюме (честно)

Мы **не** на «школьном §», и **не** на LLM-носителе. На письменном тракте von-neumann сегодня:

| Слой | Статус | Комментарий |
|------|--------|-------------|
| **Castles §1** (code) | **закрыт** | grapheme + meta-phonology held-out |
| **Castles §2** (fluent word ID) | **закрыт** | corpus + `probe_lexical_read_fluent_ru` |
| **Castles §3** (comprehension) | **частично → сильный срез** | CEFR C2 13/13 + B11 `probe_text_meaning_ru` 6/6 + held-out 3/3 — но **узкий** plan, не «весь язык» |
| **SVR D** (decode) | **закрыт** на lab corpus | analytic bootstrap для OOV |
| **SVR C** (comprehension product) | **растёт** | meaning graph + CEFR RC/WP; vocabulary depth — emergent |
| **L3–L4** (ortho/punct) | **закрыт (lab)** | `probe_orthography_ru` 4/4, `probe_grammar_punct_ru` 3/3 |
| **B5 morphemics** | **закрыт** | `probe_morphemics_ru` 2/2 по `block-09c` |
| **Инфраструктура** | **закрыто** | `capability_router` на hot path; umbrella manifest v2 |

**Главный риск:** CEFR/C2 green на **curated** сценариях ≠ type-0 на произвольном тексте. Gate честный для **wired** plan, не для открытого мира.

**Главный прогресс:** вертикальный срез **type-0** (ADR-0052 intent + ADR-0053 props) — редкая связка для field-realize без LM на hot path.

---

## Педагогика (agent-notes) ↔ CASA

### Castles §1 → §2 → §3

| Castles | CASA блоки | Evidence | Gap |
|---------|------------|----------|-----|
| §1 Code | 1–3 (grapheme, phonology meta, syllable fallback) | Ehri OM, NRP | syllable не должен стать «целью» — OK в каноне |
| §2 Skilled word ID | 4–5 corpus, closed-class | Ehri 2014 orthographic mapping | facet lexicon (object/action/property) — **только в categories**, не в probes |
| §3 Comprehension | 9b, **9d B11**, CEFR RC | Hoover–Gough SVR, Hwang passage-in-context | **нет** отдельного literature class (длинный текст, жанры) |

### SVR: RC = D × LC

| Фактор | CASA probe / skill | Статус |
|--------|-------------------|--------|
| **D** decode | `skill.read.whole`, analytic OOV | green |
| **LC** language comprehension | `skill.read.comprehend`, phrase, dialog | partial — 13 frames semantics KB |
| **RC product** | `probe_cefr_gate_ru`, `probe_text_meaning_ru` | green на held-out |

**Педагогический deny (Stalega):** PA-only / three-cueing — в каноне отвергнуты. Не добавлять «угадай по картинке» gates.

### Rosenshine / I→We→You

Teacher moments в block JSON — **есть** для Phase I–II (literacy-cards data). Text tract Phase III: ortho/punct plans **draft**, B11 class **есть**.

### Writing-to-learn (Graham)

Ortho block 10 ссылается на Graham; **нет** probe «объясни правило своими словами» как отдельного WP skill — только punct/spell atoms.

---

## Карта осей A × B (фактическая)

| Ось B | Название | Реализация | Gate | Пробел |
|-------|----------|------------|------|--------|
| B1 | Фонетика (операционно) | stage-04 | meta-phonology | — |
| B2 | Графика | stage-01 | literacy-quiz | — |
| B3 | Орфоэпия | — | deferred (audio) | осознанно вне v1 |
| B4 | Лексика | stage-06, OOV | lexical + OOV probes | facet routing не wired |
| B5 | Состав слова | block-09c spec | **probe missing** | morphemics после phrase — правильный порядок |
| B6 | Морфология | stage-08–09c | stage gates | agent KSA — проверить streak на store |
| B7 | Синтаксис / phrase | phrase events | phrase-agent-store | — |
| **B11** | **Понимание текста** | `lessons/ru-text-comprehend/` | **`probe_text_meaning_ru`** | **6 frames** — расширять JSONL→bundle |
| B8 | Орфография | moment plan draft | **probe missing** | `kb-lang-ru-orthography-v1` |
| B9 | Пунктуация | moment plan draft | **probe missing** | skill.punct.check не в mastery_gate |
| B10 | Письменный диалог | grammar-dialog KB | CEFR + nositel | life dialogue — ongoing |

**Путаница нумерации (исправить в доках):**

- **Teaching plan «Блок 11»** = пунктуация (B9).
- **Categories B11** = понимание текста (meaning graph).
- **Решение:** в ленте teaching plan использовать **Блок 9d** для B11 comprehend; teaching «Блок 11» переименовать в комментарии как «B9 punct».

---

## Tracts F1–F11 (classify → verify)

| Tract | Probe / test | Store green? | Emergent route? |
|-------|--------------|--------------|-----------------|
| F1 Lexical | `probe_lexical_read_fluent_ru` | да | да (`_BOOTSTRAP_PROBES`) |
| F2 OOV | `probe_oov_word_recall_ru` | **1/1** | да |
| F3 Ortho | `probe_orthography_ru` | **4/4** | да |
| F4 Punct | `probe_grammar_punct_ru` | **3/3** | да |
| F5 Social | `test_subject_dialogue` | да | dialog KB |
| F6–F8 | literacy / phrase | да | phrase bootstrap |
| F9 Morphemics | `probe_morphemics_ru` | **2/2** | да |
| F10 Dialog | CEFR WI | да | partial |
| **F11 Comprehend** | **`probe_text_meaning_ru`** | **да 6/6** | **да** (после mastery streak) |

---

## Что упустили (приоритет)

### P0 — закрыто (2026-06-07)

1. ~~Lab ortho/punct~~ — `probe_orthography_ru`, `probe_grammar_punct_ru` green.
2. ~~Morphemics lab~~ — `probe_morphemics_ru` green.
3. ~~`capability_router` hot path~~ — `resolve_capability_skill` + `geometry` в `RouteContext`.
4. ~~Umbrella manifest v2~~ — `lessons/von-neumann-ru-native/class.manifest.json`.

### P1 — педагогическая полнота Castles §3

5. **Расширить semantics KB** — `frames.jsonl` authoring + compile; жанры: narrative, instruction, argument (Hwang).
6. **Блок 9b vs 9d** — 9b = lemma/fact duck test (legacy pilot); 9d = full meaning graph class. Обновить teaching plan: 9b **superseded** для exit criteria → 9d + CEFR RC.
7. **`promote_frame_from_journal`** (ADR-0053 v2 planned) — агент фиксирует hypothesis prop → teacher compile в bundle после gate.
8. **Literature micro-class** — 3–5 сценариев «главный герой / конфликт / конец» (Band B school arc), не ЕГЭ.

### P2 — инфраструктура и честность claims

9. **CEFR doc sync** — C1/C2 больше не «ожидаем red» на von-neumann; отделить **curated C2** от **open-world nositel**.
10. **B4 lexicon facets** — stratified held-out (object/action/property) для routing, не лингвистика.
11. **`skill.spell.check` / `skill.punct.check`** в `PROBE_GATE_BY_SKILL`.
12. **Second probe pass** для B11 — held-out **не** из ingest moments (как grapheme 8 cues).

### P3 — вне RU v1 (но в school arc)

13. Audio tract (B3), EN mirror, STEM spines — в [school-program-arc](CASA-von-neumann-school-program-arc-v1.md), не блокируют RU.

---

## Рекомендуемая лента (обновление teaching plan)

```text
Блок 1–5    CODE + WORDS          → Phase I exit (как сейчас)
Блок 5α     Material→Verbal       → probe_material_verbal_ru  [RU-α prerequisite phrase]
Блок 6–9    META + PHRASE         → Phase II exit
Блок 9b     Passage fact (pilot)  → prerequisite only (lemma pick)
Блок 9c     Morphemics            → probe_morphemics_ru  [GREEN 2/2]
Блок 9d     Text meaning (B11)    → probe_text_meaning_ru  [GREEN 6/6 + held-out 3/3]
Блок 10     Ortho (B8)            → probe_orthography_ru  [GREEN 4/4]
Блок 11     Punct (B9)            → probe_grammar_punct_ru  [GREEN 3/3]
Блок 12     Dialog + CEFR         → probe_cefr_gate_ru  [GREEN C2 curated]
```

**Phase III minimum (пересмотр):** L1 + L2 + **9d** + (10–11 когда green) + CEFR B1 exit; **C1+** — отдельное заявление с wider held-out.

---

## Школьная программа (macro)

[CASA-von-neumann-school-program-arc-v1.md](CASA-von-neumann-school-program-arc-v1.md) — **draft**, RU только active. Для полноты «класса как школы» не хватает:

| Spine | В arc | В CASA RU |
|-------|-------|-----------|
| L1 Literacy | Wave 0–2 | **active** |
| Literature | Band B integrated | **нет class** |
| Writing-to-learn | Expression spine | только ссылки на Graham |
| EN SNL | Wave 1 hard gate | latn stage в literacy-cards, не в ленте |

Это нормально для **RU-only v1**; не смешивать с «дырами» в RU ladder.

---

## Anti-patterns (не откатывать)

- CEFR green → заявление «nositel везде» без open-text probe
- Расширять B11 paste-gates — prop-compose **закономерен** при обучении
- LLM на hot path «пока не готов» — ломает north star
- PA-only / three-cueing moments в новых plans
- Один monolithic probe «весь русский»

---

## Следующие 3 шага (практика)

1. **RU-α:** `lessons/ru-material-verbal/` + `probe_material_verbal_ru` green (train + held-out) — Galperin bridge до phrase.
2. **RU-ε:** `agent.world.*` authoring + `compile_world_bundle` (ADR-0054).
3. **RU-N criteria:** open probe spec — [CASA-native-writer-criteria-v1.md](CASA-native-writer-criteria-v1.md).

---

## Ссылки (pedagogy MCP)

- RU index: `worlds/pedagogy-russian-language/kb-pedagogy-ru-scientific-evidence-v1.md`
- Castles §1–§3: `kb-pedagogy-ru-castles-2018-evidence-v1.md`
- SVR: `kb-pedagogy-ru-hoover-gough-1990-svr-evidence-v1.md`
- F→O playbook: `worlds/pedagogy-general/playbook-pedagogy-fundamentals-to-operational-v1.md`

*Версия: v1.0 · 2026-06-07 · аудит после B11 class + CEFR C2 milestone*
