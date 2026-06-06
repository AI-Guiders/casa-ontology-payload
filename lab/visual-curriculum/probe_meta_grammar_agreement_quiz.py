#!/usr/bin/env python3
"""L3 grammar meta — subject-verb agreement pairs quiz (ADR-0030)."""

from __future__ import annotations

from probe_infra import run_spec_regression, setup_probe_imports


def main() -> None:
    setup_probe_imports()
    from casa.prisms.visual.grammar_meta import grammar_meta_report

    report = run_spec_regression(
        grammar_meta_report("meta-grammar-agreement"),
        report_filename="teacher-meta-grammar-agreement.json",
    )
    raise SystemExit(0 if report.get("verdict_pass") else 1)


if __name__ == "__main__":
    main()
