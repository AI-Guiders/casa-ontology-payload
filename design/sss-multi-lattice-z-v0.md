# ССС: отдельные решётки + связи по z

**Status:** lab smoke (`sss_stack_v0`, store `sss-lab-v0`) — полосы deprecated  
**Date:** 2026-05-28  
**Parent:** [`second-signal-system-v0.md`](second-signal-system-v0.md)  
**Machine-readable:** [`sss-lattice-stack.v0.json`](sss-lattice-stack.v0.json)

## Идея

Полосы B0–B3 на одной плоскости (`layout.v1`) — **временный** компромисс.  
Целевое: **каждый уровень знака = целая решётка** `(x, y)`; **ось z** — стек решёток и **пространственные мосты** между соседними z-слоями.

Ничто в модели не мешает: один цилиндр = тензор `S[x, y, z]`, где `z` — не только «фаза encode/repair» на той же карте, а **индекс решётки** (графема / слог / слово / фраза).

## Две оси z (не путать)

| Ось | Смысл | Пример |
|-----|--------|--------|
| **`z_level`** (ССС) | **какая** решётка активна | z=0 графемы, z=1 слоги, z=2 слова |
| **`z_phase`** (поршень внутри слоя) | **что делаем** на этой решётке | encode → repair → digest (как в [`layered-ca-pipeline-v0.md`](layered-ca-pipeline-v0.md)) |

Полный тик: сначала выбрать/пройти `z_level`, внутри — микро-фазы `z_phase` + CA-шаги `t`.

```text
        z_level (решётки ССС)
              ↑
    L3 phrase ├─────────────────┐
    L2 word   ├──────── z_bridge ─┤ compose ↑
    L1 syll   ├──────── z_bridge ─┤
    L0 graph  ├─────────────────┘
              │
    каждый слой: свои (x,y), свой NCA, свой digest
```

## z-мосты (пространственная связь уровней)

Мост — не только ребро `E:` в JSON, а **канал на поле** между клеткой `(x,y)` на `z=k` и клеткой `(x',y')` на `z=k+1`.

| Тип | Смысл | Lab v1 |
|-----|--------|--------|
| **compose** | активность на L0 (м+а) поднимает кандидата на L1 (ма) | детерминированный порт по co-activation |
| **lift** | слог → слово | то же между L1→L2 |
| **bind** | слово → фраза | L2→L3 |
| **correct** | teacher-сигнал **между** z (было на L0, норма на L1) | episodic write на мост |

Контракт порта (v0):

```json
{
  "id": "z_bridge_L0_L1",
  "from_lattice": "L0_grapheme",
  "to_lattice": "L1_syllable",
  "kind": "compose",
  "coupling": "local_3x3_xy",
  "channels": ["zbr.compose.*"]
}
```

`local_3x3_xy`: NCA на `z=k` читает соседей на `z=k±1` в окрестности `(x,y)` — **настоящая** пространственная связь, обучаемая repair.

## field_state (целевая форма)

```json
{
  "subsystem": "sss",
  "schema_version": "sss_lattice_stack_v1",
  "lattices": {
    "L0_grapheme": { "z": 0, "width": 32, "height": 32, "cells": [], "phase": "repair" },
    "L1_syllable": { "z": 1, "width": 32, "height": 32, "cells": [] },
    "L2_word":     { "z": 2, "width": 32, "height": 32, "cells": [] },
    "L3_phrase":   { "z": 3, "width": 32, "height": 32, "cells": [] }
  },
  "z_bridges": ["z_bridge_L0_L1", "z_bridge_L1_L2", "z_bridge_L2_L3"],
  "sn": { "active_lattice": "L0_grapheme" }
}
```

Один `field_state.json` — **стек**, не один плоский `grid.cells` на 64×64.

## SN / CEN

- **SN:** `active_lattice` (какой z_level открыт), salience **внутри** решётки + разрешение подъёма по мосту.
- **CEN:** babble readout **с активной решётки**; запрос «мама» может поднять z L0→L1→L2 по compose-цепочке.
- **Digest:** per-lattice digest, опционально **composite** digest после прохода по мостам.

## От stub v0 к v1

| v0 (сейчас) | v1 (целевое) |
|-------------|--------------|
| полосы `dmn_b0..b3` в одном `grid` | 4 решётки в `lattices.*` |
| `bukvar_codec` кладёт в y-band | `sss_codec` пишет в `Lk` целиком |
| нет z-мостов | `zbr.*` каналы + train windowed по паре слоёв |
| `layered-ca-phases` только z_phase | stack json + phased rollout per lattice |

## Первая СС

Решётки `F0_vis`, `F0_math` — **другой** z-стек (или другой `subsystem_id`), мосты `E:` hub к `L2_word`, не смешивать каналы с ССС.

## Bench

- **lattice_coverage** — каждая ожидаемая графема только на L0, не размазана по L2.
- **z_compose_hit** — активация `м`+`а` на L0 → `ма` на L1 после rollout с мостом.
- **no_flat_union** — отключён grep `claims_nav` на hot path.

## Для Cursor

Говорить: **решётки по z**, **z-мосты**, не «полосы букваря».  
`layout.v1` bands — deprecated path; новый канон — `sss-lattice-stack.v0.json`.
