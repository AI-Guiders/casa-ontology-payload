# RU lexicon: modern vs archaic (v0)

**Date:** 2026-05-30  
**Status:** accepted (design); **prod = modern only** — см. [`lexicon-usage-axes.md`](lexicon-usage-axes.md)  
**Parent:** [`agent-store-catalog.md`](agent-store-catalog.md)

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

1. **modern** — есть в `ru-general/headwords.v1.txt` (DetCorpus) после `norm_word`.
2. **archaic** — есть в Afan/L2 literary store, **нет** в DetCorpus (напр. `абазвався`).
3. **overlap** — в обоих корпусах; в prod-merge остаётся **одна** лемма, votes усиливаются (см. catalog).

Инструмент: `tools/split_ru_headwords_modern_archaic.py`.

Выход:

```text
lab/corpus/ru-general/headwords.v1.txt      # modern (источник)
lab/corpus/ru-archaic/headwords.v1.txt      # archaic-only
lab/corpus/ru-archaic/split-report.json  # счётчики + samples
```

---

## Stores (целевая матрица)

| store_id | tier | corpus_id | runtime |
|----------|------|-----------|---------|
| `lexicon-ru-general` | general | `detcorpus-50k-cc0` | prod T9 |
| `lexicon-ru-archaic` | **archaic** | `afanasyev-sharded` | lab / ФЭБ parity |
| `ingest-ref-afan` | ingest_ref | `afanasyev-monolith` | не boot |

Переименование папки `lexicon-ru-archaic` → `lexicon-ru-archaic` — опционально v1; до v1 достаточно смены **tier** в `catalog.json`.

---

## Ingest / rebuild

```bash
# 1) Modern список
python tools/fetch_ru_frequency_headwords.py

# 2) Literary из store или корпуса
python tools/lexicon_headwords.py  # export from store — см. split tool --literary-store

# 3) Split
python tools/split_ru_headwords_modern_archaic.py \
  --literary-store lab/agent-stores/lexicon-ru-archaic \
  --write-archaic

# 4) Prod store только modern
python tools/init_lexicon_store.py --corpus-id ru-general
```

Archaic store пересобирать **только** из `ru-archaic/headwords.v1.txt` (subset remigrate), не смешивать с general field_state.

---

## Примеры

| Форма | Класс | Комментарий |
|-------|-------|-------------|
| `абазвався` | archaic | диал. «взялся/обязался», ФЭБ №135 |
| `дом` | overlap | есть везде |
| `здравствуйте` | modern | DetCorpus, может не быть в Афане |

---

## Checklist

- [ ] `catalog.json`: tier `archaic` у Afan sharded store
- [ ] Profile `ru_lexicon` → `lexicon-ru-general` после сборки modern store
- [ ] T9 bench: отдельные отчёты `report_sweep_ru_general.json` vs `report_sweep_ru_archaic.json`
- [ ] Не union archaic в merged без ADR
