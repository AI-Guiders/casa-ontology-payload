# Experiment J (complete): русский язык — выход из «яслей»

**Status:** active north star (language only)  
**Date:** 2026-05-29  
**Paused:** Exp K (C#) — не отменён, отложен.

## Почему не фальстарт

Сначала C# без literacy был перекос; **J0** — правильная поправка. C# grade8 KB остаётся в репо, но **не в фокусе** до закрытия языкового контура.

## Где агент сейчас («ясли»)

| Умение | Статус | Доказательство |
|--------|--------|----------------|
| Найти claim по **похожим** словам | ✅ | answer@1 grammar, K0-style benches |
| **Перефраз** учебного запроса | ✅ | J0 paraphrase read@1 **0.95** |
| Норма (запятая, согласно, паронимы) | ✅ частично | `kb-russian-language-rules-v1` |
| **Писать** связный ответ | ✅ v0 шаблон | write@sketch **1.0** (literacy queries) |
| «Книжка» целиком | ❌ | только размеченные claims |
| Смысл вне KB | ❌ | нет embedding / LM на hot path |

## North star (язык закончен = «выпуск»)

> По русскому запросу (в т.ч. перефраз) агент **понимает намерение**, **находит** норму/правило в памяти, **формулирует** короткий ответ своими словами с опорой на claims — и **держит** это на поле после damage (repair), без C# и без облачного LM как обязательного hot path.

**Не входит:** литературный анализ, весь интернет, свободная болтовня.

## Три столпа

```text
        ┌─────────────┐
        │  J0 read    │  перефраз, intent, RU/EN учебные формулировки
        └──────┬──────┘
               ▼
        ┌─────────────┐
        │  J grammar  │  норма, правки текста, Грамота-опора
        └──────┬──────┘
               ▼
        ┌─────────────┐
        │  J write    │  answer_text / articulation grammar
        └──────┬──────┘
               ▼
        ┌─────────────┐
        │  J field    │  union + answer@k repair (NCA windowed)
        └─────────────┘
```

## Фазы (порядок работ)

### ✅ Phase A — literacy read (J0)

- KB: `kb-russian-literacy-agent-v1.md`
- Bench: `exp_j0_literacy/queries_read.jsonl`, `queries_paraphrase.jsonl`
- Smoke: `run_exp_j0_literacy_sync.ps1`

### ✅ Phase B — literacy + grammar write (2026-05-29)

- `tools/articulation_grammar_v0.py` → поле **`answer_text`** в `cen_plan` / `sn_cen_infer`
- Bench: `tools/bench_write_sketch.py`, `run_exp_j_language_write_bench.ps1`
- **write@sketch:** literacy 15/15 **1.0**; grammar 20 queries — см. `report_write_grammar.json`
- Не путать с «генерацией романа» — пересказ условия + правило из claims

### ✅ Phase C — grammar hardening (2026-05-29)

- `queries_grammar.jsonl` (20), §15 retrieval anchors в grammar KB
- **grammar read@1 = 0.95**; write@sketch = 1.0
- Улучшен `_score_claim` (фразовый chunk в query)

### ✅ Phase D — train (2026-05-29); curve — fix script

- `run_exp_j_train_language_windowed.ps1` — **600 ep ~40 min**, grammar+literacy union (**253** tokens)
- Модель: `nca_out_exp_j_ru_language_windowed_v1/model.pt` (~0,5 MB) → `language-agent-lab-v0/checkpoints/model_hard.pt`
- Repair probe (grammar): **mix_windowed ≈ 0.74** (≥ 0.7)
- `bench_curve` в скрипте упал (`--bundles` vs `--bundle`) — починить отдельно
- FPN session: удержание «о чём правим текст» 3+ тика

### ⏸ Phase E — следующая ось (после выпуска J)

- [Exp L: concrete → abstract + букварь](experiment-l-concrete-to-abstract-v0.md) — схемы (палочки), `V:` vision, корова/овца/пчела
- Exp K C#, emit — **после** J + начального L0–L1

## Store (единственный фокус)

`lab/agent-stores/language-agent-lab-v0`

Union bundles (целевой минимум):

- `kb-russian-language-rules-v1`
- `kb-russian-literacy-agent-v1`
- (опц.) `kb-regex-mre3-ru-chapter-map-v1` — только если нужен regex-трек

**Не синкать в language store:** `kb-csharp-console-grade8` (остаётся в `code-agent-lab-v0` до Phase E).

## Еженедельный smoke (язык)

```powershell
$env:AGENT_NOTES_KB = 'D:\experiments\agent-notes\knowledge'
.\scripts\run_exp_j0_literacy_sync.ps1
.\scripts\run_exp_j_language_sync.ps1
# когда будет:
# .\scripts\run_exp_j_language_bench.ps1
```

## Критерий «выпуск из яслей» (чеклист)

- [x] paraphrase read@1 ≥ 0.9 (**0.95**)
- [x] grammar answer@1 ≥ 0.95 (**0.95** / 20 queries)
- [x] write@sketch ≥ 0.8 (**1.0**)
- [x] repair mix ≥ 0.7 (**~0.74** windowed, grammar bundle)
- [x] Документировано: что агент **не** умеет (книги, вне KB); **dialogue v1** — приветствие, я/ты/мама, без подмены C#
- [x] Устный экзамен (2026-05-28): `scripts/run_exp_j_oral_exam.ps1` — см. отчёты ниже

### Устный экзамен (прогон lab)

| Бенч | Метрика | Результат |
|------|---------|-----------|
| off-topic / dialogue guard | guard@1 | см. `queries_off_topic.jsonl` (ответ из dialogue, не C#) |
| oral exam (curated) | pass | **1.0** (18/18) |
| grammar recall | answer@1 | **0.95** |
| grammar write | write@sketch | **1.0** |
| paraphrase | answer@1 | **0.70** (после code-guard; было ~0.95 до жёсткого фильтра) |

**Свободная речь:** hot path `articulation_realize_v0` (слоты + шаблоны, без вставки claim); legacy `compose_answer_text_sketch` — только bench. См. [`articulation-realize-v0.md`](articulation-realize-v0.md). Болтовня / слабый match → dialogue KB + `soft_miss`, без подмены C#.

Артефакты: `lab/exp_j_ru_v1/report_oral_exam.json`, `report_off_topic_guard.json`.

После всех галочек — можно возвращаться к Exp K без чувства «изверги».

## Связанные документы

| Док | Роль |
|-----|------|
| [`experiment-j0-russian-literacy-v1.md`](experiment-j0-russian-literacy-v1.md) | J0 детали |
| [`experiment-j-text-modality-v1.md`](experiment-j-text-modality-v1.md) | J field, NCA, scripts |
| [`experiment-k-code-emit-v0.md`](experiment-k-code-emit-v0.md) | paused |
| [`experiment-l-concrete-to-abstract-v0.md`](experiment-l-concrete-to-abstract-v0.md) | next: схемы + картинки букваря |
