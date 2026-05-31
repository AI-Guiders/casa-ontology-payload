# ru-archaic-v0 — диалектные / не-DetCorpus леммы из Афанасьева

**Канон:** [`design/ru-lexicon-modern-archaic-v0.md`](../../../design/ru-lexicon-modern-archaic-v0.md)

Список **archaic-only** = headwords из `sss-ru-lexicon-v0` (L2 Афан), которых **нет** в DetCorpus (`ru-general-v0`).

Пример: `абазвався` (ФЭБ №135) — archaic, не modern T9.

## Сборка

```bash
python tools/fetch_ru_frequency_headwords_v0.py
python tools/split_ru_headwords_modern_archaic_v0.py \
  --literary-store lab/agent-stores/sss-ru-lexicon-v0 \
  --write-archaic
```

→ `headwords.v1.txt`, `split-report.v0.json`

## Store

Отдельный rebuild L2 из этого списка — **не** смешивать с `sss-ru-general-v0` field_state.
