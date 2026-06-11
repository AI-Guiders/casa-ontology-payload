# ADR-0080: Impulse trace — сквозная observability efferent pass

**Status:** proposed  
**Date:** 2026-06-11  
**Provenance:** диалог — «наблюдаемость есть, но не на полную катушку»; аналог нервного импульса (EPSP/IPSP, порог, траектория)  
**Related:** [CASA-scratch-emergence-conditions-dialogue-v1.md](CASA-scratch-emergence-conditions-dialogue-v1.md), [CASA-work-verification-dialogue-thread.v1.md](CASA-work-verification-dialogue-thread.v1.md), [CASA-ADR-0057-dialogue-situations-character.md](CASA-ADR-0057-dialogue-situations-character.md), [CASA-ADR-0078-partner-voice-invariants-v1.md](CASA-ADR-0078-partner-voice-invariants-v1.md), [CASA-ADR-0079-runtime-host-csharp-nativeaot.md](CASA-ADR-0079-runtime-host-csharp-nativeaot.md), `casa/domain/dialogue_provenance.py`

---

## Context

CASA уже имеет **редкую для agent stack observability**: bind scores, zone bias, `bind_trace`, `meaning_provenance`, journal, verify по pragmatic class. Но отладка partner turn часто упирается в **итоговую поверхность** («почему такая реплика?» / «почему пусто?»), а не в **траекторию**.

### Что есть сейчас (фрагменты)

| Артеfact | Что даёт | Чего не даёт |
|----------|----------|--------------|
| `bind_trace()` | top winner после bind | конкуренты, runner-up, порог «ничего не прошло» |
| `meaning_provenance` | intent + props | путь через prisms/collectors/scorers |
| verify script | pragmatic class per turn | почему класс X победил над Y |
| journal / pulse | факт tick | synaptic log по узлам |

**Следствие:** можно **PASS** verify и всё равно не понимать *почему* — или видеть oracle-подобное поведение post hoc, не по трассировке.

### Гипотеза (из обсуждения)

Человеческое действие — не один «if», а **волна** через сеть с возбуждением/торможением и порогами. CASA-аналог:

```text
afferent (partner cue, WM, affect)
    → collectors (synapses in)
    → scorers (+/− potentials)
    → bind competition (summation → winner / sub-threshold)
    → situated compose (blocks → articulation)
    → efferent out + memory write
```

**Impulse** = один such pass с **накоплением записи**, куда волна зашла и что активировала — без подмены compose готовыми Python-фразами.

---

## Decision

### 1. Ввести объект **Impulse** (один efferent pass)

Каждый partner turn (и опционально idle efferent tick) получает:

```json
{
  "schema": "casa.impulse.v1",
  "impulse_id": "<uuid>",
  "tick": 108,
  "store_dir": "...",
  "mode": "partner_channel",
  "debug_level": "summary",
  "started_at_ms": 0,
  "finished_at_ms": 0,
  "outcome": "spoken|silent|deferred|error"
}
```

Impulse **не** oracle: он не содержит «правильный ответ», только **что система реально активировала и отфильтровала**.

### 2. **Synaptic events** — лог по пути (не call graph)

Каждый узел pipeline, который меняет кандидатов или scores, append'ит event:

```json
{
  "seq": 12,
  "node": "dialogue_bind.speech_act_scoring",
  "kind": "score|activate|suppress|threshold|select|budget",
  "inputs": {
    "partner_text_hash": "...",
    "active_slots": ["how_are_you"],
    "candidate_count": 14
  },
  "potentials": [
    {"id": "ru.dialog.affect.cautious", "score": 42, "delta": +8, "reason": "affect_scoring.security_low"},
    {"id": "ru.dialog.mirror.ack", "score": 31, "delta": -5, "reason": "continuer.skip_clause_1"}
  ],
  "selected": ["ru.dialog.affect.cautious"],
  "rejected_above_floor": 3,
  "notes": []
}
```

| `kind` | Аналог | Пример |
|--------|--------|--------|
| `activate` | EPSP / afferent | collector вернул block |
| `score` | суммирование PSP | `partner_scoring`, `thread_scoring` |
| `suppress` | IPSP | defense gate, zone budget cut |
| `threshold` | порог не пройден | все scores < floor → silent |
| `select` | winner | bind top-k → situated input |
| `budget` | metabolic / discourse cap | `discourse/budget.py` отрезал slot |

**Запрещено** в synaptic log: template dispatch вида `if act == "thanks": return "не за что"` — только **ids блоков/claims** и числовые deltas.

### 3. Уровни `debug_level`

