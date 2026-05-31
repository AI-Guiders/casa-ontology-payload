# Control lattice stack v0 (DMN / SN / FPN / CEN как память по z)

**Date:** 2026-05-30  
**Status:** lab implemented (`control_cylinders`, `migrate_control_stack`, `control-lab`)  
**Supersedes:** [`fpn-control-region.md`](fpn-control-region.md) (полосы на одном 64×64)  
**Parent:** [`sss-multi-lattice-z.md`](sss-multi-lattice-z.md), [`multi-cylinder-memory.md`](multi-cylinder-memory.md), [`layered-ca-pipeline.md`](layered-ca-pipeline.md)  
**Machine-readable (roadmap):** `design/control-lattice-stack.json`

---

## Решение

**Контур управления** (DMN, SN, FPN, CEN) описываем **так же**, как SSS-память:

- каждая функция = **отдельная решётка** `(x, y)` со своим `lattice_id`;
- связи = **`control_bridge`** (аналог `z_bridge`), не соседние полосы на y;
- нехватка ёмкости → **новая решётка**, не сжатие в угол одного grid;
- внутри решётки — те же **`z_phase`** (encode → repair → digest/gate) и **оконный NCA** по горизонтали.

**Термин:** в JSON — `prisms` / `prism_control` (и т.д.). Геометрия — **призма** (квадратное основание × стек уровней z), не цилиндр; см. [`multi-cylinder-memory.md`](multi-cylinder-memory.md) § геометрия.

```text
  prism_memory (lexicon)              prism_control (CU / WM)
  ────────────────────              ─────────────────────
  L0_grapheme                       lattice_dmn_digest
       │ z_bridge compose                │ P1 digest
  L1_syllable                       lattice_sn_gate
       │                                 │ P2a salience →
  L2_word_*                         lattice_fpn_wm
       │                                 │ P2b → lattice_cen_plan
  L3_phrase                         lattice_cen_act
                                        │ P3 task → DMN
                                        └ P4 outcome → FPN
```

**SN/CEN/FPN не «четвёртый язык»** — отдельный подсистемный стек **`prism_control`**, связанный **портами** с `prism_memory` (см. multi-cylinder: CU поверх призм).

---

## Почему уходим от полос

| Полосы на одном grid | Стек решёток |
|---------------------|--------------|
| DMN/SN/FPN/CEN делят xy с мусором | каждый домен — своя сетка |
| FPN «не влезает» без перекройки LTM | `lattice_fpn_wm` + мосты |
| один NCA damage на весь буфер | repair **per lattice** |
| `layout.v1` deprecated в SSS stack | единый паттерн с L2 shards |

Память **уже доказала** эффективность: 64× `L2_word_*`, отдельный `model.pt`, windowed CUDA train, boot из `ltm/`.

---

## Две оси (как в SSS)

| Ось | На решётке control |
|-----|---------------------|
| **`z_level` / lattice_id** | какая сетка: `lattice_dmn`, `lattice_sn`, … |
| **`z_phase`** | encode → repair → digest/gate на **этой** сетке |
| **`control_bridge`** | перенос сигнала между решётками (не фаза CA) |

Мосты из [`fpn-control-region.md`](fpn-control-region.md) сохраняем как **типизированные рёбра**:

| bridge | from → to | Несёт |
|--------|-----------|--------|
| P1 | DMN → SN | digest, concept_ids |
| P2a | SN → FPN | salience mask |
| P2b | FPN → CEN | goal + subgoal |
| P3 | CEN → DMN | task.query |
| P4 | CEN → FPN | outcome |
| P5 | FPN → SN | mode bias (opt) |

---

## Предлагаемые lattice_id (v0 → v1 ADR-0010)

| lattice_id | z_ctrl | Роль | z_phase tail | Статус |
|------------|--------|------|--------------|--------|
| `lattice_dmn` | 0 | ontology / claims digest | digest | ✅ lab |
| `lattice_sn` | 1 | salience gate (bottom-up) | gate | ✅ lab |
| `lattice_fpn_wm` | 2 | working memory goal/mode/stack | encode+repair | ✅ lab |
| `lattice_cen` | 3 | planner action | encode+repair | ✅ lab |
| **`lattice_predict`** | 4 | forward-model rollout + prediction error | encode→roll→digest | ✅ digest brick (R3) |
| **`lattice_dan`** | 5 | top-down attention spotlight | gate(mask) | ✅ digest brick (R4) |
| **`lattice_value`** | 6 | limbic priority / guardrail tag | digest(scalar) | ✅ digest brick (R5) |

