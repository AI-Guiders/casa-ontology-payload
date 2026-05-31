# CASA-ADR-0014: призма агента (`prism_agent`) — собственная память на поле

**Статус:** принято (design + lab v0 scaffold, 2026-05-31)  
**Область:** agent store / multi-prism / NCA  
**Связано:** [`multi-cylinder-memory.md`](multi-cylinder-memory.md), [`CASA-ADR-0013-agent-journal.md`](CASA-ADR-0013-agent-journal.md), [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md), [`prism-layout-and-naming-v1.md`](prism-layout-and-naming-v1.md)

---

## Контекст

У агента должна быть **целая своя призма памяти** — не блокнот JSONL и не эфемерный F1, а **полноценный субстрат**:

- создавать решётки когда хочет;
- класть **любые** токены куда хочет;
- читать / менять / удалять без gate от teacher или sleep;
- **обучать NCA** на своих полках, если захочет.

**`prism_memory` + `ltm/`** — curated «учебник профиля»: ingest, sleep, export tier A.  
**`prism_hippo`** — быстрые эпизоды **под consolidate** в memory, не личный архив.  
**`journal/`** (ADR-0013) — **prose-слой** (как agent-notes): текст, concepts списком; не заменяет решётку.

---

## Решение

### 1. Четвёртая призма: `prism_agent`

```text
                    ┌──────── SN / FPN ────────┐
                    └───────┬─────────┬────────┘
                            │         │
         prism_memory       │    prism_agent  ◄── агент владеет
         (ltm/ curated)     │    (agent/ disk)
              ▲             │         │
              └── sleep ────┘    optional promote
```

| id | Роль | Диск | В `ltm/` export? |
|----|------|------|------------------|
| `prism_memory` | LTM профиля | `ltm/` + `nca/memory/` | да |
| `prism_hippo` | episodic → sleep | field / optional hippo tier | частично |
| `prism_control` | SN/CEN/FPN | `ltm/control/` | да |
| **`prism_agent`** | **личная память агента** | **`{store}/agent/`** | **нет** |

### 2. Раскладка на диске (отдельно от картриджа)

```text
{store}/
├── ltm/                    # профиль (tier A)
├── nca/                    # repair профиля
├── field_state.json        # runtime всех prism_*
└── agent/                  # tier agent-owned (NEW)
    ├── manifest.json       # lattices registry, nca.models
    ├── lattices/
    │   └── agent-scratch-math.json
    └── nca/
        └── agent-scratch-math/model.pt
```

**`journal/`** остаётся рядом — текстовый adjunct; **`agent/`** — spatial + NCA.

### 3. Именование решёток

Canonical id: **`agent-{slug}`** (kebab), напр. `agent-scratch-math`, `agent-hypothesis-7`.  
Префикс `agent-` — не попадает в `export_ltm_pack` / profile manifest.

Агент **волен** задать `width`×`height`, `z_level`, `concept_prefix`, произвольные token strings (`M:…`, `T:…`, `E:…`, своё).

### 4. Операции (контракт v0)

| Операция | Смысл |
|----------|--------|
| `create_lattice` | новая решётка в `prism_agent` |
| `place` | токен в `(x,y)` или cluster-placement |
| `read` / `list` | decode / inventory |
| `delete_lattice` | убрать полку (и опц. nca) |
| `save` / `load` | persist `agent/` ↔ `field_state.prisms.prism_agent` |
| `train_nca` | тот же damage→regrow math, weights в `agent/nca/` |

**Без обязательного sleep/Critic.** Promote в `prism_memory` → `ltm/` — **явная** команда (roadmap: `agent_promote`).

### 5. NCA на agent-полках

- Тот же trainer (`run_nca_training`), другой **out-dir**: `agent/nca/{lattice_id}/model.pt`.
- Registry в `agent/manifest.json`, не смешивать с profile `nca/models` без merge.
- Агент может train когда угодно; profile NCA не перезаписывается.

### 6. Boot

```text
boot_store(ltm/)  →  prism_memory + control
load_agent_prism(agent/)  →  prism_agent  (если есть)
load journal/  →  prose (отдельно)
```

Profile boot **не затирает** `agent/`.

---

## Связь journal ↔ prism_agent

| Нужно | Куда |
|-------|------|
| «Я сформулировал закон словами» | `journal/` |
| «Я разложил палочки на сетке» | `prism_agent` lattice |
| «Хочу regrow после damage» | `agent/nca/` train |
| «В учебник профиля» | promote → ingest / sleep → `ltm/` |

---

## Инструменты v0

