# Experiment J0: читать и писать (русский literacy)

**Status:** phase 1 read ✅; phase 2 write ✅ (`answer_text`, write@sketch 1.0 literacy)  
**Date:** 2026-05-29  
**Focus:** **закончить язык** (J + J0). Exp K (C#) — **on hold**, см. [`experiment-k-code-emit.md`](experiment-k-code-emit.md).

## North star

> Агент **понимает перефраз** запроса на русском и может **сформулировать** короткий связный ответ по памяти (не только top-3 цитаты).

## Слои языка (единый трек J)

```text
J0 literacy  →  читать запрос, перефраз, намерение, черновик ответа
J  grammar   →  норма письма (орфография, пунктуация, паронимы)
J  field     →  union store, answer@k, NCA repair (опционально углубить)
```

## KB

| Документ | Claims (после sync) | Роль |
|----------|---------------------|------|
| `kb-russian-literacy-agent-v1.md` | ~90+ | перефразы, intent, письмо |
| `kb-russian-language-rules-v1.md` | grammar | орфография, синтаксис нормы |

Путь: `worlds/evidence-humanities-shelf/kb-russian-literacy-agent-v1.md`

## Store

`lab/agent-stores/language-agent-lab` — **union**: grammar + MRE3 (опц.) + **literacy**.

## Metrics

| Metric | Bench | Target v1 |
|--------|-------|-----------|
| **read@1 direct** | `queries_read.jsonl` | ≥ 0.9 |
| **read@1 paraphrase** | `queries_paraphrase.jsonl` | ≥ **0.85** |
| **write@sketch** | manual / future articulation | TBD |

`expect_any` — хотя бы один якорь в top `answer_blocks`.

## Smoke

```powershell
$env:AGENT_NOTES_KB = '../agent-notes/knowledge'
.\scripts\run_exp_j0_literacy_sync.ps1
```

## Phase 2 — писать (следующий шаг)

| Задача | Критерий |
|--------|----------|
| **write@sketch** | Ответ 2–4 предложения: что понял + откуда claim |
| articulation **grammar** | MoE / шаблон: не телеграф, связные предложения |
| bench `queries_write.jsonl` | ≥ 0.8 автопроверка (ключевые фразы + нет пустого blocks) |

## Phase 3 — «выпуск из яслей»

| Задача | Критерий |
|--------|----------|
| grammar answer@1 | ≥ 0.95 на `exp_j_ru_queries.jsonl` (расширить) |
| paraphrase read@1 | удержать ≥ 0.9 |
| repair mix (union windowed) | ≥ 0.7 на language store (если train) |
| **не цель сейчас** | C#, compile, emit_code |

Канон финиша: [`experiment-j-language-complete-v1.md`](experiment-j-language-complete-v1.md).

## Relation

| Exp | Роль |
|-----|------|
| **J0** | читать/писать, перефраз |
| **J** | грамматика нормы |
| **K** | C# — **paused** |
