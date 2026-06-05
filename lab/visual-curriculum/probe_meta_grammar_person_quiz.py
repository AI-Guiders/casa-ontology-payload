#!/usr/bin/env python3
"""L2 grammar meta — person category registry quiz (ADR-0030)."""

from __future__ import annotations

import argparse
import json

from probe_infra import generated_report_path, setup_probe_imports


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    args = p.parse_args()

    setup_probe_imports()
    from casa.prisms.visual.grammar_meta import grammar_meta_report

    report = grammar_meta_report("meta-grammar-person")
    report_path = generated_report_path("teacher-meta-grammar-person.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"wrote {report_path}")
    raise SystemExit(0 if report.get("pass") else 1)


if __name__ == "__main__":
    main()
