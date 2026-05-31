# ru-archaic — диалектные / не-DetCorpus леммы из Афанасьева

**Канон:** [`design/ru-lexicon-modern-archaic.md`](../../../design/ru-lexicon-modern-archaic.md)

Список **archaic-only** = headwords из `sss-ru-lexicon` (L2 Афан), которых **нет** в DetCorpus (`ru-general`).

Пример: `абазвався` (ФЭБ №135) — archaic, не modern T9.

## Сборка

```bash
python tools/fetch_ru_frequency_headwords.py
python tools/split_ru_headwords_modern_archaic.py \
  --literary-store lab/agent-stores/sss-ru-lexicon \
  --write-archaic
```

→ `headwords.v1.txt`, `split-report.json`

## Store

Отдельный rebuild L2 из этого списка — **не** смешивать с `sss-ru-general` field_state.
