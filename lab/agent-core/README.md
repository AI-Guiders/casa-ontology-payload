# Agent core ltm (immutable input modality)

Shared across agent profiles — **not** per lexicon store.

| Pack | Lattices | Role |
|------|----------|------|
| [alphabet](alphabet/) | `L0_grapheme_cyrl`, `L0_grapheme_latn` | **immutable** RU 33 + EN 26 (отдельные 32²) |
| [vk-layouts](vk-layouts/) | `L0_vk_physical`, `L0_layout_qwerty_us`, `L0_layout_jcuken_ru`, `L0_punct_latn`, `L0_punct_cyrl` | полные QWERTY + ЙЦУКЕН (+ shift), пунктуация, связь с `lang.*` и alphabet |

## Alphabet (listen once)

```bash
python tools/build_alphabet_core_ltm.py
python tools/bench_alphabet_core.py
# optional NCA on tiny 32² lattice:
python tools/build_alphabet_core_ltm.py --train-nca --device cuda
```

Design: [`design/alphabet-core-immutable.md`](../../design/alphabet-core-immutable.md)

## Listen → field

```bash
python tools/build_keyboard_layout_core_ltm.py
python tools/bench_keyboard_layout_core.py
python tools/vk_layout_ingest.py   # + modality KB on field
```

Design: [`design/keyboard-layout-core-immutable.md`](../../design/keyboard-layout-core-immutable.md)

Imprints **edges** on field (not flat lookup table):

```text
E:vk.physical.KeyA|layout.qwerty_us|grapheme.latn.a
```

**Modality listen** (как букварь для идей, не только букв): ingest кладёт `C:input.modality.*` и graph `E:` из [`kb-input-modality-vk.v1.json`](../exp_bilingual/kb-input-modality-vk.v1.json) на поле (рядом с compose-рёбрами раскладок). Tool: `input_modality_ingest.py`.

## Boot

Linked bilingual boot merges core ltm automatically. Decode: **field compose** via `vk_decode.py` (`decode_source: compose`).

Profile: `bilingual-layout-parity.json` → `core_ltm.ltm_dir`.

## Agent KB

Concepts for agents: [kb-input-modality-vk.v1.json](../exp_bilingual/kb-input-modality-vk.v1.json)  
Design note: [input-modality-vk-layout.md](../../design/input-modality-vk-layout.md)

## Benches

```bash
python tools/bench_vk_layout_field.py
python tools/bench_input_modality_field.py
python tools/bench_keyboard_full.py
python tools/bench_keyboard_ortho_bridge.py
python tools/bench_layout_parity.py
dotnet test apps/Casa.Act.Core.Tests   # lab oracle only
```

**Train:** VK = listen only (no NCA). Lexicon NCA → `agent_autonomous_tick --sleep --train-nca` or `nca_stale_shards --train`.
