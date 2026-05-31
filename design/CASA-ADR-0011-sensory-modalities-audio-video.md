# CASA-ADR-0011: аудио / видео модальности, sensor-призма и мосты к тексту

**Статус:** proposed (design; lab — после Exp J green + fv=6 cartridge)  
**Дата:** 2026-05-31  
**Область:** первая сигнальная система (образ, звук, движение), codec/tokenizer, `prism_sensor`, control stack (DAN/SN/predict)  
**Связано:** [`second-signal-system.md`](second-signal-system.md), [`f0-math-logical-layer.md`](f0-math-logical-layer.md), [`experiment-l-concrete-to-abstract.md`](experiment-l-concrete-to-abstract.md), [`bukvar-text-modality.md`](bukvar-text-modality.md), [`CASA-ADR-0010-control-zone-predict-attention-value.md`](CASA-ADR-0010-control-zone-predict-attention-value.md), [`understanding-contract.md`](understanding-contract.md), [`multi-cylinder-memory.md`](multi-cylinder-memory.md), [`casa-cosmos-mapping.md`](casa-cosmos-mapping.md)

---

## Контекст (из диалога)

Если дать агенту **те же классы каналов**, что у человека, часть модальностей доступна относительно легко (зрение, аудио, частично тактильность), а часть — **пр practically нет** (запах, вкус как непрерывный сенсорный поток без специализированного «нос/язык» у железа).

CASA уже разделяет:

- **вторая СС (ССС)** — `L0…L3`, текст, знаки;
- **первая СС (roadmap)** — `vis.*`, `math.*`, сенсомоторика;
- **control (`prism_control`)** — DMN/SN/FPN/CEN + predict/DAN/value (ADR-0010).

**Пробел:** нет канонического контура **audio / video → tokens → hub → lang.** и нет **управляющих решёток**, которые выбирают *какую* модальность катить на тик.

**Инвариант (как Exp L):** сырые пиксели / waveform **не** в NCA v0. Внешний encoder → **токены на grid** (Cosmos **Tokenizer**).

---

## 1. Карта модальностей: что даём, что нет

| Канал | Человеку | Агенту v0–v1 | В поле CASA |
|-------|----------|--------------|-------------|
| **Текст** | чтение, речь (2-я СС) | ✅ keyboard, corpus, TTS | `L0…L3`, `lang.*` |
| **Статичное изображение** | зрение | ✅ file / webcam frame | `vis.*` + `E:` → `lang.*` (Exp L L2) |
| **Видео** | зрение + время | ✅ frame stack, низкий FPS | `vid.*` episodic → `vis.*` / `H3_scene` |
| **Аудио** | слух | ✅ mic, wav, TTS stream | `aud.*` → `grapheme.*` / `lang.*` (listen ADR-0004 roadmap) |
| **Тактильность** | кожа, пропrio | ⚠️ haptic API, gamepad — **символы** | `touch.*`, `motor.*` (ADR-0005 write) |
| **Вестибular / balance** | внутреннее ухо | ⚠️ IMU если есть | `motion.*` scalar tags |
| **Запах / вкус** | хеморецепция | ❌ нет датчика | только **`chem.odor.*` / `chem.taste.*`** как **символы** из текста или teacher («пахнет лимоном») |
| **Боль / голод** | interoception | ⚠️ симуляция | `intero.*` value tags для `lattice_value` |

**Правило:** отсутствие железа ≠ запрет на **понятие** в онтологии. Запах в CASA = **claim + hub**, как «ветер» до Exp L — не continuous olfactory tensor.

---

## 2. Архитектура: где живут audio / video

### 2.1 Три призмы + sensor buffer

```text
                    prism_control (CU)
                    DAN: active_modality + sparse lattice mask
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
  prism_sensor         prism_hippo       prism_memory
  (краткий буфер)      (эпизоды)         (LTM)
  ─────────────        ───────────        ─────────────────
  io_frame aud/vid     H3_scene (видео)   A0…A2 aud stack
  rolling window       H1_surface (звук   V0…V2 vid stack
  encode → tokens      cue)               L0…L3 SSS
                       consolidate ─────► hub E: cross-modal
```

| prism | id (новое / существующее) | Роль |
|-------|---------------------------|------|
| **`prism_sensor`** | **новое** (или расширение `prism_io` из multi-cylinder) | последние N ms / K frames; **write-only на wake**; не LTM |
| **`prism_hippo`** | существует | `H3_scene` для видео-эпизода; `H1_surface` для короткого аудио-cue |
| **`prism_memory`** | существует | долговременные **`A*`** / **`V*`** решётки + ССС |

