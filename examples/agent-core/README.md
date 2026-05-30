# Agent core ltm (immutable input modality)

Shared across agent profiles — **not** per lexicon store.

| Pack | Lattices | Role |
|------|----------|------|
| [vk-layouts-v0](vk-layouts-v0/) | `L0_vk_map`, `L0_grapheme` | vk.physical.* → layout.* → grapheme.* (compose) |

## Listen → field

```bash
python tools/vk_layout_ingest_v0.py
```

Imprints **edges** on field (not flat lookup table):

```text
E:vk.physical.KeyA|layout.qwerty_us|grapheme.latn.a
```

**Modality listen** (как букварь для идей, не только букв): тот же ingest кладёт `C:input.modality.*` и graph `E:` из [`kb-input-modality-vk.v1.json`](../exp_bilingual_v0/kb-input-modality-vk.v1.json) на `L0_vk_map`. Tool: `input_modality_ingest_v0.py`.

## Boot

Linked bilingual boot merges core ltm automatically. Decode: **field compose** via `vk_decode_v0.py` (`decode_source: compose`).

Profile: `bilingual-layout-parity.v0.json` → `core_ltm.ltm_dir`.

## Agent KB

Concepts for agents: [kb-input-modality-vk.v1.json](../exp_bilingual_v0/kb-input-modality-vk.v1.json)  
Design note: [input-modality-vk-layout-v0.md](../../design/input-modality-vk-layout-v0.md)

## Benches

```bash
python tools/bench_vk_layout_field_v0.py
python tools/bench_input_modality_field_v0.py
python tools/bench_keyboard_full_v0.py
python tools/bench_keyboard_ortho_bridge_v0.py
python tools/bench_layout_parity_v0.py
dotnet test apps/Casa.Act.Core.Tests   # lab oracle only
```

**Train:** VK = listen only (no NCA). Lexicon NCA → `agent_autonomous_tick_v0 --sleep --train-nca` or `nca_stale_shards_v0 --train`.
