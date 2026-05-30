# CASA Bilingual T9 Demo

Research lab: **predictive text on a field** with **parallel EN/RU script branches** (homoglyphs).  
Not an LLM autocomplete — `anchors[]` from L2 lexicon + `unified_tick` (script → T9).

## Quick start

```powershell
cd casa-ontology-payload

# Full cycle: init RU dev store + EN folk + all benches
python tools/run_t9_demo_cycle_v0.py

# Interactive C# console (after cycle green)
dotnet run --project apps/Casa.T9.Console
```

Type `co` → see **EN: cow** and **RU: сова** candidates. `Esc` to quit.

## Components

| Piece | Role |
|-------|------|
| `tools/init_ru_dev_store_v0.py` | Minimal RU lexicon (~90 headwords) → `sss-ru-lexicon-v0/` |
| `tools/init_en_folk_store_v0.py` | EN folk lexicon → `sss-en-folk-v0/` |
| `tools/run_t9_demo_cycle_v0.py` | Init + benches (ambiguous, T9, unified, linked) |
| `tools/t9_runtime_v0.py` | Python stdio JSON server for C# UI |
| `apps/Casa.T9.Console` | Interactive dual-column T9 demo |

## Python runtime protocol (stdio)

1. Start: `python tools/t9_runtime_v0.py serve`
2. First line: `{"event":"ready","boot_ms":...}`
3. Per keystroke: `{"op":"tick","prefix":"co"}\n`
4. Response: `{"event":"tick","commitment":"ambiguous","branches":[...]}`
5. Quit: `{"op":"quit"}`

Env: `CASA_PYTHON` — path to python if not on PATH.

## Optional NCA train

T9 prefix rank uses **L2 votes on grid**; NCA not required for demo.

```powershell
python tools/run_t9_demo_cycle_v0.py --train-nca --device cuda
```

## Design

- ADR: `design/CASA-ADR-0006-t9-predictive-text.md`
- Homoglyphs: `design/CASA-ADR-0003-emergent-forms-tags-predictor.md` § homoglyph vs confusable

**Status:** research preview, not production keyboard.
