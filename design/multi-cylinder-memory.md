# Несколько блоков-призм (prism_*): память + гиппокамп

**Status:** design (расширение vN-mapping; **= sleep из north star**)  
**Date:** 2026-05-28  

## Геометрия: призма (квадратное основание), не цилиндр

Каждый `prism_*` — **стек квадратных решёток** одного размера в `(x, y)`, уровни различаются по **z** (`z_level` / `z_ctrl`). Одна решётка — **квадрат** в плоскости xy (32×32, 64×64). Стек уровней — **прямая призма** с квадратным основанием: «высота» = число решёток по z, не круглый цилиндр.

**Куб** — частный случай призмы, когда по z столько же «этажей», сколько клеток по стороне основания *и* это один непрерывный тензор `S[x,y,z]`. У нас z — **индекс решётки** (отдельные карты + мосты), поэтому в каноне говорим **призма / стек**, не «один куб 32³».

В `field_state`: корень **`prisms`**, блоки **`prism_memory`**, **`prism_control`**, **`prism_hippo`**, schema **`multi_prism_v1`**. Старые `cylinders` / `cyl_*` читаются при загрузке (`normalize_prisms`). Файл модуля `memory_prisms.py` — legacy имя; API: `ensure_cylinders` = `ensure_prisms`.

**North star §5:** «периодическая консолидация (import / finetune / **sleep**)» — [`agent-existence-north-star.md`](agent-existence-north-star.md)  
**See also:** [`von-neumann-casa-mapping.md`](von-neumann-casa-mapping.md), [`sss-multi-lattice-z.md`](sss-multi-lattice-z.md)

## Идея

Один буфер 64×64 — **PoC**. Целевое: **несколько блоков (`prism_*`)** — отдельные субстраты с общей шиной и CU, у каждого своя роль.

```text
                    ┌──────────── SN / FPN (CU) ────────────┐
                    │         active_prism, gate        │
                    └───────────┬─────────────┬────────────┘
                                │             │
              ┌─────────────────▼──┐    ┌─────▼──────────────────┐
              │  PRISM_MEMORY       │    │  PRISM_HIPPO            │
              │  долговременные     │◄───│  эпизоды, fast write    │
              │  решётки L0..L3     │    │  pattern separation     │
              │  F0 math/vis        │    │  consolidate → memory   │
              └─────────────────────┘    └─────────────────────────┘
                     ▲                              │
                     └──────── consolidate ─────────┘
                              (sleep / T_batch)
```

Ничто не мешает: это **не** три файла JSON на диске как «память», а **три блока-призмы** (три `subsystem` в agent store) с **мостами** между ними.

## Sleep = T_consolidate (это одно и то же)

В north star **sleep** — не метафора «агент отдыхает», а **отдельный режим макро-тика**:

| Режим | Что крутится | Призмы |
|-------|----------------|----------|
| **T_wake** | perceive → SN → CEN → babble/act | read **prism_memory**, write **prism_hippo** on correct |
| **T_sleep** | consolidate → NCA/repair → prune | **hippo → memory**, без внешнего I/O |

```text
  T_wake:  … → babble wrong → episode → prism_hippo
  T_sleep: prism_hippo ──merge──► prism_memory ; hippo trim ; field_version++
  T_wake:  … babble лучше на том же cue (held-out)
```

**Import / finetune** из §5 north star — **соседние** каналы (KB с диска, opt-in train), но **не замена** sleep:  
git ingest = I/O; **sleep** = перенос **своего** episodic из гиппокампа в LTM.

Hook в lab (roadmap): `agent_autonomous_tick.py --sleep-only` или каждые N wake-тиков → один `T_sleep`.

## Призмы (id)

| id | Роль | Аналог | Содержимое |
|----|------|--------|------------|
| **`prism_memory`** | Долговременная память | кора / DMN | SSS `L0..L3`, F0 stacks, медленно меняется |
| **`prism_hippo`** | Быстрая эпизодическая | гиппокамп | стек **H0…H3** (специалисты), consolidate → memory — [`hippo-lattice-stack.md`](hippo-lattice-stack.md) |
| **`prism_io`** (опц.) | Буфер ввода | сенсорный буfer | текущий utterance, не смешивать с LTM сразу |
| **`prism_agent`** | **Личная память агента** | scratch LTM | `{store}/agent/` — решётки + NCA; **не** в profile `ltm/` export — [`CASA-ADR-0014-agent-prism.md`](CASA-ADR-0014-agent-prism.md) |

