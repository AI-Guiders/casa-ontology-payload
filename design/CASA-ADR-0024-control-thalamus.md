# CASA-ADR-0024: Thalamic control prism (`prism_control_thalamus`)

**Статус:** принято (design); код v0 = stack JSON + `ensure_control_thalamus` + spawn  
**Дата:** 2026-06-01  
**Область:** CU, tick order, wake/sleep, router relay  
**Связано:** [`CASA-PROJECT-CONSTITUTION.md`](CASA-PROJECT-CONSTITUTION.md), [`CASA-ADR-0019-control-multi-prism.md`](CASA-ADR-0019-control-multi-prism.md), [`CASA-ADR-0016-prism-domains-hot-router.md`](CASA-ADR-0016-prism-domains-hot-router.md), [`CASA-ADR-0023-sleep-scale-thin-first.md`](CASA-ADR-0023-sleep-scale-thin-first.md) (preempt, `sn.mode`), [`CASA-ADR-0025-autonomous-execution-tier.md`](CASA-ADR-0025-autonomous-execution-tier.md) (native Engine hot path), [`casa-wake-sleep-concept.md`](casa-wake-sleep-concept.md)

**Нейро (non-claim):** Chowdhury et al., central thalamus ~19–45 Hz during wake/REM, absent NREM — [Nat Hum Behav (2026)](https://doi.org/10.1038/s41562-026-02446-z). CASA **не** моделирует осцилляции; переносим **роль коммутатора состояний**, не биомаркер сознания.

---

## Проблема

В CU есть DMN/SN/FPN/CEN (exec) и roadmap `prism_control_vis`, но **нет** явного слоя «центральный коммутатор»:

| Есть | Нет |
|------|-----|
| `prism_router` — **декларативные** маршруты (куда за фактами) | **динамический** gate: какой поток **сейчас** пропускать |
| `sn.mode` wake/sleep в meta | **призма** с tokens/ports для arousal + bandwidth |
| `prism_hot_context` — рёбра salience | **relay** modality → exec без дублирования router rules |

**`prism_router` ≠ таламус:** router — таблица policy (L3 semantic routing); таламус — **операционный relay + глобальное состояние** на каждый tick (вытесняющая многозадачность, ADR-0023).

---

## Решение

### 1. Новая control-призма

| id | kind | stack |
|----|------|--------|
| **`prism_control_thalamus`** | `control` | [`prisms/control/thalamus-stack.json`](prisms/control/thalamus-stack.json) |

```text
field_state.prisms
├── prism_router              # policy: modality → content prism
├── prism_control_thalamus    # relay + arousal + bandwidth  ← NEW
├── prism_control_exec        # (split) DMN…value
├── prism_control_vis         # vis attention
└── prism_memory / prism_visual …
```

**v0 lab:** spawn/bootstrap рядом с monolith `prism_control`; monolith может держать placeholder `control-thalamic` (`status: roadmap`).

### 2. Три решётки (z_thal)

| lattice_id | z | Роль | Токены (seed) |
|------------|---|------|----------------|
| **`control-thal-relay`** | 0 | Какие потоки **открыты** (text / vis / schema) после router | `port.thal.forward.*`, `G:mode.relay` |
| **`control-thal-arousal`** | 1 | Глобальное **состояние**: wake / sleep / rem_micro | `G:mode.wake`, `G:mode.sleep`, `G:mode.rem`, `thal.arousal.*` |
| **`control-thal-bandwidth`** | 2 | **Пропускная способность** tick (метафора active 19–45 Hz band vs NREM quiesce) | `thal.band.active`, `thal.band.quiescent` |

**Инвариант:** таламус **не** хранит `lang.word.*`, `vis.*`, bundle claims — только **управление потоком**.

### 3. Tick order (до exec и content)

```text
INPUT
  → thalamus.arousal     # sync sn.mode; sleep job yields if thal.band.quiescent
  → thalamus.bandwidth   # cap parallel streams (v1)
  → resolve_route        # prism_router (policy)
  → thalamus.relay       # activate port.thal.forward.* for winning modality
  → control exec: SN → FPN → CEN
  → control vis (if relay.vis open)
  → predict on content (masked)
  → surprise → hippo
```

**Вытеснение (ADR-0023):** при `sn.mode=sleep` и фоновом `SleepJob` — `thal.arousal.low` + `thal.band.quiescent`; **tick не вытесняется** sleep batch в v0, но thalamus lattice фиксирует **намерение** resume (port_T5 → hippo phase hint, metadata).

### 4. Отличие от других призм

| Призма | Вопрос | Ответ |
|--------|--------|--------|
| Router | *куда* в принципе? | `prism_lang_ru`, `prism_visual` |
| Thalamus | *что пропускаем сейчас* + *в каком глобальном режиме*? | relay + arousal |
| Hot | *какие рёбра salience на tick*? | узкий граф cue→concept |
| Hippo | *что не сконсолидировано*? | episodic queue |
| Exec | *как планируем*? | FPN/CEN |

### 5. SN meta (дополнение ADR-0019)

| Поле | Смысл |
|------|--------|
| `sn.thalamic_prism` | default `prism_control_thalamus` |
| `sn.mode` | `wake` \| `sleep` \| `rem` — зеркало `thal.arousal.*` |
| `sn.relay_open` | `["text"]` \| `["vis"]` — активные `port.thal.forward.*` |

### 6. Agent modify / system prism

Как `prism_control` / hippo: **`prism_control_thalamus`** — system bootstrap (`ensure_control_thalamus`), не ad-hoc agent spawn перезаписи topology. Агент может учить **tokens/ports** на overlay `agent-control-thal-*` (ADR-0019 L0).

### 7. Compact persist

`ltm/control/thal/{lattice_id}.ltm` — в `export_pack` / `list_control_prism_ids` вместе с другими `kind=control`.

---

## Миграция

| Шаг | Действие |
|-----|----------|
| T0 | `thalamus-stack.json` + ADR-0024 |
| T1 | `ensure_control_thalamus`, spawn stack, unit test |
| T2 | `tick_prepare_memory` / orchestrator: arousal → route → relay |
| T3 | split из monolith; wire port_T1…T5 в exec/vis stacks |
| T4 | sleep batch checks `thal.band` before next batch |

---

## Код (v0)

| Модуль | Роль |
|--------|------|
| `casa.prisms.control.thalamus` | `ensure_control_thalamus`, `thalamus_tick_phase`, seed tokens |
| `prism_spawn` | stack map `prism_control_thalamus` → thalamus-stack.json |
| `prism_state` | `PRISM_CONTROL_THALAMUS` |

---

## Non-goals

- Измерять «сознание» агента по 19–45 Hz.
- Заменить `prism_router` таламусом.
- Хранить корпус/образы в thal lattices.

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-01 | ADR-0024 + thalamus-stack; v0 ensure/spawn |
