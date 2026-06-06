#!/usr/bin/env python3
"""L2 grammar meta — person category registry quiz (ADR-0030)."""

from __future__ import annotations

import argparse
import json

from probe_infra import run_spec_regression, setup_probe_imports


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    args = p.parse_args()

    setup_probe_imports()
    from casa.prisms.visual.grammar_meta import grammar_meta_report

    report = run_spec_regression(
        grammar_meta_report("meta-grammar-person"),
        report_filename="teacher-meta-grammar-person.json",
    )
    raise SystemExit(0 if report.get("verdict_pass") else 1)


if __name__ == "__main__":
    main()
