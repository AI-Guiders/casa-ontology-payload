# Immutable keyboard layouts (QWERTY + JCUKEN)

**Date:** 2026-05-30  
**Status:** lab  
**Pack:** `lab/agent-core/vk-layouts/ltm/`  
**Sources:** `design/keyboard-layouts/*.toml`

## Решётки (не смешивать)

| Lattice | Роль |
|---------|------|
| `L0_vk_physical` | 48×48 — физические клавиши, modifiers, zones |
| `L0_layout_qwerty_us` | 32×32 — полный QWERTY (+ shift layer) → `grapheme.latn.*` |
| `L0_layout_jcuken_ru` | 32×32 — полный ЙЦУКЕН → `grapheme.cyrl.*` |
| `L0_punct_latn` | пунктуация/символы EN-раскладки → `grapheme.latn.*` |
| `L0_punct_cyrl` | пунктуация/символы RU-раскладки → `grapheme.cyrl.*` |

Алфавит букв — отдельный pack [`alphabet-core-immutable.md`](alphabet-core-immutable.md) (`L0_grapheme_cyrl` / `L0_grapheme_latn`).

## Соответствие языку

На каждой layout-решётке (meta + рёбра):

```text
C:layout.qwerty_us
E:layout.qwerty_us|locale|lang.en
E:layout.qwerty_us|alphabet_lattice|L0_grapheme_latn
E:layout.qwerty_us|punct_lattice|L0_punct_latn

C:layout.jcuken_ru
E:layout.jcuken_ru|locale|lang.ru
E:layout.jcuken_ru|alphabet_lattice|L0_grapheme_cyrl
E:layout.jcuken_ru|punct_lattice|L0_punct_cyrl
```

Пунктуация: `C:punct.latn.,` + `E:punct.latn.,|realizes|grapheme.latn.,`

## Команды

```bash
python tools/build_keyboard_layout_core_ltm.py
python tools/build_keyboard_layout_core_ltm.py --train-nca --device cuda
python tools/bench_keyboard_layout_core.py
```

Legacy монолит `L0_vk_map` **не экспортируется** в новых pack; decode собирает index с `L0_layout_qwerty_us` + `L0_layout_jcuken_ru`.