Sensor-призма **не дублирует** DMN: DMN = «что знаем»; sensor = «что **сейчас** на входе».

### 2.2 Стеки первой СС (параллель F0 math, vis roadmap)

**Нейтральная ось T0…T3** ([`sss-layer-names.md`](sss-layer-names.md)) — те же роли, другой **профиль**:

#### Audio profile `A0…A2`

| z | lattice_id | Роль | Токены (пример) |
|---|------------|------|-----------------|
| **A0** | `A0_spectrum` | frame / mel / envelope | `A:bin:12`, `A:energy:0.7` |
| **A1** | `A1_phon` | phoneme / syllable / prosody | `A:ph:ma`, `A:prosody:rise` |
| **A2** | `A2_event` | событие, источник | `aud.event.door`, `aud.voice.human` |

#### Video profile `V0…V2`

| z | lattice_id | Роль | Токены (пример) |
|---|------------|------|-----------------|
| **V0** | `V0_patch` | patch / saliency map | `V:patch:3,7`, `V:motion:0.2` |
| **V1** | `V1_object` | object / part | `vis.animal.cow`, `vis.face.person` |
| **V2** | `V2_scene` | сцена, layout | `vid.scene.kitchen`, `vid.scene.farm` |

**Exp L `vis.*`** = канон **именованных якорей** на V1; статичная картинка — `V1` без temporal stack.

Machine-readable (roadmap): `design/sensor-lattice-stack.json`.

---

## 3. Tokenizer / codec (Cosmos parity)

| Вход | Encoder (вне hot path) | Выход на grid |
|------|------------------------|---------------|
| wav / mic | mel / lightweight ASR phoneme lattice | `A0` → `A1` placement via `sensor_codec.py` |
| PNG / SVG | (Exp L) file hash + optional patch embed | `V1` token + `vis.*` id |
| MP4 / webcam | 1–5 FPS keyframes + optical-flow scalar | `V0` motion + `V2` scene delta |
| teacher text | существующий `codec_grid` / SSS | `L0…L3` |

**Контракт:** encoder может быть **тяжёлым** (Whisper segment, small ViT) — но **offline / edge MCP**, не внутри каждого NCA step. Hot path читает **digest токенов**, как DMN digest сегодня.

---

## 4. Связь с текстовой модальностью (hub, не merge)

Тот же паттерн Exp L:

```text
  aud.event.door ──E──► lang.word.stuk
  vis.animal.cow ──E──► lang.word.korova
  A:ph:ma ──E──► grapheme.м + syllable.ма   (listen / букварь)
  vid.scene.farm ──E──► phrase.farm_visit   (B3, позже)
```

| Направление | Механизм | Орган |
|-------------|----------|-------|
| **sound → знак** | mass listen, без quiz | Extract → hippo → sleep → L0/L1 |
| **знак → образ** | teacher показывает картинку **после** слова | CEN bind + `E:` |
| **cross-modal surprise** | слышу «мама», visual пусто | **predict** error → SN → Extract |
| **articulation** | TTS / surface из digest | CEN + `surface` (не wav oracle) |

**Не делаем:** один L2 shard «и для звука и для букв» — разные решётки, мост **`z_bridge_aud_L0`** / **`f_bridge_A1_L1`**.

---

## 5. Отдельные зоны обработки (не «плоский hub»)

**Уточнение после ревью:** фраза «новые control-органы необязательны» относилась только к **маршрутизации** (DAN/SN/predict/value). **Сенсорная обработка** — отдельные **подсистемы-призмы**, как слуховая / зрительная / пространственная кора, а не побочный эффект text hub.

| Биология (грубо) | CASA (целевое) | Не смешивать с… |
|------------------|----------------|-----------------|
| A1/A2, слуховая кора | **`prism_auditory`** (`A0…A2` stack + NCA) | `L0…L3` ССС |
| V1/V2, ventral «what» | **`prism_visual`** (`V0…V2` + `vis.*`) | DMN digest |
| MT/V5, dorsal «where/how» | **`prism_spatial`** (`S0…S2`, см. §6) | F0 math symbols |
| intraparietal, глубина | **`S2_depth`** / disparity lattice | плоский `V1` patch id |
| superior colliculus, salience | **`lattice_sn`** (control) | — |
| FEF / dorsal attention | **`lattice_dan`** (control) | — |

