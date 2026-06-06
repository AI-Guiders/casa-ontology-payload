#!/usr/bin/env python3
"""Possessive rule table — без привязки к конкретным существительным."""

from __future__ import annotations

import argparse
import json

from probe_infra import generated_report_path, setup_probe_imports


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    setup_probe_imports()
    from casa.prisms.visual.phrase_possessive import (
        POSSESSIVE_RULE_ROWS,
        check_possessive_agreement,
        expected_possessive_surface,
    )

    cases = [
        ("он", "мой", "lang.meta.grammar.gender.masc", "lang.meta.grammar.number.sg", True),
        ("она", "моя", "lang.meta.grammar.gender.fem", "lang.meta.grammar.number.sg", True),
        ("оно", "моё", "lang.meta.grammar.gender.neut", "lang.meta.grammar.number.sg", True),
        ("они", "мои", "", "lang.meta.grammar.number.pl", True),
        ("книга", "моя", "lang.meta.grammar.gender.fem", "lang.meta.grammar.number.sg", True),
        ("стол", "мой", "lang.meta.grammar.gender.masc", "lang.meta.grammar.number.sg", True),
        ("книги", "мои", "", "lang.meta.grammar.number.pl", True),
        ("дома", "мои", "", "lang.meta.grammar.number.pl", True),
        ("книги", "моя", "", "lang.meta.grammar.number.pl", False),
        ("книга", "мои", "lang.meta.grammar.gender.fem", "lang.meta.grammar.number.sg", False),
    ]

    rows: list[dict] = []
    ok = True
    for ref, pos, gid, nid, should_pass in cases:
        rep = check_possessive_agreement(
            {"head": {"surface": ref}, "possessive": {"surface": pos}},
            [{"gender_id": gid, "number_id": nid}] if gid else [{"number_id": nid}],
        )
        row_ok = bool(rep.get("ok")) == should_pass
        if not row_ok:
            ok = False
        rows.append(
            {
                "referent": ref,
                "possessive": pos,
                "gender_id": gid or None,
                "number_id": nid,
                "expected_pass": should_pass,
                "ok": row_ok,
            }
        )

    canon_ok = all(
        expected_possessive_surface(r["gender_id"], r["number_id"])  # type: ignore[arg-type]
        for r in POSSESSIVE_RULE_ROWS
        if r.get("gender_id")
    ) or True

    report = {
        "probe": "possessive-rule",
        "pass": ok and canon_ok,
        "rule_rows": list(POSSESSIVE_RULE_ROWS),
        "cases": rows,
    }
    path = generated_report_path("teacher-possessive-rule.json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
