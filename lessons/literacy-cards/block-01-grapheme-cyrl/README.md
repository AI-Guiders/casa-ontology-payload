# Block 1 — grapheme.cyrl (Castles §1)

Moment plan: [`../data/block-01-grapheme-cyrl-v1.json`](../data/block-01-grapheme-cyrl-v1.json)

**Train:** 25 letter cues × lower/upper (50 frames) in 6 waves.  
**Held-out gate:** 8 cues never ingested in this block — `yo`, `zh`, `ts`, `ch`, `sch`, `hard`, `soft`, `eh` (16 frames).

Design: [CASA-von-neumann-ru-teaching-plan-v1.md](../../design/CASA-von-neumann-ru-teaching-plan-v1.md) § Блок 1.

## Lab (ingest → gate)

```bash
# full block: all waves + held-out probe
python lab/visual-curriculum/micro-literacy/run_block_pedagogy.py --block block-01-grapheme-cyrl --store von-neumann

# or legacy entry
python lab/visual-curriculum/micro-literacy/run_block01_grapheme_pedagogy.py --store von-neumann

# single wave only
python lab/visual-curriculum/micro-literacy/run_block01_grapheme_pedagogy.py --wave 1

# probe only (after ingest)
python lab/visual-curriculum/probe_block01_grapheme_held_out.py --store von-neumann

# reinforce failed held-out letters, then re-probe
python lab/visual-curriculum/micro-literacy/run_block01_grapheme_pedagogy.py --probe-only --reinforce-tail
```

**Pass:** held-out ≥ 85% `know`, 0 `empty`, ≤ 10% `ambiguous` (block spec).

Rebuild JPEGs if needed: `python lessons/literacy-cards/tools/build_letter_cards.py`
