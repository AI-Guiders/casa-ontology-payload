# Block 7c — `lang.meta.register.*`

Spec: [`../data/block-07c-register-bind-cyrl-v1.json`](../data/block-07c-register-bind-cyrl-v1.json)

**Meta ids:** `lang.meta.register.sentenceInitial`, `lang.meta.register.allCaps`

**Pedagogy:** rule card → contrast surfaces in one moment → co-sleep `lang.word.*` ↔ `lang.meta.register.*`. Gate: `register_meta_bind_min: 2` (sentenceInitial + allCaps). Apelsin — один lemma.

```bash
python lessons/literacy-cards/tools/build_register_meta_cards.py
python lab/visual-curriculum/micro-literacy/run_block_pedagogy.py --block block-07c-register-bind-cyrl --store von-neumann
python lab/visual-curriculum/probe_block_held_out.py --block block-07c-register-bind-cyrl --store von-neumann
```

Prerequisite: block 4/5 lemma in LTM; block 6b meta-language (green).
