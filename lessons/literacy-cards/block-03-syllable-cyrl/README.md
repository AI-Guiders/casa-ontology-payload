# Block 3 — syllables (analytic bootstrap)

Spec: [`../data/block-03-syllable-cyrl-v1.json`](../data/block-03-syllable-cyrl-v1.json)

**Held-out (11):** bound/prefix syllables над, под, от, … -ость — not in train waves.

```bash
python lab/visual-curriculum/micro-literacy/run_block_pedagogy.py --block block-03-syllable-cyrl --store von-neumann
python lab/visual-curriculum/probe_block_held_out.py --block block-03-syllable-cyrl --store von-neumann
```

Gate: ≥85% know on held-out syllable frames.
