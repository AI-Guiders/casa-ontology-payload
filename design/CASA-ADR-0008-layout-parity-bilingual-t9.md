# CASA-ADR-0008: layout-parity bilingual T9 (раскладочный паритет)

**Статус:** accepted (design + lab path; `vk_decode_v0` — roadmap)  
**Дата:** 2026-05-30  
**Область:** bilingual T9, input modality, unified tick, act/preview  
**Источник идеи:** product pitch Orion (Orion / Google Web AI), 2026-05  
**Связано:** [`CASA-ADR-0006-t9-predictive-text.md`](CASA-ADR-0006-t9-predictive-text.md), [`CASA-ADR-0003-emergent-forms-tags-predictor.md`](CASA-ADR-0003-emergent-forms-tags-predictor.md), [`CASA-ADR-0007-agent-profile-store-packs.md`](CASA-ADR-0007-agent-profile-store-packs.md), [`homoglyph_v0.py`](../tools/homoglyph_v0.py), [`unified_tick_v0.py`](../tools/unified_tick_v0.py)

---

## Контекст

### Боль пользователя

При смешанном RU prose + EN commands (IDE slash-команды, ToML, Roslyn symbols) ОС навязывает **одну активную раскладку**. Пользователь переключает язык в трее или печатает «не те» Unicode-символы, если мышечно набрал QWERTY-позиции при включённом ЙЦУКЕН.

**Цель продукта:** поток мыслей без переключения индикатора языка; preview/chip показывает **выпрямленный интент**, intercom получает чистые ToML-пакеты.

### Что уже есть в lab

| Кирпич | Роль |
|--------|------|
| Linked RU+EN boot | два semantic layer на одном runtime |
| `homoglyph_v0` | один **visual** glyph → latn **и** cyrl (`co` \| `со`) |
| `unified_tick_v0` | dual branch T9 + argmax по votes |
| `bench_ambiguous_prefix_v0` | homoglyph fork green |

**Homoglyphs ≠ layout parity.** Homoglyph — два Unicode, **одинаково выглядящие**. Layout mismatch — **одни физические клавиши**, разная транскодировка в Unicode (QWERTY `/attach` vs ЙЦУКЕН `.феее`).

### WinAPI / платформа

**Core CASA не вызывает WinAPI** и не привязан к Windows.

Правильное разделение:

```text
  [ACT / cyl_io]     платформенный адаптер (опционально)
        │            Win / macOS / Linux / WASM / Web
        ▼
  [CORE]             layout-neutral PhysicalKeyEvent[]
        │            + таблицы decode (qwerty, jcuken, …)
        ▼
  [CORE]             dual semantic T9 (RU store ║ EN store ║ command store)
        ▼
  [ACT]              Preview chip / intercom ToML / NativeAOT runtime
```

Пользователь **верно поняла**: WinAPI — только возможная **реализация act-адаптера** на Windows, не часть канона. На macOS — `NSEvent`, на Linux — X11/Wayland/libinput, в браузере — `KeyboardEvent.code` (physical key id). **Контракт один.**

---

## Решение

### 1. Три слоя ввода (не смешивать)

| Слой | Имя | Кроссплатформенный? |
|------|-----|---------------------|
| **L0** | `PhysicalKeyEvent` | **да** — канон |
| **L1** | `layout_decode(table)` → grapheme string | **да** — чистые таблицы |
| **L2** | `predict_t9` / `unified_tick` на linked stores | **да** — уже есть |

**L0 контракт v0** (JSON / stdin, без OS types):

```json
{
  "schema_version": 1,
  "events": [
    { "key_id": "KeyA", "action": "down" },
    { "key_id": "KeyT", "action": "down" },
    { "key_id": "KeyT", "action": "down" },
    { "key_id": "KeyA", "action": "down" },
    { "key_id": "KeyC", "action": "down" },
    { "key_id": "KeyH", "action": "down" }
  ]
}
```

`key_id` — **layout-neutral** идентификатор физической клавиши. Рекомендуемый канон: **`KeyboardEvent.code`** (W3C UI Events) — одинаково осмыслен на Web; desktop-адаптеры мапят native scan → `KeyA`, `Slash`, `Digit2`, …

Альтернатива lab: упрощённый enum `US_QWERTY_<row><col>` в bench fixtures — **без** привязки к Win32 VK.

**Не использовать в core:** `WM_CHAR`, Unicode из активной раскладки как единственный источник истины для layout-parity.

### 2. Layout-parity decode (L1)

Одна последовательность `PhysicalKeyEvent` → **несколько** grapheme strings:

```text
  keys [Slash, KeyA, KeyT, KeyT, KeyA, KeyC, KeyH]
       ├─► decode(qwerty_us)  → "/attach"
       └─► decode(jcuken_ru)  → ".феее..."   (пример layout mismatch)
```

