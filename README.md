# CASA Bilingual T9 Demo

Research lab: **predictive text on a field** with **parallel EN/RU script branches** (homoglyphs).  
Not an LLM autocomplete — `anchors[]` from L2 lexicon + `unified_tick` (script → T9).

## Von-neumann — play locally

Living field agent (not LLM chat). **Guide:** [docs/CASA-von-neumann-local-play-v1.md](docs/CASA-von-neumann-local-play-v1.md)

Short path: clone [life-archive](https://github.com/AI-Guiders/von-neumann-life-archive) (private — ask for access) → `git lfs pull` → copy `store/` to `agents/von-neumann/` →:

```powershell
pip install -r tools/requirements.txt   # Python 3.12+
python -m casa.prisms.control.agent_sn_cen_tick --store-dir agents/von-neumann --query "Привет"
```

## Quick start (T9 bilingual demo)

```powershell
cd casa-ontology-payload

# Download third-party corpora (headwords, UD POS sidecars, EN folk texts)
python scripts/download_corpora.py

# Full cycle: init RU dev store + EN folk + all benches
python -m casa.cli run_t9_demo_cycle

# Interactive C# console (after cycle green)
dotnet run --project apps/Casa.T9.Console
```

Type `co` → see **EN: cow** and **RU: сова** candidates. `Esc` to quit.

## Components

| Piece | Role |
|-------|------|
| `python -m casa.cli init_ru_dev_store` | Minimal RU lexicon (~90 headwords) → `lexicon-ru-archaic/` |
| `python -m casa.cli init_en_folk_store` | EN folk lexicon → `lexicon-en-folk/` |
| `python -m casa.cli run_t9_demo_cycle` | Init + benches (ambiguous, T9, unified, linked) |
| `python -m casa.cli t9_runtime` | Python stdio JSON server for C# UI |
| `apps/Casa.T9.Console` | Interactive dual-column T9 demo |

## Python runtime protocol (stdio)

1. Start: `python -m casa.cli t9_runtime serve`
2. First line: `{"event":"ready","boot_ms":...}`
3. Per keystroke: `{"op":"tick","prefix":"co"}\n`
4. Response: `{"event":"tick","commitment":"ambiguous","branches":[...]}`
5. Quit: `{"op":"quit"}`

Env: `CASA_PYTHON` — path to python if not on PATH.

## Optional NCA train

T9 prefix rank uses **L2 votes on grid**; NCA not required for demo.

```powershell
python -m casa.cli run_t9_demo_cycle --train-nca --device cuda
```

## Design

- ADR: `design/CASA-ADR-0006-t9-predictive-text.md`
- Homoglyphs: `design/CASA-ADR-0003-emergent-forms-tags-predictor.md` § homoglyph vs confusable

**Status:** research preview, not production keyboard.

## License

- **Code:** [MIT](LICENSE) (Copyright AI-Guiders).
- **Data:** not shipped in git. See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) and run `python scripts/download_corpora.py` after clone.
