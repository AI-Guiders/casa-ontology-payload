# CASA-ADR-0028: Полевой сенсорный опыт (уровни 2–3) — цель для Неймана

**Статус:** черновик — **на обсуждение** (фиксирует *куда* идём; не отменяет mm v1)  
**Дата:** 2026-06-02  
**Область:** что значит «настоящее» зрение и слух для агента CASA — не OCR/ASR как память, а след на решётке  
**Связано:**

- [`CASA-ADR-0021-experience-agent-transfer.md`](CASA-ADR-0021-experience-agent-transfer.md) — опыт = поле + `ltm/`, не oracle на read
- [`CASA-ADR-0026-multimodal-event-ingest.md`](CASA-ADR-0026-multimodal-event-ingest.md) — **v1 bootstrap** через `canon.words` / глифы (уровень 0–1)
- [`CASA-ADR-0027-sensory-motor-periphery-mcp.md`](CASA-ADR-0027-sensory-motor-periphery-mcp.md) — доставка: периферия → адаптер → … → мозг
- [`CASA-ADR-0012-cide-parity-fieldbus-and-migration.md`](CASA-ADR-0012-cide-parity-fieldbus-and-migration.md) — `prism_visual`, `prism_auditory`, FieldBus
- [`CASA-PROJECT-CONSTITUTION.md`](CASA-PROJECT-CONSTITUTION.md) — LLM снаружи; NCA = пространственное поле; квалиа вне scope

---

## Решение (одной фразой)

**Целевой опыт Неймана — афферентные тракты (ур. 2–3):** первичные (зрение, слух) с импринтом на решётке; символические (schema, lexical) — свой субстрат, но не «зрительный тракт». OCR/ASR — **`text_bypass` (шunt)**, не определение зрения. Эфферент: `motor_speech` → петля в слуховой.

---

## Зачем отдельный ADR

ADR-0026/0027 описывают **как доставить события**. Этот ADR описывает **тракты** внутри агента — с разделением **первичный / символический / эфферентный** — и почему текстовый bootstrap не равен зрительному тракту.

---

## Тракт (термин)

**Тракт** (*tract*) — **целостный путь одной модальности или канала curriculum** от входа в агента до чтения на tick, через собственный субстрат.

Не синонимы:

| Термин | Что это |
|--------|---------|
| **Тракт** | цепочка со станциями [1]–[5] (ниже) |
| **Периферия** (0027) | рецептор + доставка сырья **в первичный** тракт |
| **Решётка** | станция [2]–[3] (импринт / раннее поле) |
| **`text_bypass`** | **шunt**, не `tract_id`: OCR/ASR → lexical **минуя** импринт |
| **Кросс-модальный хаб** | связи между трактами после sleep/hot — **не** отдельный тракт |
| **mm_event** | может кормить тракт, шunt или эфферент |
| **Призма** | контейнер решёток (`prism_visual`, …) |

### Классы трактов

Каждый `tract_id` в manifest/store помечается:

| Поле | Значения |
|------|----------|
| **`direction`** | `afferent` \| `efferent` |
| **`tract_kind`** | `primary_sensory` \| `symbolic` |

| Класс | `direction` | `tract_kind` | `tract_id` | Смысл |
|-------|-------------|--------------|------------|--------|
| **Первичный афферентный** | afferent | primary_sensory | `visual`, `auditory` | фотоны / давление → **импринт** (ур. 2–3) — «настоящее» зрение/слух в ADR |
| **Символический афферентный** | afferent | symbolic | `schema`, `lexical_ru` | дискретный/структурный вход (палочки, слова урока); свой sleep/predict, **не** узкий сенсорный тракт |
| **Эфферентный** | efferent | — | `motor_speech` | intent → TTS → мир → **обратно** в `auditory` (петля) |

