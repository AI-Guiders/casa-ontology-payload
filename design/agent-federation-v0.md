# Agent federation v0 (card + knowledge delta)

**Date:** 2026-05-28  
**Status:** design + JSON schemas (no runtime yet)  
**DMN lab baseline:** tiered train G + dual-checkpoint infer **H** (`lab/exp_h_dual_bench_v1/`)

## Artifacts

| File | Role |
|------|------|
| `design/agent-card.v0.schema.json` | Agent passport: bundles, tier, checkpoints |
| `design/knowledge-delta.v0.schema.json` | Exchange packet between agents |
| `manifests/kb-bundle-tiers.v0.json` | easy / hard routing @ infer |

## Agent card (summary)

One card per **cluster agent** (goals / research / ops):

- **L0 hash** — immutable epistemics the agent must not violate on import.
- **bundles** — per-doc ontology the agent owns.
- **checkpoints** — `model_phase1.pt` (easy), `model_hard.pt` (hard); infer policy from H.
- **decode** — canonical threshold / min_votes.

## Knowledge delta (summary)

Agents exchange **deltas**, not full KB:

1. **bundle** add/replace/patch (graph + claims keep `doc_path`, `section`, edges).
2. **digest** — what changed (concepts, edges, active modules).
3. **requires** — graph closure (dst nodes the receiver must already have).
4. **epistemic** — confidence, conflicts (L0: do not merge unchecked claims).

Import pipeline (v1 `tools/import_knowledge_delta.py`):

```
receive delta → verify requires → merge bundle → encode DMN grid → field_state.json
                → optional copy checkpoint_hard → optional quick bench
```

See `design/import-knowledge-delta-v1.md`.

## Example card (research, from lab)

See `lab/agent-cards/research-agent.v0.json` (generated stub).

## Example delta

```json
{
  "schema_version": 1,
  "type": "knowledge_delta",
  "source_agent_id": "research-agent-01",
  "target_cluster": "research",
  "bundle": {
    "path": "lab/kb-perdoc/research-ml.bundle.v1.json",
    "action": "replace"
  },
  "digest": {
    "summary": "Updated ML hypotheses section",
    "added_concept_ids": [],
    "added_edges": ["E:...|references|..."],
    "modules_activated": ["research/research-ml/1-core-hypothesis"],
    "tier": "hard"
  },
  "requires": ["casa-goals.bundle.v1.json"],
  "provides": ["research-ml.bundle.v1.json"],
  "epistemic": {
    "confidence": 0.9,
    "source_doc_paths": ["work/projects/.../research-ml-....md"]
  }
}
```

## What zone next?

| Zone | Now? | Why |
|------|------|-----|
| **DMN lab** | **Freeze** at H | Best train/infer policy found; further = incremental G, ingest automation |
| **Federation schemas** | **Done (v0)** | Card + delta — contracts for exchange |
| **SN gate** | **Done (v1)** | `tools/sn_cen_runtime.py` |
| **CEN stub** | **Done (v1)** | rule planner + optional LLM later |
| **import_knowledge_delta** | **Done (v1)** | `tools/import_knowledge_delta.py` — online field write |
| **cascade-ide** | Parallel track | ADR 0156 correspondence / reverse anchors — UI L2, not field train |

Recommended sequence (unchanged from `cen-sn-runtime-v0.md`):

1. Freeze DMN (H policy in docs/KB).  
2. **SN** lab stub on digest.  
3. **CEN** read gated digest + emit `task_*`.  
4. Wire federation import when an agent receives `knowledge_delta`.

## Repo

https://github.com/AI-Guiders/casa-ontology-payload
