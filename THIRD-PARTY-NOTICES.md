# Third-party notices

This repository's **code** is MIT-licensed (see `LICENSE`). It additionally uses
third-party **datasets** that are *not* committed to git — they are downloaded on
demand into `lab/corpus/**/source/` (gitignored) by:

```bash
python scripts/download_corpora.py
```

Each dataset keeps its own license. You are responsible for complying with those
licenses when you redistribute derived artifacts (headword lists, frequency
sidecars, POS maps, trained stores). Where a source is **CC BY-SA 4.0**, derived
data is share-alike: redistribute it under the same terms with attribution.

| Dataset | Used for | Upstream | License |
|---------|----------|----------|---------|
| **DetCorpus 50k** (Russian word frequency for children) | RU `headwords.v1.txt`, `frequency.ipm.v1.jsonl` | [Digital-Pushkin-Lab/Russian-Word-Frequency-Lists-for-Children](https://github.com/Digital-Pushkin-Lab/Russian-Word-Frequency-Lists-for-Children) | CC0-1.0 (public domain) |
| **FrequencyWords `en_50k`** (OpenSubtitles-derived) | EN `headwords.v1.txt`, `frequency.ipm.v1.jsonl` | [hermitdave/FrequencyWords](https://github.com/hermitdave/FrequencyWords) | MIT |
| **UD Russian-GSD** (CoNLL-U treebank) | RU `ud_lemma_pos.v1.json` (lemma → UPOS) | [UniversalDependencies/UD_Russian-GSD](https://github.com/UniversalDependencies/UD_Russian-GSD) | CC BY-SA 4.0 |
| **UD English-EWT** (CoNLL-U treebank) | EN `ud_lemma_pos.v1.json` (lemma → UPOS) | [UniversalDependencies/UD_English-EWT](https://github.com/UniversalDependencies/UD_English-EWT) | CC BY-SA 4.0 |

License values are recorded per the upstream repositories as of 2026-05; verify
the current `LICENSE`/`README` in each upstream repo before redistribution.

> **Share-alike note.** The UD treebanks are CC BY-SA 4.0. Any artifact derived
> from them (e.g. `ud_lemma_pos.v1.json` and POS bundles built from it) inherits
> share-alike obligations and must be redistributed under CC BY-SA 4.0 with
> attribution to Universal Dependencies. Keep this in mind when shipping stores
> that bake in UD-derived POS data.
