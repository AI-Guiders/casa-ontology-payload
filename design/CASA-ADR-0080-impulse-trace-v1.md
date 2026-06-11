# ADR-0080: Impulse trace — общая нервная подсистема (observability)

**Status:** proposed  
**Date:** 2026-06-11 (rev.2 — substrate-wide, not dialogue-only)  
**Provenance:** диалог — «наблюдаемость есть, но не на полную катушку»; аналог нервного импульса (EPSP/IPSP, порог, траектория); *impulse — для всего efferent, не только partner*  
**Related:** [CASA-scratch-emergence-conditions-dialogue-v1.md](CASA-scratch-emergence-conditions-dialogue-v1.md), [CASA-work-verification-dialogue-thread.v1.md](CASA-work-verification-dialogue-thread.v1.md), [CASA-ADR-0019-control-multi-prism.md](CASA-ADR-0019-control-multi-prism.md), [CASA-ADR-0024-control-thalamus.md](CASA-ADR-0024-control-thalamus.md), [CASA-ADR-0057-dialogue-situations-character.md](CASA-ADR-0057-dialogue-situations-character.md), [CASA-ADR-0078-partner-voice-invariants-v1.md](CASA-ADR-0078-partner-voice-invariants-v1.md), [CASA-ADR-0079-runtime-host-csharp-nativeaot.md](CASA-ADR-0079-runtime-host-csharp-nativeaot.md), `casa/domain/dialogue_provenance.py`

---

## Context

CASA уже имеет **редкую для agent stack observability**: bind scores, zone bias, pulse, journal, modality-specific provenance. Но отладка «почему агент **сделал X**» (реплика, молчание, defer, motor act, attention shift) упирается в **итоговую поверхность**, а не в **траекторию** через субстрат.

**Dialogue** — самый болезненный потребитель сегодня, но **не единственный**. На каждом macro_tick одновременно живут:

- control stack (SN / CEN / FPN / thalamus — [ADR-0019](CASA-ADR-0019-control-multi-prism.md), [ADR-0024](CASA-ADR-0024-control-thalamus.md))
- modality tracts (partner text, motor compose, vision gate, math/logical — intelligence zones)
- bind + efferent для **любого** выбранного channel

Impulse trace должен быть **общей нервной подсистемой** (substrate service), а не «логом диалога».

### Что есть сейчас (фрагменты, без единого импульса)

| Артеfact | Область | Чего не даёт |
|----------|---------|--------------|
| `bind_trace()` | dialogue bind | конкуренты, runner-up, cross-modality |
| `meaning_provenance` | dialogue | путь через prisms/collectors/scorers |
| pulse / journal | macro_tick | synaptic log по узлам |
| verify_dialogue | partner only | почему класс X победил над Y |

### Гипотеза (из обсуждения)

Человеческое действие — **волна** через сеть с возбуждением/торможением и порогами. CASA-аналог — **один macro_tick**, внутри — одна или несколько **impulse** по efferent channels:

```text
macro_tick T
  afferent (sensory, partner, interoception, WM replay)
    → thalamus / SN (salience, relay)
    → zone routers + collectors (synapses in)
    → scorers (+/− potentials, IPSP)
    → bind / policy (summation → winner | sub-threshold)
    → tract realizers (dialogue | motor | vis | …)
    → efferent out + memory write
```

**Impulse** = запись этой волны: *куда зашла, что активировала, что подавила, что прошло порог* — без oracle-templates.

---

## Decision

### 1. Подсистема **Nervous / Impulse** (substrate-wide)

Новый слой (имя кода — черновик):

```text
casa/nervous/
  impulse.py       # ImpulseRecorder, schema, flush
  channels.py      # channel ids + outcome enums
```

**Не** `dialogue_provenance` only — dialogue **подключается** как consumer/recorder hook.

Каждый **macro_tick** имеет `tick_id`. Внутри — **0..N impulses** (по efferent channel):

| `channel` | Efferent | Пример outcome |
|-----------|----------|----------------|
| `partner_dialogue` | text tract / partner_outbox | spoken, silent, deferred |
| `idle_efferent` | scheduled initiative | spoken, skipped |
| `motor_compose` | write modality ([ADR-0005](CASA-ADR-0005-write-modality-motor-compose.md)) | composed, blocked |
| `vision_gate` | vis attention ([ADR-0018](CASA-ADR-0018-vision-modality-v0.md)) | frame_selected, hold |
| `control_routing` | SN/CEN mode shift | mode_changed, no_op |
| `sleep_train` | async worker enqueue | queued (summary only) |

Один tick может породить **несколько** impulses (partner + vis), связанных общим `tick_id`.

### 2. Объект **Impulse** (header)

```json
{
  "schema": "casa.impulse.v1",
  "impulse_id": "<uuid>",
  "tick_id": 108,
  "channel": "partner_dialogue",
  "store_dir": "...",
  "debug_level": "summary",
  "started_at_ms": 0,
  "finished_at_ms": 0,
  "outcome": "spoken|silent|deferred|blocked|error|no_op",
  "zones_touched": ["social", "linguistic", "emotional"]
}
```

Impulse **не** oracle: только **фактическая** активация и отбор.

### 3. **Synaptic events** — общий формат (не call graph)

