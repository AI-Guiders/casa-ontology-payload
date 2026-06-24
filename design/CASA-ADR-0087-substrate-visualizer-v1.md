# ADR-0087: Substrate visualizer — topology, activation, impulse replay

**Status:** proposed (draft)  
**Date:** 2026-06-22  
**Provenance:** оператор (Света) — impulse trace (0080) даёт observability, но сырой JSON; нужна карта зон / призм / решёток и replay активаций @ tick для Neumann pilot (Tier-1 без Cursor)  
**Related:** [CASA-ADR-0080-impulse-trace-v1.md](CASA-ADR-0080-impulse-trace-v1.md), [CASA-ADR-0012-cide-parity-fieldbus-and-migration.md](CASA-ADR-0012-cide-parity-fieldbus-and-migration.md), [CASA-ADR-0061-intelligence-zones.md](CASA-ADR-0061-intelligence-zones.md), [CASA-ADR-0068-memory-zone.md](CASA-ADR-0068-memory-zone.md), [CASA-ADR-0067-zone-prism-wire-migration.md](CASA-ADR-0067-zone-prism-wire-migration.md), [zone-prism-map.v1.json](zone-prism-map.v1.json), `tools/listen_beat_annotator.html`, `tools/listen_beat_annotator_serve.py`, `casa/nervous/impulse.py`, UX mockup: [assets/substrate-activation-heatmap-vs-list.png](assets/substrate-activation-heatmap-vs-list.png)

---

## Context

### Что болит

[CASA-ADR-0080](CASA-ADR-0080-impulse-trace-v1.md) закрыл **«почему efferent»** — append-only impulse (`casa.impulse.v1`, synaptic events, channels). Оператор и verify читают **JSON / JSONL**; для живой отладки listen / life tick / partner это:

- нет **топологии** субстрата (intelligence zones → prisms → lattices);
- нет **пространственной** картины активации (что горело на решётке, какие hub в bind);
- нет **единого scrubber** по `macro_tick` (impulse + field snapshot + honesty).

**Прецедент UI:** `tools/listen_beat_annotator.html` + `listen_beat_annotator_serve.py` — локальный HTTP, read-only, Tier-1 friendly.

### Что уже есть (фрагменты)

| Artifact | Даёт | Не даёт |
|----------|------|---------|
| `impulse_trace.jsonl` / ring | synaptic log @ channel | topology, lattice heatmap |
| `bind_trace()` / verify | dialogue bind | cross-modality map |
| `concept_honesty_report.json` | concept gate | runtime activation |
| `zone-prism-map.v1.json` | normative wiring | live store state |
| FieldBus (0012) | phase events | human panel (roadmap CIDE) |

**Gap:** **projection layer** — один JSON contract для human UI, не сырой store dump.

### Не дублировать

| Система | Роль |
|---------|------|
| **Impulse trace (0080)** | source of truth для «почему» — visualizer **читает**, не пишет |
| **FieldBus (0012)** | inter-module events; позже `ImpulseSummaryEvent` → watcher |
| **CIDE agent panel** | долгосрочный host; **тот же snapshot contract** |
| **Oracle / chat UI** | **не** показывать «правильный ответ» — только substrate state |

---

## Decision

### 1. Substrate visualizer — operator tool, не intelligence zone

**Не** новая zone и **не** hot-path модуль. **Read-only** projection + static HTML dashboard @ local serve (как beat annotator).

```text
agent store (field_state, impulse ring, manifest)
        │
        ▼
tools/substrate_snapshot.py  ──►  substrate_snapshot.v1.json  (@ tick | latest)
        │
        ▼
tools/substrate_dashboard_serve.py  ──►  substrate_dashboard.html
```

**Invariant:** UI **никогда** не пишет в store; не подменяет `ImpulseRecorder`.

### 2. Три панели + общий tick scrubber

| Panel | Вопрос | Data source |
|-------|--------|-------------|
| **Topology** | *где что смонтировано?* | `zone-prism-map.v1.json` + store manifest + actual `lattices` keys |
| **Activation** | *что горело @ tick?* | lattice digest (top-K tokens), bind hubs, limbic/character snapshot |
| **Impulse replay** | *почему efferent?* | impulse summary/full for `tick_id` (0080 schema) |

**Scrubber:** `macro_tick` / `field_version` — синхронизирует три панели. Default: **latest** impulse + matching tick.

**Layout (normative UX — parity с beat annotator):**

```text
┌ header: store path · field_version · tick scrubber ◀ 42 ▶ ─────────┐
├ topology tree (left, ~30%) │ activation (center) │ impulse (right) ┤
└ footer: decode_ms · truncated flag · CASA_IMPULSE_TRACE level ──────┘
```

**Visual tokens** (reuse `listen_beat_annotator.html` CSS variables):

