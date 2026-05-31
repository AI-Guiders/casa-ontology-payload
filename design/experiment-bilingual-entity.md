# Experiment: bilingual entity hub (RU + EN surfaces)

**Status:** lab v0 (parallel with EN lexicon + EN L1)  
**Date:** 2026-05-30  
**Parent:** [`understanding-contract.md`](understanding-contract.md), [`predictor.md`](predictor.md)

---

## North star

**Корова ≠ cow как «перевод строк».** Одна **сущность** (`entity.cow`), несколько **поверхностей** на поле:

```text
  C:entity.cow  (hub / L3)
       ▲                    ▲
       │ E:denotes          │ E:denotes
  C:lang.word.корова    C:lang.word.cow
  W:корова (L2 RU)      W:cow (L2 EN)
```

T9 / predict зажигает **якоря слов** на своей полке. **Hub** связывает surface → entity → другие surfaces.

---

## Токены и рёбра

| Token / id | Роль |
|------------|------|
| `entity.cow` | сущность (не языковая строка) |
| `lang.word.cow` | EN surface concept |
| `lang.word.корова` | RU surface concept |
| `E:lang.word.cow\|denotes\|entity.cow` | surface → entity |
| `E:entity.cow\|surface.ru\|lang.word.корова` | optional inverse index |
| `M:unit:cow` | F0 unit (Exp L), `E:entity.cow\|M:maps\|M:unit:cow` roadmap |

**Не канон:** `E:lang.word.cow|align|lang.word.корова` — только lab shortcut; истина через **entity**.

---

## Три параллельные ветки (Multitask)

| # | Deliverable | Bench |
|---|-------------|-------|
| 1 | `en_dev_headwords` + ingest EN on L2 | `bench_en_t9_smoke` |
| 2 | `segment_en` + L1 heuristics | `bench_segment_en` |
| 3 | `entity_hub_ingest` + `hub_neighbors` | `bench_entity_hub` |

Merge: один store (`sss-ru-lexicon` + EN listen + hub on L3).

---

## Bench entity hub (pass criteria)

Given anchor `lang.word.cow` or cue T9 `cow`:

1. `hub_neighbors` → includes `entity.cow`
2. surfaces via entity → includes `lang.word.корова` (if RU word on field)

Not: T9 top-1 `cow` == `корова`.

---

## Paths

```text
lab/exp_bilingual/
  en_dev_headwords.v1.txt
  kb-entity-surfaces-dev.v1.json
  en_segment_cues.v1.json
  entity_hub_cues.v1.json

tools/
  ingest_en_lex_dev.py
  segment_en.py
  entity_hub_ingest.py
  hub_neighbors.py
  bench_*.py
```
