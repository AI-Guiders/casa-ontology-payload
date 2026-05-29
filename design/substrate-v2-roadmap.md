# Substrate v2 roadmap (implemented)

**Status:** lab + IDE bridge v2 (2026-05-28)  
**Repos:** `casa-ontology-payload`, `cascade-ide/CasaField.Core`

## 1 — Living ingest

| Item | Tool / artifact |
|------|-----------------|
| 1a kb→bundle | `tools/kb_sync.py` |
| 1b finetune policy | `import_knowledge_delta.py`: default no finetune; `--finetune` or `--bench` + `--finetune-if-below` |
| 1c version + hash | `field_state.field_version`, `fingerprint.bundles.*.content_hash`, `field_state_stale()` |
| 1d digest_only | `type: digest_only` in import pipeline |

## 2 — Multi-bundle union field

`field_write.rebuild_union_field()` merges all store bundles → one grid + combined `claims_nav`.

## 3 — CEN v2

`sn_cen_runtime.py`: scored claim match, `targets[]` (kb/code), `task_band`, `llm_hook` stub.

## 4 — SN + embeddings stub

`embeddings_layout.salience_from_layout()` — section hub boost on decode tokens.

## 5 — Native C# hot path

`cascade-ide/CasaField.Core`: `GridDecoder`, `FieldStateLoader`, `SnCenRuntime`, `CasaFieldHotPath`.  
MCP: `casa_field_infer`.

## 6 — Code correspondence

`semantic_payload`: `code_anchors` on claims; propagated to `claims_nav`; CEN/IDE `open_code`.

## KB watcher (v1)

`tools/kb_field_watcher.py` — poll + debounce → `kb_sync` → import. See `design/kb-field-watcher-v1.md`.

## Smoke

```powershell
cd Financial\software\open\casa-ontology-payload
.\scripts\run_substrate_v2_smoke.ps1
.\scripts\run_kb_watcher_v0.ps1 --once
```
