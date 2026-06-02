# CASA-ADR-0026: Multimodal event ingest (audio+vision → scenes/episodes → sleep)

**Статус:** черновик (design)  
**Дата:** 2026-06-02  
**Область:** feeding для audio/vision стека, формат события, offline/live pipeline  
**Связано:** `CASA-ADR-0021-experience-agent-transfer.md` (curriculum как события), [`CASA-ADR-0027-sensory-motor-periphery-mcp.md`](CASA-ADR-0027-sensory-motor-periphery-mcp.md) (доставка), [`CASA-ADR-0028-field-native-sensory-experience.md`](CASA-ADR-0028-field-native-sensory-experience.md) (цель: полевой опыт ур.2–3, не только текст), `memory-hierarchy.md`

---

## Решение (одной фразой)

**Камера+микрофон кормят агента не “сырым потоком”, а серией маленьких мультимодальных событий (`mm_event`)**: текст (ASR), глифы/объекты (OCR/детекторы) и явный контекст → **scene + episodes** в `{store}/` → `sleep` консолидирует связи, как и для curriculum JSON.  
Для “речи” нужен второй тип события: **действие агента (`mm_action`)** — попытка произнести/воспроизвести (TTS/юниты) + обратная связь от мира/учителя, тоже в форме события.

**Роль v1:** этот ADR описывает **bootstrap (уровни 0–1)** — текст и глифы в `canon.*`. Целевой «настоящий» сенсорный опыт (отпечаток кадра/звука на решётках, время) — **[ADR-0028](CASA-ADR-0028-field-native-sensory-experience.md)**.

---

## Почему так

- **Сырой поток** (видео/аудио) слишком большой и слишком “необратимый” для памяти: он должен жить в “сенсорах/логах”, а не в решётках.
- Модель CASA (ADR-0021) требует, чтобы runtime не читал учебник: значит и сенсоры должны превращаться в **опыт агента**, а не в “внешний oracle”.
- Нам нужна **одна и та же форма** для ingest: teacher lesson, live sensor, offline dataset → всё это “события” на входе, опыт после sleep — один и тот же.

---

## Canonical mm_event (v1)

Минимальная форма, которую можно генерировать как из “live” захвата, так и из оффлайн датасета.

```json
{
  "schema_version": 1,
  "event_id": "uuid-or-monotonic",
  "ts_ms": 1717280000000,
  "window_ms": 1200,

  "audio": {
    "asr_text": "числитель знаменатель это дробь",
    "asr_words": [
      {"w": "числитель", "t0": 0.10, "t1": 0.55, "p": 0.92},
      {"w": "знаменатель", "t0": 0.56, "t1": 1.05, "p": 0.88}
    ]
  },

  "vision": {
    "images": [
      {"path": ".cascade-ide/webcam-captures/burst-001/frame_0001.jpg"}
    ],
    "ocr_text": "1/2 = (||) ||",
    "glyphs": [
      {"g": "1/2", "p": 0.81},
      {"g": "(||) ||", "p": 0.73}
    ],
    "objects": [
      {"type": "stick", "count": 4, "p": 0.90},
      {"type": "heap", "count": 2, "p": 0.86}
    ]
  },

  "canon": {
    "context": ["heap_model:fraction"],
    "words": ["числитель", "знаменатель", "дробь"],
    "math_glyphs": ["числитель / знаменатель = дробь", "1/2", "(||) ||", "/", "="],
    "punctuation": ["/", "=", "(", ")", "[", "]"]
  }
}
```

### Инварианты

- `canon.words` — список **нормализованных** слов (нижний регистр, NFC) для `listen_word/listen_scene`.
- `canon.math_glyphs` — компактные строки-стимулы (например `1/2`, `(||) [(||)(||)]`, `3 × 2`) для `schema-math` (`append_episode`).
- `canon.context` — маленькие теги, влияющие на чтение неоднозначных токенов:
  - пример: `heap_model:fraction` отличает `()` как “слот кучки” от `()` как `math.num.zero` в lesson-11.

---

## Canonical mm_action (v1): попытка произнести + обратная связь

