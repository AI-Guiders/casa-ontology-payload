#!/usr/bin/env python3
"""Bench grapheme/L2 basin separability (ADR-0003; no #Latin string checks)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import sys
import time
from pathlib import Path

from casa.prisms.memory.boot_linked_stores_v0 import boot_linked_stores
from casa.prisms.memory.en_lexicon_v0 import read_headwords
from casa.prisms.memory.grapheme_clusters_v0 import run_cluster_bench
from casa.prisms.memory.grapheme_ingest_v0 import bootstrap_linked_graphemes
from casa.prisms.shared.store_layout_v0 import STORE_EN_FOLK_V0, STORE_RU_LEXICON_V0, agent_store_dir


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench L2/L0 script basin separability")
    p.add_argument("--ru-store", type=Path, default=agent_store_dir(STORE_RU_LEXICON_V0, root=root))
    p.add_argument("--en-store", type=Path, default=agent_store_dir(STORE_EN_FOLK_V0, root=root))
    p.add_argument(
        "--cues",
        type=Path,
        default=root / "lab/exp_bilingual_v0/grapheme_cluster_cues.v1.json",
    )
    p.add_argument(
        "--headwords",
        type=Path,
        default=root / "lab/exp_bilingual_v0/en_folk_headwords.v1.txt",
    )
    p.add_argument("--no-bootstrap-l0", action="store_true")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    headwords = read_headwords(args.headwords)

    t0 = time.perf_counter()
    boot = boot_linked_stores(args.ru_store, args.en_store)
    boot_ms = round((time.perf_counter() - t0) * 1000)
    state = boot["state"]

    bootstrap_rep = None
    if not args.no_bootstrap_l0:
        t1 = time.perf_counter()
        bootstrap_rep = bootstrap_linked_graphemes(state, en_words=headwords)
        bootstrap_ms = round((time.perf_counter() - t1) * 1000)
    else:
        bootstrap_ms = 0

    report = run_cluster_bench(state, cues)
    report["boot_ms"] = boot_ms
    report["bootstrap_ms"] = bootstrap_ms
    report["bootstrap"] = bootstrap_rep
    report["boot"] = {k: v for k, v in boot.items() if k != "state"}

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)

    print(
        f"\nSUMMARY: {report['passed']}/{report['total']} "
        f"boot={boot_ms}ms bootstrap={bootstrap_ms}ms "
        f"latn={ (bootstrap_rep or {}).get('latn_count', '?') } "
        f"cyrl={ (bootstrap_rep or {}).get('cyrl_count', '?') }",
        file=sys.stderr,
    )
    raise SystemExit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
