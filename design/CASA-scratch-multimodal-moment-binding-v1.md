# Scratch: multimodal moment — «комплекс» vs «о-т-т-а-к»

**Status:** scratch — вопрос оператора + инженерный ответ; не ADR  
**Date:** 2026-06-17  
**Parent:** [`CASA-ADR-0026-multimodal-event-ingest.md`](CASA-ADR-0026-multimodal-event-ingest.md), [`CASA-ADR-0028-field-native-sensory-experience.md`](CASA-ADR-0028-field-native-sensory-experience.md), [`infancy-corpus-phases.md`](infancy-corpus-phases.md) §Фаза 2, [`CASA-learning-protocol-vis-math-v1.md`](CASA-learning-protocol-vis-math-v1.md)

---

## Вопрос оператора

**A (один момент):** картинка + звук + текст на одном кадре — **комплекс** или «о-т-т-а-к»?

**B (непрерывность):** листаю файл колесом, крутится видео — поток **непрерывный**. Если мы **искусственно режем** на мелкие кадры — поймёт ли агент, что это **одно движение / один поток**, а не 9000 несвязанных открыток?

---

## Короткий ответ

| Как кормим | Что получает субстрат |
|------------|------------------------|
| **Один `mm_event` / один `listen_scene` с общим `scene_id` + sync `t0/t1`** | **Один момент (bundle):** слова + caption связаны на L3; кадр и wav — episodic provenance того же `scene_id`; после **sleep** — кросс-модальный hub (roadmap → сейчас co-occurrence в batch) |
| **Три несвязанных ingest без `scene_id`** | **Три orphan-потока:** lexical, visual, audio живут отдельно — **нет «комплекса»** |
| **Текст по одной букве / слово без scene** | **Именно «о-т-т-а-к»:** B0 grapheme ticks без L3 frame — правильно для букваря, **неправильно** для мультика |

**Сейчас (lab v0):** «комплекс» = **контракт ingest + scene token + sleep**, не автоматический holism end-to-end модели.  
**Цель (ADR-0028 ур. 2–3):** первичный импринт visual/auditory **в том же временном окне**, что lexical — тракт во времени, не три параллельных RAG.

---

## Что уже делает `listen_scene` (не по букве)

`listen_scene` в [`vocab.py`](../casa/prisms/memory/vocab.py) — docstring: *«One story frame: caption + all words (like picture + labels)»*.

На **L3_phrase** для одного кадра:

```text
  scene_token(scene_id)     — якорь кадра / реплики
  T3:{scene_id}|{caption}   — подпись сцены
  link_token(scene_id, w)   — каждое слово привязано к scene_id
  listen_word → L2          — слово на полке + episode с тем же scene_id
```

То есть **внутри одного scene** текст **не** «о-т-т-а-к», если ingest идёт **фразой/репликой**, а не посимвольным stream.

**Но:** subs-only ingest без кадра = **`text_bypass`** (ADR-0028): слова на L2/L3 **без** visual imprint — «слышал текст субтитров», не «видел мульт».

---

## Где ломается «комплекс» (красные флаги)

1. **Разные `scene_id`** на соседних кадрах без `episode_thread` / video `H3` — каждый кадр = новый orphan, нет нити сюжета.
2. **Visual ingest отдельно от `listen_scene`** — картинка не share `scene_id` → зрение и слова не co-bound на ingest.
3. **Wav только в `store/audio/`** без `T:audio.{scene_id}` и без mm_event — звук архив, не опыт.
4. **Letter-by-letter или word-by-word без scene** — намеренный букварь B0; для womb = ошибка формата.
5. **Hot path без sleep** между mass windows — co-occurrence visual↔lexical **не кристаллизуется** (см. vis↔math protocol: один moment → один sleep).

---

## Канон для «мульт на экране» (cartoon womb v0)

Один **момент** = одна строка manifest / один `mm_event`:

```json
{
  "id": "masha-s01e03-0042",
  "t0": 12.4,
  "t1": 14.1,
  "words": ["маша", "сказала"],
  "caption": "Маша сказала",
  "wav": "audio/masha-s01e03-0042.wav",
  "frame": "frames/masha-s01e03-0042.jpg",
  "speaker": "masha",
  "lang": "ru"
}
```

