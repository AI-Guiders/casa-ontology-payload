# Block 2 — meta-phonology (vowel / consonant)

Spec: [`../data/block-02-meta-phonology-cyrl-v1.json`](../data/block-02-meta-phonology-cyrl-v1.json)

**Held-out (6 letter frames):** eh, ya, yo, yu, s, t — category cards always in train waves.

```bash
python lab/visual-curriculum/micro-literacy/run_block_pedagogy.py --block block-02-meta-phonology-cyrl --store von-neumann
python lab/visual-curriculum/probe_block_held_out.py --block block-02-meta-phonology-cyrl --store von-neumann
```

Gate: 100% know on held-out letter-class frames.
