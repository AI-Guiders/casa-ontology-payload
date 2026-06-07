# CASA: CEFR gate — русский письменный тракт (von-neumann)

**Статус:** design v1 (2026-06-07)  
**Framework:** [CEFR](https://www.coe.int/en/web/common-european-framework-reference-languages) / TORFL (ТРКИ)  
**Связано:** [CASA-nositel-gate-v1.md](CASA-nositel-gate-v1.md), [CASA-von-neumann-class-ru-v1.md](CASA-von-neumann-class-ru-v1.md), [CASA-von-neumann-ru-teaching-plan-v1.md](CASA-von-neumann-ru-teaching-plan-v1.md)

---

## Intent (ADR-0052) + Meaning (ADR-0053)

Partner turn: **intent = победивший F-tract** (`compete_tract_intent`), не if-ladder в `semantic_read`. Cues — `ru.tract.*` / `ru.speech_act.*` в KB. См. [CASA-ADR-0052-intent-as-tract-competition-v1.md](CASA-ADR-0052-intent-as-tract-competition-v1.md).

Понимание текста: **meaning graph** `ru.prop.*` из `passage_meaning` → bind над `passage.sent` → compose из slots. См. [CASA-ADR-0053-type0-written-meaning-graph-v1.md](CASA-ADR-0053-type0-written-meaning-graph-v1.md).

**Milestone (2026-06-07):** `probe_cefr_gate_ru` на `von-neumann` — **13/13 wired know**, `achieved_level=C2`, `block_12_pass=true`, `nositel_claim_pass=true` (после inference props B1 + meaning graph C1/C2). Это честный written gate, не LLM.

---

## Диагностика проводки (2026-06-07)

На C1-RC / C2 до фикса в `gather_subject_dialogue_blocks` оставался **один** блок `subject.field.snapshot` (score 2): passage без `lang.word.*` в KB → ноль lemmas, `ru.meta.discourse.*` не инжектился, journal wake на discuss отрезан → **`_discuss_discourse` возвращал пустую строку**. Это разрыв **bind → PhraseComposer**, не «плохой гейт».

Фикс (v2): **discuss hot path = `infer_discourse_sketch` only** — bind `passage.sent.*` + `passage.surface.*` + `ru.meta.discourse` linkers; длина и полнота фразы от **score bind'а** (`discourse_budget`), без if-ladder в `passage_comprehend`. Оценка C1 — живой turn, не substring gate.

---

## Зачем пересобрали gate

Старый `interlocutor_v1` (8 сценариев) ловил plumbing, но **не отвечал на вопрос уровня**: A2? B1? C1?

**CEFR gate** — единая шкала A1→C2 с дескрипторами по навыкам. Проба считает **`achieved_level`** (честно по сценариям), а не «носитель» по умолчанию.

| Термин | Значение |
|--------|----------|
| **`achieved_level`** | Высший уровень, где все **wired** обязательные сценарии уровня зелёные |
| **Block 12 exit** | `achieved_level >= B1` (письменный диалог, не C1) |
| **«Носитель» (твой бар)** | `achieved_level >= C1` + C1/C2 сценарии wired и green — **отдельное заявление** |
| **interlocutor_v1** | Подмножество B1, регрессия; не заменяет CEFR |

---

## Scope v1 (что измеряем)

| CEFR skill | v1 письменный тракт | Отложено |
|------------|---------------------|----------|
| **Reading comprehension** (RC) | Короткий connected text, факты, простой вывод | Длинные аргументативные тексты (C1+) |
| **Written interaction** (WI) | Чат/IDE turn: привет, о себе, уточнение | Спонтанная переписка без подготовки на любую тему |
| **Written production** (WP) | Ответ по тексту, gloss, орфография в контексте | Отчёты, эссе, нюанс/ирония (C1–C2) |
| Spoken interaction | — | Аудиотракт |
| Listening | — | Аудиотракт |

Источники дескрипторов: CEFR Companion Volume (ALTE); TORFL уровни ТЭУ(A1)…ТРКИ-IV(C2); для формулировок RC/WI/WP — [EUR CEFR table](https://www.eur.nl/en/education/language-training-centre/cefr-levels).

---

## Уровни → CASA (честная карта)

| CEFR | TORFL | Письменный дескриптор (сжато) | CASA Phase / probe |
|------|-------|--------------------------------|-------------------|
| **A1** | ТЭУ | Понимаю знакомые имена/слова; простой обмен приветствиями; очень короткая запись | Phase I exit, grapheme/corpus smoke |
| **A2** | ТБУ | Понимаю короткие тексты на бытовые темы; рутинный WI; связное сообщение на знакомую тему | Phase I–II, corpus + простой discuss |
| **B1** | ТРКИ-I | Главная мысль ясных текстов; вхожу в WI на знакомые темы; связный текст + причины/объяснения | **Block 12 target**, `cefr-gate-plan-v1` |
| **B2** | ТРКИ-II | Статьи/отчёты; развёрнутый WI; ясный детальный WP; честный partial вне поля | Ortho/punct probes + honest-oov |
| **C1** | ТРКИ-III | Связный структурированный WP; точные формулировки; длинные сложные RC | **wired** — `probe_cefr_gate_ru`; curated plan (см. Milestone §) |
| **C2** | ТРКИ-IV | Почти носитель: стиль, нюанс, сложные жанры | **wired** — register rewrite + meaning graph; **не** open-world nositel |

**Не путать:** школьные A1–A3 в `literacy-cards` (grapheme/syllable) ≠ CEFR A1 — в manifest явно разведены.

---

## Навыки и ID дескрипторов (plan)

| ID | Level | Skill | CEFR-смысл |
|----|-------|-------|------------|
| A1.WI.1 | A1 | WI | Простой обмен приветствиями/благодарностью |
| A1.RC.1 | A1 | RC | Понимаю отдельные знакомые слова в короткой фразе |
| A2.WI.1 | A2 | WI | Краткая информация о себе (имя, чем занимаюсь) |
| A2.RC.1 | A2 | RC | Факты из короткого бытового текста (кто/что/сказал) |
| A2.WP.1 | A2 | WP | Короткий ответ по содержанию текста |
| B1.RC.1 | B1 | RC | Главная мысль + простой вывод (почему/зачем) |
| B1.WI.1 | B1 | WI | Уточняющий вопрос, если нет входного текста |
| B1.WP.1 | B1 | WP | Объяснение слова/нормы (gloss), не шаблон |
| B1.WP.2 | B1 | WP | Проверка правописания в данном абзаце (partial OK) |
| B2.WP.1 | B2 | WP | Честный partial: орфография без претензии на предмет |
| C1.WP.1 | C1 | WP | Структурированное мнение за/против (`expect_pro_con_structure`) | wired |
| C1.RC.1 | C1 | RC | Позиция автора, paraphrase strict | wired |
| C2.WP.1 | C2 | WP | Смена регистра + сохранение фактов | wired |

---

## Probe

```bash
python lab/visual-curriculum/probe_cefr_gate_ru.py --store von-neumann
```

**Plan:** `lessons/ru-text-tract/data/cefr-gate-plan-v1.json`

### Выход пробы

```json
{
  "achieved_level": "B1",
  "block_12_pass": true,
  "nositel_claim_pass": false,
  "by_level": { "A1": {"know": 2, "total": 2}, "B1": { ... }, "C1": {"status": "deferred"} }
}
```

- **`block_12_pass`:** `achieved_level >= B1`
- **`nositel_claim_pass`:** `achieved_level >= C1` и **все** wired C1/C2 green — на текущем von-neumann **false** (C1 WP/RC и C2 register не закрыты)

### Критерии сценария (наследие interlocutor_v1)

Те же behavioral checks: semantic, anti_template, own_voice, honest partial — привязаны к **CEFR skill**, не к ad-hoc «dimension».

---

## Связь со старыми пробами

| Probe | Роль после CEFR gate |
|-------|---------------------|
| **`probe_cefr_gate_ru`** | **главный уровневой gate** |
| `probe_nositel_gate_ru` | регрессия B1 WI/WP (подмножество) |
| `probe_lexical_read_fluent_ru` | A2→B1 RC/L1 |
| `probe_oov_word_recall_ru` | B1 лексика |
| `probe_orthography_ru` / `probe_grammar_punct_ru` | B1–B2 WP |

---

## B2 vs B1 (не дублировать)

`B1.WP.2` и `B2.WP.1` — **разные** запросы: B2 требует явный scope по содержанию/терминам (`expect_semantic` + `expect_semantic_any`, `min_sentences: 2`), не копию B1-абзаца.

## Non-goals

- Ослаблять C1/C2 критерии ради green.
- Подменять CEFR устными навыками до аудиотракта.
- Считать размер словаря (TORFL table) gate’ом — только behavioral сценарии + отдельные L1/L2 пробы.
