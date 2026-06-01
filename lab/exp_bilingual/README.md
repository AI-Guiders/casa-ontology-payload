# Exp bilingual v0 — EN lexicon + EN L1 + entity hub

Parallel lab (Multitask). Design: [`design/experiment-bilingual-entity.md`](../design/experiment-bilingual-entity.md).

Run from repo root `casa-ontology-payload/`.

## 0. Separate EN folk store + linked hub (production layout)

RU and EN live in **different stores**; runtime **linked boot** merges L2 namespaces for predict/hub.

```bash
# Batch ingest ~6700 EN headwords (Grimm + Jacobs; articles/the/and included)
python tools/init_en_folk_store.py \
  --headwords lab/exp_bilingual/en_folk_headwords.v1.txt

# Linked RU+EN + entity hub on L3 (no duplicate L2 imprint)
python tools/bench_bilingual_linked.py \
  --ru-store lab/agent-stores/lexicon-ru-general \
  --en-store lab/agent-stores/lexicon-en-folk \
  --bundle lab/exp_bilingual/kb-entity-surfaces-dev.v1.json
```

Expected linked bench: L2 **6/6**, T9 **3/3**, entity_hub **12/12**, cross_links **3/3**.

Gate script (track A): `scripts/run_bit9_gate.ps1` — **merged preview eval** (canonical) + linked + unified + ambiguous + runtime smoke.

### Merged BiT9 preview — **canonical eval** (`co` → сон/сок/сом + cow + корова)

Single pass/fail bench for product semantics: ipm-ranked EN/RU chip, hub injection, junk filter (`сол`), no early `сова` on 2-char prefix.

```bash
python tools/bench_bit9_merged_preview.py \
  --cues lab/exp_bilingual/merged_preview_eval_cues.v1.json \
  --out lab/exp_bilingual/reports/bit9_merged_preview.json
```

Expected **6/6** (`co_merged_bit9`, `c`/`cow`/`со`/`сов`/`сова` paths). Cues: `merged_preview_eval_cues.v1.json`. API: `merge_preview.py`, `bench_bit9_merged_preview.py`.

### Grapheme basin separability (ADR-0003)

```bash
python tools/bench_grapheme_clusters.py \
  --cues lab/exp_bilingual/grapheme_cluster_cues.v1.json
```

### Ortho inverse extract (Process lab)

Bootstrap **only** `Capitalize` + `Upper`; `Lower` emerges after surprise + Extract on **hot-path**:

```bash
python tools/bench_ortho_inverse.py
```

Expected **7/7**: `ortho_tick` (predict→act→critic→extract) — no manual extract in bench.

Single tick API: `tools/ortho_tick.py` → `ortho_tick()`, `simulate_ortho_plain_surprise()`.

### Script / language by letters (L0 basins, **commit mode**)

Each letter votes on `grapheme.latn.*` or `grapheme.cyrl.*` — **already picked script** (unambiguous cues only; homoglyph pairs like `co`/`со` → use ambiguous bench below):

```bash
python tools/bench_script_detect.py \
  --cues lab/exp_bilingual/script_detect_cues.v1.json
```

Expected **9/9** (`mother`, `мама`, `a` vs `а`; **not** `co` — that is pre-commit). API: `script_tick.py`, `script_detect.py`.

### Ambiguous prefix — **merged preview** (`co` → сон/сок/сом + cow)

Visual `co` is read as **both** latn and cyrl homoglyphs; **preview chip** interleaves EN + RU anchors (freq RU on `со`, EN homoglyph on `co`). Not the old `cow|сова` demo — hub pairs `cow↔корова` separately.

```bash
python tools/bench_ambiguous_prefix.py \
  --cues lab/exp_bilingual/ambiguous_prefix_cues.v1.json
```

Expected **2/2** tracks (`co_merged_bit9`, `ru_freq_co_path`). API: `merge_preview.py`, `ambiguous_prefix.py`.

## Bilingual T9 demo (console)

Full cycle + C# UI:

```bash
python tools/run_t9_demo_cycle.py
dotnet run --project apps/Casa.T9.Console
```

See repo [`README.md`](../../README.md).

### Unified macro-turn (script → T9 → hub)

One pipeline for typing: script layer (commit or ambiguous) → T9 per branch → optional entity hub:

```bash
python tools/bench_unified_tick.py \
  --cues lab/exp_bilingual/unified_tick_cues.v1.json
```

Expected **3/3** (`мама` RU type + hub, `cow` EN + hub, `co` ambiguous → `cow`). API: `unified_tick.py`.

### Cursive grapheme PNGs (Script MT / Propisi)

Export visual glyphs linked to `grapheme.latn.*` / `grapheme.cyrl.*`:

```bash
# Latin: ScriptS.ttf in fonts/ (or Script MT Bold fallback) — 26 PNGs
python tools/grapheme_glyph_export.py

python tools/bench_grapheme_glyphs.py
```

Output: `lab/exp_bilingual/grapheme-glyphs/{latn,cyrl}/*.png` + `manifest.v1.json`.  
**ScriptS.ttf** (fonts/) — both scripts; fallback: Script MT + Propisi.

Derives `grapheme.latn.*` (26) + `grapheme.cyrl.*` from lexicon — **no tags**. Checks L2/L0 basin purity and B/В cross-talk. Expected **8/8**.

Re-init EN store (adds L0 latn to field_state + ltm):

```bash
python tools/init_en_folk_store.py
```

## 1. English dev lexicon → L2 (legacy overlay on RU store)

```bash
python tools/ingest_en_lex_dev.py \
  --store-dir lab/agent-stores/lexicon-ru-archaic \
  --headwords lab/exp_bilingual/en_dev_headwords.v1.txt

python tools/bench_en_t9_smoke.py \
  --store-dir lab/agent-stores/lexicon-ru-archaic \
  --headwords lab/exp_bilingual/en_dev_headwords.v1.txt
```

Latin headwords → lex_sort «other» bucket (dev OK).

## 2. English syllables (L1 heuristics)

```bash
python tools/bench_segment_en.py \
  --cues lab/exp_bilingual/en_segment_cues.v1.json
```

## 3. Entity hub (сущность, не word=word)

```bash
python tools/entity_hub_ingest.py \
  --store-dir lab/agent-stores/lexicon-ru-archaic \
  --bundle lab/exp_bilingual/kb-entity-surfaces-dev.v1.json

python tools/bench_entity_hub.py \
  --store-dir lab/agent-stores/lexicon-ru-archaic \
  --bundle lab/exp_bilingual/kb-entity-surfaces-dev.v1.json
```

Model: `entity.cow` ← `E:denotes` ← `lang.word.cow` / `lang.word.корова`.

## Smoke (all three)

```bash
python tools/bench_segment_en.py --cues lab/exp_bilingual/en_segment_cues.v1.json
python tools/bench_en_t9_smoke.py --store-dir lab/agent-stores/lexicon-ru-archaic --headwords lab/exp_bilingual/en_dev_headwords.v1.txt
python tools/bench_entity_hub.py --store-dir lab/agent-stores/lexicon-ru-archaic --bundle lab/exp_bilingual/kb-entity-surfaces-dev.v1.json
```

Expected: segment **10/10**, en_t9 **12/12**, entity_hub **12/12**.
