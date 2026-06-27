# CASA-ADR-0088: Hippocampus quad-mode — wake, consolidate, integrate, idle micro (episodic connectivity)

**Status:** proposed (draft)  
**Date:** 2026-06-25  
**Provenance:** оператор (Света) + агент — после FSR (модальности, listen wire, W5b); следующий эпик: **связность эпизодов + понимание** (не gate колготок)  
**Область:** `prism_hippo` (P2 episodic), `run_sleep`, **life tick** (orchestrator hot path: listen, partner, curriculum, …), `lesson_moment`, UC held-out / retention  
**Связано:**

- [CASA-ADR-0047-hippo-surprise-concept-binding.md](CASA-ADR-0047-hippo-surprise-concept-binding.md) — bindable vs open_probe; per-episode merge
- [CASA-ADR-0023-sleep-scale-thin-first.md](CASA-ADR-0023-sleep-scale-thin-first.md) — batched `run_sleep`, preemptive scheduler
- [CASA-ADR-0009-experience-replay-retention.md](CASA-ADR-0009-experience-replay-retention.md) — interleaved replay, `retention@N`
- [CASA-ADR-0010-control-zone-predict-attention-value.md](CASA-ADR-0010-control-zone-predict-attention-value.md) — value-priority consolidate
- [prism-memory-architecture-v1.md](prism-memory-architecture-v1.md) § P2 — fast write wake → consolidate sleep
- [casa-wake-sleep-concept.md](casa-wake-sleep-concept.md) — Extract → Remember → Use
- [understanding-contract.md](understanding-contract.md) — смысл на поле, не RAG
- [CASA-learning-protocol-vis-math-v1.md](CASA-learning-protocol-vis-math-v1.md) — `bridges_emergent`, co-occurrence
- [CASA-scratch-track-integration-v1.md](CASA-scratch-track-integration-v1.md) — FSR vs meaning track
- KB CLS: `agent-notes/knowledge/worlds/ml-learning-dynamics/kb-ml-learning-dynamics-mcclelland-1995-cls-evidence-v1.md`

---

## Решение (одной фразой)

**Гиппокамп — четыре режима, не один «sleep»:** (1) **`hippo_wake`** — быстрая запись и границы эпизода на **life tick**; (2) **`sleep_consolidate`** (deep / SWS) — interleaved перенос в `ltm/`; (3) **`sleep_integrate`** (REM-like) — дальняя связность и сюжет; (4) **`idle_micro`** (light / DMN) — короткая фоновая досклейка между блоками **жизни** без полного sleep epoch. Понимание требует **всех четырёх на своих местах**; FSR free speech — выход поверх, не замена.

**Scope:** quad-mode относится ко **всему life loop** агента (orchestrator), не к operator-tool `listen_womb_tick` как единственному пути.

---

## Контекст

### FSR сейчас vs следующий эпик

| Слой | FSR (`fix/neumann-free-speech-recovery`) | Следующий эпик (этот ADR) |
|------|------------------------------------------|---------------------------|
| Percept | listen stream, cochlear_stub, visual imprint, W5b affect | эпизодные **границы** и кросс-модальный буфер на **life** |
| Память | hippo queue + `run_sleep` merge (Lane A/B, ADR-0047) | **quad-mode** + `bridges_emergent` на life stream, не только curriculum |
| Понимание | surprise ≠ сюжет; bind без `words[]` — осознанно | UC: связь кадр↔кадр, причинность, partner retell из поля |
| Gate | колготки G0, pytest | **не** «понял сюжет колготок» |

Инцидент `lesson_moment` (2026-06-02): без **co-occurrence** visual+math в одном hippo batch → `bridges_emergent: 0`; с moment → `2`. Consolidate работает; **integrate** и **wake indexing** на общем life path — нет.

### Что уже есть в коде (не выдумывать заново)

```text
life tick: surprise → append_episode (hippo)   ← частично wake
sleep:     run_sleep → strengthen / F0        ← consolidate (ADR-0047 Lane A/B)
           lesson_moment → batch → sleep      ← co-occurrence hook
replay:    ADR-0009 buffer after consolidate  ← interleaved rehearsal
```

**Пробел:** гиппокамп воспринимается как «очередь до сна». Для эпизодической связности на **бодрствовании** нужен явный контур **index/buffer**; для сюжета — контур **integrate**, не сводимый к `_strengthen_concept` per episode.

---

## Neuro analogy (non-claim)

