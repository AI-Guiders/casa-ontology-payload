# KB field watcher v1

**Status:** `tools/kb_field_watcher.py`  
**Goal:** KB edit → bundle rebuild → `field_state.json` without manual import.

## Flow

```
mtime change (payload_docs md) → debounce → kb_sync.sync_and_import → union field
```

No PyTorch on watch path. Finetune off unless `--tier hard` + import flags.

## Run

```powershell
cd Financial\software\open\casa-ontology-payload

# One-shot refresh all manifest docs
python tools/kb_field_watcher.py --once --store-dir examples/agent-stores/research-agent-lab-v0

# Poll watch (foreground)
python tools/kb_field_watcher.py --store-dir examples/agent-stores/research-agent-lab-v0
```

Log: `examples/agent-stores/<agent>/watcher_log.ndjson`

## Requirements

- `AGENT_NOTES_KB` or `--kb-root` pointing at agent-notes `knowledge/`
- Manifest: `manifests/kb-bundles-ca-substrate-agent.json` (`payload_docs`)
