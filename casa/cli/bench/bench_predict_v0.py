#!/usr/bin/env python3
"""Bench Predictor v0: predict + critic on segment (and optional schema) cues."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from critic_v0 import critic_validate  # type: ignore
from predictor_v0 import predict  # type: ignore
from store_boot_v0 import boot_store  # type: ignore


def run_bench(
    state: dict,
    cues: list[dict],
    *,
    bundle: dict | None = None,
) -> dict:
    rows: list[dict] = []
    passed = 0
    for item in cues:
        cue = str(item.get("cue") or "")
        expect = item.get("expect") or item.get("expect_top")
        modality = str(item.get("modality") or "segment")
        pred = predict(state, cue, modality=modality, bundle=bundle)
        crit = critic_validate(
            pred,
            expect=str(expect) if expect is not None else None,
            expect_in=[str(x) for x in item.get("expect_in") or []] or None,
        )
        ok = crit["verdict"] in ("pass", "provisional") and crit["checks"][0].get("pass")
        if ok:
            passed += 1
        rows.append(
            {
                "id": item.get("id"),
                "modality": modality,
                "cue": cue,
                "expect": expect,
                "anchors": [
                    a.get("word") or a.get("concept_id") for a in pred.get("anchors") or []
                ][:6],
                "focus": pred.get("focus"),
                "hypothesis": pred.get("hypothesis"),
                "confidence": pred.get("confidence"),
                "lexicon_miss": pred.get("lexicon_miss"),
                "verdict": crit["verdict"],
                "clarify": crit.get("clarify"),
                "ok": ok,
            }
        )
    total = len(cues)
    return {
        "schema_version": 1,
        "bench": "predict_v0",
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / max(1, total), 3),
        "items": rows,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Bench predictor + critic v0")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--cues", type=Path, required=True)
    p.add_argument("--bundle", type=Path, default=None)
    p.add_argument("--boot-ltm-only", action="store_true", default=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    if not isinstance(cues, list):
        raise SystemExit("cues must be a JSON array")
    bundle = json.loads(args.bundle.read_text(encoding="utf-8")) if args.bundle else None

    boot = boot_store(args.store_dir, prefer_field_state=not args.boot_ltm_only)
    report = run_bench(boot["state"], cues, bundle=bundle)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