```text
  prism_control          ← CU: куда смотреть, что катить, surprise
        │
        ├── prism_auditory   (A* lattices, own NCA train)
        ├── prism_visual     (V* lattices)
        ├── prism_spatial    (S* — 3D / ego / depth)
        ├── prism_memory     (SSS L*, F0 math, hubs E:)
        └── prism_hippo      (episodes H*, incl. H3 spatiotemporal scene)
```

**Control ≠ perception.** DAN говорит *«крути A1, не L2»*; но **содержимое A1** живёт в `prism_auditory`, не в control stack.

Каждая sensory-призма — тот же паттерн, что SSS: **отдельные решётки**, `model.pt` per shard при масштабе, `z_bridge` внутри модальности, **`x_bridge_*`** между призмами (aud↔vis, vis↔spatial).

---

## 6. Третье измерение: перестать видеть мир плоским

2D grid **на одной решётке** — инженерный субстрат CA (как 64×64 L2), **не** утверждение «мир плоский». 3D — **отдельный spatial stack**, не squeeze в xy картинки.

### 6.1 Бинокуляр / стерео (vision)

| Этап | Биология | Инженерно v0 → v1 |
|------|----------|-------------------|
| Два retina | left / right eye | `cam_left`, `cam_right` или synthetic stereo pair |
| Disparity | V1 → V2 depth cells | **`S0_disparity`**: tokens `S:d:0.12` (normalized depth per patch) |
| Surface / layout | dorsal stream | **`S1_surface`**: egocentric mesh / planes (coarse v0: `S:plane:floor`) |
| Object in space | «корова **там**» | **`S2_object_pose`**: `S:pose:cow@xyz` + `E:` → `vis.animal.cow` |

Rollout: два кадра → codec disparity map → **не** один `V1` token, а **мост** `v_bridge_V1_S0` → depth lattice. Monocular fallback: motion parallax + size cue (одна камера, несколько тиков).

### 6.2 Бинаural audio (слух)

Симметрично зрению:

| | Vision | Audio |
|---|--------|-------|
| Два входа | L/R eye | L/R mic / HRTF |
| Inter-channel cue | disparity | **ITD/ILD** → `A0_binaural` |
| Space | `S2_object_pose` | **`A2_localization`**: `aud.src@az,el,d` |
| Bind | vis ↔ spatial | aud ↔ spatial (`a_bridge_A2_S2`) |

### 6.3 Пространство ≠ текст

«Корова слева» — не только `lang.word.korova` + hint, а **`S2` + `E:`** к `vis.*`. Язык **именует**; spatial **размещает**. Букварь (2-я СС) подключается **после** или **параллельно**, не заменяет dorsal stream.

### 6.4 Hippo для 4D (время + место)

`H3_scene` расширяется: не только dialogue turn, а **spatiotemporal episode** — «дверь хлопнула **слева**, потом шаги **сзади**». Consolidate → `S2` + `A2` + `V2` в memory, не flatten в одну строку.

Machine-readable (roadmap): `design/spatial-lattice-stack.json`.

---

## 7. Управляющая призма (`prism_control`) — только маршрутизация

ADR-0010: control **не заменяет** auditory/visual/spatial cortex; он **оркестрирует** их.

### 7.1 Роли control stack по модальностям

| lattice | Мультимодальная роль |
|---------|----------------------|
| **`lattice_dan`** | **modality spotlight**: `{text \| aud \| vid \| math}` + sparse mask **внутри** стека (какие `words-ru-*` / `A1_phon` / `V1_object`) |
| **`lattice_sn`** | bottom-up salience: audio onset, motion spike, novel object → gate |
| **`lattice_predict`** | cross-modal rollout: «если сцена farm → ожидаю aud.event.cow» vs observed |
| **`lattice_value`** | эмоциональная просодия, успех teacher, страх/ surprise → replay weight |
| **`lattice_fpn_wm`** | holds **active_modality** + stack of subgoals («сначала listen, потом name») |
| **`lattice_cen`** | act: TTS speak / point vis / write — **после** predict |

### 7.2 Новые мосты (P10–P13, design)

| bridge | from → to | Несёт |
|--------|-----------|--------|
| **P10** | sensor → SN | novelty / onset digest |
| **P11** | DAN → sensor + memory | **which stack** to encode this tick |
| **P12** | predict → SN | **cross-modal** prediction error |
| **P13** | memory hub → DMN | merged concept_ids from `E:` (text+vis+aud) |

