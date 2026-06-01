# CASA cross-prism transfer matrix v1

**Status:** canon (design)  
**Machine:** [`matrix-casa-cross-prism-transfer-v1.json`](matrix-casa-cross-prism-transfer-v1.json)  
**ADR:** [`CASA-ADR-0021-experience-agent-transfer.md`](../CASA-ADR-0021-experience-agent-transfer.md)

KB transfer matrices (agent-notes) define *principles*; this file is the **runtime projection** for `prism_router` bootstrap.

| Trigger | Route to | Lattice hint |
|---------|----------|----------------|
| `schema` | `prism_math` | `schema-math` |
| `vis` / `image` | `prism_visual` | `V1_object` |
| `t9` + locale | `prism_lang_ru` | `L2_word` |
| `segment` / `listen` + locale | `prism_lang_ru` | `L2_word` |
| locale only | `prism_memory` | (profile default) |

Empty domain prisms fall back to `profile.default_content_prism` or `prism_memory` for lattice bodies until split.
