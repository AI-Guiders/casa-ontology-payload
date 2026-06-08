# ADR-0058: Limbic Affect Prism (subject-mode hot path)

**Status:** accepted (design); код — roadmap  
**Date:** 2026-06-07  
**Related:** ADR-0057 (situations + character development), ADR-0059 (innate organ basis), ADR-0010 (predict / DAN / value), ADR-0055 (WM prism), ADR-0024 (thalamus), [control-lattice-stack.md](control-lattice-stack.md), [agent-existence-north-star.md](agent-existence-north-star.md)

---

## Context

ADR-0057: субъект без **лимбического органа** не накопит субъективный опыт — только lexicon (`ru.dialog.affect` ≠ переживание).

**Уже есть, но не то:**

| Артефакт | Что делает | Почему не закрывает limbic в REPL |
|----------|------------|-----------------------------------|
| [`value.py`](../casa/prisms/control/value.py) | scalar **P9** — приоритет replay/sleep из surprise + teacher correction | нет valence/arousal; не в hot path compose/disposition |
| [`predict.py`](../casa/prisms/control/predict.py) | digest forward-model, **P8** prediction error | не подключён к `dialogue_tick` / partner turn |
| [`attention.py`](../casa/prisms/control/attention.py) | DAN spotlight mask | не в subject articulation |
| ADR-0010 `lattice_value` | NCA решётка, lab brick | поле ≠ persisting **affect state** субъекта |
| `ru.dialog.affect` | уроковый текст | материал речи, не organ |

**von-neumann REPL** идёт мимо control stack: `semantic_read` → tract → bind → compose. **Лимбика в этом контуре отсутствует** — отсюда молчание без «стыда», capabilities вместо repair.

---

## Decision

### 1. Отдельный organ: **Affect prism** (лимбика subject-mode)

**Не расширять** `value.py` до «всего эмоционального» — разделение обязанностей:

| Organ | Вопрос | Выход |
|-------|--------|-------|
| **predict** (P8) | *что ожидал vs что пришло?* | prediction error → surprise concepts |
| **affect prism** | *как это ощущается / насколько важно для меня сейчас?* | valence, arousal, security, episodic tags |
| **value** (P9) | *что консолидировать первым?* | scalar replay priority |
| **character prism** (ADR-0057) | *какой я в среднем?* | slow EMA поверх affect |

Пакет (Python hot path v0, field lattice v1):

```
casa/prisms/affect/
  model.py       — AffectState, AffectAxes, AffectEvent
  read.py        — affect_state(state, store) → snapshot
  update.py      — affect_after_turn(...), affect_on_consolidate(...)
  apply.py       — deltas для compose reweight, disposition, tract tie-break, character EMA
  persist.py     — state["affect_prism"] + optional store shard
  __init__.py
```

Field roadmap: Emotional Zone ([ADR-0060](CASA-ADR-0060-emotional-zone.md)) — `agent-limbic-core` + `agent-affect-sandbox` in `prism_agent.intelligence_zones.emotional`; Python package `casa/prisms/affect/`.

### 2. Модель состояния (v0)

```python
@dataclass
class AffectAxes:
    valence: float    # [-1, 1]  неприятно ↔ приятно
    arousal: float    # [0, 1]   спокойно ↔ возбуждён
    security: float   # [0, 1]   устойчивость «я» / линии диалога

@dataclass
class AffectState:
    axes: AffectAxes
    episodic: dict[str, float]   # e.g. "dialog.repair_pending", "dialog.math_fail"
    last_event: str
    tick: int
```

**Инициализация T=0:** нейтраль (0, 0.2, 0.5) — organ **есть**, не «пусто до curriculum».

**Обновление:** только **subject-side** hooks после:

- partner turn (stimulus);
- subject turn (исход: ответ / молчание / defer);
- disposition (defer/refuse);
- optional P8 surprise feed from predict когда подключён.

**Не обновляется:** teacher paste строк; operator JSON «be sad».

### 3. События → delta (v0, эмпирически калибруемые)

| Event | Условие | Δ axes / episodic |
|-------|---------|-------------------|
| `partner_greeting` | social + greeting hints | valence +, security + |
| `self_failure` | пустой reply / defer на прямой вопрос | valence −, arousal +, `dialog.repair_pending` |
| `partner_repair_invite` | «прости», «неожиданно», meta после сбоя | arousal +, episodic repair flag |
| `self_repair_success` | связный ответ при repair_pending | valence +, security +, clear flag |
| `partner_trust` | благодарность, продолжение после сбоя | valence +, security + |
| `prediction_error` | P8 surprise magnitude | arousal +, valence − (mild) |

Калибровка — probe, не философия. Важно: **события из прожитого tick**, не keyword router в compose.

### 4. Apply — куда течёт affect (hot path)

```text
partner/subject turn
    → affect_update(event)
    → affect_apply(ctx):
         · reweight_blocks_for_reply  (± bind по valence/security)
         · DiscourseBudget.score_floor (arousal ↑ → короче/длиннее emergent)
         · SubjectDisposition          (security ↓ + repair_pending → prefer honest defer)
         · tract tie-break             (не social-over-math при math stimulus + arousal)
         · character_prism EMA         (slow, ADR-0057)
    → compose (ADR-0056)
```