```bash
python -m casa.cli agent_prism create-lattice --store-dir … --id agent-scratch-math --width 32 --height 32
python -m casa.cli agent_prism place --store-dir … --lattice agent-scratch-math --token "M:qty:2×entity:stick" --x 3 --y 4 --write
python -m casa.cli agent_prism list --store-dir …
python -m casa.cli agent_prism train-nca --store-dir … --lattice agent-scratch-math --epochs 25 --write
python -m casa.cli agent_bridge add-bridge --store-dir … --from-lattice agent-control-routing --to-prism prism_control --to-lattice control-dmn --token "E:agent.control.routing|denotes|control.dmn" --write
python -m casa.cli agent_bridge list-bridges --store-dir …
```

Код: `casa/prisms/memory/agent_prism.py`, `casa/prisms/memory/agent_bridges.py`.

---

## Non-goals v0

- Авто-merge agent → memory на каждый place.
- SN routing «по умолчанию читай agent» — opt-in `active_prism`.
- Agent prism в CIDE parity pack export.

---

## Self-modification: control-решётки и мосты (не profile patch)

Агент **волен** менять своё «ядро на поле» — но **не** тем, что молча переписывает `prism_control` в `ltm/`. Три уровня:

| Уровень | Пример | Свобода |
|---------|--------|---------|
| **Runtime** | tick, infer, train loop в Python/C# | снаружи (deploy) |
| **Self-tier** | `prism_agent`, `agent/bridges/` | **полная**, без Critic |
| **Profile-tier** | `prism_control`, `prism_memory`, export | только **`agent_promote`** |

### Своя control-полка в `prism_agent`

ID по конвенции: `agent-control-*` (как `agent-scratch-math` для памяти). Роль — эксперимент CU: WM, routing hint, private SN scratch — **не** замена shipped `control-dmn` / `lattice_sn` до promote.

```text
  prism_control (profile)     prism_agent
  control-dmn, lattice_sn  ←── agent-control-my-routing
       ▲                              │
       └──── agent_bridge ────────────┘
              (явное ребро агента)
```

**Пустота** возникает, когда новая решётка **изолирована**. Агент устраняет это сам: кладёт **мост** к уже существующим полкам профиля — тогда cue/digest идёт по **ребру**, не в void.

### Мосты агента (self-tier)

Хранятся в `{store}/agent/bridges.json` (или секция `manifest.json`), **не** в `ltm/control/`:

```json
{
  "schema_version": 1,
  "bridges": [
    {
      "id": "ab-agent-control-to-dmn",
      "kind": "agent_bridge",
      "from": { "prism": "prism_agent", "lattice_id": "agent-control-routing" },
      "to": { "prism": "prism_control", "lattice_id": "control-dmn" },
      "relation": "routes_to",
      "tokens": ["E:agent.control.routing|denotes|control.dmn"]
    },
    {
      "id": "ab-agent-wm-to-lexicon",
      "from": { "prism": "prism_agent", "lattice_id": "agent-control-wm" },
      "to": { "prism": "prism_memory", "lattice_id": "words-ru-07" },
      "relation": "cue_from",
      "tokens": ["E:agent.wm.goal|activates|memory.lexicon.shard"]
    }
  ]
}
```

| `kind` | Смысл |
|--------|--------|
| `agent_bridge` | перенос сигнала agent lattice → profile lattice (аналог `control_bridge` / `x_bridge`, но **владелец — агент**) |
| `agent_edge` | ребро `E:*` на agent-решётке, указывающее на `concept_id` или token профиля |

Tick (roadmap): при `active_prism=prism_agent` или hybrid mode SN **объединяет** digest profile + **достижимые** через `agent/bridges` agent-решётки. Без моста — agent lattice только local decode; с мостом — **не указывает в пустоту**.

Promote моста в канон profile (`control_bridge` в `design/prisms/control/stack.json`) — отдельный **`agent_promote_bridge`**, не side-effect place.

### Операции (roadmap API)

| Операция | Self-tier |
|----------|-----------|
| `create_lattice` | `agent-control-*` |
| `place` / `train_nca` | как сейчас |
| **`add_bridge`** | from agent lattice → profile lattice или concept |
| **`remove_bridge`** | агент снимает связь |
| `agent_promote` | lattice и/или bridge → profile `ltm/` |

Код v0: lattice + bridges (`agent_prism.py`, `agent_bridges.py`). Tick merge digest — v1 в `agent_sn_cen_tick`.

---

## Roadmap v1+

- `agent_promote` lattice → F0 / L2 + optional `export_ltm_pack --include-agent` (opt-in backup).
- **`agent_add_bridge` / `agent_promote_bridge`** — связь agent control → profile (см. § Self-modification).
- MCP tools mirror CLI.
- Tick: merge digest по `agent/bridges.json` при hybrid routing.
