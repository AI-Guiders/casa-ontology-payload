# CEN / SN runtime contract v0

**Status:** SN/CEN **lab v1** implemented — see `design/sn-cen-lab-v1.md`, `tools/sn_cen_infer.py`  
**Layout:** `design/layout.v0.json` · overview `design/casa-layout-v0.md`

## DMN (done in PoC)

- **Role:** ontology / memory — bundle encoded as token field, patch damage, NCA recovery.
- **Output:** digest band (concept ids + confidence) at port **P1 → SN**.

## SN — Router / Salience

| Concern | v0 contract | v1 lab |
|---------|-------------|--------|
| **Reads** | P1 digest, optional salience input from CEN task band | decode → `FieldDigest`; optional layered gate means |
| **Writes** | `gate_*` channels — which DMN/CEN ports are open | `GateState.ports` + `gate_vector` in JSON report |
| **Damage tests** | Gate stuck open/closed; recovery = restore routing, not full ontology | deferred |
| **Lab** | `sn_router` region in layout | `tools/sn_cen_runtime.sn_route` |

## CEN — Planner / Executor

| Concern | v0 contract | v1 lab |
|---------|-------------|--------|
| **Reads** | Gated digest (via SN), `task_*` band (current goal / tool call) | `GatedDigest` + optional `--query` |
| **Writes** | `task_*`, optional **P3 → DMN** memory query (future) | `TaskEmit` JSON (`query_to_dmn` stub) |
| **Damage tests** | Task band corrupted; measure recovery of task state, not KB atoms | deferred |
| **Relation to IDE** | Cockpit PFD/MFD zones are **UI** analogs, not this field | LLM hook later |
| **Lab** | — | `tools/sn_cen_runtime.cen_plan` |

## Sequencing

1. ~~Freeze DMN defaults~~ — G train / H infer frozen.  
2. ~~SN gating on digest~~ — `sn_route` v1 (deterministic + optional layered gate).  
3. ~~CEN task band~~ — `cen_plan` v1 JSON; field `task.*` channels deferred.  
4. Optional: embeddings layer (`design/embeddings-on-layout-v0.md`), LLM in CEN, `import_knowledge_delta.py`.

## Repo

https://github.com/AI-Guiders/casa-ontology-payload · open pack: `Financial/software/open/casa-ontology-payload`
