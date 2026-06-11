# ADR-0079: Runtime host (C# NativeAOT) vs train worker (Python)

**Status:** proposed  
**Date:** 2026-06-10  
**Provenance:** диалог — «пора ли переписать на C# + NativeAOT, Python только NCA train»; north star *autonomous persistence first*  
**Related:** [agent-existence-north-star.md](agent-existence-north-star.md), [CASA-scratch-emergence-conditions-dialogue-v1.md](CASA-scratch-emergence-conditions-dialogue-v1.md), [CASA-ADR-0078-partner-voice-invariants-v1.md](CASA-ADR-0078-partner-voice-invariants-v1.md), [CASA-design-partnership-stages-and-initiative-v1.md](CASA-design-partnership-stages-and-initiative-v1.md)

---

## Context

CASA hot path сегодня — **~650 Python-модулей** (`casa/`): FPN tick, prisms, bind, discourse, defense, zones, life reactor, store. Partner chat уже **thin client** (`chat.py` → pulse + `partner_outbox` / text tract); life — **отдельный процесс** (`unified_agent_reactor_loop`, `ensure_life_reactor`).

Боли, которые подталкивают к C#:

| Наблюдение | Слой |
|------------|------|
| Reactor «живёт / умирает», venv, второй console | **операционка существования (T)** |
| Нужен один deployable artifact на Windows | **NativeAOT host** |
| Roslyn / dotnet-debug уже в workflow оператора | **единый toolchain** |

Боли, которые **не** лечит смена языка:

| Наблюдение | Слой |
|------------|------|
| Popuga / hint→paste, situated turn | **semantics bind+compose** |
| Oracle vs field routing | **policy + curriculum** |

**North star:** *Autonomous persistence first* — агент крутится без человека в каждом шаге. Перепис всего `casa/` — **months of freeze** на emergence; перенос **тела** (life + store + IPC) — совместим с текущей работой над partner-voice.

---

## Decision

### 1. Два процесса, один store — не monolith rewrite

```text
┌─────────────────────────────────────────────────────────────┐
│  Casa.Runtime.Host  (C# NativeAOT)                          │
│  • unified life loop (T, idle quanta, persist cadence)    │
│  • store read/write (field_state, session, checkpoints)     │
│  • partner IPC (text tract, pulse, partner_outbox.jsonl)    │
│  • teacher inbox poll (filesystem)                          │
│  • optional: thin chat CLI or IPC to Forge                  │
└───────────────┬─────────────────────────────┬───────────────┘
                │ tick envelope (v1)          │ sleep queue job
                ▼                             ▼
┌───────────────────────────┐   ┌─────────────────────────────┐
│  Compose bridge (phase 1) │   │  Casa.Train.Worker (Python) │
│  Python subprocess OR     │   │  • NCA shard train / regrow │
│  later: in-process C#     │   │  • ingest lab, bundle exp   │
└───────────────────────────┘   │  • curriculum probes (lab)  │
                                └─────────────────────────────┘
                ▲
                │  canon agent store (versioned paths)
                └──────────────────────────────────────────
```

**Python остаётся:**

- **Offline train** — NCA queue, shard regrow @ sleep, store repair tools.
- **Lab / ingest** — bundle edits, situation packs, duck probes до стабилизации hot path.

**C# забирает первым:**

- Continuous **existence** — то, что должно работать как Windows service / один `.exe` без venv.
- **Store authority** — кто пишет checkpoint, кто держит file lock, кто эмитит pulse.

**Compose (bind + discourse)** — **последний** переносимый блок, не первый. До green duck test на situated dialogue — bridge вызывает существующий Python compose по контракту.

### 2. Граница = сообщения (Kay), не «если mirror → …»

| Порт | Направление | Содержимое |
|------|-------------|------------|
| **P-store** | host ↔ disk | `field_state.json`, `agent_session.json`, bundles/, journal/, NCA shards — **схема версионируется** |
| **P-pulse** | host → observers | `write_pulse` equivalent: macro_tick, sn_mode, phase |
| **P-partner-in** | chat → host | partner cue / text tract enqueue |
| **P-partner-out** | host → chat | `partner_outbox.jsonl` drain |
| **P-tick-compose** | host → compose | `TickComposeRequest` → `TickComposeResponse` (см. §3) |
| **P-sleep-train** | host → worker | job id, shard ids, store snapshot path — **async**, не в partner hot path |

