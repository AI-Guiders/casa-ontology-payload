# Memory map: `sss-ru-lexicon`

Generated: 2026-05-31T06:40:38.491473+00:00
field_version: **8**

## Disk

| Path | Size |
|------|------|
| `field_state.json` | 409.8 MiB |
| store total | 546.9 MiB |
| `nca/` | 131.9 MiB |
| `_parallel_shards/` | 0 B |

## Hierarchy (prism_memory)

```text
prism_memory
  L0_grapheme_cyrl  (tokens=66)
  L0_grapheme_latn  (tokens=52)
    L1_syllable  (tokens=924)
      L2_word  (tokens=0)
      L2_word_00  (tokens=1310)
      L2_word_01  (tokens=1312)
      L2_word_02  (tokens=1310)
      L2_word_03  (tokens=1312)
      L2_word_04  (tokens=1310)
      L2_word_05  (tokens=1312)
      L2_word_06  (tokens=1310)
      L2_word_07  (tokens=1312)
      L2_word_08  (tokens=1310)
      L2_word_09  (tokens=1312)
      L2_word_10  (tokens=1310)
      L2_word_11  (tokens=1312)
      L2_word_12  (tokens=1310)
      L2_word_13  (tokens=1312)
      L2_word_14  (tokens=1310)
      L2_word_15  (tokens=1312)
      L2_word_16  (tokens=1310)
      L2_word_17  (tokens=1312)
      L2_word_18  (tokens=1310)
      L2_word_19  (tokens=1312)
      L2_word_20  (tokens=1310)
      L2_word_21  (tokens=1312)
      L2_word_22  (tokens=1310)
      L2_word_23  (tokens=1312)
      L2_word_24  (tokens=1310)
      L2_word_25  (tokens=1312)
      L2_word_26  (tokens=1310)
      L2_word_27  (tokens=1312)
      L2_word_28  (tokens=1310)
      L2_word_29  (tokens=1312)
      L2_word_30  (tokens=1310)
      L2_word_31  (tokens=1312)
      L2_word_32  (tokens=1312)
      L2_word_33  (tokens=1310)
      L2_word_34  (tokens=1312)
      L2_word_35  (tokens=1310)
      L2_word_36  (tokens=1312)
      L2_word_37  (tokens=1310)
      L2_word_38  (tokens=1312)
      L2_word_39  (tokens=1310)
      L2_word_40  (tokens=1312)
      L2_word_41  (tokens=1310)
      L2_word_42  (tokens=1312)
      L2_word_43  (tokens=1310)
      L2_word_44  (tokens=1312)
      L2_word_45  (tokens=1310)
      L2_word_46  (tokens=1312)
      L2_word_47  (tokens=1310)
      L2_word_48  (tokens=1312)
      L2_word_49  (tokens=1310)
      L2_word_50  (tokens=1312)
      L2_word_51  (tokens=1310)
      L2_word_52  (tokens=1312)
      L2_word_53  (tokens=1310)
      L2_word_54  (tokens=1312)
      L2_word_55  (tokens=1310)
      L2_word_56  (tokens=1312)
      L2_word_57  (tokens=1310)
      L2_word_58  (tokens=1312)
      L2_word_59  (tokens=1310)
      L2_word_60  (tokens=1312)
      L2_word_61  (tokens=1310)
      L2_word_62  (tokens=1312)
      L2_word_63  (tokens=1312)
        L3_phrase  (tokens=263529)
```

## L2 sharding

- enabled: True
- mode: **lexicographic**
- lex_plan: **corpus_quantile**
- shards: 64
- indexed words: 41953
- attested word-initial letters (30): а, б, в, г, д, е, ё, ж, з, и, й, к, л, м, н, о, п, р, с, т, у, ф, х, ц…
- active shard lattices: 64