**Шunt (не тракт):** `text_bypass` — маршрут ingest: `canon.words` → `listen_scene` / `lexical_ru` **без** импринта на `prism_visual` (L/R/G/B). В manifest: `route: text_bypass`, `target_tract: lexical_ru`, `experience_level: 0`.

Узкое «сенсорное» в заголовке ADR = **первичные** `primary_sensory`; schema/lexical остаются **трактами**, но в документации не называются зрительным/слуховым трактом.

### Станции тракта (обобщённо)

```text
  [1] Рецептор          периферия (первичные) или учитель/mm (символические)
  [2] Импринт / код   codec → след на решётке (ур. 2 у первичных; токены/глифы у symbolic)
  [3] Раннее поле     hippo, episodes по этому tract_id
  [4] Консолидация    sleep → ltm/
  [5] Чтение          predict + router
        │
        └──► кросс-модальный хаб (sleep/hot): visual ↔ schema ↔ lexical — не [6]-й тракт
```

**Уровень 3** = **первичный** (или symbolic) тракт с **временной осью**: цепочка импринтов, relay, `lattice_thal_relay`.

### Карта `tract_id` (целевая)

| `tract_id` | Человеческое | `direction` | `tract_kind` | Рецептор / источник | Решётка | Router |
|------------|--------------|-------------|--------------|---------------------|---------|--------|
| **`visual`** | зрительный | afferent | primary_sensory | камера RGB | `V1_lum`, `V1_chrom_{r,g,b}` | `vis`, `image` |
| **`auditory`** | слуховой | afferent | primary_sensory | микрофон | auditory lattice | `listen`, `segment` |
| **`schema`** | структурно-мат. | afferent | symbolic | учитель, `(||)`, палочки | `schema-math` | `schema` |
| **`lexical_ru`** | лексика RU | afferent | symbolic | уроки, ASR→слова | `L2_word`, L3 | `t9` |
| **`motor_speech`** | речь-выход | efferent | — | `mm_action` | — (петля в auditory) | action |

```text
  PRIMARY AFFERENT                    SYMBOLIC AFFERENT
  ┌─ visual ─────────────────┐      ┌─ schema ─── (||), math
  │  camera→LRGB imprint→…  │      └─ lexical_ru ─ слова
  └─ auditory ───────────────┘              │
           ▲                                  │
           │         кросс-модальный хаб      │
           └──────── sleep / hot ────────────┘
                    (не отдельный tract_id)

  EFFERENT: motor_speech → TTS → мир ──► auditory (feedback)

  SHUNT: text_bypass ──► lexical_ru  (ур. 0, без V1 imprint)
```

### Read path по классу (ADR-0021)

| `tract_kind` | На tick без внешней модели |
|--------------|----------------------------|
| **primary_sensory** | predict по **активации сенсорной решётки** + `ltm/` |
| **symbolic** | predict по **токенам/структуре** на своей решётке + `ltm/` (нормально; другой тип опыта) |
| **text_bypass** | явно ур. 0: опора на текст в поле; внешняя ASR/OCR только на ingest |

### Связь с ADR-0027

0027 = станции **[1]–[2]** для **первичных** трактов (адаптер, codec) + доставка в symbolic.  
0028 = полная карта трактов и критерии «настоящего» зрения/слуха = **только** `primary_sensory` ур. 2–3.

### Связь с уровнями 0–3

| Ур. | Роль |
|-----|------|
| 0 | `text_bypass` → symbolic lexical |
| 1 | узлы на стыке **visual** ↔ **schema** (два тракта, один ep) |
| 2 | импринт на **primary_sensory** |
| 3 | тракт во времени ([2]→[3]→[4]) |

---

## Физическая модель: фотоны → импринт → обработка

И биология, и камера сходятся на одной схеме: **свет даёт пространственный след**, дальше работает уже «кора», а не фотон по отдельности.

