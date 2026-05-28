# Layered CA pipeline v0 (cylinder / piston analogy)

**Status:** design + lab scaffold  
**Analogy (not implementation mandate):** one 2D lattice (x, y); **z** = which CA section the field passes through; **t** = micro-steps inside that section; **T** = absolute agent tick.

See also: `design/casa-layout-v0.md`, `design/layout.v0.json`, `design/layered-ca-phases.v0.json`.

## Axes

| Symbol | Meaning |
|--------|---------|
| x, y | Spatial cell on 64×64 |
| z | Phase index (encode → repair → digest → gate → …) |
| t | CA iterations within one z |
| T | Macro tick (outside this doc) |

**Regions** (DMN / SN / CEN) = *where* on (x,y). **Phases** (z) = *which rule* runs. Combined via masks.

## Phases v0 (lab)

| z | id | Rule | Writes |
|---|-----|------|--------|
| 0 | encode | deterministic codec | tok in DMN |
| 1 | dmn_repair | NCA (trained) | tok in DMN |
| 2 | digest | NCA (trainable) | digest on port P1 |
| 3 | gate | deterministic v0 | gate in SN |

## Code

- `tools/layered_nca_core.py` — masks, phased rollout
- `tools/train_layer_digest.py` — train z=digest with frozen DMN checkpoint
- `tools/layered_infer.py` — full piston pass + metrics
