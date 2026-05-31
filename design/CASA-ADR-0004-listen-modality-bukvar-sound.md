# CASA-ADR-0004: listen-модальность — звук буквы → слог → слово

**Статус:** draft (обсуждение, 2026-05-30)  
**Область:** ССС / букварь / listen / acoustic cue / unified tick  
**Связано:** [`bukvar-text-modality.md`](bukvar-text-modality.md), [`second-signal-system.md`](second-signal-system.md), [`CASA-ADR-0003-emergent-forms-tags-predictor.md`](CASA-ADR-0003-emergent-forms-tags-predictor.md), [`predictor.md`](predictor.md), [`understanding-contract.md`](understanding-contract.md)

---

## Контекст

### Лестница уже есть в design, hot path — нет

[`bukvar-text-modality.md`](bukvar-text-modality.md) фиксирует порядок **B0→B3**:

```text
B0  буква / звуковой якорь     grapheme.*
B1  слог                      syllable.*
B2  слово                     lang.word.*
B3  фраза / диалог            phrase / ru.dialog.*
```

Lab v0 сильнее покрывает **глаза** (L0 grapheme, script, ortho, T9 по буквам) и **слово на L2**, чем **уши**.  
Обсуждение: добавить **modality=listen** в ту же petлю predict → critic → extract, не отдельный «аудио-словарь».

### Почему не «phoneme JSON» и не TTS-oracle

| Подход | Проблема |
|--------|----------|
| Ingest `phoneme: /mama/` на слово | RAG-фонетика; агент не «слышал», а прочитал IPA |
| Kokoro / generic TTS как **учитель** | артефакты просодии, один «идеальный» голос, critic учится шуму синтеза |
| Waveform end-to-end без слоёв | пропуск B0/B1; нет связи с уже построенным L0/L2 |

**Kokoro** (и аналоги) допустимы для **озвучки UI человеку**, не как **ground truth** в critic/extract.

### Связь с ADR-0003

- **Form** просодии (ударение, темп сцены) — emergent после surprise, не tag при рождении.
- **Particular** — episodic «как прозвучало здесь», не второй headword.
- **Predictor** активирует anchors; **Extract** крепит `E: syllable.* | part_of | lang.word.*` после correct.

---

## Решение (draft)

### 1. Listen — модальность, не подсистема

```text
  cue (listen)              predict                    critic
  ────────────              ───────                    ──────
  B0: «м» (звук буквы)  →   L0 grapheme basin     →   teacher / scene
  B1: «ма» (слог)       →   L2 word anchors       →   expect_in: мама…
  B2: «мама» (слово)    →   focus lang.word.*     →   match + hub
```

Тот же **tick-router**, что T9 / script / ortho / unified ([`unified_tick.py`](../tools/unified_tick.py) roadmap):

```text
  listen B0/B1  →  (optional script)  →  T9/word  →  ortho  →  hub
```

Listen **не заменяет** буквы: **структура цилиндра** остаётся B0→B3; **вход** при этом может быть любым — в том числе часами фоновой речи целиком.

### 1b. Фоновая речь — как у ребёнка (mass listen)

Ребёнок **не** начинает с диктовки слогов. Он **долго слышит поток речи** — родители, другие люди, сцена — **без экзамена** и без изоляции «только буква».

| Метафора | CASA |
|----------|------|
| Речь вокруг дома | **listen mass** — корпус, dialogue turns, ambient clips |
| Много голосов | episodic particular (`T:voice.mom`, `T:voice.stranger`) — не один TTS |
| Слышит **и** слова, **и** фразы | вход на **всех** уровнях одновременно; не «запретить word audio» |
| Не отвечает на каждый звук | mass **не** critic-oracle; coverage / activation, не read@1 |
| Потом лепет / babble | controlled tick B0/B1 — **отдельно** от mass, для lab и correct |

