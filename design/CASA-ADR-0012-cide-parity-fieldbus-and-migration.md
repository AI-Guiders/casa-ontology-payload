# CASA-ADR-0012: parity с CIDE (FieldBus, слои, CU) + post-train migration

**Статус:** accepted (design); **migration — после** fv=6 train + post_train green  
**Дата:** 2026-05-31  
**Связано:** [`prism-layout-and-naming-v1.md`](prism-layout-and-naming-v1.md), [`CASA-ADR-0011-sensory-modalities-audio-video-v0.md`](CASA-ADR-0011-sensory-modalities-audio-video-v0.md), [`von-neumann-casa-mapping-v0.md`](von-neumann-casa-mapping-v0.md), CIDE [ADR 0099 DataBus](../../cascade-ide/docs/adr/0099-ide-databus-typed-events-and-projections.md), [ADR 0148 AEE](../../cascade-ide/docs/adr/0148-agent-execution-environment-verification-ladder-and-native-tooling.md), [naming-layers-v1](../../cascade-ide/docs/design/naming-layers-v1.md)

---

## Контекст

1. **Целевой стек призм** согласован (memory, control, sensory, hippo, spatial) — см. [`prism-layout-and-naming-v1.md`](prism-layout-and-naming-v1.md), [`design/prisms/`](prisms/).
2. **Legacy** (`tools/sss_*`, flat `nca/words-ru-*`, `ltm/l2/`, `cyl_*`) мешает масштабированию.
3. **CIDE** переходит на semantic naming и уже имеет: **DataBus**, **composition** (CDS/CCU), **Orchestrator**, **verification ladder**, **чёткие слои** (agent → AEE → substrate → bus).
4. **CASA** уже имеет von Neumann mapping ([`von-neumann-casa-mapping-v0.md`](von-neumann-casa-mapping-v0.md)); нужно **явно** переложить CIDE-паттерны, не копировать IDE-бинарник.

**Решение:** принять CIDE **архитектурные роли**, реализовать **FieldBus + prism composition + TickOrchestrator**; после post_train — **миграция paths + shims**, затем снятие legacy.

---

## 1. Как должен выглядеть стек (канон)

```text
                         ┌── prism_control (CU) ──────────────────┐
                         │  control.dmn … control.value (ADR-0010)  │
                         └───┬───┬───┬───┬──────────┬─────────────┘
                             │   │   │   │          │
  prism_sensor          prism_auditory  prism_visual  prism_spatial
  io.buffer             sensory.audio.* sensory.vis.* sensory.spatial.*
         │                     \         │           /
         └──────────────────────► prism_hippo (episodic.*)
                                    │ sleep
                                    ▼
                              prism_memory (memory.*)    prism_math (logic.*)
                                    │
                              concept hub (E: edges)
```

**Паттерн внутри каждой призмы:** `stack.v0.json` → lattices → NCA → LTM; `z_bridge` внутри; `x_bridge` между призмами.

**Два такта:** `T_wake` (perceive → control → act → hippo) / `T_sleep` (consolidate, replay, repair).

**2D grid ≠ flat world:** 3D в `prism_spatial`, не в z_level vis.

---

## 2. CIDE → CASA: перенос идей (не копипаста кода)

| CIDE | Роль | CASA (аналог) | Где в коде (целевое) |
|------|------|---------------|----------------------|
| **IDataBus** (0099) | typed domain events, pub/sub | **FieldBus** — события тика/поля | `casa/field_bus/` |
| **CCU / channel DTO** (0097) | свёртка в снимок канала | **Digest projection** per lattice | `lattice_*_v0.digest()` |
| **Composition / CDS** (0036) | intent → surface frame | **Store profile composition** — какие призмы смонтированы | `store_manifest.json`, `design/prisms/` |
| **Agent Orchestrator** (0148) | step: tools + verify policy | **TickOrchestrator** — wake/sleep step | `agent_autonomous_tick_v0.py` → `casa/tick/orchestrator.py` |
| **Verification Ladder** | diagnose → build → test | **Understanding ladder** (UC): extract → remember → use | [`understanding-contract-v0.md`](understanding-contract-v0.md) |
| **AEE / native tools** | Roslyn, MSBuild in-proc | **Codec adapters** (wav, frame, KB ingest) — **вне** NCA hot path | `casa/prisms/*/codec/` |
| **Substrate** (Roslyn, git) | источник истины среды | **field_state + LTM** — источник истины агента | `lab/agent-stores/` |
| **Semantic ids** (naming-layers) | `verify_rung.build.affected` | `memory.lexicon`, `control.predict`, `sensory.spatial.*` | manifest aliases |

