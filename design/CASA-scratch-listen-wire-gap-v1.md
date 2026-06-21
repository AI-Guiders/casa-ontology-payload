# Scratch: listen / Lalabook — wire-gap checklist

**Status:** scratch — оператор + инженерный план (обновлено 2026-06-16)  
**Date:** 2026-06-20  
**Parent:** [`CASA-scratch-multimodal-moment-binding-v1.md`](CASA-scratch-multimodal-moment-binding-v1.md), [`listen_corpus/README.md`](../listen_corpus/README.md), ADR-0028, ADR-0060/0061/0063

---

## Канон life tick (2026-06-16)

**Life tick = все живые каналы на этом шаге → один percept → один TickOrchestrator → sleep только закрепляет.**

**Co_occurs A↔V — два слоя (не дублирование, а online + consolidate):**

| Слой | Когда | Что |
|------|-------|-----|
| **Online (life tick)** | `percept.av.coactive` + ids | `aud.window.*` + `vis.*` в digest; `bind_av_coactive_on_tick` → `E:aud\|co_occurs\|vis` на поле |
| **Sleep** | batch episodes | `extract_emergent_aud_vis_bridges` — добивает пропущенные пары / усиливает из hippo (cold ingest без life tick) |

Cold mass ingest без life tick: co_occurs в hippo links на imprint, lattice crosslink — на sleep. Replay/womb с life tick: bind **на том же шаге**, sleep потом reinforce.

Lalabook, partner, keyboard — разные **источники** на те же рельсы. Womb/stream — не отдельный runtime.

```text
stream @ t (frame + audio window)
  → imprint (prism_visual + prism_auditory)     # сырьё
  → perceptual_prepare_life_sensory (joint)       # thalamus
  → run_life_tick / TickOrchestrator              # predict / surprise / hippo
  → affect_after_listen_scene (theme bias)        # limbic, без OCR
  → sleep (batch) → A↔V bridges                   # консолидация
```

---

## Два «просмотра» — как понимать

| Фаза | Что происходит | Это re-download? |
|------|----------------|------------------|
| **A — Stage 0 (сейчас)** | Cold ingest: `listen_moment` → A0 + V + L3-якорь на `scene_id`, sleep каждые N сцен | Нет повторного YouTube — байты в `casa-listen-corpus/` |
| **B — после замыкания wire** | Тот же корпус **проживается** через life tick + replay tool | **Не** обязательно второй mass ingest; `listen_replay_scenes.py` |

**Уточнение:** у эмоций уже был audio-only ingest, сейчас идёт **дозапись visual** на те же `scene_id` — это не «второй мультик», а **дозамыкание модальности** на том же материале.

Полный re-ingest всего корпуса после wire — только если добавили **новое измерение** импринта (новый codec, affect tags). Нужен skip-by-`scene_id` или replay tool.

---

## Замкнуто (проверить, не переписывать)

| Петля | Gate / evidence |
|-------|-----------------|
| Один момент A+V+L3 | `tools/verify_listen_imprint.py --visual` |
| Bind без оракула | manifest `profile=bind`, нет `words[]`, нет subs |
| Beat timeline (paired/motion) | `listen_beat_model`, `apply_listen_beats`, annotator |
| `listen_moment` | `casa/prisms/memory/listen_moment.py` |
| Auditory imprint | `casa/prisms/auditory/imprint.py` → `prism_auditory` |
| Visual imprint | `casa/prisms/visual/imprint.py` → `prism_visual` |
| Joint percept + macro tick | `perceptual_prepare_life_sensory` → `run_life_tick` (`listen_womb_tick`) |
| Percept → digest | `merge_digest_with_perceptual_turn` в orchestrator |
| Sleep vis↔lex/math | `memory_prisms.run_sleep` → `extract_emergent_vis_*_bridges` |
| **Sleep A↔V** | `auditory/bridge_vis.py` → `extract_emergent_aud_vis_bridges` |
| Limbic theme (listen) | `affect_after_listen_scene` — collection/profile, не OCR |
| Impulse trace | `listen_moment` + **stream** `sensory_hooks` + orchestrator `percept_life` / `av_coactive` |
| Phase B replay | `tools/listen_replay_scenes.py` (life tick, skip unchanged FV) |
| Zones @ T=0 | `agents/.../agent-limbic-core`, percept, social… |
| Partner ↔ limbic | `intelligence/tick.py`, `dialogue_bind/binder.py` |

---

## Разомкнуто — checklist (порядок работ)

### P0 — доказать Stage 0 на реальном корпусе

- [ ] **G0.1** Multimodal ingest эмоций завершён: log → `scenes_with_visual: 16`
- [ ] **G0.2** `verify_listen_imprint.py --visual` на store с Lalabook frame
- [ ] **G0.3** В field: `A:scene:{id}` + `V:scene:{id}` + L3 anchor для одной главы
- [ ] **G0.4** `prism_auditory` с решётками (не только legacy `A0_*` в `prism_memory`)

**Команды:**

```powershell
python tools/listen_mass_ingest.py `
  --manifest "..\casa-listen-corpus\lalabook\emotions\ukt4kquicra\manifest.ndjson" `
  --store-dir agents/von-neumann

python tools/verify_listen_imprint.py --store-dir agents/von-neumann --visual
```

---

