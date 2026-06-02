#!/usr/bin/env python3
"""Teacher/lab: verify lang-ru-math-bridge probes on agent field (no runtime oracle)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json

from casa.prisms.memory.f0_stack import decode_f0_lattice, rank_cue_on_f0
from casa.prisms.memory.lexicon_shard import concept_votes_l2
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.vocab import recall_words_for_scene
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import default_agent_store


def check_lang_bridge(
    store_dir: Path,
    class_dir: Path,
    *,
    manifest_name: str = "class.manifest.json",
) -> dict:
    manifest = json.loads((class_dir / manifest_name).read_text(encoding="utf-8"))
    boot = boot_store(store_dir, prefer_field_state=True)
    state = ensure_prisms(boot["state"])
    lats = memory_lattices(state)
    lat = lats.get(SCHEMA_MATH) or {}
    dec = decode_f0_lattice(lat) if lat.get("cells") else {}

    rows: list[dict] = []
    for row in manifest.get("probe") or []:
        kind = str(row.get("kind") or "l2")
        if kind == "l2":
            word = str(row.get("word") or "")
            expect = str(row.get("expect") or f"lang.word.{word}")
            votes, shard = concept_votes_l2(state, expect)
            ok = votes >= int(row.get("min_votes") or 1)
            rows.append(
                {
                    "kind": kind,
                    "word": word,
                    "expect": expect,
                    "votes": votes,
                    "shard": shard,
                    "pass": ok,
                }
            )
        elif kind == "math_f0":
            cue = str(row.get("cue") or "")
            expect = str(row.get("expect") or "")
            ranked = rank_cue_on_f0(dec, cue, bundle=None)
            top = ranked[0][0] if ranked else None
            top3 = [r[0] for r in ranked[:3]]
            ok = top == expect or expect in top3
            rows.append(
                {
                    "kind": kind,
                    "cue": cue,
                    "expect": expect,
                    "top": top,
                    "top3": top3,
                    "pass": ok,
                }
            )
        elif kind == "scene":
            sid = str(row.get("scene_id") or "")
            expect_words = [str(w) for w in (row.get("expect_words") or [])]
            min_cv = int(row.get("min_c_votes") or 1)
            recalled = {r["word"]: r["c_votes"] for r in recall_words_for_scene(state, sid)}
            missing = [w for w in expect_words if recalled.get(w, 0) < min_cv]
            rows.append(
                {
                    "kind": kind,
                    "scene_id": sid,
                    "expect_words": expect_words,
                    "recalled": recalled,
                    "missing": missing,
                    "pass": not missing,
                }
            )

    passed = sum(1 for r in rows if r.get("pass"))
    total = len(rows)
    threshold = float(manifest.get("probe_threshold") or 0.75)
    score = passed / total if total else 0.0

    report = {
        "store_dir": str(store_dir.resolve()),
        "class_id": manifest.get("class_id"),
        "field_version": state.get("field_version"),
        "probe": rows,
        "probe_score": score,
        "probe_ok": score >= threshold,
        "passed": passed,
        "total": total,
    }
    (class_dir / "last-bridge-check.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Check lang-ru-math-bridge on agent store")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--class-dir", type=Path, default=REPO_ROOT / "lessons/lang-ru-math-bridge")
    args = p.parse_args()
    rep = check_lang_bridge(args.store_dir or default_agent_store(), args.class_dir)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