Размер v0: **32×32** (как SSS), NCA profile `sss` из [`nca-train-defaults.json`](nca-train-defaults.json).

Cosmos-паритет: [`casa-cosmos-mapping.md`](casa-cosmos-mapping.md). ADR: [`CASA-ADR-0010-control-zone-predict-attention-value.md`](CASA-ADR-0010-control-zone-predict-attention-value.md).

### Мосты P1–P9

| bridge | from → to | Несёт | Статус |
|--------|-----------|--------|--------|
| P1 | DMN → SN | digest, concept_ids | ✅ |
| P2a | SN → FPN | salience mask | ✅ |
| P2b | FPN → CEN | goal + subgoal | ✅ |
| P3 | CEN → DMN | task.query | ✅ |
| P4 | CEN → FPN | outcome | ✅ |
| P5 | FPN → SN | mode bias (opt) | ✅ |
| **P6** | FPN → DAN | goal → spotlight | ✅ design + encode seed |
| **P7** | DAN → DMN | sparse activation mask | ✅ design + encode seed |
| **P8** | predict → SN | prediction error / surprise | ✅ digest brick |
| **P9** | value → SN / sleep / replay | priority bias | ✅ value brick + replay |

```text
  VALUE ──P9──► SN ◄──P8── PREDICT
                  │ P2a
                  ▼
                 FPN ──P6──► DAN ──P7──► DMN / L2 (sparse)
                  │ P2b
                  ▼
                 CEN ──P3──► DMN
```

**Session mirror:** `agent_session.json` ↔ tokens на `lattice_fpn_wm` (как в старом FPN design), не источник правды в prod.

---

## NCA train: окна + решётки

### Внутри одной решётки (уже есть)

Windowed train: tile 16×16, stride 8, ghost 2, `max_windows_per_batch` — **параллельные crop’ы на GPU** в одном `train_memory_nca` / shard subprocess.

### Между решётками (сейчас / цель)

| Режим | Сегодня | Цель |
|-------|---------|------|
| L2 shards | **последовательно** subprocess на lattice | опционально **очередь parallel** |
| control stack | не реализован | тот же train driver по списку `lattice_id` |

**Один GPU (8 GB):** несколько одновременных `train_sss_nca` на разных решётках обычно **конкурируют за VRAM** — не всегда быстрее. Выигрыш parallel lattice:

- **несколько GPU** — по решётке на device;
- **пока GPU учит lattice A** — CPU готовит crops для B;
- **batch scheduler** (roadmap) — один процесс, очередь окон с разных lattice без двух моделей в памяти.

**Несколько GPU:** `CUDA_VISIBLE_DEVICES=0 train … lattice_sn` ∥ `CUDA_VISIBLE_DEVICES=1 train … lattice_fpn` — линейное ускорение до N карт.

### Параллелизм «как белок»

```text
  Узел = lattice_id  →  train NCA (windowed, horizontal)
  Ребро = control_bridge  →  deterministic / trainable port (roadmap)
  Новый домен  →  +1 узел, не resize карты
```

---

## Runtime

| Шаг | Статус |
|-----|--------|
| `control-lattice-stack.json` | ✅ |
| `prism_control` в `field_state` + `ltm/ctrl/*.ltm` | ✅ `migrate_control_stack`, `init_control_lab` |
| `decode_field_grid` → `lattice_dmn` | ✅ |
| `sn_cen_infer --from-field` + `--session` | ✅ pipeline `sn_cen_control_stack` |
| Tick P1–P4 на поле (замена `layered_infer`) | roadmap |
| `train_control_nca_*` | roadmap (`train_memory_nca --lattice-id lattice_dmn`) |

```bash
python tools/init_control_lab.py
python tools/bench_control_stack.py --store-dir lab/agent-stores/control-lab
.\scripts\run_control_stack_migrate.ps1
```

---

## Store / profile

Control lattices ship в **agent store** рядом с lexicon:

```text
{store}/ltm/lattice_sn.ltm
{store}/nca/lattice_sn/model.pt
```

Profile **не** подключает отдельный store для FPN — boot поднимает `prism_memory` + **`prism_control`** из одного store pack (roadmap).

---

## Non-goals v0

- Не дублировать L2 lexicon в control lattices.
- Не требовать control NCA до green lexicon shards.
- Не возвращать y-bands в новых продуктах.

---

## Связанные файлы

- [`context-axis.md`](context-axis.md) — контекст на тике; FPN WM на `lattice_fpn_wm`
- [`agent-store-catalog.md`](agent-store-catalog.md) — картриджи памяти
- [`fpn-control-region.md`](fpn-control-region.md) — **historical** (полосы)
