# CASA-ADR-0019: Control unit multi-prism + visual division (CU)

**Статус:** принято (design); код v0 = monolith `prism_control` + roadmap split  
**Дата:** 2026-06-01  
**Область:** `prism_control*`, control stack, tick, DAN/vis  
**Связано:** [`control-lattice-stack.md`](control-lattice-stack.md), [`CASA-ADR-0016-prism-domains-hot-router.md`](CASA-ADR-0016-prism-domains-hot-router.md), [`CASA-ADR-0018-vision-modality-v0.md`](CASA-ADR-0018-vision-modality-v0.md), [`CASA-ADR-0024-control-thalamus.md`](CASA-ADR-0024-control-thalamus.md), [`prism-layout-and-naming-v1.md`](prism-layout-and-naming-v1.md)

---

## Контекст

Сейчас **весь CU** — один `prism_control` с 7 решётками (DMN → … → DAN → Value) в [`control-lattice-stack.json`](control-lattice-stack.json).

Память уже по ADR-0016: **multi-prism** (`prism_memory`, `prism_lang_ru`, router, hot).  
Зрение ([ADR-0018](CASA-ADR-0018-vision-modality-v0.md)) требует:

1. **Content:** `prism_visual` — образы `vis.*` (перцепт → codec → поле).
2. **Control:** отдельный **отдел** — куда смотреть, salience по кадру, связь FPN goal ↔ spotlight ↔ `prism_visual`.

Один monolith CU без vis-отдела смешивает «планировать задачу» и «управлять взглядом».

---

## Решение

### 1. Control тоже multi-prism (на вырост)

Ввести **`kind: control`** (открытый словарь, как `content` / `router`):

| Prism id | Роль | Решётки (stack) |
|----------|------|-----------------|
| **`prism_control`** | bootstrap / legacy monolith v0 | полный stack (7 lattices) |
| **`prism_control_exec`** | DMN, SN, FPN, CEN, predict, value | `design/prisms/control/core-stack.json` |
| **`prism_control_thalamus`** | relay, arousal, bandwidth (wake/sleep gate) | `design/prisms/control/thalamus-stack.json` |
| **`prism_control_vis`** | зрительное внимание, frame gate | `design/prisms/control/vis-stack.json` |
| **`prism_control_motor`** | письмо / compose (roadmap) | ADR-0005 |

**v0 (не ломать lab):** один `prism_control` как сейчас; новые призмы — **spawn / migrate opt-in**.  
**v1:** `ensure_control` поднимает `prism_control_exec` + `prism_control_vis`; monolith — alias или coordinator без cells.

```text
field_state.prisms
├── prism_router              # modality → content (policy)
├── prism_control_thalamus    # relay + arousal + bandwidth  ← ADR-0024
├── prism_control_exec        # «мыслить / планировать»
├── prism_control_vis         # «куда смотреть»
├── prism_visual              # «что на поле vis.*»
└── prism_memory              # lang.*
```

**SN meta (roadmap):**

| Поле | Смысл |
|------|--------|
| `sn.active_prism` | content в фокусе (как ADR-0016) |
| `sn.active_control_prism` | какой CU-призм ведёт tick (default `prism_control` → exec) |
| `sn.vis_frame_id` | текущий кадр / ref (не файл, id перцепта) |

### 2. Отдел зрения в CU — не в SSS L2

**`prism_control_vis`** хранит **управление взглядом**, не картинку:

| lattice_id | z_ctrl | prefix | Роль |
|------------|--------|--------|------|
| `control-vis-salience` | 0 | `vis.attn.` | bottom-up: что выделяется в кадре |
| `control-vis-spotlight` | 1 | `vis.spot.` | top-down: FPN goal → область |
| `control-vis-gate` | 2 | `vis.gate.` | gate: пускать ли codec в `prism_visual` |

Токены (как в CU сегодня): `G:mode.scan`, `P:p10_fpn_to_vis_spot`, `vis.frame.<id>`, `port.vis_mask.forward`.

