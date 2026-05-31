# Lexicon usage axes v0 (modern prod, archaic parked)

**Date:** 2026-05-30  
**Status:** accepted (design + lab tools)  
**Parent:** [`agent-store-catalog-v0.md`](agent-store-catalog-v0.md), [`context-axis-v0.md`](context-axis-v0.md)  
**Companion:** [`infancy-corpus-phases-v0.md`](infancy-corpus-phases-v0.md) (фаза 5 prod vs фазы 2–4 listen/archaic)

---

## Позиция

- **Prod RU T9** = только **modern** DetCorpus (`sss-ru-general-v0`). Афан **не** в hot path.
- Диалект / архаика / ультраредкое = **оси на лемме**, не отдельный runtime-store в profile.
- Arhaic corpus (`sss-ru-lexicon-v0`, `ru-archaic-v0/`) — **lab / ingest ref**, помечается осями `era=archaic`, `active_for_t9=false`.

---

## Оси (на каждую лемму)

| Ось | Значения | Смысл |
|-----|----------|--------|
| **era** | `modern` \| `archaic` \| `dialect` \| `unknown` | Эпоха / источник записи |
| **usage_band** | `active` \| `rare` \| `ultra_rare` \| `unused` | Частота (DetCorpus ipm/rank) |
| **active_for_t9** | bool | Допуск в predict T9 (prod default: только `true`) |
| **sources** | string[] | `detcorpus-50k-cc0`, `opensubtitles-en-50k`, `afanasyev-sharded`, … |

Sidecar: `{store}/lexicon_axes.v0.jsonl` или `lab/corpus/ru-general-v0/lexicon_axes.v0.jsonl` (копируется в store при init).

### Пороги `usage_band` (DetCorpus rank, v0)

| band | Условие (rank 1 = самое частое) |
|------|----------------------------------|
| `active` | rank ≤ 8 000 **или** ipm ≥ 15 |
| `rare` | rank ≤ 25 000 **или** ipm ≥ 2 |
| `ultra_rare` | остальные modern-леммы |
| `unused` | нет на L2 / вне корпуса (резерв) |

`active_for_t9` по умолчанию: `era==modern` и `usage_band` ∈ `{active, rare}`.

**BiT9 / EN:** леммы **вне** `lexicon_axes` (нет строки в sidecar) при `t9_policy=prod` **не фильтруются** — иначе RU-оси отрезали бы весь EN L2. Фильтр только для лемм, **перечисленных** в sidecar. EN general: `opensubtitles-en-50k` → `lab/corpus/en-general-v0/frequency.ipm.v1.jsonl`; linked boot **мержит** RU+EN оси.

---

## Runtime

```text
boot_store → load lexicon_axes.v0.jsonl → state["lexicon_axes"]
predict_t9(..., t9_policy="prod") → filter candidates по active_for_t9
_t9_score → sort: votes + length; ipm/rank if prefix ≥3 graphemes (homoglyph-safe)
tick JSON (roadmap): context.lexicon_filter + sample axis на top anchor
```

Политики `t9_policy`:

| policy | Фильтр |
|--------|--------|
| `prod` | только `active_for_t9` |
| `lab` | без фильтра (все L2) |
| `modern_all` | `era==modern` |

---

## Афан

Не удаляем store — **не подключаем** в profile. Леммы вроде `абазвався`: `era=archaic`, `active_for_t9=false`. См. [`ru-lexicon-modern-archaic-v0.md`](ru-lexicon-modern-archaic-v0.md) (split tool для lab).

---

## Команды

```bash
python tools/fetch_ru_frequency_headwords_v0.py
python tools/fetch_en_frequency_headwords_v0.py
python tools/build_lexicon_usage_axes_v0.py --corpus ru-general
python tools/build_lexicon_usage_axes_v0.py --corpus en-general --copy-to-store lab/agent-stores/sss-en-folk-v0
python tools/init_lexicon_store_v0.py --corpus-id ru-general
python tools/bench_t9_lexicon_sweep_v0.py --store-dir lab/agent-stores/sss-ru-general-v0
```
