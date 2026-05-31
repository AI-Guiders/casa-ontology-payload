# `tools/` — deps + CLI compat

Runtime lives in **`casa/`**. Run CLIs:

```powershell
python -m casa.cli store_boot_v0 --store-dir lab/agent-stores/sss-ru-general-v0 --smoke
# or backward compat:
python tools/run.py store_boot_v0 --store-dir ...
```

Module map: `casa/cli/legacy_manifest.json` (274 entries).

Python deps: `requirements-dev.txt` (pytest), `requirements.txt` (runtime).