| Этап | Глаз | Камера | CASA (ур. 2–3) |
|------|------|--------|----------------|
| **1. Улавливание** | фотоны → палочки/колбочки | фотоны → матрица (CMOS/CCD) | периферия: кадр / burst в `RawCapture` |
| **2. Импринт** | распределение возбуждения на **сетчатке** | заряд/напряжение на **матрице** (ещё не «смысл») | **RetinalCodec** → **4 решётки** L+R+G+B в `prism_visual` (32×32, токены) |
| **3. Предобработка** | сетчатка + горизонтальные клетки (контраст, движение) | БПФ/демозаика, усиление — **в камере/ISP** | фиксированные фильтры в codec (край, бин яркости); допустимо в **perception**, не в predict |
| **4. Ранний сигнал** | импульсы в LGN / V1 | цифровой кадр, motion vectors | episodes на visual lattice + теги relay (ур. 3) |
| **5. Память и смысл** | кора, гиппокамп, консолидация | — (вне камеры) | hippo → **sleep** → `ltm/`; **predict** по полю |

```text
  Фотоны          ИМПРИНТ (пространственный)        ОБРАБОТКА (время + память)
  ───────         ─────────────────────────         ───────────────────────────

  Глаз:           сетчатка                          LGN / V1 / … / память
  Камера:         матрица + АЦП (RAW/frame)         CPU/GPU (если VLM — это уже «чужая кора»)

  Нейманн:        V1_lum + V1_chrom_{r,g,b}         prism_control + sleep + predict
                  ▲
                  └── RetinalCodec: RGB с камеры → L вычисляется, четыре карты одной сцены
```

**Следствия для дизайна:**

- **Уровень 2** в таблице ниже = именно **импринт** (как плёнка или кадр RAW после АЦП), записанный на решётку агента.
- **OCR / caption / VLM** = не импринт, а **чужая кора**, вклиненная до того, как у Неймана появился свой след (уровень 0 — допустим как bootstrap, не как зрение).
- **Камера и глаз** для CASA эквивалентны на границе **периферии**: оба отдают `RawCapture`; различие — в шуме, спектре, динамике, не в архитектуре мозга.
- **ЦАП/квантование** в камере ≈ **дискретизация в RetinalCodec** (токен на ячейку решётки): потеря информации есть, но **топология** (что где на сцене) сохраняется намеренно.

**Слух (кратко):** давление → базилярная мембрана / микрофон → **временной** импринт (осциллограмма, mel-полосы) на **auditory lattice** — та же логика «сначала физический след, потом поле, потом сон».

---

## Шкала уровней (канон обсуждения)

| Ур. | Название | Что попадает в мозг | Статус для `von-neumann` |
|-----|----------|---------------------|---------------------------|
| **0** | Текстовая проекция | `canon.words`, OCR/ASR-строки → `listen_scene` / L2 | **сейчас** (mm v1, lang-bridge) |
| **1** | Структурное | `vision.objects`, глифы `(||)`, роли сцены | **частично** (math-palochki, schema) |
| **2** | **Полевое (импринт)** | фотоны/звук → след на **`V1_lum` + chrom R/G/B** / auditory | **цель** |
| **3** | **Динамическое** | цепочка окон → эпизоды + relay во времени | **цель** |

**Направление обсуждения:** продуктовая перцепция Неймана = **2 + 3** (импринт + время). Уровни 0–1 = bootstrap (в т.ч. «чужая кора» в виде OCR/ASR).

---

## Что считается «настоящим» в CASA (инженерно)

Не квалиа («как красный»), а инварианты:

1. **Субстрат:** стимул меняет **собственные** `cells` / `ltm` агента, не только journal-запись о тексте.
2. **Read path:** на tick **нет** вызова внешней vision/speech-модели; только поле + consolidated память (ADR-0021).
3. **Ошибка сенсора:** surprise → hippo → sleep (тот же цикл, что Kolb/math).
4. **Перцепция вне мозга допустима** только как **codec** (обучение offline, lab); **жизнь** — отпечаток + динамика на поле.

