#!/usr/bin/env python3
"""NUN-Bench freeze gate — machine verification of every record before a version freeze.

The generator is deterministic and every injection carries replay metadata, so the whole
dataset is checkable, not just a human-reviewed sample:

  REPLAY    — every injected error is reconstructed from the pool pair + its own metadata
              (apply ``replacement`` at ``char_span``) and must match the record byte for
              byte; the injector re-run on the pool pair must reproduce the same output.
  CONTROLS  — control pairs must be byte-identical to their pool pairs (nothing touched).
  POLARITY  — the corrupted side of a polarity record must carry NO surviving negation
              token (the flip is clean) while the pool original carries exactly one.
  CANARIES  — invented drug names only, all in the held-out split.
  STRUCTURE — counts per class, unique ids, one generator version, required fields.

Hard failures block the freeze (exit 1). REMARKS are surface-quality flags for the human
pass — records that are valid errors but worth eyeballing (leading-zero numbers «03 ml»,
section-number quantities «Dafiro 3.», physically absurd unit swaps «tablet contains 5 ml»).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from casa.curriculum.benchmark import _CANARY_DRUGS, _NEG_PATTERNS, INJECTORS

# negations that must NOT survive in a corrupted polarity side (concord leftovers)
_SURVIVING_NEG = re.compile(
    r"\b(no|not|never|nunca|ningún|ninguna|ningunos?|nadie|jamás|jamas)\b", re.IGNORECASE)

# «… Dafiro 3.» — a bare trailing number after a capitalized name: leaflet section number,
# not a dose; a quantity hit there is a valid discrepancy but a weak «dangerous» exemplar
_SECTION_NUM = re.compile(r"[A-ZÁÉÍÓÚÑ][\wÁ-ÿ]+\s+\d+\s*\.?\s*$")

# «tablet contains 5 ml» — a solid form with a volume unit: unambiguous but absurd
_ABSURD_UNIT = re.compile(
    r"\b(comprimido|cápsula|tablet|capsule)[\wÁ-ÿ\s]{0,40}?\b\d+(?:[.,]\d+)?\s*ml\b",
    re.IGNORECASE)


def _load_jsonl(path: str | Path) -> list[dict]:
    rows = []
    with Path(path).open(encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                rows.append(json.loads(ln))
    return rows


def verify_benchmark(bench_path: str | Path, pool_path: str | Path) -> dict[str, Any]:
    """Verify every record; returns a report with hard ``failures`` and soft ``remarks``."""
    bench = _load_jsonl(bench_path)
    pool = {r["id"]: r for r in _load_jsonl(pool_path)}

    failures: list[str] = []
    remarks: list[str] = []

    ids = [r["id"] for r in bench]
    if len(ids) != len(set(ids)):
        failures.append("duplicate record ids")
    versions = {r.get("generator") for r in bench}
    if len(versions) != 1:
        failures.append(f"mixed generator versions: {versions}")

    required = {"id", "src_lang", "tgt_lang", "src", "tgt", "label", "error_class",
                "injection", "source", "split", "kernel_parseable", "generator"}
    for r in bench:
        missing = required - r.keys()
        if missing:
            failures.append(f"{r.get('id', '?')}: missing fields {sorted(missing)}")

    errors = [r for r in bench if r["label"] == "error"]
    controls = [r for r in bench if r["label"] == "equivalent"]
    canaries = [r for r in bench if r["source"] == "canary"]

    for r in errors:
        inj = r["injection"]
        if not inj:
            failures.append(f"{r['id']}: error row without injection metadata")
            continue
        if r["source"] == "canary":
            continue  # canaries are fabricated, no pool original to replay from
        base = r["id"].rsplit("#", 1)[0]
        src_pair = pool.get(base)
        if src_pair is None:
            failures.append(f"{r['id']}: pool pair {base} not found")
            continue
        if r["src"] != src_pair["en"]:
            failures.append(f"{r['id']}: EN side differs from pool")
        # replay from metadata alone
        orig = src_pair["es"]
        s, e = inj["char_span"]
        if orig[s:e] != inj["original"]:
            failures.append(f"{r['id']}: char_span does not select `original` in the pool text")
            continue
        replay = orig[:s] + inj["replacement"] + orig[e:]
        if replay != r["tgt"]:
            failures.append(f"{r['id']}: metadata replay does not reproduce tgt")
        # full determinism: the injector itself reproduces the record
        res = INJECTORS[r["error_class"]](orig, "es", base)
        if res is None or res[0] != r["tgt"] or res[1] != inj:
            failures.append(f"{r['id']}: injector re-run does not reproduce the record")

        if r["error_class"] == "polarity":
            if _SURVIVING_NEG.search(r["tgt"]):
                failures.append(f"{r['id']}: negation survives in corrupted side — not a clean flip")
            n_orig = sum(len(re.findall(p, orig, flags=re.IGNORECASE)) for p in _NEG_PATTERNS["es"])
            if n_orig != 1:
                failures.append(f"{r['id']}: pool original has {n_orig} negations, expected exactly 1")
        elif r["error_class"] == "quantity":
            if re.search(r"\b0\d", inj["replacement"]):
                remarks.append(f"{r['id']}: corrupted number has a leading zero "
                               f"(«{inj['original']}» → «{inj['replacement']}») — reads as a typo")
            if _SECTION_NUM.search(r["tgt"]) and not re.search(
                    r"\d\s*(mg|ml|µg|mcg|g|l|°C|%)", r["tgt"], re.IGNORECASE):
                remarks.append(f"{r['id']}: trailing bare number — likely a leaflet section "
                               f"number, weak danger exemplar: «{r['tgt']}»")
        elif r["error_class"] == "unit":
            if _ABSURD_UNIT.search(r["tgt"]):
                remarks.append(f"{r['id']}: solid dose form with volume unit — unambiguous "
                               f"but physically absurd: «{r['tgt']}»")

    for r in controls:
        if r["source"] == "canary":
            continue
        base = r["id"].rsplit("#", 1)[0]
        src_pair = pool.get(base)
        if src_pair is None:
            failures.append(f"{r['id']}: pool pair {base} not found")
        elif r["src"] != src_pair["en"] or r["tgt"] != src_pair["es"]:
            failures.append(f"{r['id']}: control differs from pool pair — must be untouched")

    for r in canaries:
        if r["split"] != "heldout":
            failures.append(f"{r['id']}: canary leaked into the public split")
        if not any(d in r["src"] for d in _CANARY_DRUGS):
            failures.append(f"{r['id']}: canary without an invented drug name")

    per_class = {k: sum(1 for r in errors if r["error_class"] == k) for k in INJECTORS}
    report = {
        "total": len(bench), "errors": len(errors), "controls": len(controls),
        "per_class": per_class, "canaries": len(canaries),
        "heldout": sum(1 for r in bench if r["split"] == "heldout"),
        "parseable_errors": sum(1 for r in errors if r["kernel_parseable"]),
        "replayed": sum(1 for r in errors if r["source"] != "canary"),
        "failures": failures, "remarks": remarks,
        "verdict": "PASS" if not failures else "FAIL",
    }
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse

    from casa.curriculum.render import ensure_utf8_console

    ensure_utf8_console()
    ap = argparse.ArgumentParser(description="Verify a NUN-Bench build before freezing it.")
    ap.add_argument("--bench", default=".scratch/opus/nunbench-v0.1-draft.jsonl")
    ap.add_argument("--pool", default=".scratch/opus/emea-pairs-v1.jsonl")
    args = ap.parse_args(argv)

    report = verify_benchmark(args.bench, args.pool)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
