# Scratch: listen / Lalabook — wire-gap checklist

**Status:** scratch — оператор + инженерный план  
**Date:** 2026-06-20  
**Parent:** [`CASA-scratch-multimodal-moment-binding-v1.md`](CASA-scratch-multimodal-moment-binding-v1.md), [`listen_corpus/README.md`](../listen_corpus/README.md), ADR-0028, ADR-0060/0061

---

## Два «просмотра» — как понимать

| Фаза | Что происходит | Это re-download? |
|------|----------------|------------------|
| **A — Stage 0 (сейчас)** | Cold ingest: `listen_moment` → A0 + V + L3-якорь на `scene_id`, sleep каждые N сцен | Нет повторного YouTube — байты в `casa-listen-corpus/` |
| **B — после замыкания wire** | Тот же корпус **проживается** через новые афференты: limbic bias, percept `listen`, reactor replay hippo, sleep-extract A↔V | **Не** обязательно второй mass ingest; предпочтительно **replay** уже лежащих эпизодов |

**Уточнение:** у эмоций уже был audio-only ingest, сейчас идёт **дозапись visual** на те же `scene_id` — это не «второй мультик», а **дозамыкание модальности** на том же материале.

Полный re-ingest всего корпуса после wire — только если добавили **новое измерение** импринта (новый codec, affect tags). Нужен skip-by-`scene_id` или отдельный replay tool.

---

## Замкнуто (проверить, не переписывать)

| Петля | Gate / evidence |
|-------|-----------------|
| Один момент A+V+L3 | `tools/verify_listen_imprint.py --visual` |
| Bind без оракула | manifest `profile=bind`, нет `words[]`, нет subs |
| `listen_moment` | `casa/prisms/memory/listen_moment.py` |
| Auditory imprint | `casa/prisms/auditory/imprint.py` → `prism_auditory` |
| Visual imprint | `casa/prisms/visual/imprint.py` → `prism_visual` |
| Sleep vis↔lex/math | `memory_prisms.run_sleep` → `extract_emergent_vis_*_bridges` |
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

| ID | Gap | Где | Действие |
|----|-----|-----|----------|
| **W1** | A↔V crosslink по `scene_id` на sleep | `memory_prisms.run_sleep` | Добавить `extract_emergent_aud_vis_bridges` (co-occurrence `aud.window.*` + `V:*frame*` + `scene.*`) |
| **W2** | vis↔lex слаб без L2 episodes | `bridge_lex.py` | Ожидаемо для bind; мост идёт через **корпус РЯ** + A↔scene, не через OCR |
| **W3** | Дубли `A0_*` в memory vs `prism_auditory` | `auditory/bootstrap.py`, migrate | Одноразовая migrate: auditory lattices → `prism_auditory` |

**Verify:** после sleep на 16 сценах — SQL/field query: crosslink edges с `relation=co_occurs` или `heard_in` между A и V на shared scene.

---

### P2 — афферент listen → zones (без оракула)

| ID | Gap | Где | Действие |
|----|-----|-----|----------|
| **W4** | Perceptual не знает `listen` | `perceptual/zone.py` `DEFAULT_FAN_OUT` | Модальность `listen_cartoon` → fan-out `linguistic` + `emotional` (low gain) |
| **W5** | Пассивный просмотр не трогает limbic | `affect/model.py`, новый hook | `affect_after_listen_scene(state, scene_id, caption_cluster)` — только **theme hints** из `collection` / chapter title, не OCR |
| **W6** | Impulse trace listen | `nervous/listen_hooks.py` | Уже есть; подключить из `listen_mass_ingest` (сейчас только verify) |

**Принцип:** limbic delta от **жанра/коллекции** (`emotions`, `bedtime`) + co-bound A+V, не от расшифровки текста в кадре.

---

### P3 — проживание во времени (второй «просмотр»)

| ID | Gap | Где | Действие |
|----|-----|-----|----------|
| **W7** | Life reactor не читает womb | `tools/agent_inbox_runner.py`, `body/text_tract.py` | Inbox mode `womb_replay`: hippo episodes `T:audio.*` / `V:scene.*` → tick без partner text |
| **W8** | Нет idempotent replay | новый `tools/listen_replay_scenes.py` | Replay by `scene_id` list из manifest; skip если `field_version` imprint unchanged |
| **W9** | Нить серии между главами | manifest `source` / `video_id` | L3 `episode_thread` edge между соседними `scene_id` одного video (roadmap H3) |

**Второй просмотр (фаза B):** `listen_replay_scenes.py` после W4–W7, не повторный yt-dlp.

---

### P4 — efferent (позже, не блокер Lalabook)

| ID | Gap | Примечание |
|----|-----|------------|
| **W10** | Listen → speech | Stage 1+; не ожидаем ответа на мультик |
| **W11** | A1 phon → `lang.word.*` | Emergent lex из звука; отдельный extract после A0 стабилен |

---

## Матрица «кто с кем говорит»

```text
СЕЙЧАС (Stage 0):
  Lalabook frame+wav ──► listen_moment ──► prism_auditory + prism_visual + L3 anchor
                                    └──► hippo episodes (scene_id)
                                    └──► sleep ──► vis↔lex (weak), vis↔math (N/A)

ПОСЛЕ P1–P3:
  hippo replay / womb tick ──► percept(listen) ──► emotional zone (theme bias)
                          └──► sleep ──► A↔V bridge
                          └──► (optional) impulse trace

УЖЕ РАБОТАЕТ (параллельно):
  partner text ──► percept(text) ──► limbic ──► bind ──► reply
```

---

## Go / no-go перед фазой B

| Критерий | Порог |
|----------|-------|
| G0 все зелёные | 16/16 visual + auditory tokens |
| W1 или ручной audit | ≥1 A↔V crosslink на тестовой сцене после sleep |
| W4–W5 в коде | percept `listen_cartoon` + affect hook без text oracle |
| W7 или W8 | replay tool отрабатывает 1 главу без дубля поля |

---

## Файлы (критические)

| Файл | Роль |
|------|------|
| `casa/prisms/memory/listen_moment.py` | hub момента |
| `casa/prisms/memory/memory_prisms.py` | sleep + emergent extract |
| `casa/prisms/perceptual/zone.py` | новая модальность |
| `casa/prisms/affect/model.py` | limbic после listen |
| `casa/nervous/listen_hooks.py` | observability |
| `tools/listen_mass_ingest.py` | cold path |
| `tools/verify_listen_imprint.py` | Stage 0 gate |
| `listen_corpus/lalabook.playlists.json` | корпус |

---

## Не делать

- OCR / subs → `words[]` на Lalabook bind
- Второй yt-dlp batch «для проживания»
- Template `if emotions: valence -= 0.5` — только theme/cluster hints + field evidence
