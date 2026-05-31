# Memory map: `sss-ru-general-v0`

Generated: 2026-05-31T19:26:56.376362+00:00
field_version: **7**

## Disk

| Path | Size |
|------|------|
| `field_state.json` | 26.1 MiB |
| store total | 238.5 MiB |
| `nca/` | 157.7 MiB |
| `_parallel_shards/` | 0 B |

## Hierarchy (prism_memory)

```text
prism_memory
  alphabet-en  (tokens=52)
  alphabet-ru  (tokens=66)
      lexicon-ru-00  (tokens=1560)
      lexicon-ru-01  (tokens=1562)
      lexicon-ru-02  (tokens=1562)
      lexicon-ru-03  (tokens=1562)
      lexicon-ru-04  (tokens=1562)
      lexicon-ru-05  (tokens=1562)
      lexicon-ru-06  (tokens=1562)
      lexicon-ru-07  (tokens=1562)
      lexicon-ru-08  (tokens=1562)
      lexicon-ru-09  (tokens=1562)
      lexicon-ru-10  (tokens=1562)
      lexicon-ru-11  (tokens=1562)
      lexicon-ru-12  (tokens=1562)
      lexicon-ru-13  (tokens=1562)
      lexicon-ru-14  (tokens=1562)
      lexicon-ru-15  (tokens=1562)
      lexicon-ru-16  (tokens=1562)
      lexicon-ru-17  (tokens=1562)
      lexicon-ru-18  (tokens=1562)
      lexicon-ru-19  (tokens=1562)
      lexicon-ru-20  (tokens=1562)
      lexicon-ru-21  (tokens=1560)
      lexicon-ru-22  (tokens=1562)
      lexicon-ru-23  (tokens=1562)
      lexicon-ru-24  (tokens=1562)
      lexicon-ru-25  (tokens=1562)
      lexicon-ru-26  (tokens=1562)
      lexicon-ru-27  (tokens=1562)
      lexicon-ru-28  (tokens=1562)
      lexicon-ru-29  (tokens=1562)
      lexicon-ru-30  (tokens=1562)
      lexicon-ru-31  (tokens=1562)
      lexicon-ru-32  (tokens=1562)
      lexicon-ru-33  (tokens=1562)
      lexicon-ru-34  (tokens=1562)
      lexicon-ru-35  (tokens=1562)
      lexicon-ru-36  (tokens=1562)
      lexicon-ru-37  (tokens=1562)
      lexicon-ru-38  (tokens=1562)
      lexicon-ru-39  (tokens=1562)
      lexicon-ru-40  (tokens=1562)
      lexicon-ru-41  (tokens=1562)
      lexicon-ru-42  (tokens=1560)
      lexicon-ru-43  (tokens=1562)
      lexicon-ru-44  (tokens=1562)
      lexicon-ru-45  (tokens=1562)
      lexicon-ru-46  (tokens=1562)
      lexicon-ru-47  (tokens=1562)
      lexicon-ru-48  (tokens=1562)
      lexicon-ru-49  (tokens=1562)
      lexicon-ru-50  (tokens=1562)
      lexicon-ru-51  (tokens=1562)
      lexicon-ru-52  (tokens=1562)
      lexicon-ru-53  (tokens=1562)
      lexicon-ru-54  (tokens=1562)
      lexicon-ru-55  (tokens=1562)
      lexicon-ru-56  (tokens=1562)
      lexicon-ru-57  (tokens=1562)
      lexicon-ru-58  (tokens=1562)
      lexicon-ru-59  (tokens=1562)
      lexicon-ru-60  (tokens=1562)
      lexicon-ru-61  (tokens=1562)
      lexicon-ru-62  (tokens=1562)
      lexicon-ru-63  (tokens=1562)
```

## L2 sharding

- enabled: True
- mode: **lexicographic**
- lex_plan: **corpus_quantile**
- shards: 64
- indexed words: 49981
- attested word-initial letters (30): а, б, в, г, д, е, ж, з, и, й, к, л, м, н, о, п, р, с, т, у, ф, х, ц, ч…
- active shard lattices: 0

| Shard | Headword range (lex) | words in plan | tokens on grid |
|-------|----------------------|---------------|----------------|

Regenerate: `python tools/sss_memory_manifest_v0.py --store-dir ... --write`
