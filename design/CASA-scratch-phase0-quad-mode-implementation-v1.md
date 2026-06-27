# Scratch: Phase 0 — full ADR-0088 quad-mode (understanding mechanics)

**Status:** scratch — execution plan (operator: реализовать ADR **полностью**, не stub-only)  
**Date:** 2026-06-25  
**Branch:** `fix/neumann-free-speech-recovery`  
**Normative:** [CASA-ADR-0088-hippocampus-quad-mode-episodic-connectivity.md](CASA-ADR-0088-hippocampus-quad-mode-episodic-connectivity.md)  
**Related:** [CASA-scratch-listen-wire-gap-v1.md](CASA-scratch-listen-wire-gap-v1.md), [understanding-contract.md](understanding-contract.md), ADR-0047, ADR-0023, ADR-0009

---

## Зачем (оператор)

Mass listen без **механики понимания** = сенсорный hoarding. Цель — **ситуация + эпизод + связность во времени**, не только мелодика/пиксели.

**Phase 0** = весь контур ADR-0088 (wake → idle → consolidate → integrate), затем kolgotki/mass listen как **probe**, не как KPI «N секунд видео».

---

## Duck test (pilot corpus)

**Corpus:** lalabook emotions ch00 (колготки), beats из manifest (`profile=bind`, **без** `words[]` oracle).

| Beat | ~t | Смысл (held-out eval only — **не** ingest) |
|------|-----|---------------------------------------------|
| **b004** | 22–28 s | колготки боятся всего |
| **b029** | 124–132 s | «вокруг интересно и совсем не страшно» |

**«Понял» (claims_nav OFF):**

1. **Wake:** b004 и b029 — разные `moment_id`, один `episode_id` (глава 0); A+V coactive → один moment each.
2. **Consolidate:** `bridges_emergent > 0` in-batch на listen stream (A↔V per beat).
3. **Integrate:** полевая distant link между moment b004 ↔ b029 (provenance, не `beat.note`).
4. **Idle:** между beat-блоками — journal handoff / moment buffer priming без full merge.
5. **Use (later R6):** partner bind может сослаться на `moment_id` / `episode_id` — не в scope первого PR slice.

---

## Inventory: что уже есть

| Компонент | Файл / модуль | Quad-mode |
|-----------|---------------|-----------|
| A+V imprint | `listen_moment.py`, `listen_womb_tick.py` | raw sensory |
| Life tick | `agent_life.run_life_tick` | partial wake |
| Hippo queue | `append_episode`, `prism_hippo.episodes` | no `moment_id` |
| Sleep merge | `run_sleep` | **consolidate** (implicit) |
| Replay prep | `hippo/sleep_replay.prepare_sleep_replay` | consolidate adjunct |
| A↔V emergent | `auditory/bridge_vis.py` (sleep hook) | consolidate Lane B |
| Beat timeline | manifest `beats[]`, `listen_beat_model` | ingest granularity |
| Concept store | `concept_built_in`, 283 hubs | use layer (R6+) |

**Нет в коде:** `moment_id`, `close_episode_boundary`, `sn.hippo_mode`, `run_sleep(phase=integrate)`, `run_idle_micro`, `integration_report`, orchestrator idle hook.

---

## Target architecture (full ADR)

```text
hippo_wake     @ every life tick (+ beat step on listen replay)
idle_micro     @ activity gap / chapter boundary / orchestrator idle
sleep_consolidate  @ run_sleep(phase="consolidate")  [default, v0 compat]
sleep_integrate    @ run_sleep(phase="integrate") after consolidate drained
```

**Invariant:** consolidate **before** integrate on same store pass. Idle **не** replaces overload deep sleep (ADR-0047).

---

## Implementation slices (ordered PRs)

### Slice 0 — Schema + mode dispatch

| Task | Detail |
|------|--------|
| `sn.hippo_mode` | `wake` \| `consolidate` \| `integrate` \| `idle_micro` on `state["sn"]` |
| Hippo meta | `state["hippo_index"]`: `{active_episode_id, active_moment_id, moment_buffer[], journal[]}` |
| API | `close_episode_boundary(state, reason=...)`, mint `moment_id` / `episode_id` helpers |

**Files (new):** `casa/prisms/hippo/wake_index.py`, `casa/prisms/hippo/mode.py`  
**Tests:** unit mint + boundary rules (scene change, chapter change, silence gap)

---

### Slice 1 — `hippo_wake` on life loop

| Task | Detail |
|------|--------|
| Wire life tick | After percept merge: `hippo_wake_index_tick(state, percept_digest)` |
| Listen replay | One manifest **beat** = one `moment_id`; stream tick = sub-span inside moment |
| `append_episode` | Extend kwargs: `moment_id`, `episode_id`, `modality_tags`, `episode_source="wake"` |
| Cross-modal buffer | Hold A+V+limbic snapshot in `moment_buffer` until moment close or idle handoff |
| Boundaries | scene/chapter change, `visual_delta` threshold, beat `t1`, operator cue |