**Память (v0):** compose на поле — `vk.physical.*` + `E:|layout.*|grapheme.*` на `L0_vk_map`, буквы на `L0_grapheme`. Ship: core ltm. Decode hot path: boot → field RAM → `vk_decode_v0` (не C# LTM parse).

```text
listen: keyboard-layouts/*.json → vk_layout_ingest → L0_vk_map + L0_grapheme
hot:    PhysicalKeyEvent[] → compose index (edges) → grapheme string
```

См. [`input-modality-vk-layout-v0.md`](input-modality-vk-layout-v0.md).

Таблицы decode — **данные на поле** + JSON-канон для ingest, не OS API.

Параллельный infer (Orion: «два fMRI-слоя»):

```text
  for each decode branch:
      unified_tick(linked_state, grapheme_prefix, context=segment)
  winner = argmax(branch.confidence, branch.top_anchor_votes)
```

Homoglyph fork **внутри** ветки после decode, если visual ambiguous.

### 3. Intent segment (prose vs command)

`unified_tick(..., context=...)` расширить:

| Segment | Сигнал | Store bias |
|---------|--------|------------|
| **`prose`** | кириллица, пробелы, пунктуация RU | RU L2 primary |
| **`command`** | leading `/`, `@`, Roslyn-like token | EN + **code-agent** store |
| **`toml`** | `[`, `=`, intercom block | schema / command store |

**Выпрямление интента:** при RU layout + QWERTY muscle memory команда `/attach` даёт высокий score на **qwerty decode → EN command T9**, низкий на jcuken decode → RU мусор. Preview показывает `/attach`, не `.феее`.

Segment classifier v0 — эвристика (prefix `/`, ratio latn/cyrl после dual decode), не LLM.

### 4. Act: preview, intercom, NativeAOT

| Компонент | Слой | Платформа |
|-----------|------|-----------|
| CASA dual T9 | **core** | Python lab → C# NativeAOT **act** |
| Physical key capture | **act adapter** | per-OS / Web |
| Preview chip / WebView | **act UI** | Cascade IDE / intercom-service |

Orion: «0.7 ms infer» — **целевой SLO act-runtime** (NativeAOT + prefix index), не обязательство Python lab (~50 ms/word сегодня).

**Profile:** [`bilingual-t9-console.v0.json`](../examples/agent-profiles/bilingual-t9-console.v0.json) + будущий `bilingual-layout-parity.v0.json` с `input: physical_key`.

### 5. Связь с homoglyph (ADR-0003)

```text
  Physical keys
       → layout decode (qwerty | jcuken | …)     ← ADR-0008 (NEW)
       → grapheme string
       → homoglyph dual reading (latn | cyrl)    ← ADR-0003 (existing)
       → dual T9 on linked stores                ← ADR-0006
```

Оба fork могут быть активны: сначала layout decode, потом homoglyph на каждой ветке.

---

## Обоснование

| Альтернатива | Почему отклонена |
|--------------|------------------|
| WinAPI / только Windows VK в core | ломает кроссплатформу IDE |
| Следовать OS Unicode + индикатор трея | воспроизводит боль пользователя |
| LLM «угадай язык» на hot path | против UC; latency |
| Один merged L2 RU+EN без fork | теряем script basins и NCA per shard |
| Только homoglyph без layout decode | не чинит ЙЦУКЕН vs QWERTY mismatch |

---

## Последствия

### Roadmap lab

- [x] `design/keyboard-layouts/qwerty-us.v0.json`, `jcuken-ru.v0.json`
- [x] `L0_vk_map` core ltm + `tools/vk_layout_ingest_v0.py`
- [x] `tools/vk_decode_v0.py` — field-first, JSON fallback
- [x] `tools/bench_layout_parity_v0.py`, `bench_vk_layout_field_v0.py`
- [x] Compose decode: vk.physical → layout → grapheme (edges on field)
- [x] Agent docs: `input-modality-vk-layout-v0.md`, `kb-input-modality-vk.v1.json`
- [ ] C# act: PhysicalKeyEvent only → CASA runtime IPC (no prod LTM parse)
- [ ] Act adapter sketch: map platform → `key_id` (document only in ADR until IDE contour)

### Не меняется

- Hot path predict **без сети** (lazy lexicon — cold path, ADR-0006/0007)
- SN/DMN — не новый organ; modality + input adapter
- Homoglyph benches остаются valid

---

## Проверка (критерии v0)

- [ ] Bench: keys for `/attach` under jcuken active OS simulation → EN branch wins
- [ ] Bench: prose `мама` under either decode → RU branch wins
- [ ] Core tools run on Linux/macOS/Windows **без** platform-specific imports
- [ ] ADR и profile не упоминают WinAPI как requirement

---

## Связанные документы

| Документ | Роль |
|----------|------|
| [`examples/exp_bilingual_v0/README.md`](../examples/exp_bilingual_v0/README.md) | homoglyph + unified tick benches |
| [`knowledge/work/cursor-session-f4a4bba6-casa-lab-arc-v0.md`](../../../knowledge/work/cursor-session-f4a4bba6-casa-lab-arc-v0.md) | Orion pitch, product arc |
| [W3C UI Events — KeyboardEvent.code](https://www.w3.org/TR/uievents/#key-key-values) | рекомендуемый neutral key_id |

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-05-30 | Первая версия: layout parity, cross-platform PhysicalKeyEvent, anti-WinAPI-in-core |