P1–P9 сохраняются; P10–P13 — **надстройка**, не ломает control-lab.

### 7.3 Unified tick (concept)

```text
  T_wake:
    1. sensor_codec (if io present) → prism_sensor tokens
    2. DAN: pick modality + sparse lattices
    3. DMN read (masked) + predict rollout
    4. SN: salience ∪ prediction error
    5. FPN → CEN → act (surface / TTS / bind E:)
    6. wrong/correct → prism_hippo
```

---

## 8. Listen vs «металлический голос»

Два слоя, не путать:

| Слой | Что | CASA |
|------|-----|------|
| **Перцепция** | слышит teacher / mic | `A0→A1`, Extract, **без** TTS oracle |
| **Продукция** | говорит наружу | TTS MCP (Kokoro и т.д.) = **actuator**, не память |

Живой голос — качество **actuator + prosody tags** (`A:prosody:*`) на поле, не сырой PCM в LTM.

Roadmap listen: [`bukvar-text-modality.md`](bukvar-text-modality.md) «утроба», CASA-ADR-0004 (mass audio → grapheme).

---

## 9. Запах и «недоступные» каналы

```text
  Teacher: «Пахнет лимоном»
       │
       ▼
  Extract → chem.odor.lemon (symbolic concept_id)
       │
       E: ──► lang.word.lemon , vis.fruit.lemon (если есть)
```

Агент **не** получает continuous olfactory vector — но может **учиться связям**, как слепой учит «красный» через описание. Это честнее, чем симулировать несуществующий датчик.

---

## 10. Roadmap (поэтапно)

| Шаг | Deliverable | Зависимости |
|-----|-------------|-------------|
| **R1** | этот ADR + stack JSON sketches (sensor / spatial) | — |
| **R2** | Exp L L2 static `vis.*` + `E:` → `lang.*` | Exp J |
| **R3** | **`prism_auditory`** stub + `A0` codec (wav → tokens) | R1 |
| **R4** | **`prism_visual`** stub + `V1` (static image) | R1, R2 |
| **R5** | `A1_phon` / listen bench → grapheme/syllable | R3, bukvar B0 |
| **R6** | DAN routes **between prisms** + bench | ADR-0010 field |
| **R7** | Video → `V2` + `H3_scene` (temporal) | R4 |
| **R8** | **`prism_spatial`**: mono depth cues (motion/size) | R4 |
| **R9** | Stereo pair → `S0_disparity` + `S2_object_pose` | R8, 2× webcam |
| **R10** | Binaural → `A2_localization` + `a_bridge` → `S2` | R3, R9 |
| **R11** | Cross-modal predict error (aud/vis/spatial mismatch) | R6, lattice_predict |

**Не в v0:** end-to-end CLIP-from-scratch, full SLAM, olfactory tensor. **В v1+:** настоящий 3D ego-centric map, не один 64×64 slice.

---

## 11. Отклонённые альтернативы

| Альтернатива | Почему нет |
|--------------|-----------|
| Raw PCM / pixels в NCA | repair/train cost; против Exp L / Cosmos tokenizer |
| Отдельный LLM «vision» | против UC; внешняя RAM |
| Запах как float[] без датчика | ложная модальность; только symbolic `chem.*` |
| Audio-only без hub к L0 | второй изолированный язык; не букварь |
| **Вся сенсорика через text hub** | **плоский мир**; нет dorsal/spatial; против нейроанатомии |
| **3D = z на одной vis-решётке** | путает индекс CA-уровня с egocentric depth; нужен `prism_spatial` |
| Control stack = vision | смешивает CU и V1; ADR-0010 ≠ V1 |

---

## 12. Критерии готовности

- [ ] R2: vis@1 bench green (картинка → `lang.word.*` через `E:`)
- [ ] R5: aud@1 bench: phoneme cue → syllable/grapheme top-1 > baseline
- [ ] R6: DAN selects **prism** (aud vs vis vs text), inactive prisms skipped
- [ ] R9: stereo depth: nearer object → lower `S:d` error vs monocular baseline
- [ ] R11: cross-modal prediction error > threshold triggers Extract (hippo write)

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-05-31 | v0 proposed: sensor prism, A/V stacks, control routing P10–P13, text hub, smell-as-symbol |
| 2026-05-31 | v0.1: отдельные prism_auditory/visual/spatial; binocular + binaural; 3D ≠ flat grid |
