# Lexicon usage axes v0 (modern prod, archaic parked)

**Date:** 2026-05-30  
**Status:** accepted (design + lab tools)  
**Parent:** [`agent-store-catalog.md`](agent-store-catalog.md), [`context-axis.md`](context-axis.md)  
**Companion:** [`infancy-corpus-phases.md`](infancy-corpus-phases.md) (фаза 5 prod vs фазы 2–4 listen/archaic)

---

## Позиция

- **Prod RU T9** = только **modern** DetCorpus (`lexicon-ru-general`). Афан **не** в hot path.
- Диалект / архаика / ультраредкое = **оси на лемме**, не отдельный runtime-store в profile.
- Arhaic corpus (`lexicon-ru-archaic`, `ru-archaic/`) — **lab / ingest ref**, помечается осями `era=archaic`, `active_for_t9=false`.

---

## Оси (на каждую лемму)

| Ось | Значения | Смысл |
|-----|----------|--------|
| **era** | `modern` \| `archaic` \| `dialect` \| `unknown` | Эпоха / источник записи |
| **usage_band** | `active` \| `rare` \| `ultra_rare` \| `unused` | Частота (DetCorpus ipm/rank) |
| **active_for_t9** | bool | Допуск в predict T9 (prod default: только `true`) |
| **sources** | string[] | `detcorpus-50k-cc0`, `opensubtitles-en-50k`, `afanasyev-sharded`, … |

Sidecar `{store}/lexicon_axes.jsonl` — **ingest artifact only** (provenance / rebuild). После init/boot материализуется на **L3** как `E:lang.word.*|usage_axis|…` (`lexicon_field_oracle.py`). **Predict не читает sidecar** — только поле.

### Пороги `usage_band` (DetCorpus rank, v0)

| band | Условие (rank 1 = самое частое) |
|------|----------------------------------|
| `active` | rank ≤ 8 000 **или** ipm ≥ 15 |
| `rare` | rank ≤ 25 000 **или** ipm ≥ 2 |
| `ultra_rare` | остальные modern-леммы |
| `unused` | нет на L2 / вне корпуса (резерв) |

`active_for_t9` по умолчанию: `era==modern` и `usage_band` ∈ `{active, rare}`.

**BiT9 / EN:** леммы **вне** `lexicon_axes` (нет строки в sidecar) при `t9_policy=prod` **не фильтруются** — иначе RU-оси отрезали бы весь EN L2. Фильтр только для лемм, **перечисленных** в sidecar. EN general: `opensubtitles-en-50k` → `lab/corpus/en-general/frequency.ipm.v1.jsonl`; linked boot **мержит** RU+EN оси.

---

## Runtime

```text
ingest / init_lexicon_store → axes JSONL (audit) + imprint L3 usage_axis edges
boot_store → materialize sidecar → L3 if missing; lexicon_oracle_for_predict(state)
predict_t9(..., t9_policy="prod") → L2 votes + L3 oracle (ipm/rank/era) — no bundle
```

Политики `t9_policy`:

| policy | Фильтр |
|--------|--------|
| `prod` | только `active_for_t9` |
| `lab` | без фильтра (все L2) |
| `modern_all` | `era==modern` |

---

## Афан

Не удаляем store — **не подключаем** в profile. Леммы вроде `абазвався`: `era=archaic`, `active_for_t9=false`. См. [`ru-lexicon-modern-archaic.md`](ru-lexicon-modern-archaic.md) (split tool для lab).

---

## Команды

```bash
python tools/fetch_ru_frequency_headwords.py
python tools/fetch_en_frequency_headwords.py
python tools/build_lexicon_usage_axes.py --corpus ru-general
python tools/build_lexicon_usage_axes.py --corpus en-general --copy-to-store lab/agent-stores/lexicon-en-folk
python tools/init_lexicon_store.py --corpus-id ru-general
python tools/bench_t9_lexicon_sweep.py --store-dir lab/agent-stores/lexicon-ru-general
```
