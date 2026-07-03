#!/usr/bin/env python3
"""Coverage-ceiling comparison across domains on the SAME language pair (en-es).

The paper's «controlled domain» claim rests on one contrast: on EMEA medical labels the
structural coverage ceiling is high, while on general software-UI text (KDE4) — same
language pair, so the ONLY difference is domain — it is low. This script measures both the
same way (random sample, fixed seed, no length filter) so the numbers are apples-to-apples,
and writes a JSON + markdown artifact for the paper.

  python -m scripts.ceiling_compare --limit 10000 --seed 42 \
      --emea .scratch/opus/emea-pairs-v2.jsonl \
      --kde-en .scratch/opus/kde4-en-es/KDE4.en-es.en \
      --kde-es .scratch/opus/kde4-en-es/KDE4.en-es.es \
      --out lab/nunbench/v0.1.2/ceiling-compare.json
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def _sample_jsonl(path: str, limit: int, seed: int) -> list[tuple[str, str]]:
    pairs = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                r = json.loads(ln)
                if r.get("en") and r.get("es"):
                    pairs.append((r["en"], r["es"]))
    rng = random.Random(seed)
    rng.shuffle(pairs)
    return pairs[:limit]


def _sample_bitext(en_path: str, es_path: str, limit: int, seed: int) -> list[tuple[str, str]]:
    en = [ln.strip() for ln in open(en_path, encoding="utf-8")]
    es = [ln.strip() for ln in open(es_path, encoding="utf-8")]
    pairs = [(e, s) for e, s in zip(en, es) if e and s]
    rng = random.Random(seed)
    rng.shuffle(pairs)
    return pairs[:limit]


def main(argv: list[str] | None = None) -> int:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from casa.curriculum.reality_check import ceiling_report
    from casa.curriculum.render import ensure_utf8_console
    from casa.curriculum.world import build_meaning_state

    ensure_utf8_console()
    ap = argparse.ArgumentParser(description="Cross-domain coverage-ceiling comparison (en-es).")
    ap.add_argument("--emea", default=".scratch/opus/emea-pairs-v2.jsonl")
    ap.add_argument("--kde-en", default=".scratch/opus/kde4-en-es/KDE4.en-es.en")
    ap.add_argument("--kde-es", default=".scratch/opus/kde4-en-es/KDE4.en-es.es")
    ap.add_argument("--limit", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="lab/nunbench/v0.1.2/ceiling-compare.json")
    args = ap.parse_args(argv)

    state, lat = build_meaning_state()

    def ceiling(pairs):
        r = ceiling_report(state, lat, pairs, langs=("en", "es"))
        return {"n": r["total"], "both_parse_now": r["coverage"],
                "ceiling": r["max_coverage"], "both_bare_label": r["both_ceiling"],
                "combos": r["combos"]}

    out = {
        "seed": args.seed, "limit": args.limit, "language_pair": "en-es",
        "emea_medical": ceiling(_sample_jsonl(args.emea, args.limit, args.seed)),
        "kde4_software": ceiling(_sample_bitext(args.kde_en, args.kde_es, args.limit, args.seed)),
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    e, k = out["emea_medical"]["ceiling"], out["kde4_software"]["ceiling"]
    print("| domain (en-es, same pair) | n | ceiling (max reachable coverage) |")
    print("|---|---|---|")
    print(f"| EMEA medical labels | {out['emea_medical']['n']} | {e:.1%} |")
    print(f"| KDE4 software UI | {out['kde4_software']['n']} | {k:.1%} |")
    print(f"\ncontrast: medical {e:.1%} vs software {k:.1%} — same language pair, domain is the "
          f"only difference.\n→ {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
