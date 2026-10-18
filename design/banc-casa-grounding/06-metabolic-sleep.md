# BANC grounding: Metabolic / Sleep
**Status:** draft (P2)  
**Date:** 2026-09-19  
**CASA:** ADR-0064 · ADR-0009 sleep · ADR-0010 P9 · ADR-0065 recovery  
**Data:** BANC v888 (proxy) · fly sleep literature (external)

---

## 1. CASA surface (what we built)

**Metabolic Zone** = tick ATP budget, fatigue, sleep pressure, hard sleep trigger (0064). Distinct from executive surprise counter (signal vs integrated cost).

| Mechanism | CASA |
|-----------|------|
| cognitive_overload | agency downshift |
| WM theta/prune | capacity limit |
| `/sleep` / hippo merge | consolidate pipeline |
| neuromod coupling | arousal → metabolic cost (0066) |

Sleep = **offline** consolidate + integrate (0088 quad-mode).

---

## 2. BANC slice (queries + numbers)

**Honest limit:** BANC tier-1 tables do **not** ship a dedicated «sleep circuit» annotation. Proxies only:

| Proxy | Count | Interpretation |
|-------|-------|----------------|
| `circadian_neuron` (cell_class) | 28 | clock / day-night gate |
| DA-predicted circadian | 28 | modulated arousal rhythm |
| `diuresis,stress_tolerance,pain_threshold` (cell_function) | 43 | homeostatic stress |
| neurosecretory VNC | 43 | peptidergic slow hormones |
| neuropeptide: Dh31, Dh44, Lk | 44–86 each | metabolic/arousal peptides (lit) |

**Network load proxy:** 11.7M edges · median count=1 — wake-state wiring is **sparse per synapse**; sleep plasticity (MB replay) is **dynamic**, not in static edgelist.

**Literature anchor (not in table):** fly sleep = increased arousal threshold, synaptic homeostasis in MB/CX, dopamine modulation of sleep need.

**Read:** metabolic/sleep in connectome = **scattered peptidergic + circadian nodes**, not a single «sleep zone». CASA metabolic zone is **legitimate abstraction** — fly solves it via distributed hormones + behavior state.

---

## 3. Motifs

```text
  tick load / surprise storm
        │
        ▼
  metabolic ATP drain ──► fatigue ↑
        │
        ▼
  sleep pressure threshold ──► run_sleep
        │
        ▼
  offline: consolidate (MB replay analog) + integrate
        │
  circadian gate (optional slow bias)
```

| Fly (lit) | CASA metabolic |
|-----------|----------------|
| sleep need accumulates | ATP/fatigue integral |
| MB replay offline | hippo consolidate |
| DA modulates sleep | value → sleep priority |
| circadian 28 neurons | slow day/night bias (optional genetic) |

---

## 4. Rhyme / Gap / Port

| | Rhyme | Gap | Port |
|---|-------|-----|------|
| **Integrated cost** | distributed peptidergic | surprise counted but not costed | **single** metabolic integral per tick |
| **Hard sleep trigger** | behavioral quiescence | sleep only manual `/sleep` | overload → **forced** `run_sleep` |
| **Offline plasticity** | MB replay | consolidate = batch copy | value-weighted replay (03, 04) |
| **Circadian** | 28 clock neurons | no diurnal rhythm | genetic optional `circadian_bias` |
| **No fly ATP** | — | metaphor only | do not claim homolog; **functional** budget |

---

## 5. Probes

| ID | Probe | Pass |
|----|-------|------|
| CZ-Me1 | Sustained overload → sleep triggered without operator | auto `run_sleep` |
| CZ-Me2 | Post-sleep: fatigue ↓, consolidate queue drained | state delta |
| CZ-Me3 | Arousal×metabolic coupling: panic extends wake | 0066+0064 chain |
| CZ-Me4 | Sleep does not erase episodic (hippo intact) | journal audit |

---

## 6. Follow-up

- Best-effort: extract circadian + neurosecretory subgraph for fixture.
- Do **not** over-fit BANC for sleep — cite literature + CASA ADR-0009 as primary.
- Cross-ref 03-memory (consolidate), 04-neuromodulator (arousal hold).