| Token | Value | Use |
|-------|-------|-----|
| `--bg` | `#12141a` | page |
| `--panel` | `#1c2030` | cards |
| `--text` / `--muted` | `#e8ecf4` / `#9aa3b8` | body / hints |
| `--accent` | `#6ea8ff` | heatmap hot, scrubber, links |
| `--ok` / `--warn` | `#5fd38d` / `#ffcc66` | gate pass / orphan lattice |
| `--border` | `#2d3548` | grid lines |

**Reference mockup:** [assets/substrate-activation-heatmap-vs-list.png](assets/substrate-activation-heatmap-vs-list.png) — target look for Activation panel (operator-approved 2026-06-22).

### 3. Topology tree (normative shape)

```text
infrastructure
├── memory (0068)     → prism_memory, prism_hippo, domains.{lang,math,concept,…}
├── genetic (0062)    → genome.v1.json hash (read-only meta)
└── nervous (0080)    → impulse ring path, debug level

intelligence (0061 clients)
├── executive, emotional, social, linguistic, logical, spatial, …
│     └── owner_prisms / compose_bias → lattice_ids[]

agent blocks
├── wm_prism, agent lattices (agent-concept-core, agent-curriculum-net, …)
```

**UI:** collapsible tree; leaf = lattice id → click opens **Activation** panel for that lattice.

**Single source:** manifest + `zone-prism-map` merged with **observed** keys from loaded state (highlight «in map but missing in store» / «in store but orphan»).

### 4. Activation projection (bounded)

**Anti-pattern:** отдавать весь `field_state` или full NCA grid в браузер.

#### 4.1 View modes (`view_mode`)

| `view_mode` | When (auto) | UI |
|-------------|---------------|-----|
| **`heatmap`** | `width × height ≤ 4096` (max side ≤64) | 2D grid: cell color = token weight @ (x,y) |
| **`tokens`** | `width × height > 4096` **or** operator override | Ranked list: bar + monospace token + % weight |
| **`graph`** | lattice tagged `concept-graph` or id `agent-concept-graph` | Force-directed / layered nodes + isa/affords edges |

**Auto rule:**

```text
if lattice_id in CONCEPT_GRAPH_IDS or edge_sample dominates digest:
    view_mode = graph
elif width <= 64 and height <= 64:
    view_mode = heatmap
else:
    view_mode = tokens   # caption: «grid hidden — lattice WxH»
```

Operator may **force** `?view=tokens|heatmap|graph` in UI; default = auto.

#### 4.2 Heatmap UX (≤64×64)

- Canvas or CSS grid; **empty cells** `--border` / `#2d3548`; **active** lerp toward `--accent` by normalized weight.
- Sparse hubs (concept index): second accent `--warn` / orange for `C:concept.*` tokens.
- **Hover:** tooltip `token @ (x,y) · weight · decode_ms`.
- **Click:** pin selection → side strip: `edge_sample` for that token.
- **Zoom:** optional 2×2 binning when `width,height ≥ 32` so panel fits ~256px; label «each cell = 2×2».
- Subtitle under title: *«spatial prior — где на решётке сидит hub»* (RU) or English in `lang=en` toggle later.

#### 4.3 Token list UX (>64×64 or override)

- Virtual scroll list, **K≤64** rows from `top_tokens`.
- Each row: horizontal bar (width ∝ weight), `token` monospace, `NN%` right-aligned.
- Header: lattice id + `token_count` + `decode_ms`; badge **«grid hidden»** when auto-fallback from heatmap.
- Filter chips: `concept.*`, `lemma.*`, `lang.*` — client-side prefix on loaded digest only.
- Subtitle: *«слишком большая сетка — только top-K, без ложной геометрии»*.

#### 4.4 Graph UX (concept graph lattices)

- Nodes = active concepts + one-hop types from `edge_sample`; edge labels `isa` / `affords` / `names`.
- Highlight nodes present in `bind_blocks` @ tick.
- Not a heatmap substitute — **topology of meaning**, not NCA coordinates.

#### 4.5 Snapshot digest per lattice @ tick

```json
{
  "lattice_id": "agent-concept-core",
  "width": 32,
  "height": 32,
  "view_mode": "heatmap",
  "token_count": 128,
  "top_tokens": [{"token": "C:concept.orange", "weight": 0.82, "x": 12, "y": 7}],
  "cells": [{"x": 12, "y": 7, "token": "C:concept.orange", "weight": 0.82}],
  "edge_sample": ["concept.orange|E:lemma.ru.apelsin"],
  "decode_ms": 4,
  "truncated": false
}
```

| Field | Cap | Notes |
|-------|-----|-------|
| `view_mode` | enum | server hint; UI may override |
| `top_tokens` | K≤64 | always present (list + graph) |
| `cells` | ≤4096 | **heatmap only** — sparse (x,y,weight,token); omit if `tokens` mode |
| `edge_sample` | ≤32 | concept graph / bind context |
| `bind_blocks` | ≤16 | global in `activations.bind`, overlay on any view |

**Optional overlays:** `affect_axes`, `character_ema` slice, `active_concept_theory` (0085) — slim bar above activation panel.

