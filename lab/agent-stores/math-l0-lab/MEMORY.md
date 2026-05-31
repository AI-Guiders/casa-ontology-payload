# math-l0-lab

F0 math lab — `schema-math` only (sticks, emergent ops, Exp L). **No** DetCorpus lexicon.

Init:
```bash
python -m casa.cli init_math_l0_lab --bundle D:/Experiments/Personal Cursor Folder/Financial/software/open/casa-ontology-payload/lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json
python -m casa.cli bench_math_schema --store-dir lab/agent-stores/math-l0-lab
python -m casa.cli bench_schema_predict --store-dir lab/agent-stores/math-l0-lab --bundle D:/Experiments/Personal Cursor Folder/Financial/software/open/casa-ontology-payload/lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json
```

Do **not** run stick/emergent teacher loops on `sss-ru-general` (prod RU lexicon).