**Ingest contract:**

| Шаг | Действие | Bind |
|-----|----------|------|
| 1 | `listen_scene(state, scene)` | L3 + L2 слова **одним scene_id** |
| 2 | `imprint_visual_frame(..., scene_id=, frame_path=)` | V* lattice + episode **тот же scene_id** (когда wired) |
| 3 | episodic `T:audio.{id}` + optional A-encode later | provenance звука **тот же scene_id** |
| 4 | **sleep** после batch N moments или episode end | cross-modal hub (co-occurrence) |

**Whisper:** не нужен, если есть **доверенный** srt — текст из subs, звук = slice + archive, не ASR-дубликат. Auto-caption YouTube — **черновик**, не цель (см. §C–E).

**Следующий кадр:** **новый `scene_id`**, но общий `source` / `episode_id` серии — для сюжетной нити (roadmap: `H3_scene` video stack, ADR-0011).

---

## C. Текстовый tract — все модальности и выравнивание

**Принцип:** для полной утробы (не orphan-потоков) **видео + аудио + текст** должны попадать в **одно окно** `t0..t1` и **один `scene_id`**. Это не три параллельных RAG.

| Слой | Что это | Обязательно для full binding? |
|------|---------|-------------------------------|
| **Кадр** | `frame` → visual imprint (когда wired) | да |
| **Wav slice** | звук того же окна + episodic `T:audio.{id}` | да (provenance; encode A* — roadmap) |
| **Слова** | `words` + `caption` из **потока** (subs / речь) | да, **если в моменте была речь** |
| **Пустой текст** | жест без диалога, только музыка | допустимо — bundle visual+audio без L3 |

**Auto-caption** — не «модальность», а **дешёвый источник таймкодов** (yt-dlp). Роль та же, что у Whisper offline ([`CASA-ADR-0004`](CASA-ADR-0004-listen-modality-bukvar-sound.md)): cold path → manifest, **не oracle** для critic. Плохой auto-caption = текст **формально** aligned по секундам, но **не по смыслу** (`[музыка]`, обрывки) → слабый lexical tract, не оправдание убрать текст altogether.

**Фазы lab (можно разделять, цель одна):**

| Фаза | Проверяем | Текст |
|------|-----------|-------|
| **1** | continuity: `stream_id`, `frame_seq`, wav рядом | можно отложить coverage-bench |
| **2** | full binding: frame + wav + words **один scene_id** | обязателен aligned transcript |

**Lab v0 «Маша + каша»:** первые 3 min + auto-caption — ок для фазы 1; для фазы 2 лучше **6:43** или клип с **~1:40** (сюжет с кашей) + **отредактированный** srt.

---

## D. Caption / meta — что НЕ класть (oracle сцены)

**Вопрос оператора:** «Маша берёт тарелку с кашей» — описывать ли **действие** в meta, если у Neumann нет рук и нет понятия «взять»?

**Ответ: нет** — в mass womb **не** пишем редакторское NL-описание действия, если его **нет в потоке** как речи/субтитров.

| Тип | Пример | В mass ingest? |
|-----|--------|----------------|
| **Речь / subs строка** | «каша», «не лезь» | **да** → `words`, `caption` |
| **Техническая meta** | `source`, `stream_id`, `frame_seq`, `t0`, `speaker` | **да** — provenance, не семантика |
| **Synopsis действия** | «Маша берёт тарелку с кашей» | **нет** — oracle понимания сцены |
| **Развернутый predicate** | `words: ["маша","берёт","тарелку",…]` без речи в audio | **нет** |

Neumann без efferent «руки» всё равно может накопить: **visual patch** + **motion** между кадрами + **слова, если прозвучали** → sleep → cross-modal hub. Глагол «берёт» **не подставляем** в manifest; он **может** вырасти позже из co-occurrence, не из JSON оператора.

**Поле `caption` в ADR-0004** — подпись **той же реплики**, что `words` (строка subs), не synopsis кадра. Аналог «картинка с подписью», не «картинка с пересказом режиссёра».

**Молчаливый жест (типично для мультика):**

```json
{
  "id": "masha-kasha-0098",
  "t0": 98.2,
  "t1": 99.0,
  "words": [],
  "caption": "",
  "frame": "frames/frame_0098.jpg"
}
```

