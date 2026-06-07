#!/usr/bin/env python3
"""Block 9c gate — morph segment binds + held-out frames (morph-role-ru)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_CURRICULUM = Path(__file__).resolve().parent
if str(_CURRICULUM) not in sys.path:
    sys.path.insert(0, str(_CURRICULUM))

from probe_block_held_out import _run_frame_gate  # noqa: E402
from probe_infra import setup_probe_imports  # noqa: E402

_BLOCK = "block-09c-morphemics-cyrl"
_PROBE = "probe_morphemics_ru_v0"


def main() -> None:
    setup_probe_imports()
    from block_pedagogy import load_block_spec

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--spec", type=Path, default=None)
    args = p.parse_args()

    spec = load_block_spec(args.spec, block_id=_BLOCK)
    spec.setdefault("gate", {})["probe_id"] = _PROBE
    report = _run_frame_gate(spec, block_id=_BLOCK, store_id=args.store)
    print(
        json.dumps(
            {
                "probe": _PROBE,
                "know": report.get("know"),
                "total": report.get("total"),
                "morph_bind_ok": (report.get("morph_segment_bind") or {}).get("ok"),
                "gate_pass": report.get("gate_pass"),
                "path": str(_CURRICULUM / "generated" / f"teacher-probe-{_BLOCK}-held-out.json"),
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if report.get("gate_pass") else 1)


if __name__ == "__main__":
    main()
