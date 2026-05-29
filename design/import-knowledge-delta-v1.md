# Import knowledge delta v1 (online field write)

**Status:** lab tool `tools/import_knowledge_delta.py`  
**Related:** `design/knowledge-delta.v0.schema.json`, `design/agent-federation-v0.md`

## Idea

Agent learns by **writing KB into the field**, not by retraining Qwen:

```
receive delta → verify requires → merge bundle → encode DMN grid → field_state.json
                → optional copy checkpoint_hard → optional quick bench
```

No mandatory `train_*.py` on import. Hard-tier **auto finetune** (default): short module train + vocab expand → `store/checkpoints/model_hard.pt`. Disable: `--no-finetune`.

## Artifacts

| Path | Role |
|------|------|
| `tools/import_knowledge_delta.py` | CLI import pipeline |
| `tools/field_write.py` | merge bundle, encode grid, update field state |
| `examples/agent-stores/<agent>/` | per-agent local store |
| `examples/agent-stores/<agent>/field_state.json` | online field (grid + bundle digest) |
| `examples/agent-stores/<agent>/bundles/` | merged bundle copies |
| `examples/agent-stores/<agent>/import_log.ndjson` | append-only import audit |

## Run

```powershell
cd Financial\software\open\casa-ontology-payload

# Full bundle replace (sample delta)
python tools/import_knowledge_delta.py `
  --delta examples/agent-cards/sample-knowledge-delta.v0.json `
  --copy-checkpoint --bench

# Patch delta (after first import populated store)
python tools/import_knowledge_delta.py `
  --delta examples/test-deltas/patch-import-concept.v0.json `
  --bench
```

## Field state (v1)

Single active bundle grid in DMN rect (multi-bundle union field = v2). Each import updates:

- `bundles[name].concept_count`, `digest` from delta
- `grid.cells` — encoded v3 section layout, masked to `dmn_ontology`

## L0 / epistemic

If `epistemic.conflicts_with` intersects merged claims → **fail** unless `--force`.

## Next (v2)

- Multi-bundle field union on one grid
- `digest_only` delta type → SN/CEN refresh without full re-encode
- Wire cascade-ide: import delta → refresh correspondence anchors
