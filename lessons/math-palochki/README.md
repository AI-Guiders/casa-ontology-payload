# Class: math-palochki

Arithmetic from sticks (palochki): action first, notation second, operand names in parallel (max 3–4 terms per lesson).

**Audience:** early numeracy (≈ 6–8), or agent curriculum event chain for von-neumann.

**Session length:** 15–25 min + optional 10 min stick play (repeat, no new words).

## Цикл (Нейманн)

```text
Урок (ingest)  →  run_agent (выводит сам)  →  check_agent_mastery (ты проверяешь)
```

Подробно: [MASTERY.md](MASTERY.md). Цель агента: [../../agents/von-neumann/GOAL-arith-mastery.md](../../agents/von-neumann/GOAL-arith-mastery.md).

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
| 13 | `kolb-count-rows` | Teacher demo: ряд счёта | presentation, без oracle |
| 14 | `commutative` | Перестановка + и × | `math.prop.commutative_*` |
| 15 | `associative-distributive` | Группировка, распределение | assoc, distributive |
| 16 | `identities-division` | 0, 1, ÷↔× | identity, inverse |
| 17 | `roles-and-four-ops` | Роли + 4 действия | recap roles + op scenes |
| 19 | `place-value-tens-ones` | Десятки и единицы | десяток, единица |
| 18 | `fraction-heaps` | Дроби на кучках | числитель, знаменатель, 1/2 2/3 3/4 |

## Группы в скобках (lesson 11)

```text
()       = 0    # пустая группа
(|)      = 1
(||)     = 2
(|||)    = 3
(IIIII)  = 5    # «римские» палочки I внутри скобок
```

## Kolb / «что если?» — часть жизни агента

Не curriculum и не привязка к `math.num.*`. Когда агент живёт (`run_agent.py`), в idle он сам пробует cue → predict → sleep → re-probe.

Teacher lesson-13 — **демо** count_row через ingest; runtime Kolb от этого не зависит.

## Division canon (lesson 07)

```text
|||| ÷ 2  →  (||)(||)     # groups of 2 → 2 heaps → quotient = 2
```

## Дроби на кучках (lesson 18)

Целое делим на **K равных кучек**. **Числитель** — сколько кучек взяли; **знаменатель** — на сколько кучек делили.

```text
1/2 = (||) ||              # 1 кучка из 2
2/3 = (||) [(||)(||)]      # 2 кучки из 3
3/4 = ()[()()()]           # 3 взяли (в скобках), 1 доля снаружи — палочки не рисовали
3/4 = (||) [(||)(||)(||)]  # то же: снаружи четверть, в […] три взятые кучки
```

`()` **в дроби** — не «ноль палочек» из lesson 11, а **слот одной кучки** (доли), когда внутри просто не стали рисовать `||`. Квадратные скобки `[…]` группируют несколько кучек одной порцией.

Связь с делением (lesson 08): `|||| на 2 кучки` → каждая доля — половина.

## Ingest + проверка

```powershell
cd d:\Experiments\PersonalCursorFolder\Financial\software\open\casa-ontology-payload
python casa/prisms/memory/gen_math_palochki_class.py
python tools/ingest_lesson_class.py --store-dir agents/von-neumann
python tools/run_agent.py --store-dir agents/von-neumann --once   # или жить дальше
python tools/check_agent_mastery.py --store-dir agents/von-neumann
```

Reports: `last-ingest-report.json`, `last-mastery-report.json`.

Cold bootstrap (один раз): `python tools/init_agent_self.py --store-dir agents/von-neumann`

## CASA mapping

| Lesson | Layer |
|--------|--------|
| 00–12 | numerals, ops, roles (legacy episodes with surface teaching) |
| 13–17 | `presentation: true` — co-scenes, properties, no numeric oracle in correct |
| 14–16 | `math.prop.*` on bundle; agent consolidates on sleep |
| 17 | `math.role.*` + op scenes |
| 18 | `math.frac.*` — дробь как доля кучек (числитель / знаменатель) |

Target agent: `agents/von-neumann/`.

## Agent workbook (not here)

Teacher material stays in `lessons/`. Тетрадь — только в `agents/von-neumann/journal/`.
