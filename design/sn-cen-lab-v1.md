# SN + CEN lab v1

Runtime after frozen DMN policy (G train / H infer).

## Pipeline

```
encode -> DMN repair (tier checkpoint) -> decode -> FieldDigest
  -> SN (gate ports) -> GatedDigest
  -> CEN (task JSON) -> TaskEmit
```

Optional `--layered`: digest/gate channel means from piston pipeline (Exp E digest/gate checkpoints).

## Tools

| Script | Role |
|--------|------|
| `tools/sn_cen_runtime.py` | SN route + CEN plan (pure Python) |
| `tools/sn_cen_infer.py` | End-to-end infer + JSON report |
| `tools/agent_card.py` | Resolve tier checkpoint from agent card |

## Run

```powershell
cd Financial\software\open\casa-ontology-payload
python tools/sn_cen_infer.py --bundle lab/kb-perdoc/research-ml.bundle.v1.json
python tools/sn_cen_infer.py --bundle lab/kb-perdoc/research-ml.bundle.v1.json --query "NCA training"
python tools/sn_cen_infer.py --bundle lab/kb-perdoc/research-tda-flow.bundle.v1.json --layered
```

Output: `lab/sn_cen_out/infer_v1.json`

## v1 limits

- CEN is rule-based (no LLM); `query_to_dmn` stub for low-confidence probe.
- Task band is JSON only; `task.*` field channels deferred.
- SN gate: deterministic from digest confidence or layered gate means.

## Hot path (--from-field)

After `import_knowledge_delta`, SN/CEN reads `field_state.json` directly — no NCA repair:

```powershell
python tools/sn_cen_infer.py --from-field --query "import knowledge delta"
python tools/sn_cen_infer.py --from-field --store-dir lab/agent-stores/research-agent-lab-v0
```

Typical `wall_ms` < 50 ms (decode + SN + CEN only).

See also: `design/cen-sn-runtime-v0.md`, `design/layout.v0.json` (regions + ports).
