# Block 6 (partial) — closed-class words

Spec: [`../data/block-06-closed-class-cyrl-v1.json`](../data/block-06-closed-class-cyrl-v1.json)

**Train:** 42 function words (`ru-closed-class-v1.txt`). **Held-out:** last 10 in wordlist order.

```bash
python lab/visual-curriculum/micro-literacy/run_block_pedagogy.py --block block-06-closed-class-cyrl --store von-neumann
python lab/visual-curriculum/probe_block_held_out.py --block block-06-closed-class-cyrl --store von-neumann
```

Meta-language (`lesson-07-meta-language`) — отдельный ingest, не этот spec.