**Verbalize:** compose **не** обязан сказать «я расстроен» — affect смещает **выбор** clauses на поле. Lexeme `ru.dialog.affect` — один из кандидатов, не единственный.

### 5. Tick order (subject-mode)

```text
thalamus.arousal (wake/sleep)          ← ADR-0024
perceive partner turn
predict expected digest (optional P8)  ← predict.py
affect_read → affect_update(events)    ← NEW
semantic_read + tract competition
WM / intent prisms
bind + affect_apply
compose + subject turn
affect_persist + dialogue ring
on sleep: affect_consolidate + value P9 replay order
```

### 6. Persist & provenance

```json
"state": {
  "affect_prism": {
    "axes": {"valence": -0.2, "arousal": 0.6, "security": 0.4},
    "episodic": {"dialog.repair_pending": 1.0},
    "last_event": "self_failure",
    "tick": 42
  }
}
```

Provenance outbound turn: `affect_axes`, `affect_event` — duck test и отладка REPL `/verbose`.

---

## Relationship to ADR-0010 stack

```text
PREDICT ──P8──► surprise ──► affect_update (arousal/valence)
AFFECT  ──────► compose / disposition / character
VALUE   ◄── derived from affect magnitude + teacher tags ── P9 replay
SN      ◄── salience mask (bottom-up); DAN ◄── FPN (top-down) — still roadmap on grid
```

**lattice_value** остаётся scalar guardrail/replay; **affect prism** — multidimensional **live** state. На consolidate: `episode_value()` может **читать** `|valence| + arousal` из affect, не дублировать логику.

---

## Implementation phases

| Phase | Deliverable |
|-------|-------------|
| **v0** | `affect/` package; wire `process_dialogue_on_tick`; probe «greeting → math silence → repair» |
| **v0.1** | `affect_apply` in `reweight_blocks_for_reply`; math tract not drowned by social |
| **v1** | P8 from `predict.py` on dialogue digest; surprise → affect |
| **v1.1** | character prism EMA from affect traces |
| **v2** | `lattice_affect` field mirror + NCA train (optional) |

Tests: `tests/test_affect_prism_dialogue.py` — event deltas, repair scenario, no template paste.

---

## Anti-patterns

| ❌ | ✅ |
|----|-----|
| Soul doc / operator mood JSON | axes at T=0 + self-update |
| Keyword «прости» → apology template | event `partner_repair_invite` → affect → emergent compose |
| Merge affect into `value.py` only | separate organs + P9 derives from affect |
| Claim human qualia | functional state + provenance |

---

## Sibling organs — что ещё упустили (матрица)

Легенда: **Hot** = subject dialogue tick сегодня; **Lab** = код/brick есть; **Design** = ADR only; **Gap** = нет даже design v0.

| Organ | Аналог | Статус | Симптом без него |
|-------|--------|--------|------------------|
| **Affect / limbic** | amygdala, vmPFC | **Gap → ADR-0058** | нет repair/shame/urgency; lexicon вместо переживания |
| **Character** | temperament | Design (0057) | безликий правильный собеседник |
| **Predict + P8** | cerebellum / forward model | Lab (`predict.py`), не Hot | нет «ожидал ответить — не ответил» как surprise |
| **DAN** | dorsal attention | Lab (`attention.py`), не Hot | SN overloaded; social tract always wins |
| **Value P9** | striatum priority | Lab (`value.py`), partial sleep | replay слепой к dialog failure |
| **Thalamus** | relay, global arousal | Design + stub (`thalamus.py`) | wake/sleep не gating dialogue bandwidth |
| **SN (real)** | salience | Lab stack, REPL bypass | tract + heuristics вместо salience field |
| **FPN on field** | working memory goal | Session JSON mirror | цель диалога слабо держится между ходами |
| **Situation curriculum** | lived experience | Design (0057) | isolated block green ≠ conversation |
| **Partner model** | mentalizing | Gap | не отличает meta-repair от self-intro |
| **Motor compose** | моторная речь | ADR-0005 roadmap | write modality отдельно от dialog |
| **Interoception / insula** | body state | Design → **0066** neuromodulator + 0064 metabolic | перегруз / panic без gain dynamics |

**Приоритет для von-neumann REPL:** affect (0058/0060) → **neuromodulator dynamics (0066)** → situation curriculum → predict→P8→neuromod→affect → character EMA → DAN/tract balance.

---

## Consequences

- ADR-0057 §5 ссылается сюда как на **канон limbic**; curriculum без 0058 v0 — premature.
- `ru.dialog.affect` в bundle остаётся **лексикой**; тесты проверяют, что при repair **bind не сводится** только к нему.
- Character prism (отдельный ADR или § в 0057) **consumes** affect EMA — не дублирует оси.

## Links

- [CASA-ADR-0057-dialogue-situations-character.md](CASA-ADR-0057-dialogue-situations-character.md)
- [CASA-ADR-0010-control-zone-predict-attention-value.md](CASA-ADR-0010-control-zone-predict-attention-value.md)
- [CASA-ADR-0024-control-thalamus.md](CASA-ADR-0024-control-thalamus.md)
