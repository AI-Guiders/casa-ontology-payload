#!/usr/bin/env python3
"""Source-quality filter for the aligned EMEA pool — drop garbled pairs before injection.

The EMEA bitext is a real, noisy corpus: some lines are OCR/segmentation artifacts —
truncated mid-clause, stray bracket debris («…ácido,), sal»), unclosed parentheses, or
several distinct label instructions concatenated with no separator. Injecting into those
produces «errors» a human verifier rejects (the LLM-assisted review of v0.1.1 surfaced a
handful). This filter removes them by PATTERN, not by an id blacklist, so it cleans the
whole pool — including garbled records that simply weren't drawn for injection — and is a
single documented, reproducible preprocessing step for the paper.

Rules are conservative (high precision — a dropped good pair costs coverage, a kept garbled
pair costs a verifier's trust, and we would rather keep than wrongly drop). Every rule
carries a reason so a rejects file can be eyeballed. Whole-pair rejection: if EITHER side
trips a rule, the pair goes.
"""

from __future__ import annotations

import re
from typing import Any

# --- rule patterns -------------------------------------------------------------------------

# stray bracket debris: «,)» «),» «()» «),)» — segmentation left punctuation with no content
_BRACKET_DEBRIS = re.compile(r",\s*\)|\)\s*,|\(\s*\)|\)\s*\)|\(\s*,")

# a capitalized COMMON word right after a lowercase word with no punctuation between them is
# a run-on of two instructions («…refrigerator Do not freeze…»). A capitalized DRUG name in
# that position is normal («…while taking Bondenza»), so only flag lowercase→Capitalized when
# the capitalized word is an ordinary title/instruction word; ≥2 such joins = a concatenation.
_RUNON_JOIN = re.compile(
    r"[a-záéíóúñ]\s+(?:Do|Does|Store|Keep|Shake|Read|Use|Take|Conservar|Mantener|Agitar|"
    r"Leer|Usar|Tomar|No|Not|Before|Antes|After|Warning|Caution)\b")

# a bare measurement unit at the very start = a mid-clause cut («g of granules contains…»,
# «mg sucrose, 1.11 mg disodium phosphate…»). ONLY units — a leading article/connective is
# too noisy (a capital «The …» / «De …» opens a normal sentence), so it is not a signal.
_FRAGMENT_HEAD = re.compile(r"^\s*(?:mg|ml|µg|mcg|kg|g|l)\b")


def _reasons(text: str) -> list[str]:
    """Quality problems on one side of a pair (empty list = clean)."""
    t = str(text or "").strip()
    out: list[str] = []
    if not t:
        return ["empty"]
    if _BRACKET_DEBRIS.search(t):
        out.append("bracket-debris")
    if t.count("(") != t.count(")"):
        out.append("unbalanced-parens")
    if len(_RUNON_JOIN.findall(t)) >= 2:
        out.append("concatenated-instructions")
    if _FRAGMENT_HEAD.match(t):
        out.append("fragment-head")
    # a clause that ends with a dangling article/preposition/connective was truncated
    # («…contiene 625 mg de», «…side effects not listed in the»). A trailing bare noun is
    # NOT flagged (that is a lossy-but-complete pair, e.g. «…3 mg de ácido»).
    if _TRUNCATED_TAIL.search(t):
        out.append("truncated-tail")
    return out


_TRUNCATED_TAIL = re.compile(
    r"\b(?:of|and|or|the|a|an|in|on|at|to|for|with|by|from|"
    r"de|del|la|el|los|las|un|una|y|o|en|con|por|para)\s*$", re.IGNORECASE)


def pair_reasons(row: dict[str, Any]) -> list[str]:
    """All quality reasons to reject a pair (side-tagged); empty = keep."""
    out = []
    for side in ("en", "es"):
        out += [f"{side}:{r}" for r in _reasons(row.get(side, ""))]
    return out


def filter_pool(rows: list[dict], *, keep_reasons: bool = False) -> tuple[list[dict], list[dict]]:
    """Split the pool into (kept, rejected). Rejected rows carry a ``_reject`` reason list."""
    kept, rejected = [], []
    for r in rows:
        reasons = pair_reasons(r)
        if reasons:
            rr = {**r, "_reject": reasons} if keep_reasons else {**r, "_reject": reasons}
            rejected.append(rr)
        else:
            kept.append(r)
    return kept, rejected


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    from collections import Counter
    from pathlib import Path

    from casa.curriculum.render import ensure_utf8_console

    ensure_utf8_console()
    ap = argparse.ArgumentParser(description="Filter garbled pairs out of the EMEA pool.")
    ap.add_argument("--in", dest="inp", default=".scratch/opus/emea-pairs-v1.jsonl")
    ap.add_argument("--out", default=".scratch/opus/emea-pairs-v2.jsonl")
    ap.add_argument("--rejects", default=".scratch/opus/emea-pairs-rejects.jsonl")
    args = ap.parse_args(argv)

    rows = [json.loads(ln) for ln in Path(args.inp).read_text(encoding="utf-8").splitlines() if ln.strip()]
    kept, rejected = filter_pool(rows)

    with Path(args.out).open("w", encoding="utf-8", newline="\n") as f:
        for r in kept:
            f.write(json.dumps({k: v for k, v in r.items() if k != "_reject"}, ensure_ascii=False) + "\n")
    with Path(args.rejects).open("w", encoding="utf-8", newline="\n") as f:
        for r in rejected:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    tally: Counter = Counter()
    for r in rejected:
        for reason in r["_reject"]:
            tally[reason.split(":", 1)[1]] += 1
    print(json.dumps({
        "in": len(rows), "kept": len(kept), "rejected": len(rejected),
        "reject_rate": round(len(rejected) / len(rows), 4) if rows else 0.0,
        "by_reason": dict(tally.most_common()),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
