# Exp bilingual v0 — EN lexicon + EN L1 + entity hub

Parallel lab (Multitask). Design: [`design/experiment-bilingual-entity-v0.md`](../design/experiment-bilingual-entity-v0.md).

Run from repo root `casa-ontology-payload/`.

## 0. Separate EN folk store + linked hub (production layout)

RU and EN live in **different stores**; runtime **linked boot** merges L2 namespaces for predict/hub.

```bash
# Batch ingest ~6700 EN headwords (Grimm + Jacobs; articles/the/and included)
python tools/init_en_folk_store_v0.py \
  --headwords examples/exp_bilingual_v0/en_folk_headwords.v1.txt

# Linked RU+EN + entity hub on L3 (no duplicate L2 imprint)
python tools/bench_bilingual_linked_v0.py \
  --ru-store examples/agent-stores/sss-ru-lexicon-v0 \
  --en-store examples/agent-stores/sss-en-folk-v0 \
  --bundle examples/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json
```

Expected linked bench: L2 **6/6**, T9 **3/3**, entity_hub **12/12**, cross_links **3/3**.

### Grapheme basin separability (ADR-0003)

```bash
python tools/bench_grapheme_clusters_v0.py \
  --cues examples/exp_bilingual_v0/grapheme_cluster_cues.v1.json
```

### Ortho inverse extract (Process lab)

Bootstrap **only** `Capitalize` + `Upper`; `Lower` emerges after surprise + Extract on **hot-path**:

```bash
python tools/bench_ortho_inverse_v0.py
```

Expected **7/7**: `ortho_tick` (predict→act→critic→extract) — no manual extract in bench.

Single tick API: `tools/ortho_tick_v0.py` → `ortho_tick()`, `simulate_ortho_plain_surprise()`.

### Script / language by letters (L0 basins, **commit mode**)

Each letter votes on `grapheme.latn.*` or `grapheme.cyrl.*` — **already picked script** (unambiguous cues only; homoglyph pairs like `co`/`со` → use ambiguous bench below):

```bash
python tools/bench_script_detect_v0.py \
  --cues examples/exp_bilingual_v0/script_detect_cues.v1.json
```

Expected **9/9** (`mother`, `мама`, `a` vs `а`; **not** `co` — that is pre-commit). API: `script_tick_v0.py`, `script_detect_v0.py`.

### Ambiguous prefix — **pre-commit** (`co` → cow | сова)

Visual stream may be read as **both** latn and cyrl homoglyphs until a letter breaks the fork (`w` in `cow` locks EN; RU `сова` continues on **real Cyrillic** `со`→`сов`, not via `b`/`в` — those are confusables, not homoglyphs):

```bash
python tools/bench_ambiguous_prefix_v0.py \
  --cues examples/exp_bilingual_v0/ambiguous_prefix_cues.v1.json
```

Expected **2/2** tracks. API: `ambiguous_prefix_v0.py`, `homoglyph_v0.py`. Distinct from strict `script_detect` (which commits early when glyphs are unambiguous).

## Bilingual T9 demo (console)

Full cycle + C# UI:

```bash
python tools/run_t9_demo_cycle_v0.py
dotnet run --project apps/Casa.T9.Console
```

See repo [`README.md`](../../README.md).

### Unified macro-turn (script → T9 → hub)

One pipeline for typing: script layer (commit or ambiguous) → T9 per branch → optional entity hub:

```bash
python tools/bench_unified_tick_v0.py \
  --cues examples/exp_bilingual_v0/unified_tick_cues.v1.json
```

Expected **3/3** (`мама` RU type + hub, `cow` EN + hub, `co` ambiguous → `cow`). API: `unified_tick_v0.py`.

### Cursive grapheme PNGs (Script MT / Propisi)

Export visual glyphs linked to `grapheme.latn.*` / `grapheme.cyrl.*`:

```bash
# Latin: ScriptS.ttf in fonts/ (or Script MT Bold fallback) — 26 PNGs
python tools/grapheme_glyph_export_v0.py

python tools/bench_grapheme_glyphs_v0.py
```

Output: `examples/exp_bilingual_v0/grapheme-glyphs/{latn,cyrl}/*.png` + `manifest.v1.json`.  
**ScriptS.ttf** (fonts/) — both scripts; fallback: Script MT + Propisi.

Derives `grapheme.latn.*` (26) + `grapheme.cyrl.*` from lexicon — **no tags**. Checks L2/L0 basin purity and B/В cross-talk. Expected **8/8**.

Re-init EN store (adds L0 latn to field_state + ltm):

```bash
python tools/init_en_folk_store_v0.py
```

## 1. English dev lexicon → L2 (legacy overlay on RU store)

```bash
python tools/ingest_en_lex_dev_v0.py \
  --store-dir examples/agent-stores/sss-ru-lexicon-v0 \
  --headwords examples/exp_bilingual_v0/en_dev_headwords.v1.txt

python tools/bench_en_t9_smoke_v0.py \
  --store-dir examples/agent-stores/sss-ru-lexicon-v0 \
  --headwords examples/exp_bilingual_v0/en_dev_headwords.v1.txt
```

Latin headwords → lex_sort «other» bucket (dev OK).

## 2. English syllables (L1 heuristics)

```bash
python tools/bench_segment_en_v0.py \
  --cues examples/exp_bilingual_v0/en_segment_cues.v1.json
```

## 3. Entity hub (сущность, не word=word)

```bash
python tools/entity_hub_ingest_v0.py \
  --store-dir examples/agent-stores/sss-ru-lexicon-v0 \
  --bundle examples/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json

python tools/bench_entity_hub_v0.py \
  --store-dir examples/agent-stores/sss-ru-lexicon-v0 \
  --bundle examples/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json
```

Model: `entity.cow` ← `E:denotes` ← `lang.word.cow` / `lang.word.корова`.

## Smoke (all three)

```bash
python tools/bench_segment_en_v0.py --cues examples/exp_bilingual_v0/en_segment_cues.v1.json
python tools/bench_en_t9_smoke_v0.py --store-dir examples/agent-stores/sss-ru-lexicon-v0 --headwords examples/exp_bilingual_v0/en_dev_headwords.v1.txt
python tools/bench_entity_hub_v0.py --store-dir examples/agent-stores/sss-ru-lexicon-v0 --bundle examples/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json
```

Expected: segment **10/10**, en_t9 **12/12**, entity_hub **12/12**.