Аналогия: у человека сетчатка и cochlea не «понимают» — они **кодируют**; кора = поле CASA + sleep.

---

## Уровень 2 — полевое зрение и слух (станции тракта)

### Зрительный тракт (`tract_id: visual`, `primary_sensory`)

```text
  Кадр RGB (камера / экран — один снимок)
      ↓  [периферия — RawCapture]
  RetinalCodec (host/perception, НЕ на predict path)
      downscale 32×32; квант K уровней на канал
      L = f(R,G,B)   например 0.299R+0.587G+0.114B  (отдельный снимок с камеры не нужен)
      ↓
  imprint_visual_frame(state) — один вызов, четыре решётки:
      V1_lum       — яркость / тени / контраст сцены
      V1_chrom_r   — «красный фильтр»
      V1_chrom_g   — «зелёный фильтр»
      V1_chrom_b   — «синий фильтр»
      ↓
  append_episode(tract_id=visual, lattices=[lum,r,g,b], frame_id, scene_hash, …)
      ↓
  sleep → vis.lum.*, vis.chrom.* в ltm/; кросс-мосты между четырьмя картами
      ↓
  predict(modality=vis): гипотеза по **совместной** активности четырёх полей
```

**RetinalCodec `retinal_lrgb` (канон с первого live-кадра):**

| Решётка | Источник | Роль |
|---------|----------|------|
| `V1_chrom_r` | канал R | оттенок, «краснота» локально |
| `V1_chrom_g` | канал G | |
| `V1_chrom_b` | канал B | |
| `V1_lum` | **вычисленный** L из RGB | яркость, тени; **палочки/контур** читаются здесь же |

- Камера отдаёт **только RGB** — проще периферии; L не снимаем отдельно.
- Все четыре решётки в **`prism_visual`**, общие `(x,y)`, один `frame_id`.
- **«Сумма»** на ingest **не** делаем (не один смешанный токен); интеграция — на **predict / sleep** + `x_bridge` между lum и chrom.
- Опционально: Sobel/край на **L**-карте; фиксированные фильтры, не CLIP.

**Миграция store:** legacy `V1_object` (0 токенов в `von-neumann`) → переименовать/алиасить в **`V1_lum`**; добавить `V1_chrom_{r,g,b}` в stack `prism_visual`.

**Ёмкость:** 4 × 32×32 клеток × K уровней на канал; тень ≈ падение на L и согласованно на R,G,B; цвет ≈ доминанта chrom при том же layout на L.

**Обучаемый encoder (позже):** offline train; runtime forward only; отдельный `codec_id` в manifest только при **несовместимом** wire-формате.

**Позже:** opponent-карты (R−G, B−Y) **дополнительно** к LRGB — отдельные решётки или codec, не суффикс `v2` в имени файла.

### Именование (без зоопарка `v0` в файлах)

| Где | Как |
|-----|-----|
| **Файл / модуль** | по смыслу: `retinal_lrgb.py`, `ingest_room.py` |
| **`codec_id` в episode/manifest** | стабильная строка: `retinal_lrgb` (меняется только при смене формата токенов) |
| **Эволюция** | ADR changelog, фазы S2a/S3 — не переписывать имя файла на каждый шаг |
| **Legacy в репо** | `lattice_names_v1`, ADR-0018 — исторические; новый код не копирует паттерн |

**Не делаем:** JPEG в L2; один embedding на кадр; откладывать chrom «на потом», если зрение — главный канал curriculum.

### Слуховой тракт (`tract_id: auditory`, `primary_sensory`)

Симметрично зрительному:

```text
  WAV / поток
      ↓
  CochlearCodec: mel / onset / громкость / полосы → токены на auditory lattice
      ↓
  episodes + sleep → auditory.* , связь с L2_word (слова — второй слой, не замена)
```