Любой узел pipeline (любой zone / prism / bind policy) append'ит event:

```json
{
  "seq": 12,
  "node": "dialogue_bind.speech_act_scoring",
  "zone": "social",
  "kind": "activate|score|suppress|threshold|select|budget|route",
  "inputs": { "candidate_count": 14 },
  "potentials": [
    {"id": "ru.dialog.affect.cautious", "score": 42, "delta": 8, "reason": "affect_scoring.security_low"}
  ],
  "selected": ["ru.dialog.affect.cautious"],
  "rejected_above_floor": 3
}
```

| `kind` | Нервный аналог | Примеры (не только dialogue) |
|--------|----------------|------------------------------|
| `activate` | EPSP / afferent | collector block, vis frame, WM node |
| `score` | суммирование | `*_scoring`, zone bias, SN salience |
| `suppress` | IPSP | defense ([ADR-0074](CASA-ADR-0074-psychological-defenses.md)), repression gate |
| `threshold` | порог | no candidate ≥ floor → silent / no_op |
| `select` | winner | bind winner, tract slot, attention target |
| `budget` | metabolic cap | discourse budget, tick quantum exhausted |
| `route` | thalamus / router | hot router → prism id ([ADR-0016](CASA-ADR-0016-prism-domains-hot-router.md)) |

**Запрещено:** template dispatch (`if act == …: return phrase`) — только **ids** (concept, block, prism, tract) и numeric deltas.

### 4. Уровни `debug_level`

| Level | Когда | Содержимое |
|-------|-------|------------|
| `off` | production default | header + outcome + modality provenance (как сейчас) |
| `summary` | verify / review | winners + top-3 runner-up per stage + thresholds |
| `full` | lab | все events, все candidates |

`CASA_IMPULSE_TRACE=summary|full`, life_daemon `--impulse-trace`.

### 5. Хранение и связи

```text
tick_id ─┬─► pulse (macro)
         ├─► journal entry (per-channel summary + impulse_id[])
         ├─► modality provenance (dialogue, motor, …)
         └─► impulse_trace.jsonl (debug; rotate)
```

- `bind_trace()` → **`select` event** в channel `partner_dialogue`, не единственный trace.
- Full log: `agents/<id>/nervous/impulse_trace.jsonl` или per-impulse file.

### 6. Consumers (много, dialogue — первый)

| Consumer | Читает |
|----------|--------|
| `verify_dialogue_thread.py` | `channel=partner_dialogue`, summary |
| future motor / vis probes | свой channel |
| `tools/impulse_replay.py` | любой impulse_id |
| C# host ([ADR-0079](CASA-ADR-0079-runtime-host-csharp-nativeaot.md)) | `TickComposeResponse.impulse_summary` + будущие tract responses |

Dialogue verify — **reference implementation**, не граница подсистемы.

### 7. Non-goals (v1)

- Python call graph
- Oracle «expected output» labels
- Mandatory full trace in production
- Instrument every prism day-one — **phased**; schema and recorder **general** с первого коммита

---

## Consequences

### Positive

- «Почему агент сделал X» — одна модель для dialogue, motor, vision, control.
- Fable review видит nervous trace без знания modality internals.
- Emergence canon: routing → *куда*; impulse → *что выиграло*.
- C# host получает language-agnostic contract.

### Negative / cost

- `full` trace volume — rotate, summary default.
- Discipline: `ImpulseRecorder.current(channel)` на hot path — иначе drift.
- Каждый modality verify должен читать свой channel, не копировать dialogue script.

---

## Implementation sketch (phased)

### Phase A — substrate (general schema)

- `casa/nervous/impulse.py`: recorder, events, no-op when `off`.
- Wire `tick_id` on macro_tick; channels register at efferent entry.

### Phase B — first hooks (dialogue + control)

- `partner_dialogue`: speech_act / affect / thread / bind / situated / articulation.
- `control_routing`: SN mode, thalamus gate (minimal `route` events).

### Phase C — tools

- `tools/impulse_replay.py`, `verify_dialogue_thread --impulse`.
- Migrate `bind_trace()` → recorder `select`.

### Phase D — other channels

- motor, vision_gate, sleep_train summaries.
- Host JSON fields per tract.

---

## Acceptance

1. **partner_dialogue** non-empty → summary has `select` matching articulation source.
2. **partner_dialogue** silent → `threshold` or `budget` with reason.
3. **Same tick**, second channel (e.g. `control_routing`) can emit impulse with same `tick_id` without merging logs.
4. `CASA_IMPULSE_TRACE=off` → no jsonl growth; legacy provenance unchanged.

---

## Open questions

1. Ring size для `impulse_trace.jsonl` (100 vs 1000 impulses).
2. Raw afferent in events vs hash only (privacy / size).
3. Coordinator API: `with impulse.channel("partner_dialogue"):` vs explicit `impulse_id` threading — pick one in Phase A.

---

## References (code today)

- `casa/domain/dialogue_provenance.py` — dialogue-specific; migrate into nervous hooks
- `casa/domain/dialogue_bind/*_scoring.py`
- `casa/prisms/tick/discourse/`, `casa/prisms/control/`
- `tools/verify_dialogue_thread.py`, `tools/oracle_audit.py`
