# CEN / SN runtime contract v0

**Status:** regional contract only — DMN PoC is ahead; CEN/SN not trained in lab yet  
**Layout:** `design/layout.v0.json` · overview `design/casa-layout-v0.md`

## DMN (done in PoC)

- **Role:** ontology / memory — bundle encoded as token field, patch damage, NCA recovery.
- **Output:** digest band (concept ids + confidence) at port **P1 → SN**.

## SN — Router / Salience (next)

| Concern | v0 contract |
|---------|-------------|
| **Reads** | P1 digest, optional salience input from CEN task band |
| **Writes** | `gate_*` channels — which DMN/CEN ports are open |
| **Damage tests** | Gate stuck open/closed; recovery = restore routing, not full ontology |
| **Lab stub** | `layout_apply.mask_outside_region` already isolates DMN; SN rectangle `sn_router` reserved |

## CEN — Planner / Executor (next)

| Concern | v0 contract |
|---------|-------------|
| **Reads** | Gated digest (via SN), `task_*` band (current goal / tool call) |
| **Writes** | `task_*`, optional **P3 → DMN** memory query (future) |
| **Damage tests** | Task band corrupted; measure recovery of task state, not KB atoms |
| **Relation to IDE** | Cockpit PFD/MFD zones are **UI** analogs, not this field — see KB findings (IDE deferred) |

## Sequencing

1. Freeze DMN defaults: v3 / section / v2 edges / patch damage eval.  
2. Implement SN gating on digest **without** changing DMN codec.  
3. Add CEN task band + read path from gated digest.  
4. Optional: embeddings layer (`design/embeddings-on-layout-v0.md`) after SN read path exists.

## Repo

https://github.com/AI-Guiders/casa-ontology-payload · open pack: `Financial/software/open/casa-ontology-payload`