```text
  MASS (фон)                    CONTROLLED (учитель / lab)
  ──────────                    ───────────────────────────
  wav: мама, целые фразы   →    encode / weak activation на L2, L3
  родители, другие люди    →    episodic voice particular
  без expect / pass        →    НЕ flatten цилиндр в «мешок слов»

  позже: cue «ма» + critic  →  сужение B1→B2, Extract рёбер
```

**Различие критично:**

| | **Listen mass (вход)** | **Структура цилиндра (память)** |
|---|------------------------|----------------------------------|
| Слышит целые слова? | **да** — как ребёнок | — |
| Слой B0/B1 есть? | не обязан быть **в cue** | **да** — grapheme/syllable **в grid**, не только L2 |
| Ошибка | «только word flashcards в ingest» | «нет слогового compose» |
| Bench | coverage: token активировался N раз | tick: «ма» → anchors `мама` |

Mass **не противоречит** букварю: букварь — **как устроена память**, mass — **как устроен мир вокруг**. Ребёнок слышит «мама» тысячу раз **и** потом всё равно проходит слог/букву в лепете — у нас то же: L2 activation из фона + B0/B1 bridges из опыта/correct.

См. «утроба» в [`bukvar-text-modality.md`](bukvar-text-modality.md).

### 1c. Listen mass — технический pipeline (мультики, подкасты, корпус)

**«Пусть слушает фильмы»** = batch **cold ingest** в цилиндр, не streaming waveform в NCA. Ребёнок не хранит PCM — у нас поток речи → **сцены и слова на L2/L3**; wav — архив particular.

#### Три слоя

```text
  [1] МЕДИА (вне цилиндра)       [2] COLD INGEST (batch, offline)    [3] ЦИЛИНДР (hot encode)
  ────────────────────────       ────────────────────────────────    ───────────────────────
  mp4 / mkv / podcast mp3   →    ffmpeg → wav chunks (optional)   →   listen_scene()
  субтитры .srt / ASR       →    manifest.ndjson                  →   listen_word()
  разные голоса             →    scene {id, words, speaker, wav}  →   L2 + L3 votes↑
  audio/ в store            →    без critic                       →   episodic T:clip.*
                                   ASR/subtitles — не oracle          field_version++
                                                                      sleep → export ltm/
```

| Слой | Где живёт | В grid? |
|------|-----------|---------|
| **Медиа** | `store/audio/` (gitignore), torrents, локальный диск | **нет** |
| **Manifest** | `store/listen_mass/manifest.ndjson` | указатели, не bytes |
| **Encode** | `listen_word` / `listen_scene` ([`vocab.py`](../tools/vocab.py)) | **да** — `W:`, `L3:` scene links |

**v0:** digest и predict **не** читают waveform. Клип `wav` — для человека, replay lab и episodic `T:audio.{clip_id}`; активация слова — как при «услышал смысл» через **токены**, не FFT.

#### Hot path encode (уже есть)

```python
listen_scene(state, {
    "id": "masha-s01e03-0042",
    "caption": "Маша сказала",
    "words": ["маша", "сказала"],
    "punctuation": [],
})
# → listen_word per token + _listen_scene_on_l3 (L3_phrase links)
```

| API | Что делает | Critic |
|-----|------------|--------|
| `listen_word` | L2 `W:` + concept votes, optional episodic | **нет** |
| `listen_scene` | L3 scene token + word links + punctuation | **нет** |
| `listen_tick` (roadmap) | predict → critic на cue | **да** |

Mass ingest = миллионы вызовов `listen_scene` с `copies=1`, **без** `expect` / pass.

#### Manifest (cold path contract)

Одна строка NDJSON на реплику / субтитровую строку:

```json
{
  "id": "masha-s01e03-0042",
  "source": "masha-medved-s01e03",
  "kind": "dialogue",
  "caption": "Маша сказала",
  "words": ["маша", "сказала"],
  "punctuation": [],
  "speaker": "masha",
  "lang": "ru",
  "wav": "audio/masha-s01e03-0042.wav",
  "t0": 12.4,
  "t1": 14.1
}
```

