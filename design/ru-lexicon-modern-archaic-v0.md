# RU lexicon: modern vs archaic (v0)

**Date:** 2026-05-30  
**Status:** accepted (design); **prod = modern only** — см. [`lexicon-usage-axes-v0.md`](lexicon-usage-axes-v0.md)  
**Parent:** [`agent-store-catalog-v0.md`](agent-store-catalog-v0.md)

---

## Зачем

Корпус Афанасьева (1855, диалектная запись) даёт формы вроде **абазва́вся**, **зрабив**, **пашов** — это **не мусор ingest**, но и **не modern RU** для T9/IDE.

Prod-слот `ru_lexicon` = **modern** (частотник DetCorpus и осознанный merge).  
**Archaic** = отдельный tier/store для lab, фольклора, сравнения с ФЭБ.

---

## Оси (дополнение к catalog)

| tier | Содержимое | Profile `ru_lexicon` |
|------|------------|----------------------|
| **general** | DetCorpus 50k, нормальная лемма | **да** (prod) |
| **archaic** | Афан, диалектные глаголы/орфография | **нет** |
| **literary** | (legacy alias) → переименовать в **archaic** в реестре | нет |

**Правило merge:** `merged:detcorpus+…` включает только **modern** headwords. Arhaic не подмешивать в union без явного `--include-archaic`.

---

## Классификация headword (v0)

Для каждой леммы из literary/Afan ingest:

1. **modern** — есть в `ru-general-v0/headwords.v1.txt` (DetCorpus) после `norm_word`.
2. **archaic** — есть в Afan/L2 literary store, **нет** в DetCorpus (напр. `абазвався`).
3. **overlap** — в обоих корпусах; в prod-merge остаётся **одна** лемма, votes усиливаются (см. catalog).

Инструмент: `tools/split_ru_headwords_modern_archaic_v0.py`.

Выход:

```text
lab/corpus/ru-general-v0/headwords.v1.txt      # modern (источник)
lab/corpus/ru-archaic-v0/headwords.v1.txt      # archaic-only
lab/corpus/ru-archaic-v0/split-report.v0.json  # счётчики + samples
```

---

## Stores (целевая матрица)

| store_id | tier | corpus_id | runtime |
|----------|------|-----------|---------|
| `sss-ru-general-v0` | general | `detcorpus-50k-cc0` | prod T9 |
| `sss-ru-lexicon-v0` | **archaic** | `afanasyev-sharded` | lab / ФЭБ parity |
| `sss-afan-v0` | ingest_ref | `afanasyev-monolith` | не boot |

Переименование папки `sss-ru-lexicon-v0` → `sss-ru-archaic-v0` — опционально v1; до v1 достаточно смены **tier** в `catalog.v0.json`.

---

## Ingest / rebuild

```bash
# 1) Modern список
python tools/fetch_ru_frequency_headwords_v0.py

# 2) Literary из store или корпуса
python tools/lexicon_headwords_v0.py  # export from store — см. split tool --literary-store

# 3) Split
python tools/split_ru_headwords_modern_archaic_v0.py \
  --literary-store lab/agent-stores/sss-ru-lexicon-v0 \
  --write-archaic

# 4) Prod store только modern
python tools/init_lexicon_store_v0.py --corpus-id ru-general
```

Archaic store пересобирать **только** из `ru-archaic-v0/headwords.v1.txt` (subset remigrate), не смешивать с general field_state.

---

## Примеры

| Форма | Класс | Комментарий |
|-------|-------|-------------|
| `абазвався` | archaic | диал. «взялся/обязался», ФЭБ №135 |
| `дом` | overlap | есть везде |
| `здравствуйте` | modern | DetCorpus, может не быть в Афане |

---

## Checklist

- [ ] `catalog.v0.json`: tier `archaic` у Afan sharded store
- [ ] Profile `ru_lexicon` → `sss-ru-general-v0` после сборки modern store
- [ ] T9 bench: отдельные отчёты `report_sweep_ru_general.json` vs `report_sweep_ru_archaic.json`
- [ ] Не union archaic в merged без ADR
