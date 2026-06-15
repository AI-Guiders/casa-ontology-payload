# Bilingual glossary curricula

Term-level RU↔EN translation memory taught into the field via `teach_glossary`
(one consolidation sleep mints every `concept|names|word` edge). Deterministic,
auditable, no hallucination — this is a glossary, not fluent sentence translation.

## Files
- `en-numbers-v1.json` — number words 11–20 (bilingual scenes).
- `en-vocab-v1.json` — 15 hand-authored common words.
- `en-glossary-v1.json` — 40-word demo list for the bulk path.
- `en-glossary-ru-open.json` — **sample** slice of a real open dictionary (see below).

## Open dictionary (large scale)
`en-glossary-ru-open.json` is built from **OpenRussian.org** data, redistributed by
[Badestrand/russian-dictionary](https://github.com/Badestrand/russian-dictionary)
(nouns + verbs + adjectives). The full extraction is **32,237 clean single-word
RU↔EN pairs**; the repo ships a small sample to keep it lean and CI fast.

OpenRussian data is licensed **CC BY-SA 4.0** — attribution required, derivatives
share-alike. Keep this notice if you redistribute the derived list.

Rebuild the full list (or any sample) offline:

```sh
python scripts/build_open_glossary.py --out lab/curriculum/en-glossary-ru-open.json
# or a capped sample:
python scripts/build_open_glossary.py --out lab/curriculum/en-glossary-ru-open.json --sample 3000
```

Then load and teach at scale:

```python
from casa.curriculum import load_pairs, teach_glossary
teach_glossary(state, load_pairs("lab/curriculum/en-glossary-ru-open.json"), bundle=bundle)
```

Note: the names mint is now batched (one grid copy per sleep instead of one per
edge), so the load is roughly linear — the full 32k loads in tens of seconds rather
than minutes. Very large vocabularies (100k+) still want a dedicated lexicon lattice
rather than `schema-math` for cell headroom.
```
