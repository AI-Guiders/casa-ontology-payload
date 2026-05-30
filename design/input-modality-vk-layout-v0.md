# Input modality: physical keys & keyboard layouts (v0)

**Status:** lab v1 (full keyboard compose + shift layer)  
**ADR:** [CASA-ADR-0008](CASA-ADR-0008-layout-parity-bilingual-t9.md)  
**KB bundle:** [kb-input-modality-vk.v1.json](../lab/exp_bilingual_v0/kb-input-modality-vk.v1.json)

## Для агента (кратко)

| Термин | Что это | Не путать с |
|--------|---------|-------------|
| **PhysicalKeyEvent** | Нажатие физической клавиши (`key_id` = `KeyA`, `Slash`) | Unicode из OS / WinAPI VK |
| **Layout** | Таблица decode: те же keys → другие буквы (`qwerty_us`, `jcuken_ru`) | Homoglyph (один glyph, два Unicode) |
| **Layout parity** | Два decode параллельно → argmax по segment (prose/command) | Переключение языка в трее |
| **L0_vk_map** | Память на поле: `vk.physical.*` + рёбра к `grapheme.*` | Lookup dict в C# |
| **Shift layer** | `layout.qwerty_us.shift` → `output.A` / symbols | Отдельная OS-раскладка |
| **Modifier / action** | `E:vk.physical.ShiftLeft\|role\|modifier.shift` | Grapheme emit |
| **core ltm** | Ship-формат решётки (`.ltm`) | Сама логика decode |

## Для CASA (listen, как букварь)

Как `grapheme.*` отпечатываются на **L0_grapheme** через `ingest_graphemes_batch`, так **идеи** клавиатуры слушаются из KB bundle → поле:

```bash
python tools/vk_layout_ingest_v0.py          # vk map + modality в core ltm
python tools/input_modality_ingest_v0.py       # только listen bundle → store
python tools/bench_input_modality_field_v0.py
python tools/bench_keyboard_full_v0.py
```

Каталог клавиш: [`keyboard-keys.v0.json`](../design/keyboard-layouts/keyboard-keys.v0.json) — modifiers, actions, navigation, Fn, zones (~99 physical keys на поле).

Bundle: [`kb-input-modality-vk.v1.json`](../lab/exp_bilingual_v0/kb-input-modality-vk.v1.json)  
Ingest: `input_modality_ingest_v0.ingest_input_modality` — `C:input.modality.*`, `C:layout.*`, `E:src|relation|dst` на **L0_vk_map** (рядом с compose-рёбрами vk→grapheme).

```text
C:input.device.keyboard
C:modifier.shift
E:vk.physical.ShiftLeft|role|modifier.shift
E:vk.physical.Enter|role|action.enter
E:vk.physical.KeyA|layout.qwerty_us.shift|output.A
E:vk.physical.KeyA|zone|zone.alphanumeric
```

Boot linked store подтягивает core ltm — CASA уже «знает» термины без отдельного RAG.

## Слои (ADR-0008)

```text
L0 act     platform → PhysicalKeyEvent[]     (CIDE capture only)
L1 field   vk.physical.KeyA ──E:layout.qwerty_us──► grapheme.latn.a
L2 CASA    grapheme string → homoglyph? → dual T9 → preview
```

**Listen (один раз):** `design/keyboard-layouts/*.json` → `vk_layout_ingest_v0.py`  
**Hot path:** boot `core_ltm` → field RAM → `vk_decode_v0` (compose index из рёбер) → `layout_tick`

## На поле (compose v1)

```text
C:vk.physical.KeyA
E:vk.physical.KeyA|layout.qwerty_us|grapheme.latn.a
E:vk.physical.KeyA|layout.qwerty_us.shift|output.A
E:vk.physical.KeyA|layout.jcuken_ru|grapheme.cyrl.ф
E:vk.physical.ShiftLeft|role|modifier.shift
E:vk.physical.Enter|role|action.enter
```

Decode: `vk_decode_v0` держит modifier state (Shift down/up, **Caps Lock toggle**), выбирает base vs `.shift` layer; action keys → control glyphs (`\n`, `\b`, …).

## Мост keyboard ↔ ortho (listen, L3)

Три регистра ввода (не путать с emergent ortho):

| Регистр | Клавиатура | Ortho (display) |
|---------|------------|-----------------|
| **lowercase (default)** | `base_layer`, без модификаторов → `layout.qwerty_us` / `jcuken_ru` | `ortho.display.lowercase_register` |
| **upper / shift** | Shift или latch → `.shift` layer | `proc.grapheme.capitalize` |
| **ALL CAPS** | Caps Lock latch | `proc.word.upper` |

**`proc.grapheme.lower`** (emergent после surprise в `bench_ortho_inverse`) — **не** «клавиатура в lower». Это inverse Capitalize для **исправления surface**, когда Predict перекапитализировал. На поле: `distinct_from` → `ortho.display.lowercase_register`.

Listen (`keyboard_ortho_bridge_v0`):

```text
E:input.modality.layout|has_layer|input.modality.base_layer
E:input.modality.base_layer|standard_register|ortho.display.lowercase_register
E:proc.grapheme.lower|distinct_from|ortho.display.lowercase_register
E:proc.grapheme.lower|emergent_inverse|proc.grapheme.capitalize
```

Shift / Caps — как раньше (`surface_effect` → capitalize / upper).

## Тренировка (когда и что)

| Что | Train? | Когда |
|-----|--------|-------|
| **VK / keyboard / layouts** | **Да, NCA repair** | после `vk_layout_ingest_v0.py` → `vk_nca_train_v0.py` на `L0_vk_map` (+ `L0_grapheme`); **только CUDA** |
| **Modality KB (идеи)** | listen на поле | вместе с ingest, `C:`/`E:` на `L0_vk_map` |
| **Lexicon L2 (слова)** | **Да, NCA** | sleep после wake miss / cold ingest |

Содержимое клавиатуры — **immutable listen** (JSON → core `ltm/`). **NCA** — не энциклопедия, а **иммунитет поля**: восстановление после damage на hot path decode не нужен.

```bash
# core VK repair (CUDA обязателен)
python tools/vk_nca_train_v0.py --device cuda

# lexicon shards (CUDA по умолчанию)
python tools/agent_autonomous_tick_v0.py --store-dir lab/agent-stores/sss-ru-lexicon-v0 --sleep --train-nca
python tools/nca_stale_shards_v0.py --store-dir lab/agent-stores/sss-en-folk-v0 --train --device cuda
```

**Lexicon:** тренить при pending/stale shards (cold ingest, новые headwords). **VK:** один раз после ingest или при смене layout pack.

## Что не делать

- **C# / act не парсят `.ltm` в prod** — только boot поля и CASA readout (C# oracle — lab tests).
- **Не путать listen и NCA:** JSON/layout не «учится» эпохами; NCA только чинит lattice после повреждения.
- **Не гонять train на CPU** для VK/L2 repair в lab — `--device cuda` (или default скриптов).
- **Homoglyph ≠ layout** — `co`/`со` vs QWERTY muscle на ЙЦУКEN.

## Команды

```bash
python tools/vk_layout_ingest_v0.py
python tools/bench_vk_layout_field_v0.py
python tools/bench_keyboard_full_v0.py
python tools/bench_layout_parity_v0.py
```
