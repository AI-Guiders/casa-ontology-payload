# Experiment K: C# «как в 8 классе» — понять синтаксис и писать простые консоли

**Status:** **paused** (2026-05-29) — сначала закончить язык (J + J0), см. [`experiment-j-language-complete-v1.md`](experiment-j-language-complete-v1.md)  
**Date:** 2026-05-29 (north star 2026-05-29)  
**Depends on:** **Exp J0** (literacy read/write), Exp J (grammar), field/SN/CEN — [`experiment-j0-russian-literacy-v1.md`](experiment-j0-russian-literacy-v1.md)

## North star

> Агент **понимает** базовый C# (синтаксис + консоль), как школьник после курса: может **написать любую простую консольную программу из учебного списка**, а не один заученный шаблон.

**«Понял»** = не цитата из KB, а:

1. Собирает **новую** программу по описанию (не только guess-number).
2. **`dotnet build`** проходит (или цикл исправления по ошибкам компилятора).
3. **`dotnet run`** ведёт себя как задано (ввод, ветвления, цикл, вывод).

Guess-number — **первая контрольная**, не финал.

**Сейчас:** K0 recall по C# — да; **J0 literacy** — в работе (перефразы, «читать/писать»). **Emit / compile** — после gate J0 ≥ 0.85 paraphrase.

---

## Учебный список (tier «8 класс»)

Минимальный набор программ для **K4 generalization** (каждая — gold + 3–5 queries):

| # | Задача | Навыки |
|---|--------|--------|
| 1 | Hello, имя | `WriteLine`, строка |
| 2 | Сумма двух чисел | `ReadLine`, `TryParse` |
| 3 | Таблица умножения (одна строка) | `for` |
| 4 | Максимум из трёх | `if/else` |
| 5 | **Угадай число** | `Random`, `while`, сравнение |
| 6 | Меню 1/2/3 | `switch` или `if`, цикл |
| 7 | Счётчик до N | `while`, счётчик |
| 8 | Среднее оценок | массив или список (опционально phase 2) |

**Pass K4:** ≥ **6/8** задач: build OK + scripted run matches gold transcript.

---

## Success criteria (levels)

| Level | Критерий | Автопроверка |
|-------|----------|--------------|
| **K0** | Recall: синтаксис/библиотека по запросу | `answer@1` на `queries.jsonl` + расширенный набор |
| **K1** | CEN: `emit_code`, expert **code** (не grammar) | plan JSON |
| **K2** | Один emit → **build** OK | `bench_exp_k_emit.py --build` |
| **K3** | **run** OK (guess-number) | stdin script |
| **K4** | **Любая простая** из списка 8 | multi-task bench |
| **K5** | **Compile repair loop** (ошибка → правка) | 2–3 итерации max |

---

## KB: хватит ли данных?

### Что уже есть в agent-notes (не то же самое)

| Источник | Объём | Уровень | Для «8 класса» |
|----------|-------|---------|----------------|
| `worlds/software-dotnet-csharp/` | fundamentals, playbooks | TFM, SDK, архитектура | ❌ не учебник синтаксиса |
| `software-authoring/code-writing-principles-v1.md` | стиль, async, nullable | профи | ❌ |
| `software-dotnet-tooling-roslyn/` | MCP, диагностика | инструмент | ❌ |
| `software-dotnet-avalonia/` | UI | ❌ | ❌ |
| MS Learn ссылки в principles | внешние URL | не в claims | ⚠️ нужен ingest |

**Вывод:** в KB **много C# для инженера**, **мало для школьника**. Для Exp K **не хватает** — нужен **новый слой**, не «подключить весь dotnet-csharp».

### Что нужно добавить (оценка объёма)

Цель — как Exp J grammar: **~60–120 claims** с примерами кода в тексте.

| Модуль | Claims (оценка) | Где жить |
|--------|-----------------|----------|
| Первая программа, `Main`, `;` | ~8 | `kb-csharp-console-grade8-v1.md` |
| Типы `int`/`string`, ввод-вывод | ~12 | §2 |
| `if/else`, сравнения | ~10 | §3 |
| `while`/`for` | ~10 | §4 |
| `Random`, `Console` | ~8 | §5 |
| Методы `static` простые | ~10 | §6 |
| 8 эталонных программ (разбор по строкам) | ~40 | §7–14 |
| Типичные ошибки компилятора | ~15 | §15 |

**Итого ~80–110 claims** — достаточно для K0 recall и digest для LM emit; **не** нужен весь MSDN.

### Lab сейчас