Если агент должен “сам” начать говорить (как ребёнок), ему нужен **контур действия**: попытка → реакция среды.  
В CASA это делается не подбором частот, а **дискретными мотор-юнитами** (пусть грубыми) и последующей оценкой.

Минимальная форма:

```json
{
  "schema_version": 1,
  "action_id": "uuid-or-monotonic",
  "ts_ms": 1717280000100,
  "window_ms": 1500,

  "agent": {
    "store_id": "von-neumann",
    "mode": "imitate|request|label|echo"
  },

  "motor": {
    "tts_units": [
      {"u": "ru:сло", "t0": 0.00, "t1": 0.18},
      {"u": "ru:жи", "t0": 0.18, "t1": 0.34},
      {"u": "ru:те", "t0": 0.34, "t1": 0.50},
      {"u": "ru:ль", "t0": 0.50, "t1": 0.62}
    ],
    "prosody": {"rate": 1.0, "pitch": 0.0, "gain": 0.0}
  },

  "world": {
    "heard_asr_text": "сложитель",
    "heard_asr_words": [{"w": "сложитель", "p": 0.61}],
    "teacher_feedback": {
      "kind": "approve|reject|correct",
      "target_text": "слагаемое",
      "p": 0.92
    }
  },

  "canon": {
    "intent": ["imitate:last_teacher_word"],
    "said_text": "слагаемое",
    "heard_text": "сложитель",
    "reward": 1,
    "context": ["speech:ru", "domain:math"]
  }
}
```

### Инварианты mm_action

- `motor.tts_units` — **не wave** и не частоты; это последовательность устойчивых юнитов (слоги/фонемоподобные токены/кластеры), которые можно “произнести”.
- `world.heard_*` — то, что вернул перцептивный тракт (ASR), т.е. **как мир услышал** речь агента.
- `canon.reward` — очень грубая обратная связь: \(-1, 0, +1\) или \([0..1]\). В offline она может задаваться teacher-скриптом.

### Нормализация и шум ASR (Whisper) — правило v1

ASR может ошибаться (и часто делает это уверенно). В v1 мы не “чинем” текст магией; мы **учим через веса и повторяемость**:

- **Порог уверенности**: слова/токены с `p < 0.6` считаются шумом — их
  - либо не добавляем в `canon.words`,
  - либо добавляем, но с пониженным весом (в teacher-логике ingest).
- **Коррекции важнее**: для ключевых слов (термины уроков) использовать `teacher_feedback.kind=correct` и `teacher_feedback.target_text` — это создаёт устойчивую связь “как услышал” → “как правильно”.
- **Повторяемость лечит**: одно событие не должно решать; несколько независимых `mm_event/mm_action` с тем же словом обычно перекрывают единичные глюки.

Рекомендуемое расширение логирования (опционально v1):

- Вести счётчик частых “оговорок” ASR: `heard_text -> target_text` и топ ошибок по домену (`domain:math`).
- Использовать этот список как генератор micro-lessons (teacher ingest), чтобы агент быстрее перестал путаться именно в часто ошибочных парах.

---

## Как mm_event превращается в опыт

**Одна порция ingest** (для одного `mm_event`) делает:

1) `listen_scene` на L3: связывает `scene_id = mm:<event_id>` с `canon.words` и `canon.punctuation`.
2) Для каждого `canon.words` — усиление L2 (`lang.word.*`) + эпизод “слышал слово”.
3) Для каждого `canon.math_glyphs` — эпизод на `schema-math` (cue=glyph). Это позволяет F0 считыванию связывать новые глифы с уже известными `math.*` (после sleep и жизни агента).
4) Периодически `sleep` — чтобы `hippo → field/ltm` и “склейка” стали частью опыта.

**Важно:** mm_event ingest не обязан сразу давать “правильный ответ” в top-1 — критерий качества проверяется в teacher/probe (`check_agent_mastery` и отдельные mm-probe), а не на каждом live-таке.

---

## Как mm_action превращается в опыт (речь как действие)

Идея: агент учится говорить так же, как учится “делать” в math — через **эпизоды действия** и консолидацию.

