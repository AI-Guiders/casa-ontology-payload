# Lab reports

Reports here reference **role-based lab stores**, not prod lexicon.

## Demo / tick reports (root)

| Report | Store |
|--------|-------|
| `emergent-minus-math-l0-lab.json` | `math-l0-lab` |
| `stick-roman-lesson.json` | obsolete path (`lexicon-ru-general`) — re-run on `math-l0-lab` |
| `tick-demo-lexicon-ru-general.json` | move agent tick demos → `language-agent-lab` |

Re-init math lab: `python -m casa.cli init_math_l0_lab`

## `nca/`

JSON curves и smoke bench для union3 / codec / damage25 (`nca_union3_*`, `nca_bench_*`, `nca_ci_smoke_bench.json`). Bundles: [`../bundles/`](../bundles/).

## `benches/`

Прочие one-off bench dumps (`grid.damage25`, decode sweep, concept locality, …).