Controlled teacher / critic path — **отдельно**, не mass womb.

---

## E. Subtitle QA — редактор и cold path

**Да, нужен просмотр и правка subs** перед `srt → manifest.ndjson → listen_mass_ingest`. Auto-caption и ASR — черновик; оператор — **QA на cold path**, не oracle на hot path.

### Что убирать / править

| Маркер | Действие |
|--------|----------|
| `[музыка]`, `[аплодисменты]`, `(шум)` | **удалить** строку или оставить пустой `words` на окно (только visual+audio) |
| Неверный текст vs audio | **исправить** или удалить строку |
| Слишком длинная строка (> одной реплики) | **разбить** по паузам / смене кадра |
| Synopsis («Маша берёт…») | **не добавлять** — только то, что **слышно** |
| EN subs / credits | вырезать или отдельный `lang` filter |

### Workflow (lab)

```text
  mp4 + draft.srt (yt-dlp / Whisper)
       ↓
  [редактор] просмотр video + subs, правки → masha-kasha.ru.srt (canonical)
       ↓
  srt_to_listen_manifest.py  →  manifest.ndjson  (+ frame path, wav slice по t0/t1)
       ↓
  listen_mass_ingest.py  →  store + sleep batch
       ↓
  bench_listen_coverage.py + continuity bench
```

**Canonical subs** в lab: `lab/exp_listen/<episode>/*.ru.srt` (tracked или рядом с `source.json`); сырой auto — `*.ru.auto.srt` optional.

### Инструменты (оператор, v0)