**Не путать:**

| Где | Что |
|-----|-----|
| `prism_visual` / `V1_object` | **память образа** (`C:vis.animal.cow`) |
| `prism_control_vis` | **куда направить внимание** на этой памяти |
| `control-attention` (DAN) | общий top-down attention (текст, задача) |
| `control-vis-spotlight` | **модальность vis**: маска на vis-решётку |

Мосты:

```text
control-working-memory ──P6──► control-attention (DAN, общий)
control-working-memory ──P10──► control-vis-spotlight
control-vis-spotlight ──P11──► prism_visual (sparse read mask)
control-vis-salience ◄──P12── prism_visual (surprise / novelty)
control-vis-gate ──P13──► control-salience (modality=vis bias)
```

### 2b. Паритет со стеком памяти (многоуровневая структура)

**Да — логично.** Паттерн один: **каждый уровень = своя решётка `(x,y)` + `z_bridge` вверх**, свой NCA repair на sleep, свой shard/compact в `ltm/`. Отличается только **семантика уровня** (знак vs управление vs образ).

| z | Память (2-я СС, `prism_memory`) | Память vis (`prism_visual`) | CU зрение (`prism_control_vis`) | CU exec (`prism_control_exec`) |
|---|----------------------------------|-----------------------------|--------------------------------|--------------------------------|
| **0** | `L0` grapheme | `V0` patch / gist (roadmap) | `control-vis-salience` — «что бросилось в глаза» | `control-dmn` — digest / ontology |
| **1** | `L1` syllable | `V1` object (`vis.*`) | `control-vis-spotlight` — «куда целимся» | `control-salience` — gate |
| **2** | `L2` word (shards) | `V2` scene (`vis.scene.*`) | `control-vis-gate` — «принять кадр / пустить в память» | `control-working-memory` — goal/mode |
| **3** | `L3` phrase | `V3` episode layout (roadmap) | *(опц.) scan path / sequence* | `control-executive` — plan/act |

**Симметрия мостов:**

```text
prism_visual:     V0 ──compose──► V1 ──bind──► V2
prism_control_vis: salience ──► spotlight ──► gate ──► (mask) prism_visual
prism_memory:     L0 ──compose──► L1 ──lift──► L2
prism_control_exec: DMN ──► SN ──► FPN ──► CEN ──► DMN
```

CU **не дублирует** контент нижнего уровня (как SN не хранит `lang.word.*`): управляет **потоком и фокусом** на каждом z, content-призма хранит **факты/образы**. Cross-prism мост P11 = аналог `z_bridge` между control z=1 и visual z=1.

Инвариант из [`sss-multi-lattice-z.md`](sss-multi-lattice-z.md): нехватка ёмкости → **новая решётка на том же z или новый z**, не один monolith grid.

### 3. Tick (дополнение к ADR-0016)

```text
INPUT (cue, modality, optional frame)
  → prism_control_thalamus: arousal (sn.mode) → relay ports  # ADR-0024
  → resolve_route → content (prism_visual | prism_memory | …)
  → active_control_prism:
       exec: SN → FPN → CEN (как сейчас)
       vis:  если modality ∈ {vis, image} или sn.vis_frame_id
             → control-vis-gate → spotlight → mask на prism_visual
  → predict на content с mask
  → surprise → hippo
```

**Инвариант:** перцепт (растр → codec) **вне** hot path; CU vis-отдел работает с **уже отпечатанным** кадром или **id кадра**, как exec работает с digest, не с сырым bundle JSON.

### 4. Может ли агент менять control?

**Сейчас (v0):** **нет прямого spawn/patch** `prism_control` — в коде это **system prism** (`_SYSTEM_PRISM_IDS` в `prism_spawn`; ADR-0016: только `ensure_*` / migrate). Агент **не** должен тихо переписывать DMN/SN/FPN tokens в shipped `ltm/ctrl/`.

