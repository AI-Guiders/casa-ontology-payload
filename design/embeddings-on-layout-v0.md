# Embeddings on layout v0 (design stub)

**Status:** design only — not implemented in PoC lab  
**Prerequisite:** `codec_grid_v3` + `concept_mode=section` + v2 edge placement (locality contract)

## Principle

Embeddings are an **optional layer above** provenance hubs on the field, not a replacement for `S:doc|section` or `N:doc_path` anchors.

| Layer | Role |
|-------|------|
| **Layout (v3)** | Where atoms live — interpretable, damage/recovery tested |
| **Embedding channels** | Continuous similarity / soft attention between nearby hubs |
| **Digest (SN)** | Still reads discrete concept ids + confidence from DMN |

## v0 experiment sketch (future)

1. Reserve `emb_*` channels in DMN (see `layout.v0.json` channel plan).
2. Initialize embedding vector per `concept_id` from small encoder (hash or external model) **at hub cell only**.
3. NCA rule may diffuse embeddings locally; decode still uses token voting for concepts/edges.
4. A/B: v3 tokens only vs v3 + frozen embeddings vs v3 + trainable embedding channels.

## Non-goals (v0)

- Replacing Markdown provenance with opaque vectors only.
- End-to-end HCI-style layout without discrete tokens first.

## Repo

Lab implementation target: `casa-ontology-payload` (`tools/`, when scheduled).  
Public: https://github.com/AI-Guiders/casa-ontology-payload