| Поле | Обязательно v0 | Назначение |
|------|----------------|------------|
| `id`, `words` | **да** | scene_id + tokenize для `listen_scene` |
| `caption` | желательно | L3 `T3:{id}\|caption` |
| `speaker` | нет | episodic `T:voice.{speaker}` (roadmap) |
| `wav`, `t0`, `t1` | нет | архив + будущий replay; **не** в lattice v0 |
| `lang` | нет | маршрутизация RU/EN shard при bilingual mass |

#### Источники mass input

| Источник | Cold path | Примечание |
|----------|-----------|------------|
| **Мультики / фильмы** | `.srt` / `.ass` → manifest; ffmpeg режет wav по `t0/t1` | dialogue уже сегментирован |
| **Подкасты** | Whisper / vosk **offline** → предложения → manifest; diarization → `speaker` | ASR **не** в predict loop |
| **Текстовый корпус** | Afan / folk `.txt` шарды → построчно `listen_scene` | **тот же encode**, без wav; аналог «утробы» уже сегодня |
| **Human clips** | короткие wav + ручной transcript | critic lab, не mass |

ASR и субтитры — **OCR для уха**: переводят медиа в сцены для ingest, **не** ground truth для critic (ошибки ASR не должны обучать oracle).

#### Layout store (listen mass)

```text
sss-ru-lexicon/              # или sss-listen-mass/
├── ltm/                        # ship после export_ltm_pack
├── nca/
├── audio/                      # .gitignore — сырые клипы
├── listen_mass/
│   ├── manifest.ndjson         # сцены (append-only ingest log)
│   ├── sources.json            # cartoon X, podcast Y, corpus Z
│   └── coverage.json           # token → hear_count (bench output)
└── field_state.json            # lab rebuild из ltm
```

Episodic (hippo), не tag в bootstrap:

```text
T:audio.masha-s01e03-0042  |  heard_in   |  scene.masha-s01e03-0042
T:voice.masha              |  speaker_of |  …
```

#### Режимы прогона

| Режим | Действие | Critic | Bench |
|-------|----------|--------|-------|
| **mass ingest** | walk manifest → `listen_scene` | нет | — |
| **coverage** | после N часов корпуса | нет | token ∈ digest, count ≥ threshold |
| **controlled** | `listen_tick` B0/B1/B2 | да | «ма» → anchors |

Мультики/подкасты — **только mass + coverage**. Экзамен — отдельно, на вырезках или symbolic cues.

#### Что **не** делать в mass pipeline

| Плохо | Почему |
|-------|--------|
| Waveform / mel в lattice | вне CASA; нет z-bridge B0/B1 |
| Kokoro / TTS как mass source | один голос; critic учится артефактам |
| ASR в hot path predict | ошибки ASR = ложный oracle |
| Ingest только `listen_word` без scene | теряется L3 / B3 контекст фразы |
| Word-only flashcards с диска | см. обоснование § word-only bootstrap |

#### Planned tools (cold path)

| Tool | Роль |
|------|------|
| `listen_mass_ingest.py` | manifest.ndjson → `listen_scene` / checkpoint / `field_version` |
| `srt_to_listen_manifest.py` | `.srt` → manifest (+ optional ffmpeg slice) |
| `bench_listen_coverage.py` | после mass: headword / scene activation counts |
| `lab/exp_listen/` | один эпизод + cues для controlled tick |

**Минимальный v0 без wav:** субтитры → manifest → `listen_mass_ingest` — encode работает **сегодня** через существующий `listen_scene`.

**Итог одной строкой:** накачать агента «мультиками» технически значит — offline собрать manifest из субтитров или ASR, прогнать batch `listen_scene` в store, замерить coverage; wav кладём рядом для архива и будущего replay, но **в lattice v0 не кладём**.

### 2. Где на поле