**SN/CEN/FPN** — не отдельные призмы памяти, а **управление** поверх (как CU + шина между устройствами).

## Гиппокамп: что делает

| Функция | Lab / код |
|---------|-----------|
| **Быстрая запись** | babble attempt + teacher correction → `prism_hippo` only |
| **Pattern separation** | похожие эпизоды не затирают друг друга (разные tiles / hash anchors) |
| **Pattern completion** | cue «ма» → partial replay эпизода на hippo |
| **Consolidate** | batch: hippo → **merge** в `prism_memory` (NCA finetune, field_write, strengthen z_bridge) |
| **Forget / trim** | episodic TTL после успешной консолидации |

```text
  T (online):
    listen  → prism_io или hippo
    babble  → read prism_memory (+ hippo cue)
    wrong   → write prism_hippo (episode)
    right   → optional direct tweak memory (rare)

  T_consolidate (sleep / каждые N тиков):
    hippo episodes → train windows on memory lattices
    prune hippo
    field_version++ on prism_memory only
```

## Шина между призмами

| Мост | Направление | Смысл |
|------|-------------|--------|
| **`hippo_to_memory`** | hippo → memory | консолидация: «было X, стало Y» |
| **`memory_to_hippo`** | memory → hippo | cue для completion (digest snapshot) |
| **`io_to_hippo`** | io → hippo | сырой listen без порчи LTM |
| **`z_bridge_*`** | внутри prism_memory | compose L0→L1 (как сейчас SSS) |

Физически: отдельные `field_state.prisms.{id}.lattices` или отдельные store-файлы; SN держит **`active_prism`**.

> **Legacy:** при загрузке `cylinders` / `cyl_*` / `active_cylinder` нормализуются в `prisms` / `prism_*` / `active_prism` (`normalize_prisms`).

## field_state (целевая форма)

```json
{
  "schema_version": "multi_prism_v1",
  "prisms": {
    "prism_memory": {
      "subsystem": "sss",
      "lattices": { "L0_grapheme": {}, "L1_syllable": {}, "L2_word": {} }
    },
    "prism_hippo": {
      "subsystem": "episodic",
      "lattices": { "H0_episode": { "width": 32, "height": 32, "cells": [] } },
      "episodes": [
        { "id": "ep-001", "cue": "м а", "babble": "ам", "correct": "ма", "tick": 42 }
      ]
    }
  },
  "sn": {
    "active_prism": "prism_memory",
    "active_lattice": "L0_grapheme"
  },
  "consolidation": {
    "last_run_tick": 0,
    "episodes_merged": 0
  }
}
```

## Von Neumann перекладка

| vN | Несколько призм |
|----|-----------------|
| RAM | `prism_memory` |
| Cache / write buffer | `prism_hippo` |
| Disk | git KB (I/O only) |
| «Flush cache» | **consolidate** hippo → memory |
| MMU | SN: какая призма/lattice адресуется |

## Что уже есть vs что добавить

| Есть | Нужно |
|------|--------|
| `sss.lattices` ≈ prism_memory (одна призма) | `prism_hippo` + episode log |
| `field_version`, NCA repair | consolidate job (windowed train on episodes) |
| `import_knowledge_delta` (KB→field) | **не** путать с hippo: KB = I/O, hippo = **свой** опыт |
| FPN session | `T_consolidate` в autonomous loop |

## Non-goals

- Гиппокамп **не** хранит encyclopedia grammar KB.
- Consolidate **не** = git commit; git — аудит, memory — призма LTM.
- Три призмы **не** = три LLM.

## Roadmap

1. **v1** — `prism_hippo` struct + append episode on correct API (без NCA).
2. **v2** — consolidate script: episodes → strengthen tokens on `prism_memory` lattices.
3. **v3** — train `z_bridge` on consolidated pairs.
4. **v4** — `prism_io` listen buffer + SN routing io→hippo→memory.

## Для Cursor

«Несколько призм» = **несколько field-буферов** с ролями; **гиппокамп** = быстрый эпизод + **optimize/merge** в призму памяти, не отдельный chat-RAG.
