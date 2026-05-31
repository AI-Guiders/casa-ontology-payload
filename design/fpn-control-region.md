# FPN control region v0 (layout B)

**Status:** **superseded** — см. [`control-lattice-stack.md`](control-lattice-stack.md) (отдельные решётки + bridges, как SSS).  
**Date:** 2026-05-28  
**Prerequisite:** [`casa-glossary.md`](casa-glossary.md) § FPN, [`casa-layout.md`](casa-layout.md)

## Зачем отдельный FPN на grid

**CEN** — решение **на этот тик**: action, targets, один `cen_plan`.  
**FPN** — **рабочая память задачи** между тиками: цель диалога, стек подцелей, режим (grammar / code / explore), что SN должен подсвечивать.

Без FPN на поле эта нить уезжает в IDE/чат вне CA — ломается аналогия «всё на цилиндре, слои параллельны».

## Роли четырёх сетей (v1)

| Регион | Сеть | Вопрос |
|--------|------|--------|
| `dmn_ontology` | DMN | *Что знаем?* (долгая память, KB) |
| `sn_router` | SN | *Что сейчас релевантно?* (gate) |
| `fpn_control` | **FPN** | *Какую задачу держим?* (WM, multi-step) |
| `cen_planner` | CEN | *Что сделать сейчас?* (act) |

```text
0,0                                    63,0
+--------------------------------------+
|            Ontology / DMN              |  x:0..31, y:0..63
|                                      |
+======================+===============+
| Router / SN          |  (reserved)   |  x:32..63, y:0..20
|                      +---------------+
|                      | FPN / WM      |  x:32..63, y:21..42
|                      +---------------+
|                      | Planner / CEN |  x:32..63, y:43..63
+----------------------+---------------+
```

Правая половина — **три горизонтальных пояса** (~21 строки каждый). DMN сохраняет полширины и полную высоту.

## Каналы FPN

| Pattern | Смысл |
|---------|--------|
| `wm.goal.*` | активная цель (id + priority) |
| `wm.stack.*` | подцели / шаги плана (ordinal) |
| `wm.mode.*` | режим: `dialogue` \| `kb_query` \| `code_nav` \| `repair_field` |
| `wm.tick.*` | привязка к макро-тику **T** (session) |

CEN **читает** `wm.*`; FPN **пишет** после каждого исполненного action; SN **читает** `wm.mode` для bias salience.

## Порты (дополнение к P1–P3)

| Порт | Направление | Несёт |
|------|-------------|--------|
| **P1** | DMN → SN | digest *(без изменений)* |
| **P2a** | SN → FPN | salience mask + digest hint |
| **P2b** | FPN → CEN | gated WM (goal + top subgoal) |
| **P3** | CEN → DMN | `task.query.*` *(без изменений)* |
| **P4** | CEN → FPN | outcome: success / fail / need_clarify |
| **P5** | FPN → SN | top-down mode bias (опционально) |

Цикл на одном **T**:

```text
DMN ──P1──► SN ──P2a──► FPN ──P2b──► CEN ──P3──► DMN
              ▲            │            │
              └── P5 ──────┴── P4 ─────┘
```

## Поршень (z) и FPN

FPN участвует в тех же фазах **z**, что и SN/CEN, но с собственными масками:

| z | FPN |
|---|-----|
| 0 encode | WM пусто или carry-over с прошлого T |
| 1 dmn_repair | WM **не** damage-ится (как SN gate — по контракту v0) |
| 2 digest | FPN читает digest summary для привязки goal↔concepts |
| 3 gate | FPN обновляет `wm.mode` от SN |

Артикуляция (будущая z=4 или внешний слой) читает **CEN action + FPN goal**.

## Отличие от IDE session

| | FPN на grid | IDE / `agent_session.json` |
|---|-------------|----------------------------|
| Скорость | в hot path decode | UI, персистентность |
| Repair | NCA может восстанавливать WM-паттерн (lab) | JSON надёжнее для v1 |
| Симметрия | четыре сети на одном цилиндре | обязательный mirror |

**Практика v1:** источник правды session — файл; **mirror** в FPN region при каждом import / tick для infer и damage-тестов.

## Cosmos mapping

| Cosmos | FPN analog |
|--------|------------|
| Reason (long CoT, plan) | удержание цепочки рассуждения |
| Predict | нет (состояние мира = DMN) |

## Implementation sequencing

1. **Design** — этот документ + обновить glossary (recommended B).
2. **`layout.v1.json`** — регион `fpn_control`, rects, порты P2a/P2b/P4/P5.
3. **Runtime** — `fpn_state.py`: load/session → WM tensor; `sn_route` / `cen_plan` read `wm`.
4. **Lab** — damage только в DMN; FPN stuck-mode тест отдельно.
5. **IDE** — sync `agent_session` ↔ field FPN slice (опционально MCP).

## Non-goals (v0)

- Не дублировать DMN (факты остаются в claims / digest).
- Не заменять articulation MoE.
- Не требовать FPN train до стабильного DMN G/H.

## Связанные файлы

- [`casa-cosmos-mapping.md`](casa-cosmos-mapping.md)
- [`layered-ca-pipeline.md`](layered-ca-pipeline.md)
- `tools/sn_cen_runtime.py` — точка интеграции CEN/FPN
