# Import knowledge delta v1 (online field write)

**Status:** lab tool `tools/import_knowledge_delta.py`  
**Related:** `design/knowledge-delta.schema.json`, `design/agent-federation.md`

## Idea

Agent learns by **writing KB into the field**, not by retraining Qwen:

```
receive delta → verify requires → merge bundle → encode DMN grid → field_state.json
                → optional copy checkpoint_hard → optional quick bench
```

No mandatory `train_*.py` on import. Hard-tier **finetune is opt-in** (`--finetune`) or auto when `--bench` concepts F1 below `--finetune-if-below` (default 0.35).

## Artifacts

| Path | Role |
|------|------|
| `tools/import_knowledge_delta.py` | CLI import pipeline |
| `tools/field_write.py` | merge bundle, encode grid, update field state |
| `lab/agent-stores/<agent>/` | per-agent local store |
| `lab/agent-stores/<agent>/field_state.json` | online field (grid + bundle digest) |
| `lab/agent-stores/<agent>/bundles/` | merged bundle copies |
| `lab/agent-stores/<agent>/import_log.ndjson` | append-only import audit |

## Run

```powershell
cd Financial\software\open\casa-ontology-payload

# Full bundle replace (sample delta)
python tools/import_knowledge_delta.py `
  --delta lab/agent-cards/sample-knowledge-delta.json `
  --copy-checkpoint --bench

# Patch delta (after first import populated store)
python tools/import_knowledge_delta.py `
  --delta lab/test-deltas/patch-import-concept.json `
  --bench
```

## Field state (v2)

Union of all bundles in store → one DMN grid + combined `claims_nav`:

- `field_version` — monotonic counter on each write
- `fingerprint.bundles.*.content_hash` — stale detection
- `grid.source_bundles[]` — union metadata
- `schema_version` 2 on new stores

See `design/substrate-v2-roadmap.md`.

## Next (v2+)

- ~~Multi-bundle field union on one grid~~ — v2 `rebuild_union_field`
- ~~`digest_only` delta type~~ — implemented
- KB watcher → auto `kb_sync --import-to`
- Wire cascade-ide: import delta → refresh correspondence anchors
