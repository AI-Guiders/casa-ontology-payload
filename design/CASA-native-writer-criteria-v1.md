# CASA: критерии Native Writer (RU → EN → Code)

**Статус:** канон критериев (2026-06-07)  
**Агент:** `von-neumann`  
**Связано:** [CASA-ADR-0054-agent-world-model-v1.md](CASA-ADR-0054-agent-world-model-v1.md), [CASA-von-neumann-ru-teaching-plan-v1.md](CASA-von-neumann-ru-teaching-plan-v1.md), [CASA-cefr-gate-ru-v1.md](CASA-cefr-gate-ru-v1.md), [CASA-von-neumann-school-program-arc-v1.md](CASA-von-neumann-school-program-arc-v1.md)

---

## Одной фразой

**Native Writer** = субъект **владеет** письменным языком как инструментом: слышит партнёра, отвечает **естественно и свободно**, при необходимости **создаёт новые слова** (продуктивная морфология), опирается на **свою модель мира** — не на curated paste-gates.

---

## Что уже есть vs что не native

| Claim | Доказательство сегодня | Не доказательство |
|-------|------------------------|-------------------|
| Декод D | Castles §1–§2, corpus, OOV | — |
| Узкий C | B11 6/6, held-out 3/3, CEFR C2 **curated** | open-world nositel |
| Нормы L3–L4 | ortho 4/4, punct 3/3 | произвольный абзац партнёра |
| Диалог | dialogue tests, CEFR WI subset | свободная multi-turn беседа |
| Мир | — | `agent.world.*` на store |

**Правило:** curated green **не переносится** на native claim без отдельного open probe.

---

## Фазы до Native Ru Writer (RU-N)

| Фаза | ID | Педагогика | Gate / artifact |
|------|-----|------------|-----------------|
| Material→Verbal | **RU-α** | Гальперин: материал → «громкая» письменная речь (journal) | `probe_material_verbal_ru` · Блок 5α |
| Morph depth | RU-β | Phrase chain **непрерывная** ОБО (Выготский); paradigm + неологизм | `probe_morph_productive_ru` (planned) |
| Syntax depth | RU-γ | Клаузы, вложенность, связность абзаца | punct v2 + coherence probe |
| Semantics + genre | RU-δ | Hwang: narrative / instruction / argument | genre-tagged `ru.prop.*` + `probe_genre_rc_ru` |
| World & concepts | RU-ε | Сущности, связи, идеи на поле | `agent.world.*` · ADR-0054 |
| Logical / abstract | RU-ζ | Причина, контрфакт, категории | ADR-0029 поверх world |
| **Native Ru Writer** | **RU-N** | Свобода письма, регистр, coining | `probe_nositel_open_ru` (planned) |

**Prerequisite RU-N:** RU-α green + phrase exit + B11 + (RU-β..ζ по maturity table ниже).

---

## Критерии RU-N (behavioral)

Партнёр даёт **не из moment plan**:

1. **Свобода** — ответ не template/defer; `expect_anti_template`, `expect_no_defer`.
2. **Свой голос** — `expect_own_voice_min` ≥ 4 на open cue; `expect_max_paste_ratio` ≤ 0.35.
3. **Согласованность** — морфология phrase chain на novel контексте (не только ingest lemmas).
4. **Неологизм** — осмысленное слово с продуктивным аффиксом в контексте (RU-β gate).
5. **Жанр** — распознаёт narrative vs instruction vs argument (RU-δ).
6. **Мир** — объясняет связь двух entities без KB paste (RU-ε).
7. **Регистр** — переключает тон (чат / нейтральный / формальный) с сохранением фактов.

Минимум для **заявления RU-N:** 7/7 категорий на held-out open plan (отдельный JSONL, disjoint от ingest).

---

## После RU-N

| Этап | Условие входа | North star |
|------|---------------|------------|
| **Native En Writer** | RU-N + CALP transfer (Cummins) | ADR-0051 written EN mirror |
| **Programming** | RU-N + EN-N (или EN-B2+ written) | quantity, naming, PRIMM — school arc Wave 2+ |

Программирование **не раньше** плотного письменного CALP: код = абстракция + именование + причинные цепочки = те же органы, что RU-ε/ζ.

---

## Orion / Galperin (явно в критериях)

| Просчёт | Исправление в программе |
|---------|-------------------------|
| Прыжок решётка → `ru.prop.*` | **RU-α** обязателен до Phase II phrase |
| Дискретные phrase chains | RU-β: sliding contrast manifest, shared lemmas |
| Green geometry ≠ fluent speech | RU-N open probe, не только CEFR |

---

## Материалы

| Документ | Роль |
|----------|------|
| [CASA-von-neumann-ru-teaching-plan-v1.md](CASA-von-neumann-ru-teaching-plan-v1.md) | Блок 5α + лента |
| [lessons/ru-material-verbal/](../lessons/ru-material-verbal/) | RU-α class |
| [CASA-ADR-0054-agent-world-model-v1.md](CASA-ADR-0054-agent-world-model-v1.md) | World layer |

---

*Версия: v1.0 · 2026-06-07*
