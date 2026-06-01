# Class: math-palochki

Arithmetic from sticks (palochki): action first, notation second, operand names in parallel (max 3–4 terms per lesson).

**Audience:** early numeracy (≈ 6–8), or agent curriculum event chain for von-neumann.

**Session length:** 15–25 min + optional 10 min stick play (repeat, no new words).

## Syllabus

| # | Slug | Title | New terms |
|---|------|-------|-----------|
| 00 | `zero-and-digits` | Ноль и цифры ↔ палочки | ноль, пусто, 0–4, одна/две/… палочки |
| 01 | `sticks-and-heaps` | Палочка и кучки | палочка, кучка, сколько |
| 02 | `equal-heaps` | Поровну (пролог к ÷ и ×) | поровну, в каждой, кучек |
| 03 | `addition` | Сложение: склеить | слагаемое, сумма |
| 04 | `subtraction` | Вычитание: отрезать | уменьшаемое, вычитаемое, разность |
| 05 | `groups-of-n` | Группы по N | группа, по сколько, сколько раз |
| 06 | `multiplication` | Умножение | множитель, произведение |
| 07 | `division-groups-of` | Деление: по N в кучке | делимое, делитель, частное |
| 08 | `division-into-heaps` | Деление: на K кучек | (same names, other question) |
| 09 | `which-question` | Какой это вопрос? | — (drill) |
| 10 | `operand-vocabulary` | Словарь операндов | one-page recap |
| 11 | `paren-groups` | Группы в скобках | (), (\|), (IIIII) |
| 12 | `compute-drill` | Вычисления: примеры | + − × ÷ на кучках и цифрах |
| 13 | `kolb-count-rows` | Kolb: ряд счёта | count_row → emergent pattern |

## Группы в скобках (lesson 11)

```text
()       = 0    # пустая группа
(|)      = 1
(||)     = 2
(|||)    = 3
(IIIII)  = 5    # «римские» палочки I внутри скобок
```

## Kolb / «что если?» — часть жизни агента

Не отдельная команда host'а. Когда агент живёт (`run_agent.py`), в idle он сам пробует ряды, скобки, sleep — см. `agent_curiosity` внутри `agent_life`.

Teacher lesson-13 — то же через ingest-событие; дублировать runtime не обязан.

## Division canon (lesson 07)

```text
|||| ÷ 2  →  (||)(||)     # groups of 2 → 2 heaps → quotient = 2
```

## Weekly rhythm (optional)

| Day | Activity |
|-----|----------|
| Mon | new lesson |
| Wed | sticks only, no new vocabulary |
| Fri | 3 review tasks + one puzzle |

## Ingest into von-neumann

```powershell
cd d:\Experiments\PersonalCursorFolder\Financial\software\open\casa-ontology-payload
python casa/prisms/memory/gen_math_palochki_class.py
python tools/ingest_lesson_class.py --store-dir agents/von-neumann
```

Report: `lessons/math-palochki/last-ingest-report.json` (probe cues).

Ingest — **событие учителя** в store агента. Дальше жизнь продолжается **внутри агента** после `run_agent.py` (rehearse, тетради, Kolb — не host CLI).

Cold bootstrap (один раз): `python tools/init_agent_self.py --store-dir agents/von-neumann`

## CASA mapping

| Lesson | Layer |
|--------|--------|
| 00 | `math.num.zero`, digit `0`–`4` ↔ stick runs, RU count phrases |
| 01–02 | `math.num.*`, `math.entity.stick`, `math.role.heap` |
| 03–06 | `math.op.add` … `math.op.mul` + `math.role.*` |
| 07–08 | `math.op.div` + dividend/divisor/quotient |
| 10 | recap `math.role.*` ↔ `lang.word.*` |
| 11 | `math.entity.group`, `math.ctx.group`, `()` … `(IIIII)` |
| 12 | drill `math.op.*` on sticks, groups, digits |
| 13 | `count_row:*` → Kolb emergent pattern hub |

Target agent: `agents/von-neumann/` (lesson = teacher event → consolidate в **его** `ltm/`; workbook = `journal/` — агент пишет сам, когда живёт).

## Agent workbook (not here)

Teacher material stays in `lessons/`. Тетрадь — только в `agents/von-neumann/journal/`; создаёт и пишет **агент** в своей жизни, не host.