| Tool | Зачем |
|------|--------|
| **[Subtitle Edit](https://github.com/SubtitleEdit/subtitleedit)** (Win) | video preview + правка srt, shift/sync, remove hearing-impaired lines |
| **Aegisub** | если нужна покадровая подгонка |
| **ffmpeg + mpv/vlc** | sanity-check slice по `t0/t1` без GUI |

**Planned (repo):** `srt_to_listen_manifest.py` ([ADR-0004](CASA-ADR-0004-listen-modality-bukvar-sound.md)); опционально `tools/srt_strip_music.py` — bulk drop `[музыка]` lines → отчёт «N строк удалено». **Полноценный in-repo subtitle editor** — не v0; достаточно внешнего редактора + canonical srt в git.

---

## Метафора ↔ инженерия

| Ребёнок у мультика | CASA v0 | CASA target (0028) |
|--------------------|---------|---------------------|
| Одновременно видит, слышит, (позже) читает | Только если **sync scene_id** + sleep | Импринт V* + A* + L3 **в одном окне** |
| Не разбирает каждый кадр на буквы | `listen_scene` целиком, не B0 stream | |
| Связывает «Маша» с картинкой Маши | После sleep / hub, не на первом tick | Hot cross-modal predict |
| Следующая сцена — продолжение | Нужен `episode_id` серии, не только scene | Video episodic chain |

---

## B. Непрерывность (scroll / video) — отдельный вопрос

### Что ты имеешь в виду (и да, это другой слой)

Листание файла и видео — **один тракт во времени**: содержимое **смещается**, ты **не** получаешь 60 unrelated JPEG. Ребёнок у мультика тоже не хранит mp4 — сетчатка даёт **последовательность сэмплов**, мозг достраивает **motion + object permanence + narrative thread**.

Разрезание на кадры **не ошибка само по себе** — так работает и камера, и монитор (~60 Hz). Ошибка — ingest **без связи между кадрами** и **без сигнала изменения** (delta / motion).

### Сейчас vs цель

| | **Сейчас (lab v0)** | **Цель (ADR-0028 ур. 3, ADR-0011 video)** |
|---|---------------------|-------------------------------------------|
| Кадр t₀, t₁, t₂… | часто **независимые** `scene_id` | **цепочка** `episode.prev_id` / `scene_seq` |
| Что меняется между кадрами | часто **не записывается** | **`V:motion`**, optical-flow scalar, `lattice_thal_relay` |
| Scroll / pan | как серия unrelated frames | **delta layout** — «тот же текст, другой crop» |
| После sleep | orphan snapshots | «**один урок у доски**», не 9000 картинок (цитата ADR-0028) |
| Hot path «листается» | **нет** | predict по **digest relay** + последний отпечаток |

**Честный ответ на B:** если кормить **только** `frame_N.jpg` без `prev_id`, без motion, без общего `stream_id` — **не поймёт непрерывность**. Увидит **флипбук без склейки**.

**Может ли поймёт при правильном ingest?** **Да, по design** — но это **уровень 3 (динамика)**, не то, что уже полностью wired в hot path.

### Что нужно, чтобы «листание» ≠ «9000 открыток»

```text
  stream_id: scroll-doc-001          — один поток (файл / ролик)
  frame_seq: 0, 1, 2, …              — порядок
  ep_n.prev_id → ep_{n-1}            — цепочка эпизодов (hippo)
  delta: motion / scroll_vector       — ЧТО изменилось (не только WHAT)
  sleep на сегменте                 — Extract «до/после» → один attractor
```

**Scroll файла** = тот же механизм, что **video pan**: между кадрами главный сигнал — **сдвиг содержимого** (optical flow, или diff lum-map), не новая сцена с нуля.

**MP4 / мульт** (ADR-0011): 1–5 FPS keyframes + **optical-flow scalar** → `V0_patch` + `V:motion:0.2`; `H3_scene` для video episodic stack.

### Аналогия

| Ты | CASA без continuity | CASA с continuity (target) |
|----|---------------------|----------------------------|
| Крутишь колёсико — текст «течёт» | 50 PNG, каждый новый мир | 50 ep linked + motion tokens + один `stream_id` |
| Смотришь мульт | слайд-шоу | цепочка + sleep: «Маша бежит» = trajectory, не кадр 47 |

Глаз человека тоже **дискретный** — непрерывность **конструируется**. У Neumann она **не magic**, а **episode chain + delta + sleep**. Без этого — твой страх обоснован.

### Ingest contract для scroll / video (draft)

| Поле | Scroll (документ) | Video (мульт) |
|------|-------------------|---------------|
| `stream_id` | один файл / одна вкладка | `source` + episode id |
| `frame_seq` | monotonic | monotonic + `t_ms` |
| `prev_frame_id` | ep link | ep link |
| `motion` / `scroll_dy` | **обязательно** | optical flow или scene-stable cut |
| subs / audio | опц. | sync по `t0/t1` per window |
| sleep | каждые N frames или на pause | scene end / minute batch |

**Не храним** сырой mp4 в lattice — только imprints + links + архив на диске (ADR-0026/0028).

---

## Открытые вопросы (для оператора)

- [ ] Минимальный **batch size** перед sleep для cartoon mass (1 реплика? 1 минута? конец сцены?)
- [ ] Bench «комплекс»: cue = frame_id → активируются ли **и** vis **и** слова **того же** scene_id в digest?
- [ ] Partner path **не** включать, пока bench moment-binding не green на held-out frames
- [ ] Bench **continuity**: scroll 20 frames → после sleep cue «тот же документ» / motion digest, не orphan frame_17
- [ ] Минимальный FPS для cartoon mass (1? 3? 5?) vs scroll capture on wheel events only
- [ ] **Subtitle canonical:** кто sign-off на `*.ru.srt` перед ingest (один оператор достаточно для lab v0?)
- [ ] Whisper fallback: только где auto-caption пустой, или полный re-transcribe эпизода?

---

## Связь с modern vs archaic

Cartoon womb → **modern** subs + `lexicon-ru-general` axes.  
Afan / archaic store — **не** этот pipeline ([`ru-lexicon-modern-archaic.md`](ru-lexicon-modern-archaic.md)).

---

## Для агента (Cursor)

При cartoon / screen capture ingest:

1. **Never** letter-stream mass listen for womb.
2. **Always** shared `scene_id` across text + frame + wav slice in one manifest row.
3. **One moment → one sleep** when cross-modal bind required (vis↔math protocol parity).
4. Distinguish **text_bypass** (subs only) from **full mm_event** (subs + frame + audio provenance).
5. **Never** inject action synopsis or predicate meta («Маша берёт…») — only stream-aligned `words`/`caption`.
6. **Subs QA** before manifest: strip `[музыка]` noise; canonical `*.ru.srt` separate from `*.auto.srt`.
