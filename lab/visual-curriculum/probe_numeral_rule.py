#!/usr/bin/env python3
"""Numeral class rule — без привязки к JSON examples."""

from __future__ import annotations

import argparse
import json

from probe_infra import generated_report_path, setup_probe_imports


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    setup_probe_imports()
    from casa.prisms.visual.phrase_numeral import (
        DECLENSION_FEM_A_PALATAL,
        NUMERAL_RULE_ROWS,
        check_numeral_agreement,
        numeral_form_class,
    )

    gid = "lang.meta.grammar.gender.fem"
    lemma = "палка"
    row = [{"gender_id": gid, "declension_id": DECLENSION_FEM_A_PALATAL}]
    cases = [
        ("одна", "палка", True),
        ("две", "палки", True),
        ("три", "палки", True),
        ("четыре", "палки", True),
        ("пять", "палок", True),
        ("пять", "палки", False),
        ("одна", "палки", False),
        ("две", "палка", False),
        ("два", "палки", False),
    ]

    rows: list[dict] = []
    ok = True
    for num, head, should_pass in cases:
        rep = check_numeral_agreement(
            {"numeral": {"surface": num}, "head": {"surface": head}},
            row,
            example_lemma=lemma,
        )
        row_ok = bool(rep.get("ok")) == should_pass
        if not row_ok:
            ok = False
        rows.append(
            {
                "numeral": num,
                "head": head,
                "expected_pass": should_pass,
                "ok": row_ok,
                "detail": rep.get("details", [{}])[0],
            }
        )

    report = {
        "probe": "numeral-rule",
        "pass": ok,
        "rule_rows": list(NUMERAL_RULE_ROWS),
        "class_samples": {str(n): numeral_form_class(n) for n in (1, 2, 5, 11, 21, 22)},
        "cases": rows,
    }
    path = generated_report_path("teacher-numeral-rule.json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