### 2.1 FieldBus (CASA DataBus)

**Не** JSON stream наружу на каждый CA-step — **typed events** между подсистемами одного agent process:

```python
# casa/field_bus/events.py (sketch)
@dataclass(frozen=True)
class PerceiveEvent:      modality: str; lattice_ids: tuple[str, ...]; tick_id: int
class DigestReadyEvent:   prism_id: str; lattice_id: str; digest: dict
class SurpriseEvent:      source: str; prediction_error: float; tick_id: int
class ActEvent:           modality: str; surface: str; tick_id: int
class EpisodeWrittenEvent: hippo_lattice: str; episode_id: str
class ConsolidatePhaseEvent: field_version: int; shards_trained: int
class FieldVersionDriftEvent: old_fv: int; new_fv: int; stale_count: int
```

| CIDE DataBus | FieldBus |
|--------------|----------|
| `Publish<T>` / `Subscribe<T>` | same pattern; sync v1 (как 0099 in-memory) |
| UI projections | **watchers**: post_train, bench, CascadeIDE agent panel (roadmap) |
| Не заменяет transport 0094 | Не заменяет **codec I/O** (mic, git KB) — только **нормализованные события домена поля** |

**Правило:** hot path NCA **не** подписан на bus для каждой клетки; bus — **границы фаз** (perceive done, surprise, act emitted, sleep done).

### 2.2 Composition (какие «инструменты» смонтированы)

CIDE: `MainWindowHostSurfaceFrame` = intent + slot → instruments.

CASA: **store profile** = composition root:

```json
{
  "profile_id": "sss-ru-general-v0",
  "prism_composition": {
    "prism_control": { "stack": "design/prisms/control/stack.v0.json", "enabled": true },
    "prism_memory": { "stack": "design/prisms/memory/stack.v0.json", "enabled": true },
    "prism_auditory": { "enabled": false },
    "prism_visual": { "enabled": false },
    "prism_spatial": { "enabled": false },
    "prism_hippo": { "enabled": true }
  }
}
```

Включить auditory — не переписывать tick; **mount** новую призму + bridges в manifest.

### 2.3 CU и слои

```text
  CIDE                              CASA
  ────                              ────
  Agent layer (chat, orchestrator)    TickOrchestrator + teacher I/O
  AEE (verify, sandbox)             UC gates + Critic + integrity-core
  Substrate (Roslyn, files)         field_state, LTM, codecs
  DataBus                           FieldBus
```

**prism_control** = **CU** (fetch/branch via SN/DAN, execute via z_phase, PC = FPN + active_lattice).  
**NCA rollout** = **ALU** (spatial).  
**Bridges** = **bus**.  
**Codecs** = **device drivers** (не RAM).

### 2.4 Что не переносим буквально

| CIDE | Почему не 1:1 в CASA |
|------|----------------------|
| MSBuild / Roslyn ladder | другой substrate; свой **understanding ladder** |
| UI thread marshaling | agent process может быть headless |
| Skia compositor | нет UI; есть **digest projections** |
| External MCP default | CASA hot path — **on-field**; MCP = codec/actuator |

---

## 3. Post-train migration (legacy → prism layout)

**Gate:** `post_train_ru_general.status.json` → `phase: done`; fv=6 cartridge pushed; pytest + abs-path green.

### Phase M0 — design committed (можно до train end)

