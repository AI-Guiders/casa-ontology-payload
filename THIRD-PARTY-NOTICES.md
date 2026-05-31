# Third-party notices

This repository's **code** is MIT-licensed (see `LICENSE`). **Datasets and derived
sidecars are not committed** — download on demand:

```bash
python scripts/download_corpora.py
```

Each dataset keeps its own license. You are responsible for complying when you
redistribute derived artifacts (headword lists, POS maps, trained stores).

| Dataset | Used for | Upstream | License |
|---------|----------|----------|---------|
| **DetCorpus 50k** | RU `headwords.v1.txt`, `frequency.ipm.v1.jsonl` | [Digital-Pushkin-Lab/Russian-Word-Frequency-Lists-for-Children](https://github.com/Digital-Pushkin-Lab/Russian-Word-Frequency-Lists-for-Children) | CC0-1.0 |
| **FrequencyWords `en_50k`** | EN `headwords.v1.txt`, `frequency.ipm.v1.jsonl` | [hermitdave/FrequencyWords](https://github.com/hermitdave/FrequencyWords) | MIT |
| **UD Russian-GSD** | RU `ud_lemma_pos.v1.json` (lemma → UPOS index) | [UniversalDependencies/UD_Russian-GSD](https://github.com/UniversalDependencies/UD_Russian-GSD) | CC BY-SA 4.0 |
| **UD English-EWT** | EN `ud_lemma_pos.v1.json` | [UniversalDependencies/UD_English-EWT](https://github.com/UniversalDependencies/UD_English-EWT) | CC BY-SA 4.0 |
| **Grimm's Fairy Tales** (PG #17038) | EN folk ingest source text | [Project Gutenberg 17038](https://www.gutenberg.org/ebooks/17038) | Public domain |
| **English Fairy Tales** — Jacobs (PG #2591) | EN folk ingest source text | [Project Gutenberg 2591](https://www.gutenberg.org/ebooks/2591) | Public domain |
| **Afanasyev 1855** (RU folk, archaic) | `sss-ru-lexicon-v0` lab store only | 19th-c. folk collection (PD in source jurisdiction) | Public domain — **not** shipped as raw text in this repo |
| **ru-archaic headwords** | archaic-only word list (Afan L2 minus modern DetCorpus) | derived locally in lab | lab artifact — rebuild from lexicon store, not redistributed here |
| **en-tech / ru-tech headwords** | repo-scan seed lists | this repository's tracked source code | MIT (same as code) |

License values follow upstream as of 2026-05; verify current `LICENSE`/`README` before redistribution.

## UD lemma→POS sidecar (CC BY-SA 4.0)

`fetch_ud_lemma_pos_v0.py` builds an **automated index** (lemma string → UPOS tag) from
UD CoNLL-U releases. We do **not** edit UD source treebanks in that pipeline.

Whether a lemma→tag map counts as a "derivative work" under CC BY-SA is jurisdiction-
specific. We keep the sidecar **download-only** so the MIT code repo stays separate
from data. If you redistribute `ud_lemma_pos.v1.json`, follow [Universal Dependencies](https://universaldependencies.org/) attribution and CC BY-SA 4.0 terms.

## EN folk texts

Gutenberg files land in `lab/corpus/en-folk-v0/source/` (gitignored). See
`lab/corpus/en-folk-v0/README.md` for extract → ingest steps.

## Afanasyev / archaic RU

Production RU lexicon uses **DetCorpus** (`sss-ru-general-v0`). The Afanasyev-based
**archaic** store (`sss-ru-lexicon-v0`) is lab-only; raw tale text and large
`field_state.json` are not public-ship targets (see ADR-0007 preview scope).