ASR (Whisper) может работать **параллельно** для teacher/operator, но **не подменяет** полевой слух на read path.

### Символические тракты (`schema`, `lexical_ru`)

Уже работают в curriculum Неймана; в терминах трактов — **afferent + symbolic**, без обязательного импринта на `prism_visual`:

| `tract_id` | Типичный ingest | Станция [2] |
|------------|-----------------|-------------|
| `schema` | `lesson_class`, math-palochki | глифы / роли на `schema-math` |
| `lexical_ru` | `lang_lesson_class`, t9 | `L2_word`, L3 |

Стык **visual ↔ schema** (ур. 1): один эпизод может ссылать оба `tract_id`; консолидация — через **кросс-модальный хаб**, не через новый `tract_id`.

### Router

Существующие маршруты (`modality: vis` → `prism_visual`, `listen` → lang/auditory) используются **после** появления содержимого на решётках, не только как alias для t9.

---

## Уровень 3 — динамика (тракт во времени)

Поле даёт **пространство**; уровень 3 добавляет **время** вдоль того же тракта — без видео в `ltm/`:

| Механизм | Роль |
|----------|------|
| **Окна внимания** | burst → несколько `PerceptPacket` / episode (scene cut, `window_ms`) |
| **Цепочка эпизодов** | `episode.prev_id` / `scene_seq` — одна «сцена» = несколько кадров |
| **`lattice_thal_relay`** | теги динамики: `motion:high`, `scene_cut`, `av:speech_onset` (не oracle) |
| **Sleep** | Extract связывает «до/после», устойчивые паттерны движения |
| **Predict** | cue может быть **последний отпечаток** или **digest** relay-решётки |

```text
  t₀  frame₀ → LRGB imprint → ep₀
  t₁  frame₁ → LRGB imprint → ep₁  (link ep₀→ep₁)
  …
  sleep → «это один урок у доски», не 9000 независимых картинок
```

Сырой mp4 в памяти **не храним** — только диск `lab/sensory/` для воспроизводимости (как ADR-0026).

---

## Граница с ADR-0026 (`mm_event`)

| | mm v1 (0026) | Уровни 2–3 (этот ADR) |
|---|----------------|------------------------|
| Вход в ingest | `canon.words`, `math_glyphs` | **`imprint_*` на sensory lattices** + episodes |
| `mm_event` | удобный канон для host | может остаться **обёрткой** (metadata + пути к кадрам), но **не единственный след** |
| Проверка | teacher probe, mastery | predict на `vis`/`listen` modality + field |

**Правило перехода:** новые типы ingest-событий (или расширение mm):

- `kind: field_imprint` с `lattice_id`, `placements[]`, `codec_id`, `frame_ref`;
- sleep обязателен так же, как для listen_scene.

---

## Граница с ADR-0027 (доставка)

0027 отвечает: **кто** вызывает камеру и **как** не залочиться на MCP.

0028 отвечает: **что** должно оказаться в `von-neumann` после ingest — **поле**, не подпись.

```text
  0027:  Периферия → Адаптер → Perception (RetinalCodec здесь) → …
  0028:  … → imprint LRGB / auditory → hippo → sleep → predict(vis)
```

---

## Что остаётся внешним (честно)

| Допустимо offline / lab | Запрещено на predict path |
|-------------------------|---------------------------|
| Обучение RetinalCodec | CLIP/GPT-4V «что на картинке» |
| Whisper для разметки | ASR как oracle expect |
| CV-детектор для dataset | Чтение `ocr_text` из последнего mm как истины |

Внешняя модель = **мастерская**, не **кора**.

---

## Composition (ADR-0012)

Включение сенсорного опыта = mount в store profile, не переписывание tick:

