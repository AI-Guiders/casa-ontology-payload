#!/usr/bin/env python3
"""L3 grammar meta — subject-verb agreement pairs quiz (ADR-0030)."""

from __future__ import annotations

import json

from probe_infra import generated_report_path, setup_probe_imports


def main() -> None:
    setup_probe_imports()
    from casa.prisms.visual.grammar_meta import grammar_meta_report

    report = grammar_meta_report("meta-grammar-agreement")
    report_path = generated_report_path("teacher-meta-grammar-agreement.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"wrote {report_path}")
    raise SystemExit(0 if report.get("pass") else 1)


if __name__ == "__main__":
    main()