| Ступень | Lattice | concept_id (v0) | Cue в lab |
|---------|---------|-----------------|-----------|
| B0 | `L0_grapheme` | `grapheme.cyrl.м` | символ «м» или clip `м.mp3` |
| B1 | `L1_syllable` | `syllable.ма` | «ма», «мам» |
| B2 | `L2_word_*` | `lang.word.мама` | полное слово (audio или symbolic) |

**Z-bridge** (уже в stack): compose слог из grapheme, слово из слогов — тот же паттерн, что z-мосты в [`sss-multi-lattice-z.md`](sss-multi-lattice-z.md).

**Не в bootstrap:** `phoneme.*`, `#Syllable`, IPA-strings как истина.

### 3. Teacher contract (listen)

| Роль | Источник | Статус |
|------|----------|--------|
| **Critic / correct** | учитель, сцена, minimal-pair clip | oracle |
| **Listen mass** | фоновая речь: родители, другие голоса, корпус, целые фразы | вход listen, **не** ответ; **не** только слоги |
| **TTS (Kokoro и др.)** | UI, demo | **не** oracle для critic |
| **Symbolic cue v0** | строка слога «ма» | lab stub; mass wav — параллельно, не вместо |

Просодия (ударение, пауза, «как в этой фразе») — **Form + R:context.\***, выводится после mismatch, как ortho Process в ADR-0003 §7.

### 4. Lab phases (предлагаемый порядок)

| Фаза | Cue | Bench | Аудио |
|------|-----|-------|-------|
| **L0** | `listen_tick`: «м» → grapheme basin | symbolic | нет |
| **L1** | «ма» → T9-like anchors (`мама`, …) | symbolic | нет |
| **L2** | «мама» → focus + hub | + linked boot | optional |
| **L3** | manifest: **ambient** + dialogue (human, multi-speaker) | coverage L2/L3 | wav, no critic |
| **L4** | minimal pairs (stress) → Extract | surprise | human |

**Mass до controlled:** сначала encode фонового корпуса (слова и фразы в потоке); lab ticks B0/B1 — на symbolic или вырезках, не вместо «утробы».

Параллель: PNG cursive ([`grapheme-glyphs/`](../lab/exp_bilingual/grapheme-glyphs/)) — **глаз**; audio manifest — **ухо**; один `concept_id`, два visual/acoustic particular.

### 5. Bilingual

- Звук **не выбирает язык** сам: co-activation со **script** basins (latn/cyrl) и L2 shard (`L2_en_word_*` vs `L2_word_*`).
- Hub **entity** связывает *слова* разных языков, не «один звук на двоих».
- EN `mother` и RU `мама` — разные acoustic surfaces, один hub (как `cow`/`корова`).

### 6. Открытые вопросы

| # | Вопрос | Склонение draft |
|---|--------|-----------------|
| Q1 | Отдельная lattice `L0_acoustic` vs reuse L1? | v0: **L1 syllable** + L0 grapheme; отдельный acoustic lattice — v2 если нужен timbre |
| Q2 | Embedding waveform или только symbolic? | v0 **symbolic**; wav = external cue id в manifest, не в hot path digest |
| Q3 | Extract edge `syllable→word` автоматически после pass? | да, по аналогии ortho Extract; не в ingest |
| Q4 | ASR как critic для v3? | только если ASR **не** обучаем на том же TTS; иначе тот же шум |
| Q5 | Связь listen B0 с ScriptS PNG | optional `E: grapheme.* \| cursive_glyph \| file.png` — visual particular, не tag |
| Q6 | Mass = только слоги или целые клипы? | **целые клипы и фразы**; слоги — для controlled lab/correct |
| Q7 | ASR в pipeline? | **только cold ingest**; manifest = текст сцен, не live decode |
| Q8 | Отдельный store для mass? | optional `sss-listen-mass`; merge в lexicon через export/import ltm |

---

## Обоснование