Инженерная аналогия [Complementary Learning Systems](https://doi.org/10.1037/0033-295X.102.3.419) (McClelland et al. 1995), см. KB card — **не** биологическая модель.

| Режим | Folk neuroscience | CASA роль |
|-------|-------------------|-----------|
| **Wake hippo** | pattern separation, episodic buffer, «что только что было» | index queue, episode boundary, cross-modal hold |
| **Sleep consolidate** | SWS, slow replay → neocortex, **interleaved** | `run_sleep` Lane A: strengthen; CLS малые шаги (ADR-0009) |
| **Sleep integrate** | REM-like recombination, distant binding | link episodes, narrative stitch, `bridges` across time |
| **Idle micro** | NREM2 / light sleep, DMN bursts, «переспать с задачей» | короткий фон между блоками life / curriculum; partial replay без full consolidate |

**Дисклеймер:** как ADR-0023 § Neuro — scheduling metaphor, не claim «как настоящий мозг».

---

## Четыре режима (normative)

### 1. `hippo_wake` — index on life tick

**Когда:** каждый **life tick** (listen percept, partner turn, curriculum step, …), `lesson_moment` **assemble** (до sleep).

**Делает:**

- `append_episode` / sensory imprint с **episode_id**, `tick_span`, modality tags
- **Episode boundary** — смена scene/chapter, `visual_delta`, silence gap, operator cue, смена activity
- **Cross-modal buffer** — удержание A+V (+ limbic snapshot) в одном «моменте» для последующего batch
- Bind classes (ADR-0047): `bindable_surprise` / `open_probe` — без изменения канона

**Не делает:** strengthen на lattice, F0 mint, долгосрочный merge.

**Probes (epic gate):**

- эпизод на life stream переживает **N** тиков без потери `episode_id` в journal/hippo meta
- два модальных канала одного момента → **один** `moment_id` (расширение `lesson_moment`)

### 2. `sleep_consolidate` — deep / SWS analog

**Когда:** `run_sleep`, `should_force_sleep_on_overload`, batched sleep (ADR-0023).

**Делает:**

- Lane A: per-episode `_strengthen_concept` / rule (требует bind, ADR-0047)
- Lane B: F0 emergent tail — mint **новых** pattern/bridge на поле из кластеров
- `compact_persist` → shipped `ltm/`; `sleep_promote` provenance (prism P0)
- Replay buffer archive (ADR-0009); value-priority (ADR-0010)

**Инвариант CLS:** consolidate **медленный** — батчи, interleaved replay; быстрый merge всего batch = риск перетереть структуру (K5 в KB card).

**Probes:**

- `bridges_emergent > 0` при co-occurrence в batch (уже на vis↔math; **target:** life listen stream)
- `hippo_pending` ↓ после sleep; `retention@N` (ADR-0009) не деградирует под life interference

### 3. `sleep_integrate` — REM-like analog

**Когда:** отдельная фаза **после** или **между** consolidate batches; не на каждом tick.

**Делает:**

- **Distant episode linking** — ребра между эпизодами / concept hubs across ticks (не только co-presence в одном batch)
- **Narrative stitch** — «удав ↔ колготки ↔ страх тепла» как **полевые** связи с provenance, не manifest `note` oracle
- **Recombinative replay** — sample из `replay_buffer` + hippo clusters с **perturbation** / route change (design v1: deterministic sample, не LLM)
- Опционально: `link_episode_to_mint` (ADR-0047 #5 planned)

**Не делает:**

- subs/OCR/ASR oracle на write
- подмена partner efferent скриптами (ADR-0081)
- LLM-in-sleep infer сюжета

**Probes:**

- held-out **связность**: cue из эпизода T−k → activate concept/edge из эпизода T (claims_nav OFF)
- partner retell: efferent ссылается на **provenance** прошлого эпизода (caregiving 5α wire), не шаблон

### 4. `idle_micro` — light / DMN analog

**Когда:** пауза между блоками **life** (activity gap, chapter boundary), reactor/orchestrator idle, operator «отпустила» без явного `run_sleep` full epoch.

**Делает:**

- **Короткий replay-бёрст** — 1–K эпизодов из hippo tail / hot_digest (не полный consolidate batch)
- **Incubation** — снижение arousal (`prism_control` / thalamus ADR-0024), predict loop без нового ingest
- **Pre-consolidate priming** — подготовка moment buffer к следующему `sleep_consolidate` (co-occurrence не теряется на границе блока)
- Yield CPU/I/O между тяжёлыми job (cooperative с ADR-0023 SleepJob)

**Не делает:**

- полный `_strengthen_concept` sweep (это consolidate)
- distant narrative link (это integrate)
- замену явного deep sleep при overload (ADR-0047 safety valve остаётся)

**Probes:**

- после idle между двумя сегментами life stream: `moment_id` continuity или явный handoff в journal
- idle не раздувает `hippo_pending` без bound episodes (cap как ADR-0023 backpressure)

**Реализация:** v1 design normative; код — **R7** (после R2–R3); до R7 допустим явный `run_sleep --batch-size small` как ops-замена.

---

## Поток (target architecture)

```text
WAKE (hippo_wake)
  life tick (listen | partner | curriculum | …)
    → episode boundary?
    → append_episode + moment buffer (A+V+limbic)
    → hot_digest / predict (P1) — без merge

IDLE (idle_micro) — между блоками life, опционально
  arousal ↓, micro replay burst (K episodes)
  → prime moment buffer / handoff journal
  → yield (ADR-0023 cooperative)

SLEEP JOB (scheduler ADR-0023)
  Phase A: sleep_consolidate (batched run_sleep)
    → strengthen bound episodes
    → F0 emergent / bridges in-batch
    → replay_buffer archive

  Phase B: sleep_integrate (separate CLI flag)
    → distant link pass
    → recombinative replay sample
    → journal: integration_report

WAKE (use)
  UC held-out / partner / free speech (FSR)
```

**Порядок v1:** consolidate **перед** integrate на том же store. **Idle micro** — между wake blocks life и **до** consolidate, не вместо overload sleep. Ablation: integrate-only без consolidate — lab negative control.

---

## API sketch (v1 — не блокер ADR)

| Surface | Semantics |
|---------|-----------|
| `sn.hippo_mode` | `wake` \| `consolidate` \| `integrate` \| `idle_micro` |
| `run_sleep(..., phase="consolidate")` | default; совместимость с v0 |
| `run_sleep(..., phase="integrate", max_links=K)` | новый путь |
| `append_episode(..., moment_id=, episode_id=)` | wake index |
| `close_episode_boundary(...)` | явная граница сцены / activity |
| `integration_report` | stderr / journal aspect |

**CLI lab:** `sss_sleep --phase consolidate|integrate|both|idle` (extends ADR-0023 flags).

---

## Roadmap

| # | Deliverable | Depends | Acceptance |
|---|-------------|---------|------------|
| R1 | ADR-0088 + navigator row | — | этот документ |
| R2 | `moment_id` + episode boundary on **life tick** | listen 0027, orchestrator | journal shows stable episode spans |
| R3 | `sleep_integrate`: distant link pass (deterministic, full) | R2, ADR-0047 | b004↔b029 link on ch00 pilot |
| R4 | `bridges_emergent` probe on life listen stream (not only vis↔math) | R2 | lab report >0 on pilot chapter |
| R5 | Integrate + consolidate ablation in UC bench | ADR-0009 | retention@N + link recall metric |
| R6 | Partner provenance sample in efferent | ADR-0081, 5α wire | bind cites `episode_id` / `concept_id` |
| R7 | `idle_micro` on life activity gap / orchestrator idle | R2, ADR-0023 | journal handoff; micro replay without full merge |

**Execution plan (full impl, not stub):** [CASA-scratch-phase0-quad-mode-implementation-v1.md](CASA-scratch-phase0-quad-mode-implementation-v1.md)

**FSR branch:** R2–R7 on `fix/neumann-free-speech-recovery` as **Phase 0 understanding**; kolgotki mass replay after duck test (b004↔b029).

---

## Non-goals

- Привязка quad-mode **только** к operator `listen_womb_tick` (womb — один из life ingest, не канон памяти)
- Четыре биологических симулятора сна (spindle/EEG/…) как отдельные продукты
- Beat model как runtime canon просмотра
- Oracle `words[]` / ASR / OCR для «понимания сюжета»
- Замена FSR motor/partner wire
- GPU merge loop (ADR-0023 non-goal)

---

## Связь с free speech (FSR)

Free speech = **motor + partner efferent** из накопленного поля. Без **integrate** агент может **реагировать** (affect, surprise) и **консолидировать** фрагменты, но не **связывать** эпизод в рассказ. FSR не закрывается «добавить слова в manifest» — только полевая связность + UC.

---

## Резюме для партнёра

| Вопрос | Ответ |
|--------|-------|
| Один sleep? | Нет: **consolidate** (в ltm) и **integrate** (между эпизодами) |
| Hippo только спит? | Нет: **wake** индексирует на life tick; **idle_micro** — лёгкий фон между блоками |
| «Deep» vs «ещё»? | Deep = consolidate; «ещё» = integrate (REM-like); light = **idle_micro** |
| Только womb? | Нет — **весь life loop** (listen, partner, curriculum, …) |
| Следующий эпик после FSR модальностей? | Да — quad-mode + probes выше |

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-25 | Draft ADR-0088 (оператор + агент, post-FSR modalities) |
| 2026-06-25 | Четвёртый режим `idle_micro`; rename `…-quad-mode-…`; scope = life, не womb |
| 2026-06-25 | Execution scratch phase0 full impl; roadmap R2–R7 = Phase 0 (operator) |
