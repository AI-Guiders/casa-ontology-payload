#!/usr/bin/env python3
"""Paradigm select gate — pilot slug sets known in agent LTM (ADR-0036 W5)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports

_PROBE = "paradigm-select"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--min-votes", type=int, default=2)
    args = p.parse_args()

    setup_probe_imports()
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.visual.paradigm_ltm import pilot_paradigm_gate, write_paradigm_report

    store = default_store(args.store)
    report_path = generated_report_path("teacher-paradigm-select.json")

    with store_session_lock(store, holder=f"probe:{_PROBE}"):
        state = resolve_ingest_state(store, None)
        gate = pilot_paradigm_gate(state, min_votes=args.min_votes)
        write_paradigm_report(state, report_path.parent / "paradigm-ltm-report.json")
        out = {
            "store_id": args.store,
            "probe": _PROBE,
            "paradigm_select": gate.get("ok"),
            "pilot_sets": gate.get("pilot_sets"),
            "complete_sets": gate.get("complete_sets"),
            "clusters": gate.get("clusters"),
        }
        out = finalize_honest_probe_report(state, out, store=store, probe_id=_PROBE)

    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "probe": _PROBE,
                "paradigm_select": out.get("paradigm_select"),
                "complete_sets": gate.get("complete_sets"),
                "pilot_sets": gate.get("pilot_sets"),
                "gate_kind": out.get("gate_kind"),
                "path": str(report_path),
            },
            ensure_ascii=False,
        )
    )
    if not out.get("probe_gate", {}).get("passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
