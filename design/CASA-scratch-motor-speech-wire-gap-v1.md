# Scratch: motor speech — wire-gap checklist

**Status:** scratch — оператор + инженерный план  
**Date:** 2026-06-16  
**Parent:** [`CASA-ADR-0028-field-native-sensory-experience.md`](CASA-ADR-0028-field-native-sensory-experience.md), [`CASA-ADR-0026-multimodal-event-ingest.md`](CASA-ADR-0026-multimodal-event-ingest.md) (`mm_action`), [`CASA-ADR-0040-auditory-phonology-tract.md`](CASA-ADR-0040-auditory-phonology-tract.md), [`CASA-scratch-listen-wire-gap-v1.md`](CASA-scratch-listen-wire-gap-v1.md)

---

## Канон (одна фраза)

**Продукция речи = motor intent на поле → efferent `motor_speech` @ life tick → auditory self-imprint → surprise «хотел / услышал» → sleep consolidates. Не TTS-oracle.**

У человека нет TTS. Есть **артикуляторный motor** и **ухо, которое слышит себя**. Text reply (`partner_text`) — **параллельный symbolic efferent** (письмо), не замена phonation.

---

## Life tick — тот же reactor

```text
life tick @ T:
  afferent:  visual + listen + partner text (что активно)
  … percept @ T=0 → SN/CEN → surprise …
  efferent:
    symbolic:  compose → partner_text tract (есть)
    phonation: motor_plan → peripheral (L4) → self-listen imprint (нет)
  sleep: motor↔heard bridges
```

**Не** отдельный «режим говорящего». **Не** `reply_text → Kokoro`. Peripheral (vocoder / speaker) — только **исполнитель** motor units, как камера для RGB.

---

## Два efferent — не путать

| Efferent | `tract_id` | Субстрат | Статус |
|----------|------------|----------|--------|
| **Письмо партнёру** | `partner_text` | symbolic text | **есть** — `casa/body/text_tract.py` |
| **Речь (phonation)** | `motor_speech` | motor units → acoustic feedback | **нет** в hot path |

Символический compose (`subject_articulation`, slot compose) **не равен** речи: это графомоторика до того, как появится motor speech plan.

---

## Что такое «motor unit» (не wave, не TTS string)

Из ADR-0026 `mm_action` и ADR-0082:

| Поле | Смысл |
|------|--------|
| `motor.units[]` | токены **уже на поле** (`A:*` cochlear, `A:ph:*`, `lang.word.*` после bind) — **не** Python-меню в `speech_compose.py` |
| `canon.intent` | `imitate:…`, `label:…`, babble — из поля, не из LLM |
| `canon.said_plan` | что агент **намеревался** произвести (motor trace id) |
| `canon.heard_self` | что **ушо** imprint'нуло с self-listen window — не «Whisper сказал» в hot path |
| `canon.reward` | грубая обратная связь teacher / self mismatch |

**Shunt (запрещено как ядро):**

- `reply_text → TTS API → auditory ingest` — text bypass в ухо;
- commodity TTS batch для literacy primary (ADR-0040);
- ASR oracle «правильно произнёс» без cochlear self-imprint.

---

## Петля self-listen (симметрия listen wire)

| Listen (afferent, строим) | Motor speech (efferent, gap) |
|---------------------------|------------------------------|
| `aud.window.*` imprint | `motor.plan.*` / `motor.unit.*` episode |
| `percept.listen.active` | `percept.self.speech` + echo flag |
| coactive A+V | coactive **intent→sound→heard** |
| `bind_av_coactive_on_tick` | `bind_motor_heard_on_tick` (roadmap) |
| sleep `aud↔vis` | sleep `motor↔heard` |

Inbound Lalabook = **чужие** голоса. Outbound = **свой** аппарат. Bind lex↔sound asymmetry закрывается только когда **оба** контура честны.

---

## Замкнуто (не трогать без причины)

| Петля | Evidence |
|-------|----------|
| Symbolic partner efferent | `body/text_tract.py`, `process_dialogue_on_tick` |
| Field compose (не paste) | `subject_articulation`, ADR-0081 |
| Unified life tick | `run_life_tick` → `run_learning_tick` |
| Passive auditory imprint | `auditory/imprint.py`, listen wire-gap |
| `mm_action` schema (design) | ADR-0026 sample JSON |
| ADR-0040: no commodity TTS literacy primary | design gate |

---

## Разомкнуто — checklist

### P0 — контракт и body wire (без peripheral)

| ID | Gap | Действие |
|----|-----|----------|
| **M0.1** | Нет `motor_speech` tract id в store | `casa/body/speech_tract.py` — mirror `text_tract`: efferent cue + pulse, `tract_kind: motor`, `store/body/speech/` |
| **M0.2** | Нет motor plan type | `casa/domain/motor_speech_plan.py` — `MotorSpeechPlan`: `plan_id`, `units[]`, `intent`, `tick` |
| **M0.3** | Нет verify gate | `tools/verify_motor_speech_loop.py` — synthetic babble: plan → stub peripheral → self-imprint → field tokens |

**Verify M0:** один macro tick с `_perceptual_turn.motor_active` + episode `motor.plan.*` + `aud.window.self-*` без TTS env var.

---

### P1 — life tick @ T=0 (motor efferent phase)

| ID | Gap | Действие |
|----|-----|----------|
| **M1** | Motor не в orchestrator | После compose / disposition: `maybe_motor_speech_on_tick(state, wm, reply_plan)` — **optional** efferent, не всегда (= молчание ok) |
| **M2** | Percept без self-echo | `perceptual_prepare_life_tick`: merge `motor_stream` hints when self-listen window present |
| **M3** | Surprise только text | `control` сравнивает `motor.plan` vs `aud.self` digest ids на том же tick |
| **M4** | Impulse blind | `nervous/motor_speech_hooks.py` — channel `motor_compose` + `self_listen` |