- [x] ADR-0011, ADR-0012, `prism-layout-and-naming-v1.md`
- [x] `design/prisms/{control,memory,auditory,visual,spatial}/stack.v0.json`
- [ ] Commit design-only (logical commit, no store break)

### Phase M1 — aliases, no break

- [ ] `memory_manifest.json`: block `prism_layout_version`, `path_aliases` (`ltm/l2` ↔ `ltm/memory/lexicon`, …)
- [ ] `store_layout_v0.py`: resolve **both** legacy and canonical nca/ltm paths
- [x] `tools/README.md` → map legacy → `casa/prisms/*`

### Phase M2 — package skeleton + shims

- [x] Create `casa/prisms/{control,memory,shared,hippo}/` (hippo/memory skeleton only)
- [x] Move **control stack + lattice_names** under `casa/`; `tools/*` → one-line shims
- [ ] Move memory (`sss_*`) and shared (`store_layout`, `prism_state`) modules
- [ ] FieldBus v0: publish `ConsolidatePhaseEvent`, `FieldVersionDriftEvent` from stale train + post_train

### Phase M3 — store paths (new writes canonical)

- [ ] `export_ltm_pack_v0` writes `ltm/memory/lexicon/` **and** symlink/copy alias `ltm/l2/` (transition)
- [ ] NCA export: `nca/memory/lexicon/words-ru-NN/` primary; keep legacy path readable
- [ ] One store migrated (`sss-ru-general-v0`); boot smoke + bench green

### Phase M4 — drop legacy

- [ ] Remove `sss_` prefix from **new** modules; delete shims when grep clean
- [ ] Stop writing `ltm/l2`, `ltm/ctrl`, flat `nca/words-ru-*`
- [ ] Update `.gitignore` / CI for canonical paths only
- [ ] Optional: filter-repo **paths only** if duplicate cartridges bloated history (not urgent)

**Не делать в M4:** delete legacy alias resolution until all stores migrated; **do** rename physical ids to v1 kebab via `migrate_lattice_ids_v1.py` (no NCA retrain).

---

## 4. Cross-repo alignment (CIDE ↔ CASA)

| Topic | CIDE | CASA | Sync |
|-------|------|------|------|
| Semantic layers | naming-layers-v1 §6 | naming-memory-layers-v0 + sensory.* | manual cross-ref |
| Events on bus | `AgentEnvironment*` | `FieldBus.*` | **разные** enum; optional bridge MCP for IDE panel |
| Store path | — | `lab/agent-stores/` | CIDE loads agent cartridge by profile id |
| Verify epoch | git snapshot stale | `field_version` drift / stale shards | **аналогичная идея**, разный механизм |

IDE может подписаться на FieldBus (future) для PFD: «stale=32», «phase=sleep», как Verify Epoch UI.

---

## 5. Моё мнение (кратко)

**Да, перенять стоит** — не UI и не MSBuild, а **дисциплину**:

1. **Typed bus** — иначе post_train, stale train, tick и bench склеены логами.
2. **Composition** — store profile явно говорит, какие призмы живые; не `#ifdef` в коде.
3. **Orchestrator** — один wake/sleep step model вместо 200 скриптов.
4. **Projections** — DMN digest, не raw grid; как IdeHealth snapshot, не raw Roslyn tree.
5. **Semantic ids** — уже синхрон с CIDE; physical id = alias.

**Опасность:** сделать FieldBus **слишком granular** (каждый CA cell) — убьёт perf. Bus только на **фазах тика**.

**Синергия:** один человек (ты) проектирует оба конца; CASA = **substrate agent**, CIDE = **host + verify + human lens**. FieldBus — будущий шов между ними.

---

## 6. Критерии готовности migration

- [ ] Boot smoke `sss-ru-general-v0` with **canonical paths only**
- [ ] Zero imports of `tools.sss_*` outside shims (grep gate)
- [ ] FieldBus events emitted on train complete + sleep complete
- [ ] `design/prisms/*` referenced from store manifest
- [ ] Docs: no «sss» as subsystem name in new prose

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-05-31 | v0: stack canon, CIDE parity table, FieldBus sketch, M0–M4 migration |
