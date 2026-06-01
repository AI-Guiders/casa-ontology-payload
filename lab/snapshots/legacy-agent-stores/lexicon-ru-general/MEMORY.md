# Memory map: `lexicon-ru-general`

Generated: 2026-06-01T01:37:50.674626+00:00
field_version: **8**

## Disk

| Path | Size |
|------|------|
| `field_state.json` | 2.3 MiB |
| store total | 214.7 MiB |
| `nca/` | 157.7 MiB |
| `_parallel_shards/` | 0 B |

## Hierarchy (prism_memory)

```text
prism_memory
  schema-math  (tokens=16)
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

Regenerate: `python tools/memory_manifest.py --store-dir ... --write`