**Фоновая речь (родители, мультики, подкасты) и word-only bootstrap — разные вещи.** Ребёнок часами слышит целые фразы и чужие голоса — это нормальный **вход**. Мы **не** запрещаем word-level audio в mass ingest: субтитры мультика или transcript подкаста → `listen_scene` → L2/L3. Отвергаем другой край: **единственный** способ залить язык — flashcards целых слов с диска, без grapheme/syllable в цилиндре и без z-bridge compose. Mass «утроба» и иерархия B0→B3 **совместимы**: поток речи кодируется сценами; слог и буква достраиваются controlled tick и Extract после лепета.

| Альтернатива | Почему отклонена |
|--------------|-------------------|
| Phoneme tags в ingest | не emergent; не «слышал» |
| Kokoro как teacher | плохая просодия; critic учится артефактам |
| **Только word-flashcards в ingest** (плоский L2, без B0/B1 в цилиндре) | память = мешок слов; нет compose слог→слово — **не** «запрет слышать слова фоном» |
| Waveform / mel в lattice hot path | вне UC; нет связи с B0/B1 compose |
| ASR в predict/critic loop | ошибки распознавания = ложный teacher |

**Уточнение:** word-level **audio как mass input** (родители, диалог, ambient) — **норма**, как у ребёнка. Отклоняем **word-only bootstrap**: когда единственный способ залить язык — целые слова с диска, без слоёв grapheme/syllable и без z-bridge compose.

---

## Последствия

### Design

- Расширить [`predictor.md`](predictor.md) таблицу модальностей: `listen` (B0/B1/B2 cues).
- [`unified_tick.py`](../tools/unified_tick.py): slot `listen` перед T9 (roadmap); T9 канон — ADR-0006.
- [`bukvar-text-modality.md`](bukvar-text-modality.md): ссылка на этот ADR как решение по **teacher** и **TTS**.

### Lab (когда пойдём в код)

**Controlled tick:**

- `listen_tick.py` — symbolic cue, без Kokoro.
- `bench_listen_bukvar.py` — «ма» → `мама` in anchors.

**Listen mass (cold path):**

- `listen_mass_ingest.py` — manifest → `listen_scene` batch.
- `srt_to_listen_manifest.py` — субтитры мультиков → manifest.
- `bench_listen_coverage.py` — coverage после mass corpus.
- `lab/exp_listen/` — manifest + optional `audio/` + controlled cues.

### Не делаем в draft

- Kokoro в critic path.
- Waveform encode в lattice (mass v0 = symbolic scene ingest).
- ASR в hot path predict/critic.
- Пропись m↔т confusable lab (отдельная история от print homoglyphs).
- End-to-end neural listen без B0/B1.

### B3 listen — тот же gap, что и write W3

Lab v0 целится в B0/B1/B2 (буква → слог → слово). **Предложение / фраза целиком** на listen — как write W3: `L3_phrase` и `ru.dialog.*` в design есть, **bench нет**. См. ADR-0005 §5b и `bukvar-text-modality.md` (B3 gap).

---

## Verification (когда lab появится)

**Controlled:**

- [ ] B1 cue «ма» → `мама` in anchors (RU L2).
- [ ] B0 «м» → `grapheme.cyrl.м` activation (L0).
- [ ] Unified tick: listen + script + T9 на одном prefix (где применимо).
- [ ] TTS **не** вызывается в bench critic.
- [ ] После teacher correct — edge `syllable.ма | part_of | lang.word.мама` на L3 (extract lab).

**Listen mass:**

- [ ] manifest 1k+ scenes → `listen_mass_ingest` без critic errors.
- [ ] coverage: held-out headword из корпуса активен в digest после mass.
- [ ] L3 scene links присутствуют (не только orphan `listen_word`).
- [ ] wav optional: ingest green с manifest **без** wav полей (srt-only).

---

## Связанные решения

- **ADR-0003** — emergent Form, Process, не tags в ingest.
- [`CASA-ADR-0004-listen-modality-bukvar-sound.md`](CASA-ADR-0004-listen-modality-bukvar-sound.md) — listen (вход).
- [`CASA-ADR-0005-write-modality-motor-compose.md`](CASA-ADR-0005-write-modality-motor-compose.md) — write / motor (выход).