Hot path **не** содержит substring-oracle в host: host только планирует tick и вызывает compose; policy остаётся в compose engine до порта C#.

### 3. Контракт `TickComposeRequest` / `TickComposeResponse` (v1 черновик)

Файл на границе (JSON lines или single JSON per call):

**Request**

```json
{
  "schema": "casa.tick_compose.v1",
  "store_dir": "<abs path>",
  "partner_text": "…",
  "field_version": 42,
  "wm_tick": 108,
  "compose_mode": null,
  "provenance": { "source": "partner_channel", "cue_id": "…" }
}
```

**Response**

```json
{
  "schema": "casa.tick_compose.v1",
  "reply_text": "…",
  "soft_miss": false,
  "query_intent": "social",
  "dialog_hubs": ["ru.dialog.affect"],
  "bind_top_score": 50,
  "disposition": { "action": "answer", "reason": "…" }
}
```

Host **не** интерпретирует `ru.dialog.*` — только логирует provenance и пишет dialogue ring + journal hooks.

**Versioning:** поле `schema` обязательно; host отказывает compose при major mismatch.

### 4. Canon store paths (не менять без migration ADR)

| Артеfact | Роль |
|----------|------|
| `field_state.json` | поле, FPN, zones, forgetting |
| `agent_session.json` | dialogue ring, macro_ticks, meta |
| `body/` pulse + text tract | reactor liveness |
| `partner_outbox.jsonl` | initiative outbound |
| `teacher_inbox/` | lessons (не partner) |
| `bundles/*.bundle.json` | KB claims (read mostly) |
| NCA shard paths | write **только** train worker @ sleep |

Host owns **exclusive write lock** на session + field durante tick; train worker — **lease** на shard dir @ sleep (уже близко к canon queue).

---

## Phases

| Phase | Deliverable | Compose | Risk cap |
|-------|-------------|---------|----------|
| **0** | ADR + JSON schema `tick_compose.v1` + store lock rules | Python in-proc (status quo) | doc only |
| **1** | `Casa.Runtime.Host` exe: life loop, pulse, partner tract, persist; **spawn** `python -m casa.cli compose_bridge` per partner turn | Python subprocess | low — ops win |
| **2** | Chat/Forge talks to host via named pipe / gRPC localhost; drop `ensure_life_reactor` spawn python | Python subprocess | medium |
| **3** | Port **bind gather + reweight** to C#; compose still Python | hybrid | medium — tests parity |
| **4** | Port discourse realizer + sketch; retire compose subprocess | C# NativeAOT | high — only after duck test stable |
| **∞** | NCA train, ingest lab | Python worker forever OK | — |

**Stop rule:** не начинать phase 3, пока `test_situated_turn` + partnership duck probes не green **на Python compose** две недели подряд.

---

## Non-goals

- Big-bang rewrite 650 modules «потому что пора».
- Перенос NCA train в C# (numpy/torch ecosystem в Python).
- LLM inference в host (если появится — отдельный ADR / sidecar).
- Подмена partner-voice policy при порте — **те же invariants** (0078), те же tests.

---

## Consequences

**+** Один `.exe` для T; предсказуемый daemon; проще agent-forge deploy.  
**+** Чёткая граница: existence vs learning vs lab.  
**−** Два runtime до phase 4; нужны contract tests на каждой фазе.  
**−** NativeAOT: no dynamic `import`, ограничения reflection — compose port требует явных типов / source generators.

---

## Open questions

- [ ] Host IPC: named pipe vs gRPC vs stdin JSONL (как сейчас life events)?
- [ ] Embed Python (`pythonnet`) vs subprocess для phase 1 — subprocess проще, embed меньше latency?
- [ ] Repo layout: `casa-runtime/` sibling to `casa-ontology-payload` или submodule в Financial/open?
- [ ] Forge ADR: OAuth sign-in host = same exe или отдельный service?

---

## Связь с north star

| North star | Как ADR помогает |
|------------|------------------|
| **Непрерывность T** | Host = процесс, который *обязан* жить |
| **Память / store** | Host = единственный writer hot path |
| **Инициатива** | `partner_outbox` в host, не в chat |
| **Duck test** | Compose semantics не форс-мигрируют; tests travel with port |

---

## Changelog

| Дата | Запись |
|------|--------|
| 2026-06-10 | Первая версия — proposed, phases 0–4 |
