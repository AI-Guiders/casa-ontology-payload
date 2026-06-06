# Block 4 — early whole words

Spec: [`../data/block-04-early-words-cyrl-v1.json`](../data/block-04-early-words-cyrl-v1.json)

**Train:** 8 CVC/CV words (мама…вода). **Held-out:** апельсин / Апельсин (register contrast).

```bash
python lab/visual-curriculum/micro-literacy/run_block_pedagogy.py --block block-04-early-words-cyrl --store von-neumann
python lab/visual-curriculum/probe_block_held_out.py --block block-04-early-words-cyrl --store von-neumann
```

Social «Привет» — `native_ru_bootstrap`, не этот block.
