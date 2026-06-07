#!/usr/bin/env python3
import json
import re
from pathlib import Path

store = Path("agents/von-neumann")
legacy_re = re.compile(r"^(L[0-3]|F[0-2]|H[0-3]|lattice_)")


def is_legacy(s: str) -> bool:
    return bool(legacy_re.match(str(s or "")))


fs = store / "field_state.json"
if fs.is_file():
    data = json.loads(fs.read_text(encoding="utf-8"))
    lats = (data.get("prisms") or {}).get("prism_memory", {}).get("lattices", {})
    leg = sorted(k for k in lats if is_legacy(k))
    print("field_state legacy lattices:", len(leg), leg[:25])
    eps = (data.get("prisms") or {}).get("prism_hippo", {}).get("episodes") or []
    el = sorted({e.get("lattice_id") for e in eps if is_legacy(str(e.get("lattice_id") or ""))})
    print("hippo episode legacy lattice_ids:", el)

manifest = store / "ltm/pack.manifest.json"
if manifest.is_file():
    m = json.loads(manifest.read_text(encoding="utf-8"))
    keys = list((m.get("lattices") or {}).keys())
    leg = [k for k in keys if is_legacy(k)]
    print("manifest legacy keys:", len(leg), leg[:25])

nca = store / "nca"
if nca.is_dir():
    nd = sorted(d.name for d in nca.iterdir() if d.is_dir() and is_legacy(d.name))
    print("nca legacy dirs:", len(nd), nd[:25])