| Артефакт | Статус |
|----------|--------|
| `lab/kb/kb-csharp-guess-number-canonical.md` | 1 мини-док, K0 smoke **answer@1=1** |
| `code-agent-lab-v0` store | работает |
| `software-dotnet-csharp` в union | **не импортирован** в code store |

**Phase 1 KB:** написать `kb-csharp-console-grade8-v1.md` (agent-notes или lab), sync в `code-agent-lab-v0`, расширить `queries.jsonl` + `gold/` на 8 программ.

### Внешние источники (курировать, не слепой scrape)

- [C# tour — console](https://learn.microsoft.com/en-us/dotnet/csharp/tour-of-csharp/overview)
- [Console class](https://learn.microsoft.com/en-us/dotnet/api/system.console)
- Учебники «информатика 8 класс» / Stepik beginner C# — **пересказ в claims**, не копипаста книги

---

## Architecture

```text
KB tier grade8 (новый) + canonical programs
    → code-agent store / field
    → SN: code_task vs ru_grammar
    → CEN: emit_code | explain_code | answer_from_memory
    → Expert code: plan → Program.cs (LM + digest; template только для отладки)
    → Execute: dotnet build → on fail: compiler → expert code (repair)
    → K4 bench: 8 задач
```

| Слой | Exp J (русский) | Exp K (C#) |
|------|-----------------|------------|
| Эксперт articulation | **grammar** | **code** |
| «Грамматика» | орфография, запятая | **синтаксис C#**, statements |
| Проверка | answer@1 | **компилятор + run** |
| NCA | windowed RU | опционально; **не** замена понимания C# |

---

## Phases

### Phase 0 — scaffold ✅

Lab canonical guess-number, `run_exp_k_smoke.ps1`, K0 recall 1.0 на 5 queries.

### Phase 1 — KB «8 класс» ✅ (2026-05-29)

- [`kb-csharp-console-grade8-v1.md`](../../../../experiments/agent-notes/knowledge/worlds/software-dotnet-csharp/kb-csharp-console-grade8-v1.md) — **183 claims**, §0 педагогика, §1–11 синтаксис, §12–19 эталоны, §20–22 ошибки/чеклист
- Sync: `scripts/run_exp_k_sync_grade8.ps1` → **answer@1 = 1.0** на 25 queries (`lab/exp_k_grade8/queries.jsonl`)
- Gold: `lab/exp_k_grade8/gold/01..08` (+ guess-number в `exp_k_guess_number`)
- 8× `gold/*.cs` + `queries.jsonl` per task
- Manifest + sync → `code-agent-lab-v0`
- Target: **answer@1 ≥ 0.9** на **≥40** queries

### Phase 2 — plan + expert code (K1)

- Router: «напиши программу», «консоль», «C#» → `emit_code`
- Отдельный store или union с **явным** `expert=code` в CEN output

### Phase 3 — emit + build + repair (K2–K5)

- LM с digest (поле + top claims) **или** structured plan (steps → codegen)
- `bench_exp_k_emit.py`: multi-task, compile loop
- Guess-number = task #5 в общем bench

### Phase 4 — field (optional)

- Snippets на grid только если K0–K4 уже без grid

---

## Manifest & store

```text
manifests/kb-bundles-csharp-lab-v0.json     # phase 0
manifests/kb-bundles-csharp-grade8-v1.json  # phase 1 (to add)
lab/agent-stores/code-agent-lab-v0/
lab/exp_k_grade8/
  tasks/*.jsonl
  gold/*.cs
```

---

## Smoke

```powershell
.\scripts\run_exp_k_smoke.ps1
```

Phase 1 (after KB):

```powershell
.\scripts\run_exp_k_sync_grade8.ps1   # to add
```

---

## Non-goals

- Профи .NET (TFM, DI, async) как prerequisite
- Avalonia / ASP.NET
- NCA вместо компилятора
- «Понял ООП» / наследование — tier 9 класс, phase 2

---

## Relation to Exp J

| | Exp J | Exp K |
|---|-------|-------|
| Компетенция | русская норма | **C# console grade 8** |
| KB size target | ~89 grammar claims | **~80–110 code claims** (новый док) |
| Train | NCA windowed | KB + emit + compile loop first |

---

## Open decisions

1. **Один MD** `kb-csharp-console-grade8-v1` vs несколько bundles по главам.
2. **LM обязателен** для K4 с первого дня или template до 3 задач, LM с 4-й.
3. **Русские** подсказки в `Console.WriteLine` vs English — bench policy.
