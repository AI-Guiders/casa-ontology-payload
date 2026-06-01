# `tools/` — deps + CLI compat

Runtime lives in **`casa/`**. Run CLIs:

```powershell
python -m casa.cli store_boot --store-dir lab/agent-stores/lexicon-ru-general --smoke
# or backward compat:
python tools/run.py store_boot --store-dir ...
```

Module map: `casa/cli/cli_modules.json` (regenerate: `python scripts/generate_cli_modules.py`).

Python deps: `requirements-dev.txt` (pytest), `requirements.txt` (runtime).
