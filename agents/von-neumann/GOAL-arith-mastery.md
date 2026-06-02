# Цель: Нейманн — арифметика без runtime-oracle

## Критерий готовности

- **Compute:** ≥85% `mastery_probe` tier `compute` (все 4 действия, sticks + digits)
- **Roles:** ≥90% tier `role` — слагаемое, делимое, …
- **Properties:** ≥75% tier `property` — коммутативность, ноль/единица, ÷↔×

Проверка: `python tools/check_agent_mastery.py --store-dir agents/von-neumann`

## Как учится (не как проверяется)

1. **Teacher:** ingest math-palochki 00–17 — сцены, палочки, слова, co-presentation свойств
2. **Agent:** predict → surprise → hippo → sleep → Kolb → journal (свой опыт на поле)
3. **Teacher:** mastery probe — единственное место с `expect`

## Non-goals

- Нет таблицы ответов в predict
- Нет «правильного = 5» в ingest для presentation-уроков 14–17
- Bundle на tick не читается как oracle (только поле + `ltm/`)

## Тетради агента

`journal/kolb`, `journal/math-palochki` — пишет сам в жизни; teacher не заполняет.