**Принцип:** phonation efferent **после** CEN intent, **до** или **вместе с** text efferent — partner может получить текст **и** агент слышит себя; или только babble без текста.

---

### P2 — self-listen imprint (замыкание уха)

| ID | Gap | Действие |
|----|-----|----------|
| **M5** | Self wav не imprint | `imprint_auditory_window(..., scene_id=self, window_id=plan_id, source=self)` — тот же codec, что Lalabook |
| **M6** | Hippo без motor links | episode links: `motor.plan.X co_occurs aud.window.self-X` |
| **M7** | Sleep без motor↔heard | `auditory/bridge_motor.py` → `extract_emergent_motor_heard_bridges` (mirror `bridge_vis`) |
| **M8** | Online bind only sleep | `bind_motor_heard_on_tick` в orchestrator when `percept.self.speech` |

---

### P3 — curriculum (не Lalabook)

| ID | Gap | Действие |
|----|-----|----------|
| **M9** | Babble stage | `tools/motor_babble_pilot.py` — random units, reward «был звук», no lex |
| **M10** | Echo / imitate | `mm_action` ingest: teacher word → agent motor repeat → self-listen mismatch |
| **M11** | Label | vis/lex anchor + motor label attempt (после A3 inbound stable) |
| **M12** | Dialogue speech | compose → **motor plan** derived from slot material, **not** text→TTS |

**Порядок:** M9 → M10 → inbound A3 teacher pilot (ADR-0040) → M11 → optional symbolic text parallel.

---

### P4 — peripheral (L4 only)

| ID | Gap | Примечание |
|----|-----|------------|
| **M13** | Stub vocoder | Lab: units → simple synth **вне** hot path learning; field sees only imprint |
| **M14** | open-voice-tts | ADR-0040 outbound expression — **после** pronunciation gate, не literacy primary |
| **M15** | Mic loopback | Optional hardware self-listen; same imprint path as file stub |

---

## Матрица «кто с кем говорит»

```text
СЕЙЧАС:
  partner text ──► percept(text) ──► compose ──► partner_text efferent (string)
  Lalabook     ──► listen imprint ──► life tick (passive)

ЦЕЛЬ:
  compose intent ──► motor_speech plan (units on field)
                 ──► L4 peripheral (optional) ──► air
                 ──► auditory self-imprint (same tick or T+1)
                 ──► percept.self.speech + surprise
                 ──► sleep motor↔heard
  partner text ──► (parallel) symbolic efferent — не подменяет phonation
```

---

## Go / no-go перед pilot babble

| Критерий | Порог |
|----------|-------|
| Listen Stage 0 | G0 listen wire-gap зелёный на store |
| M0 tract | `body/speech/` cue roundtrip без crash |
| M1–M2 | one life tick: motor hints in digest before SN/CEN |
| M5–M6 | self-listen episode + link on field |
| No TTS in hot path | audit: zero `tts`/`kokoro` import in orchestrator/dialogue hot path |
| Agency gate | phonation из disposition/CEN/compose — **не** operator `enabled` flag |
| M9 babble | 20 plans → 20 self-windows → sleep ≥1 motor↔heard edge |

---

## Файлы (критические, roadmap)

| Файл | Роль |
|------|------|
| `casa/body/speech_tract.py` | efferent motor cue (new) |
| `casa/domain/motor_speech_plan.py` | plan + units (new) |
| `casa/prisms/motor/speech_compose.py` | field → unit sequence (new) |
| `casa/prisms/auditory/imprint.py` | reuse for self-listen |
| `casa/prisms/auditory/bridge_motor.py` | sleep motor↔heard (new) |
| `casa/prisms/perceptual/zone.py` | `motor_stream` / self-echo merge |
| `casa/prisms/tick/orchestrator.py` | motor efferent + bind hook |
| `casa/nervous/motor_speech_hooks.py` | impulse (new) |
| `tools/verify_motor_speech_loop.py` | gate (new) |
| `tools/motor_babble_pilot.py` | M9 lab (new) |
| `tools/ingest_mm_actions.py` | mm_action batch (new or extend mm) |

---

## Связь с listen wire-gap

| Listen ID | Motor speech |
|-----------|--------------|
| W10 Listen → speech | **перенесено сюда** — Stage 1+, не Lalabook blocker |
| W11 A1 phon → lex | inbound A3 + outbound motor — **разные** контуры (ADR-0040) |
| passive listen | **requires** active motor for closed speech development |

---

## Не делать

- **TTS-oracle** — `reply_text → API → auditory` как обучение;
- **ASR-oracle** в hot path — «Whisper said you were correct»;
- **Отдельный speech reactor** — только efferent phase в `run_learning_tick`;
- **Commodity TTS mass bank** для literacy co-occurrence (ADR-0040);
- **Смешивать** symbolic text efferent и motor speech в один percept token без merge rules;
- **Ждать** perfect vocoder before babble — field + stub imprint first.

---

## Первый инженерный slice (рекомендация)

1. **M0.1–M0.3** — tract + verify stub loop (no real audio hardware).
2. **M5 + M6** — self-listen imprint from stub wav generator driven by units, not text.
3. **M1 + M2** — orchestrator hooks + percept merge.
4. **M9** — babble pilot on von-neumann lab store.

Text partner channel stays; add **phonation parallel**, not replacement.