| Shard | Headword range (lex) | words in plan | tokens on grid |
|-------|----------------------|---------------|----------------|
| `L2_word_00` | а–батюшкину | 655 | 1310 |
| `L2_word_01` | батюшкины–богатырским | 656 | 1312 |
| `L2_word_02` | богатырскими–бухтаном | 655 | 1310 |
| `L2_word_03` | бухтану–весельчак | 656 | 1312 |
| `L2_word_04` | весельшая–водяного | 655 | 1310 |
| `L2_word_05` | водяной–вс | 656 | 1312 |
| `L2_word_06` | всадил–выкуп | 655 | 1310 |
| `L2_word_07` | выкупайся–вязались | 656 | 1312 |
| `L2_word_08` | вязался–горелка | 655 | 1310 |
| `L2_word_09` | горелки–давал | 656 | 1312 |
| `L2_word_10` | давала–дзень | 655 | 1310 |
| `L2_word_11` | дзеньте–досадой | 656 | 1312 |
| `L2_word_12` | досадою–едзиць | 655 | 1310 |
| `L2_word_13` | едзь–жуёць | 656 | 1312 |
| `L2_word_14` | жц–зайцы | 655 | 1310 |
| `L2_word_15` | зайчик–запустила | 656 | 1312 |
| `L2_word_16` | запустошила–звярнув | 655 | 1310 |
| `L2_word_17` | звярнуло–играли | 656 | 1312 |
| `L2_word_18` | игральный–йменню | 655 | 1310 |
| `L2_word_19` | ймеш–кишь | 656 | 1312 |
| `L2_word_20` | кл–кончилась | 655 | 1310 |
| `L2_word_21` | кончили–крестьянских | 656 | 1312 |
| `L2_word_22` | крестьянского–лад | 655 | 1310 |
| `L2_word_23` | ладан–лубочок | 656 | 1312 |
| `L2_word_24` | лубяная–махом | 655 | 1310 |
| `L2_word_25` | махоньких–молоком | 656 | 1312 |
| `L2_word_26` | молокососу–наготовил | 655 | 1310 |
| `L2_word_27` | наготовили–напоследок | 656 | 1312 |
| `L2_word_28` | напоследях–невестушку | 655 | 1310 |
| `L2_word_29` | невесты–нищую | 656 | 1312 |
| `L2_word_30` | нка–обошел | 655 | 1310 |
| `L2_word_31` | обошла–окуня | 656 | 1312 |
| `L2_word_32` | окуням–отгонять | 656 | 1312 |
| `L2_word_33` | отгрызают–ошпетило | 655 | 1310 |
| `L2_word_34` | ощенилась–пашою | 656 | 1312 |
| `L2_word_35` | пашпорта–пестрый | 655 | 1310 |
| `L2_word_36` | пестрыми–повадились | 656 | 1312 |
| `L2_word_37` | повадился–подкопался | 655 | 1310 |
| `L2_word_38` | подкопом–поймают | 656 | 1312 |
| `L2_word_39` | пойте–помачь | 655 | 1310 |
| `L2_word_40` | помаялся–посадили | 656 | 1312 |
| `L2_word_41` | посадились–поход | 655 | 1310 |
| `L2_word_42` | похода–приглядывался | 656 | 1312 |
| `L2_word_43` | приглядываться–присматриваться | 655 | 1310 |
| `L2_word_44` | присмирел–променяй | 656 | 1312 |
| `L2_word_45` | променял–пудава | 655 | 1310 |
| `L2_word_46` | пудаву–раздеть | 656 | 1312 |
| `L2_word_47` | раздеться–растворенное | 655 | 1310 |
| `L2_word_48` | растворены–рукавом | 656 | 1312 |
| `L2_word_49` | рукам–свету | 655 | 1310 |
| `L2_word_50` | светы–сибирских | 656 | 1312 |
| `L2_word_51` | сибирского–слизал | 655 | 1310 |
| `L2_word_52` | слизывает–согнулся | 656 | 1312 |
| `L2_word_53` | согреться–спрятан | 655 | 1310 |
| `L2_word_54` | спрятана–страшно | 656 | 1312 |
| `L2_word_55` | страшного–сыплются | 655 | 1310 |
| `L2_word_56` | сыпучий–толком | 656 | 1312 |
| `L2_word_57` | толку–тянумши | 655 | 1310 |
| `L2_word_58` | тянут–улеглися | 656 | 1312 |
| `L2_word_59` | улеглось–утренних | 655 | 1310 |
| `L2_word_60` | утрепали–хом | 656 | 1312 |
| `L2_word_61` | хома–червонцев | 655 | 1310 |
| `L2_word_62` | червонцы–шкапов | 656 | 1312 |
| `L2_word_63` | шкапу–яё | 656 | 1312 |

Regenerate: `python tools/memory_manifest.py --store-dir ... --write`
