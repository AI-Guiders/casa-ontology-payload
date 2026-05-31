# Memory map: `sss-ru-general-v0`

Generated: 2026-05-31T07:20:07.349132+00:00
field_version: **5**

## Disk

| Path | Size |
|------|------|
| `field_state.json` | 44.6 MiB |
| store total | 257.3 MiB |
| `nca/` | 157.7 MiB |
| `_parallel_shards/` | 0 B |

## Hierarchy (prism_memory)

```text
prism_memory
  alphabet-en  (tokens=52)
  alphabet-ru  (tokens=66)
      words-ru-00  (tokens=1560)
      words-ru-01  (tokens=1562)
      words-ru-02  (tokens=1562)
      words-ru-03  (tokens=1562)
      words-ru-04  (tokens=1562)
      words-ru-05  (tokens=1562) + NCA
      words-ru-06  (tokens=1562) + NCA
      words-ru-07  (tokens=1562) + NCA
      words-ru-08  (tokens=1562) + NCA
      words-ru-09  (tokens=1562) + NCA
      words-ru-10  (tokens=1562) + NCA
      words-ru-11  (tokens=1562) + NCA
      words-ru-12  (tokens=1562) + NCA
      words-ru-13  (tokens=1562) + NCA
      words-ru-14  (tokens=1562) + NCA
      words-ru-15  (tokens=1562) + NCA
      words-ru-16  (tokens=1562) + NCA
      words-ru-17  (tokens=1562) + NCA
      words-ru-18  (tokens=1562) + NCA
      words-ru-19  (tokens=1562) + NCA
      words-ru-20  (tokens=1562) + NCA
      words-ru-21  (tokens=1560) + NCA
      words-ru-22  (tokens=1562) + NCA
      words-ru-23  (tokens=1562) + NCA
      words-ru-24  (tokens=1562) + NCA
      words-ru-25  (tokens=1562) + NCA
      words-ru-26  (tokens=1562) + NCA
      words-ru-27  (tokens=1562) + NCA
      words-ru-28  (tokens=1562) + NCA
      words-ru-29  (tokens=1562) + NCA
      words-ru-30  (tokens=1562) + NCA
      words-ru-31  (tokens=1562) + NCA
      words-ru-32  (tokens=1562) + NCA
      words-ru-33  (tokens=1562) + NCA
      words-ru-34  (tokens=1562) + NCA
      words-ru-35  (tokens=1562) + NCA
      words-ru-36  (tokens=1562) + NCA
      words-ru-37  (tokens=1562) + NCA
      words-ru-38  (tokens=1562) + NCA
      words-ru-39  (tokens=1562) + NCA
      words-ru-40  (tokens=1562) + NCA
      words-ru-41  (tokens=1562) + NCA
      words-ru-42  (tokens=1560) + NCA
      words-ru-43  (tokens=1562) + NCA
      words-ru-44  (tokens=1562) + NCA
      words-ru-45  (tokens=1562) + NCA
      words-ru-46  (tokens=1562) + NCA
      words-ru-47  (tokens=1562) + NCA
      words-ru-48  (tokens=1562) + NCA
      words-ru-49  (tokens=1562) + NCA
      words-ru-50  (tokens=1562) + NCA
      words-ru-51  (tokens=1562) + NCA
      words-ru-52  (tokens=1562) + NCA
      words-ru-53  (tokens=1562) + NCA
      words-ru-54  (tokens=1562) + NCA
      words-ru-55  (tokens=1562) + NCA
      words-ru-56  (tokens=1562) + NCA
      words-ru-57  (tokens=1562) + NCA
      words-ru-58  (tokens=1562) + NCA
      words-ru-59  (tokens=1562) + NCA
      words-ru-60  (tokens=1562) + NCA
      words-ru-61  (tokens=1562) + NCA
      words-ru-62  (tokens=1562) + NCA
      words-ru-63  (tokens=1562) + NCA
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