```json
{
  "prism_composition": {
    "prism_memory": { "enabled": true },
    "prism_math": { "enabled": true },
    "prism_visual": { "enabled": true },
    "prism_auditory": { "enabled": true },
    "prism_hippo": { "enabled": true }
  },
  "tracts": {
    "visual": { "direction": "afferent", "tract_kind": "primary_sensory" },
    "auditory": { "direction": "afferent", "tract_kind": "primary_sensory" },
    "schema": { "direction": "afferent", "tract_kind": "symbolic" },
    "lexical_ru": { "direction": "afferent", "tract_kind": "symbolic" },
    "motor_speech": { "direction": "efferent" }
  },
  "ingest_routes": {
    "text_bypass": { "target_tract": "lexical_ru", "experience_level": 0 }
  },
  "sensory_codecs": {
    "visual": "retinal_lrgb",
    "auditory": "cochlear"
  },
  "visual_lattices": ["V1_lum", "V1_chrom_r", "V1_chrom_g", "V1_chrom_b"]
}
```

**Критерий готовности ур.2 (S2a):** после live burst — attested tokens на **всех четырёх** решётках `prism_visual` (не только L).

---

## Фазы (только 2–3)

| Фаза | Deliverable | Критерий |
|------|-------------|----------|
| **S2a** | `imprint_visual_frame` → **L + R + G + B** (`retinal_lrgb`) | RGB с камеры → 4 решётки → sleep → predict по `vis` |
| **S2b** | `imprint_auditory_window` | mel-токены на auditory lattice |
| **S3a** | цепочка ep + `scene_seq` | два кадра → связанный след после sleep |
| **S3b** | relay tags + cross-prism sleep | «эта картинка» ↔ слово «дробь» ↔ `(||)` |

Уровни 0–1 (mm text, sticks detector) **не блокируют** S2 — идут параллельно.

---

## Non-goals

- Не претензия на человеческое зрение или квалиа.
- Не «VLM внутри Неймана» как субстрат мышления.
- Не хранение видеопотока в `ltm/`.
- Не отмена mm/ASR v1 до готовности S2 — **надстройка**, не замена с нуля.

---

## Open questions

1. **Stack выше LRGB:** `V2_edges` / объекты — отдельные lattices или NCA поверх lum?  
2. **K (уровней кванта)** на канал: 8 / 16 / 32 — bench на палочках и цветных маркерах?  
3. **Cue на predict:** hash кадра, digest по 4 полям, или lum-only cue?  
4. **Связь math sticks:** структурное (ур.1) и полевое (ур.2) — один codec или два входа в один ep?  
5. **Первый живой сценарий:** стол с палочками (ур.1+2) или произвольная комната?  
6. **Именование в коде:** блок `tracts` в manifest vs отдельный `tracts.json` в store profile?  
7. **Тактильный** — `primary_sensory` non-goal v1 или заглушка?  
8. **Параллельный ingest:** один кадр → `visual` imprint **и** `text_bypass` в один tick — допустимо для lab?

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-02 | Черновик: уровни 2–3 как целевой сенсорный опыт; отличие от mm-текста |
| 2026-06-02 | § Физическая модель: глаз/камера → импринт → обработка; V1 = сетчатка/матрица |
| 2026-06-02 | § Сенсорный тракт: visual/auditory/schema/lexical, станции, обходной text_bypass |
| 2026-06-02 | Классы трактов: primary_sensory / symbolic / efferent; text_bypass = shunt; хаб ≠ тракт; manifest `tracts` |
| 2026-06-02 | RGB: три решётки prism_visual (светофильтры); «сумма» на read/sleep; v0 = L-only bootstrap |
| 2026-06-02 | **LRGB сразу:** 4 решётки (`V1_lum` + chrom R/G/B), `retinal_lrgb_v0`; L из RGB; S2a = все четыре |
| 2026-06-02 | Код S2a: `casa/domain/visual_*`, `casa/sensory/`, `casa/prisms/visual/`; CLI `ingest_visual_room`; lab `sensory/room` |
