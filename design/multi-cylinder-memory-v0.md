# Несколько цилиндров: память + гиппокамп

**Status:** design (расширение vN-mapping; **= sleep из north star**)  
**Date:** 2026-05-28  
**North star §5:** «периодическая консолидация (import / finetune / **sleep**)» — [`agent-existence-north-star-v0.md`](agent-existence-north-star-v0.md)  
**See also:** [`von-neumann-casa-mapping-v0.md`](von-neumann-casa-mapping-v0.md), [`sss-multi-lattice-z-v0.md`](sss-multi-lattice-z-v0.md)

## Идея

Один буфер 64×64 — **PoC**. Целевое: **несколько цилиндров** — отдельные субстраты с общей шиной и CU, у каждого своя роль.

```text
                    ┌──────────── SN / FPN (CU) ────────────┐
                    │         active_cylinder, gate        │
                    └───────────┬─────────────┬────────────┘
                                │             │
              ┌─────────────────▼──┐    ┌─────▼──────────────────┐
              │  CYL_MEMORY         │    │  CYL_HIPPO              │
              │  долговременные     │◄───│  эпизоды, fast write    │
              │  решётки L0..L3     │    │  pattern separation     │
              │  F0 math/vis        │    │  consolidate → memory   │
              └─────────────────────┘    └─────────────────────────┘
                     ▲                              │
                     └──────── consolidate ─────────┘
                              (sleep / T_batch)
```

Ничто не мешает: это **не** три файла JSON на диске как «память», а **три field-буфера** (или три `subsystem` в agent store) с **мостами** между цилиндрами.

## Sleep = T_consolidate (это одно и то же)

В north star **sleep** — не метафора «агент отдыхает», а **отдельный режим макро-тика**:

| Режим | Что крутится | Цилиндры |
|-------|----------------|----------|
| **T_wake** | perceive → SN → CEN → babble/act | read **cyl_memory**, write **cyl_hippo** on correct |
| **T_sleep** | consolidate → NCA/repair → prune | **hippo → memory**, без внешнего I/O |

```text
  T_wake:  … → babble wrong → episode → cyl_hippo
  T_sleep: cyl_hippo ──merge──► cyl_memory ; hippo trim ; field_version++
  T_wake:  … babble лучше на том же cue (held-out)
```

**Import / finetune** из §5 north star — **соседние** каналы (KB с диска, opt-in train), но **не замена** sleep:  
git ingest = I/O; **sleep** = перенос **своего** episodic из гиппокампа в LTM.

Hook в lab (roadmap): `agent_autonomous_tick.py --mode sleep` или каждые N wake-тиков → один `T_sleep`.

## Цилиндры (v0 naming)

| id | Роль | Аналог | Содержимое |
|----|------|--------|------------|
| **`cyl_memory`** | Долговременная память | кора / DMN | SSS `L0..L3`, F0 stacks, медленно меняется |
| **`cyl_hippo`** | Быстрая эпизодическая | гиппокамп | стек **H0…H3** (специалисты), consolidate → memory — [`hippo-lattice-stack-v0.md`](hippo-lattice-stack-v0.md) |
| **`cyl_io`** (опц.) | Буфер ввода | сенсорный буfer | текущий utterance, не смешивать с LTM сразу |

**SN/CEN/FPN** — не отдельные цилиндры памяти, а **управление** поверх (как CU + шина между устройствами).

## Гиппокамп: что делает

| Функция | Lab / код |
|---------|-----------|
| **Быстрая запись** | babble attempt + teacher correction → `cyl_hippo` only |
| **Pattern separation** | похожие эпизоды не затирают друг друга (разные tiles / hash anchors) |
| **Pattern completion** | cue «ма» → partial replay эпизода на hippo |
| **Consolidate** | batch: hippo → **merge** в `cyl_memory` (NCA finetune, field_write, strengthen z_bridge) |
| **Forget / trim** | episodic TTL после успешной консолидации |

```text
  T (online):
    listen  → cyl_io или hippo
    babble  → read cyl_memory (+ hippo cue)
    wrong   → write cyl_hippo (episode)
    right   → optional direct tweak memory (rare)

  T_consolidate (sleep / каждые N тиков):
    hippo episodes → train windows on memory lattices
    prune hippo
    field_version++ on cyl_memory only
```

## Шина между цилиндрами

| Мост | Направление | Смысл |
|------|-------------|--------|
| **`hippo_to_memory`** | hippo → memory | консолидация: «было X, стало Y» |
| **`memory_to_hippo`** | memory → hippo | cue для completion (digest snapshot) |
| **`io_to_hippo`** | io → hippo | сырой listen без порчи LTM |
| **`z_bridge_*`** | внутри cyl_memory | compose L0→L1 (как сейчас SSS) |

Физически: отдельные `field_state.cylinders.{id}.lattices` или отдельные store-файлы; SN держит **`active_cylinder`**.

## field_state (целевая форма)

```json
{
  "schema_version": "multi_cylinder_v1",
  "cylinders": {
    "cyl_memory": {
      "subsystem": "sss",
      "lattices": { "L0_grapheme": {}, "L1_syllable": {}, "L2_word": {} }
    },
    "cyl_hippo": {
      "subsystem": "episodic",
      "lattices": { "H0_episode": { "width": 32, "height": 32, "cells": [] } },
      "episodes": [
        { "id": "ep-001", "cue": "м а", "babble": "ам", "correct": "ма", "tick": 42 }
      ]
    }
  },
  "sn": {
    "active_cylinder": "cyl_memory",
    "active_lattice": "L0_grapheme"
  },
  "consolidation": {
    "last_run_tick": 0,
    "episodes_merged": 0
  }
}
```

## Von Neumann перекладка

| vN | Несколько цилиндров |
|----|---------------------|
| RAM | `cyl_memory` |
| Cache / write buffer | `cyl_hippo` |
| Disk | git KB (I/O only) |
| «Flush cache» | **consolidate** hippo → memory |
| MMU | SN: какой цилиндр/lattice адресуется |

## Что уже есть vs что добавить

| Есть | Нужно |
|------|--------|
| `sss.lattices` ≈ cyl_memory (один цилиндр) | `cyl_hippo` + episode log |
| `field_version`, NCA repair | consolidate job (windowed train on episodes) |
| `import_knowledge_delta` (KB→field) | **не** путать с hippo: KB = I/O, hippo = **свой** опыт |
| FPN session | `T_consolidate` в autonomous loop |

## Non-goals

- Гиппокамп **не** хранит encyclopedia grammar KB.
- Consolidate **не** = git commit; git — аудит, memory — цилиндр.
- Три цилиндра **не** = три LLM.

## Roadmap

1. **v1** — `cyl_hippo` struct + append episode on correct API (без NCA).
2. **v2** — consolidate script: episodes → strengthen tokens on `cyl_memory` lattices.
3. **v3** — train `z_bridge` on consolidated pairs.
4. **v4** — `cyl_io` listen buffer + SN routing io→hippo→memory.

## Для Cursor

«Несколько цилиндров» = **несколько field-буферов** с ролями; **гиппокамп** = быстрый эпизод + **optimize/merge** в цилиндр памяти, не отдельный chat-RAG.