Одна порция ingest для `mm_action` делает:

1) `listen_scene` (L3) для `scene_id = mm_action:<action_id>`: привязывает `canon.intent`, `canon.said_text`, `canon.heard_text`, `canon.reward`.
2) Эпизод “попытка сказать X” (cue=`canon.said_text`) в отдельной решётке (например `schema-speech`) *или* как `schema-math`/`lang` эпизод с тегами (v1 допускает “через текст”).
3) Эпизод “мир услышал Y” (cue=`canon.heard_text`) — чтобы закреплять соответствие “как я хотел” ↔ “как вышло”.
4) Если есть `teacher_feedback.kind=correct`: дополнительный эпизод со связью `heard → target_text` (коррекция).
5) `sleep` по батчу, чтобы укреплялись устойчивые пары/цепочки: intent → motor_units → heard_text → reward.

### Минимальный путь к «спонтанной речи»

Без внешнего контура (reward/понимание) агент не имеет причины “говорить”, кроме случайного поиска. Поэтому в v1:

- **Echo/Imitate**: учитель даёт `mm_event` со словом, затем просит `mm_action` “повтори”.  
  Reward: +1 если ASR распознал целевое слово, 0 иначе.
- **Request**: учитель/мир делает “желанный” объект доступным только после корректного `mm_action` (например `ещё`, `стоп`).  
  Reward: +1 при успехе.
- **Label**: на видео есть объект/глиф, учитель ждёт произнесения метки (“дробь”, “слагаемое”).  
  Reward: +1 при совпадении.

Это превращает речь в инструмент (действие), а не “перебор частот”.

---

## Два pipeline: offline и live

### Offline

- Источник: `events.jsonl` (1 JSON на строку) + (опционально) файлы изображений/аудио для воспроизводимости.
- Команда: `python tools/ingest_mm_events.py --store-dir agents/von-neumann --events-jsonl lab/mm/events.sample.jsonl`
  - Для речи добавляется `actions.jsonl` с `mm_action` (1 JSON на строку) и отдельный ingest (см. ниже).

### Live (операторский контур)

Live-захват делается **сенсорной периферией** (organ MCP + `sensory_relay`, см. ADR-0027); в Cursor на этапе разработки удобно те же органы через MCP. В `{store}/` попадает уже **канонический** `mm_event`.

Референс-процедура:
- Захват: webcam burst (папка кадров) + audio burst (wav)
- Аналитика: OCR по кадрам → `ocr.json`, Whisper ASR по wav → `asr.json`
- Сборка `mm_event` → append в `events.jsonl` (скрипт `tools/mm_build_event.py`)
- Ingest `events.jsonl` в store + sleep по батчу (скрипт `tools/ingest_mm_events.py`)
  - Для речи: TTS/произнесение агентом → ASR “как услышал мир” → собрать `mm_action` → append в `actions.jsonl` → ingest + sleep по батчу.

Пример команд (операторский сценарий, имена файлов условные):

```powershell
# 1) asr.json и ocr.json получаются внешними инструментами (например MCP в Cursor)
# 2) собрать событие и добавить в JSONL
python tools/mm_build_event.py --event-id live-0001 --asr-json lab/mm/asr.json --ocr-json lab/mm/ocr.json `
  --context heap_model:fraction --append-jsonl lab/mm/events.live.jsonl

# 3) ingest в агента
python tools/ingest_mm_events.py --store-dir agents/von-neumann --events-jsonl lab/mm/events.live.jsonl
```

---

## Принятое ограничение v1

- В v1 нет “универсального” CV-детектора палочек/кучек. Мы начинаем с OCR глифов и простых регэкспов по тексту/ASR; детекторы добавляются как отдельные призмы/модули без изменения mm_event канона.

### Аналогичное ограничение для речи

- В v1 мы **не** учим агент “моторно” в физическом смысле (артикуляция/частоты). Мы учим **дискретные юниты** (слоги/кластерные токены) и связываем их с тем, что ASR/мир услышал.  
- Если позже появится реальный вокодер/артикулятор, он подключается как слой реализации `motor.tts_units`, не ломая канон `mm_action`.