**Files:** `agent_life.py` (unified tick), `listen_womb_tick.py`, `listen_replay_scenes.py`, `memory_prisms.append_episode`  
**Tests:** `test_hippo_wake_index.py`; extend `test_listen_womb_tick.py`  
**Probe CLI:** `tools/hippo_journal_dump.py` — episodes/moments after replay

---

### Slice 2 — `sleep_consolidate` (explicit phase)

| Task | Detail |
|------|--------|
| `run_sleep(..., phase="consolidate")` | default; refactor body = current `run_sleep` |
| Report | `sleep_report.consolidate`: merged, bridges, replay_archive |
| Listen probe | R4: `bridges_emergent` count on life listen batch (not only vis↔math) |
| Scheduler | ADR-0023: `max_episodes`, batch drain unchanged |

**Files:** `memory_prisms.run_sleep`, `sss_sleep` CLI (if present under other name — extend)  
**Tests:** existing sleep tests + listen co-occurrence batch

---

### Slice 3 — `sleep_integrate` (full, not stub)

| Task | Detail |
|------|--------|
| `run_sleep(..., phase="integrate", max_links=K)` | separate code path after consolidate queue drained |
| Distant link pass | Deterministic: pair moments within same `episode_id` by temporal proximity + affect delta (e.g. fear cluster → relief cluster) — **no** manifest `note` read |
| Recombinative replay | Sample K from `replay_buffer` + hippo tail; route perturbation = deterministic shuffle (v1) |
| `integration_report` | `{links_created[], moments_linked[], replay_sampled[], claims_nav: "off"}` → journal + stderr |
| Field write | Edges with provenance `integrate:v1` + source moment ids |

**Files (new):** `casa/prisms/hippo/sleep_integrate.py`  
**Tests:** synthetic 2-moment same episode → ≥1 link; ablation integrate-only negative control (ADR)  
**Acceptance R3:** b004↔b029 link after full sleep job on ch00 pilot

---

### Slice 4 — `idle_micro` (full)

| Task | Detail |
|------|--------|
| `run_idle_micro(state, *, max_episodes=K)` | new entry; sets `sn.hippo_mode=idle_micro` |
| Micro replay burst | Replay 1–K from hippo tail / hot_digest — **no** full `_strengthen_concept` sweep |
| Incubation | Hook `prism_control` / thalamus: arousal ↓ (existing control zone if present) |
| Priming | Flush `moment_buffer` → journal handoff for next consolidate |
| Triggers | Chapter boundary, beat block gap, orchestrator idle between life blocks |
| Cap | ADR-0023 backpressure: idle must not grow `hippo_pending` unbounded |

**Files (new):** `casa/prisms/hippo/idle_micro.py`; wire `listen_replay_scenes` between beats  
**Tests:** idle between two beat segments → journal shows handoff; pending cap  
**Acceptance R7:** moment continuity or explicit handoff record

---

### Slice 5 — Sleep job CLI + operator runbook

```powershell
# Full quad job on store after ch00 beat pilot
python tools/sss_sleep.py --store agents/von-neumann --phase both --integrate-max-links 8

# Idle between beat blocks (replay tool flag)
python tools/listen_replay_scenes.py ... --idle-between-beats
```

Document in this scratch + one paragraph in listen-wire-gap when green.

---

## Test matrix

| Mode | Unit | Integration | Duck (kolgotki) |
|------|------|-------------|-----------------|
| wake | mint, boundary | replay b004 alone | moment ids stable |
| consolidate | sleep batch | A↔V emergent | bridges > 0 |
| integrate | 2-moment synthetic | ch00 b004+b029 sleep job | distant link |
| idle | handoff journal | 2-beat replay with gap | buffer primed |

---

## Non-goals (Phase 0)

- OCR/ASR/subs → `words[]` on bind corpus  
- Narrative QA «перескажи колготки»  
- LLM-in-sleep story inference  
- Full UC v1.4 / Critic (R5 bench — follow-on)  
- Partner provenance efferent (R6 — after integrate green)  
- Re-teach concept catalog  
- Mass listen 0–201 **until** duck test passes on b004+b029  

---

## KB / ADR hygiene

| Action | When |
|--------|------|
| ADR-0088 status → `accepted` | after Slice 0–1 merge + tests green |
| Navigator row | with acceptance |
| `scratch-neumann-tier1-roadmap` § Phase 0 | pointer to this file |
| Operator decision recorded | «full ADR, not stub» — this doc |

---

## Rough effort (agent estimate)

| Slice | Effort |
|-------|--------|
| 0 schema | 0.5–1 d |
| 1 wake | 1–2 d |
| 2 consolidate label | 0.5 d |
| 3 integrate | 1–2 d |
| 4 idle_micro | 1 d |
| 5 CLI + duck run | 0.5–1 d |

**Total Phase 0:** ~5–8 dev days; kolgotki full chapter after Slice 3 acceptance.

---

## History

| Date | Change |
|------|--------|
| 2026-06-25 | v1: full ADR-0088 phase 0 plan; duck test b004↔b029; operator intent full implementation |
