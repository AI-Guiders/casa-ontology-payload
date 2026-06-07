#!/usr/bin/env python3
"""L1 fluent whole-word read — Phase III exit (ADR-0049).

Honest status: routes through visual predict_lex held-out; not nositel gate.
Until green here, Block 12 interlocutor pass does not claim Phase III L1.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from probe_infra import default_store, generated_report_path, setup_probe_imports

_REPO = Path(__file__).resolve().parents[2]
_HELD_OUT = _REPO / "lessons/literacy-cards/data/block-05-corpus-cyrl-v1.json"
_PROBE = "probe_lexical_read_fluent_ru"


def main() -> None:
    setup_probe_imports()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    args = p.parse_args()

    store = default_store(args.store)
    out = generated_report_path(_PROBE)

    if not _HELD_OUT.is_file():
        payload = {
            "probe": _PROBE,
            "store_id": store.name,
            "status": "blocked",
            "reason": f"missing held-out spec: {_HELD_OUT}",
            "gate_pass": False,
            "phase": "III-L1",
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False))
        raise SystemExit(1)

    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent / "probe_literacy_corpus_quiz.py"),
        "--stage",
        "stage-06-words-cyrl-corpus",
    ]
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True)
    payload = {
        "probe": _PROBE,
        "store_id": store.name,
        "phase": "III-L1",
        "delegates_to": "probe_literacy_corpus_quiz:stage-06-words-cyrl-corpus",
        "exit_code": proc.returncode,
        "gate_pass": proc.returncode == 0,
        "stdout_tail": (proc.stdout or "")[-1200:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"probe": _PROBE, "gate_pass": payload["gate_pass"]}, ensure_ascii=False))
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