**Что уже меняется без «ломания CU»:**

| Слой | Кто пишет | Persist в profile |
|------|-----------|-------------------|
| `WorkingMemory` (goal, mode) | tick / FPN | checkpoint meta, не lattice cells |
| `prism_hot_context` | tick, `agent_remember` | audit / promote gate |
| `prism_router` routes | bootstrap; v1+ emergent + **Critic** | `ltm/meta/router.json` |
| control lattice **cells** | migrate, sleep **NCA repair**, bench train | `ltm/ctrl/*.ltm` — ops / sleep, не ad-hoc agent |

**Будущее (аккуратно) — три уровня допуска:**

```text
L0 overlay   prism_agent / agent-control-*   ← агент учится здесь (как Self)
L1 spawn     prism_control_vis, kind=control ← новый отдел, не трогая exec core
L2 patch     prism_control_exec lattices     ← только Critic + budget + rollback
```

| Уровень | Разрешено | Запрещено / gate |
|---------|-----------|------------------|
| **L0 overlay** | новая решётка `agent-control-wm`, `agent_bridge` → P2a/P10 | прямой overwrite `lattice_dmn` |
| **L1 spawn control** | `spawn_prism(..., kind=control)` для **нового** `prism_control_*` | пересоздание monolith `prism_control` |
| **L2 patch exec** | strengthen token / port после **surprise + critic pass** | менять P1–P9 topology; менять shipped без `agent_promote` |
| **Promote** | overlay → profile через **`agent_promote`** + sleep | auto-promote каждого tick |

**Инварианты (как для памяти):**

- Shipped **control stack topology** (какие lattice_id, bridges) — **manifest / design**, не произвол агента.
- Агент меняет **содержимое** (tokens, salience, learned ports) на **своей** или **выделенной** control-призме — как `lang.word.*` на content.
- **Integrity / POST** — вне store; guardrails на `value.*` / task tokens остаются в host.
- Multi-prism CU упрощает осторожность: **`prism_control_exec`** frozen-by-policy, **`prism_control_vis`** agent-trainable раньше exec.

См. [`CASA-ADR-0015-agent-self-memory.md`](CASA-ADR-0015-agent-self-memory.md) § Self-modification (`agent-control-*`, `agent_bridge`); roadmap ADR-0014.

### 5. Compact persist / ltm

| Prism kind | `ltm/` |
|------------|--------|
| control (each) | `ltm/control/{lattice_id}.ltm` (legacy `ltm/ctrl/`) |
| content visual | `ltm/visual/` |

`export_pack` / `compact_persist`: перечислять **все** control-призмы (как content), `prism_id` в manifest.

---

## Миграция

| Шаг | Действие |
|-----|----------|
| M0 | Добавить `control-visual` в monolith stack (опц. lattice, `status: roadmap`) — см. JSON |
| M1 | `spawn_prism(..., kind=control, prism_control_vis)` + seed vis-stack |
| M2 | `sn.active_control_prism`; tick ветка vis |
| M3 | split exec из monolith; `prism_control` = thin registry |

Параллельно с L2 remigrate / ADR-0017 — **не блокирует**.

---

## Код (план)

| Модуль | Роль |
|--------|------|
| `prism_spawn` | `kind=control`, `PRISM_KIND_CONTROL` |
| `prism_state.py` | `prism_control_vis()`, `list_control_prism_ids()` |
| `export_ltm_pack` | export all control prisms |
| `orchestrator` / `tick_prepare` | vis gate когда modality=vis |
| `design/prisms/control/*.json` | stack SSOT по подпризмам |

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-01 | ADR-0019: CU multi-prism + visual division |
| 2026-06-01 | §2b паритет z-стека с памятью / prism_visual |
| 2026-06-01 | §4 agent modify control (L0/L1/L2 + gates) |
| 2026-06-01 | `prism_control_thalamus` — ADR-0024, tick_prepare hook |