### 5. Impulse replay panel

- Parse `casa.impulse.v1` records filtered by `tick_id`.
- Graph layout: nodes = `SynapticEvent.node`, edges = seq order; highlight `kind ∈ {select, threshold, budget, route}`.
- Channel tabs: `partner_dialogue`, `motor`, `listen_stream`, `control_routing`, …
- Link **impulse_id** → FieldBus `ActEvent` payload (0012) when wired.

**Default view:** `CASA_IMPULSE_TRACE=summary` events only; full synaptic list behind «expand» (lab).

### 6. Snapshot contract `substrate_snapshot.v1`

```json
{
  "schema": "casa.substrate_snapshot.v1",
  "generated_at": "2026-06-22T12:00:00Z",
  "store_dir": "agents/von-neumann",
  "tick_id": 42,
  "field_version": 6,
  "topology": { "zones": [], "orphan_lattices": [] },
  "activations": { "lattices": {}, "bind": [] },
  "impulses": [],
  "honesty": {
    "concept": "concept_honesty_report.json",
    "listen": null
  }
}
```

**CLI:**

```bash
python tools/substrate_snapshot.py --store agents/von-neumann [--tick 42] [--out /tmp/snap.json]
python tools/substrate_dashboard_serve.py --store agents/von-neumann [--port 8765] [--open]
```

**Serve API (v0):**

| Route | Method | Returns |
|-------|--------|---------|
| `/` | GET | `substrate_dashboard.html` |
| `/api/snapshot` | GET | latest or `?tick=` snapshot |
| `/api/ticks` | GET | available `tick_id` list from impulse ring |
| `/api/topology` | GET | static merge map + store keys |

### 7. CIDE / FieldBus alignment (later)

[CASA-ADR-0012](CASA-ADR-0012-cide-parity-fieldbus-and-migration.md): UI projections subscribe to bus; **snapshot schema stays stable**.

```text
macro_tick end
  → impulse.flush_summary()
  → field_bus.publish(ImpulseSummaryEvent)
  → optional: SubstrateDigestEvent (subset of snapshot.activations)
CascadeIDE panel / substrate_dashboard.html  ← same JSON shape
```

**Phase gate:** local HTML first (Neumann Tier-1); CIDE panel reuses contract, не форк UI logic.

---

## Rollout

| Phase | Deliverable | Gate |
|-------|-------------|------|
| **P0** | This ADR + `substrate_snapshot.py` (topology only) + static HTML tree | manifest keys match store |
| **P1** | Impulse replay panel + tick scrubber | `verify_dialogue_thread --impulse` tick aligns |
| **P2** | Activation digest + **heatmap / token list / graph** per §4.1 UX | matches [mockup](assets/substrate-activation-heatmap-vs-list.png); decode < budget |
| **P3** | Live poll @ `listen_womb_tick` / life tick | optional SSE `/api/stream` |
| **P4** | CIDE watcher + `ImpulseSummaryEvent` wire | 0012 roadmap |

**Не блокирует:** curriculum teach, listen cold ingest, concept ADR slice.

**Блокирует claim:** «оператор видит субстрат без JSON grep» — после P1.

---

## Honesty / anti-patterns

| Probe | Pass |
|-------|------|
| Read-only | dashboard never mutates store |
| Topology truth | orphan lattices reported, not hidden |
| Impulse parity | UI `select` node == summary in jsonl |
| No oracle | panel has no «expected reply» column |
| Size bound | snapshot < configurable MB; truncate with `truncated: true` |
| Heatmap honesty | >64×64 never renders fake grid; shows «grid hidden» badge |

| ❌ | ✅ |
|----|-----|
| Dump full field_state to browser | bounded projection |
| Second impulse writer | read 0080 ring only |
| Hand-drawn zone map in HTML | generate from `zone-prism-map` + manifest |
| Fake heatmap on wide lattice | auto `tokens` + caption |
| Replace verify scripts | complement `verify_*` / `impulse_replay` |

---

| Replace verify scripts | complement `verify_*` / `impulse_replay` |

---

## Open questions

1. **SSE vs poll** for P3 live mode on slow stores.
2. **Auth:** local bind `127.0.0.1` only v0; token if remote Tier-1 host.
3. **Nervous zone (0080 Phase E):** topology panel shows `casa/nervous/` as infrastructure row before/without formal zone id.

*(Heatmap vs list — **resolved** §4.1–4.3; mockup [assets/substrate-activation-heatmap-vs-list.png](assets/substrate-activation-heatmap-vs-list.png).)*

---

## Summary

Substrate visualizer = **read-only projection** для оператора: **topology** (zones → prisms → lattices) + **activation** (bounded digest @ tick) + **impulse replay** (0080). Локальный HTML + serve по образцу beat annotator; стабильный `substrate_snapshot.v1` для будущей CIDE panel. Сырой JSON остаётся для CI; UI отвечает на «где всё лежит» и «что горело / почему» без oracle.