### P1 — sleep-петля на bind-корпусе (без words[])

| ID | Gap | Статус | Где |
|----|-----|--------|-----|
| **W1** | A↔V crosslink по `scene_id` на sleep | **done** | `auditory/bridge_vis.py`, hook в `run_sleep` |
| **W2** | vis↔lex слаб без L2 episodes | expected | мост через корпус РЯ + A↔scene |
| **W3** | Дубли `A0_*` в memory vs `prism_auditory` | open | `auditory/bootstrap.py`, migrate |

**Verify W1:** после sleep на сценах с A+V — edge `E:aud.window.*\|co_occurs\|vis.*frame.*` или hot context.

---

### P2 — аффerent listen → zones (без оракула)

| ID | Gap | Статус | Где |
|----|-----|--------|-----|
| **W4** | Perceptual joint visual+listen | **done** | `visual_stream` + `listen_stream`, `percept.av.coactive` |
| **W5** | Пассивный просмотр → limbic theme | **done** | `affect_after_listen_scene`, `listen_theme_cluster` |
| **W6** | Impulse trace listen | **done** | cold: `listen_moment`; stream: `sensory_hooks`; tick: `percept_life`, `av_coactive`, `vision_gate`, `affect_listen` |

**Принцип:** limbic delta от **жанра/коллекции** + co-bound A+V, не от расшифровки текста в кадре.

---

### P3 — проживание во времени (фаза B)

| ID | Gap | Статус | Где |
|----|-----|--------|-----|
| **W7** | Life reactor + stream | **done (v1)** | `listen_womb_tick` → imprint + percept + `run_life_tick` |
| **W8** | Idempotent replay | **done (v1)** | `tools/listen_replay_scenes.py` + `--replay-log` |
| **W9** | Нить серии между главами | open | L3 `episode_thread` между `scene_id` (roadmap H3) |
| **W7b** | Inbox `womb_replay` mode | open | `agent_inbox_runner` — hippo-only replay без video |

**Второй просмотр (фаза B):**

```powershell
# online stream (pilot)
python tools/listen_womb_tick.py --manifest ... --chapter 0 --start 8 --interval 0.5 --no-persist

# replay imprinted chapters through life tick
python tools/listen_replay_scenes.py --manifest ... --chapters 0 --replay-log tools/_replay_log.json
```

---

### P4 — efferent speech (отдельный wire-gap)

| ID | Gap | Примечание |
|----|-----|------------|
| **W10** | Listen → **motor speech** (не TTS) | [`CASA-scratch-motor-speech-wire-gap-v1.md`](CASA-scratch-motor-speech-wire-gap-v1.md) — Stage 1+ |
| **W11** | A1 phon → `lang.word.*` | Emergent lex **inbound** A3; outbound motor — отдельный контур (ADR-0040) |

---

## Матрица «кто с кем говорит»

```text
Stage 0 cold ingest:
  Lalabook frame+wav ──► listen_moment ──► prism_auditory + prism_visual + L3 anchor
                                    └──► hippo episodes (scene_id)
                                    └──► affect theme + impulse trace
                                    └──► sleep ──► A↔V + vis↔lex (weak)

Online / replay + partner (unified macro tick @ T=0):
  afferent (stream imprint / partner text / idle)
       └──► perceptual_prepare_life_tick (merge text + sensory)
       └──► digest + bind_av_coactive_on_tick
       └──► SN/CEN → surprise → hippo
       └──► process_dialogue (efferent reply only, if partner)
       └──► sleep периодически
```

---

## Go / no-go перед фазой B

| Критерий | Порог | Статус |
|----------|-------|--------|
| G0 все зелёные | 16/16 visual + auditory tokens | operator |
| W1 audit | ≥1 A↔V crosslink после sleep на тест-сцене | code ready |
| W4–W5 | joint percept + affect theme | **done** |
| W7 | life tick на stream pilot | **done** |
| W8 | replay 1 главу без дубля | tool ready |

---

## Файлы (критические)

| Файл | Роль |
|------|------|
| `casa/prisms/memory/listen_moment.py` | hub момента + impulse + affect |
| `casa/prisms/memory/memory_prisms.py` | sleep + emergent extract |
| `casa/prisms/perceptual/zone.py` | joint life sensory percept |
| `casa/prisms/auditory/bridge_vis.py` | sleep A↔V |
| `casa/prisms/affect/zone.py` | `affect_after_listen_scene` |
| `casa/domain/listen_womb_tick.py` | stream driver → life tick |
| `casa/prisms/memory/agent_life.py` | `run_life_tick` |
| `casa/nervous/listen_hooks.py` | cold ingest observability |
| `casa/nervous/sensory_hooks.py` | stream + bind + sleep impulse |
| `tools/listen_mass_ingest.py` | cold path |
| `tools/listen_womb_tick.py` | online stream + life tick |
| `tools/listen_replay_scenes.py` | phase B replay |
| `tools/verify_listen_imprint.py` | Stage 0 gate |
| `listen_corpus/lalabook.playlists.json` | корпус |

---

## Не делать

- OCR / subs → `words[]` на Lalabook bind
- Второй yt-dlp batch «для проживания»
- Template `if emotions: valence -= 0.5` — только theme/cluster hints + field evidence
- Отдельный «womb runtime» — только источник afferent на обычный macro tick