| Level | Когда | Содержимое |
|-------|-------|------------|
| `off` | production default | только `impulse` header + `outcome` + сжатый provenance (как сейчас) |
| `summary` | verify / Fable review | winners + top-3 runner-up per stage + threshold events |
| `full` | lab debug | все synaptic events, все candidates с score |

Env / flag (черновик): `CASA_IMPULSE_TRACE=summary|full`, life_daemon `--impulse-trace`.

**Hot path:** `summary` не блокирует tick; `full` — только dev.

### 4. Связь с существующим provenance

- `bind_trace()` → становится **`select` event** на стадии bind, не единственным trace.
- `meaning_provenance` / journal → импульс **ссылается** на `impulse_id`; journal хранит summary, не full log.
- Full log (optional): `agents/<id>/impulse_trace/<impulse_id>.jsonl` или ring buffer `impulse_trace.jsonl` (rotate).

```text
impulse_id ─┬─► journal entry (summary)
            ├─► verify_dialogue_thread (reads summary + outcome)
            └─► impulse_trace.jsonl (debug only)
```

### 5. Verify и «почему пусто»

[CASA-work-verification-dialogue-thread.v1.md](CASA-work-verification-dialogue-thread.v1.md) расширяется (отдельным PR):

| Fail mode | Impulse must show |
|-----------|-------------------|
| Silent reply | `threshold` event + best runner-up below floor |
| Wrong pragmatic class | `select` at speech_act stage vs efferent mismatch |
| Hub replay | competing `potentials` on turns N and N+1 — same winner id |
| Compose dropped winners | `select` at bind ≠ blocks received in situated |

Verify **не** матчит surface strings; читает **provenance + impulse summary**.

### 6. Non-goals (v1)

- Полный **call graph** Python — не нужен, врёт на dynamic import.
- Oracle labels «expected phrase» в trace — **запрещены**.
- Обязательный full trace в production store — только summary.
- C# host (0079) — impulse schema **language-agnostic**; Python compose пишет первым.

---

## Consequences

### Positive

- Ответ на «почему такой вывод» = воспроизводимая **траектория**, не угадывание по логам.
- Fable / external review получают artifact без доступа к коду.
- Стыкуется с emergence canon: routing говорит *куда смотреть*, impulse показывает *что выиграло*.
- Подготовка к C# host: `TickComposeResponse` включает `impulse_summary`.

### Negative / cost

- Объём данных при `full` — нужен rotate и `summary_only` по умолчанию.
- Instrumentation touch points: collectors, scorers, bind, situated, articulation — **disciplined** API (`impulse.record(...)`), иначе drift.
- Тесты должны assert на impulse events, не только surface.

---

## Implementation sketch (phased)

### Phase A — schema + writer (no behavior change)

- `casa/domain/impulse_trace.py`: `ImpulseRecorder`, event types, flush to jsonl.
- Wire header on partner tick; `debug_level=off` → no-op writer.

### Phase B — bind + compose stages

- Hook `speech_act_scoring`, `affect_scoring`, `thread_scoring`, `continuer_scoring`, bind winner, situated input.
- Migrate `bind_trace()` to emit `select` event inside recorder.

### Phase C — verify + tools

- `verify_dialogue_thread.py` — optional `--impulse` checks.
- `tools/impulse_replay.py` — pretty-print one impulse for human review.

### Phase D — host contract (0079)

- `TickComposeResponse.impulse_summary` field.

---

## Acceptance (duck test for this ADR)

1. Partner turn с **non-empty** reply → impulse summary содержит ≥1 `select` и финальный block id, совпадающий с articulation source.
2. Partner turn **silent** → impulse содержит `threshold` или `budget` с numeric reason, не «unknown».
3. Turn с `how_are_you` → summary показывает speech_act activation **до** bind select; verify не нуждается в surface anchor.
4. `CASA_IMPULSE_TRACE=off` → нет jsonl growth; provenance как сейчас.

---

## Open questions

1. Ring size для `impulse_trace.jsonl` на von-neumann store (100? 1000 impulses?).
2. Хеш partner text в events vs raw text (privacy / log size).
3. Единый impulse на **whole macro_tick** или отдельный на partner channel only — v1: **partner channel only**.

---

## References (code today)

- `casa/domain/dialogue_provenance.py` — `bind_trace`, `meaning_provenance`
- `casa/domain/dialogue_bind/*_scoring.py` — potentials
- `casa/prisms/tick/discourse/` — budget, situated, articulation
- `tools/verify_dialogue_thread.py`, `tools/oracle_audit.py`
