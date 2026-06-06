# Block 5 — frequency corpus (Phase I exit)

Spec: [`../data/block-05-corpus-cyrl-v1.json`](../data/block-05-corpus-cyrl-v1.json)

**Train:** 265 words (`ru-wordlist-v1.txt` offsets 0–264) in 4 batches.  
**Held-out:** last 66 words (20%) — never ingested in block waves.

После green gate — **новая лексика через OOV (L2)**, не расширение corpus teacher'ом.

```bash
python lab/visual-curriculum/micro-literacy/run_block_pedagogy.py --block block-05-corpus-cyrl --store von-neumann
python lab/visual-curriculum/probe_block_held_out.py --block block-05-corpus-cyrl --store von-neumann
python lab/visual-curriculum/probe_lexical_read_fluent_ru.py --offset 265 --limit 66
```

Phase I exit также: `probe_lexical_read_fluent_ru`, «Привет» social (ADR-0049 #1).
