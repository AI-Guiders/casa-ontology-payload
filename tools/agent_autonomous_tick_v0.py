#!/usr/bin/env python3
"""Autonomous wake/sleep tick: cold lexicon ingest + incremental NCA (v0)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from field_write import load_field_state, save_field_state  # type: ignore
from lexicon_cold_ingest_v0 import process_lexicon_misses  # type: ignore
from nca_registry_v0 import find_stale_shards  # type: ignore
from predictor_v0 import detect_lexicon_miss, l2_prefix_candidates, predict_t9  # type: ignore
from sss_cylinders_v0 import ensure_cylinders  # type: ignore
from store_layout_v0 import field_state_path  # type: ignore


def _run_py(root: Path, cmd: list[str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, encoding="utf-8")
    ms = round((time.perf_counter() - t0) * 1000)
    out = (proc.stdout or "").strip()
    doc: dict[str, Any] = {}
    if out:
        try:
            doc = json.loads(out)
        except json.JSONDecodeError:
            doc = {"raw_stdout": out[-4000:]}
    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "ms": ms,
        "cmd": cmd,
        "report": doc,
        "stderr_tail": (proc.stderr or "")[-2000:],
    }


def wake_phase(
    state: dict,
    *,
    cues: list[dict[str, Any]],
    top_k: int,
) -> dict[str, Any]:
    ticks: list[dict[str, Any]] = []
    misses: list[dict[str, Any]] = []
    for cue in cues:
        prefix = str(cue.get("prefix") or cue.get("cue") or "")
        ranked = l2_prefix_candidates(state, prefix, top_k=top_k)
        pred = predict_t9(state, prefix, top_k=top_k)
        miss = detect_lexicon_miss(prefix, ranked)
        row = {"prefix": prefix, "predict": pred, "lexicon_miss": miss}
        ticks.append(row)
        if miss.get("miss"):
            misses.append(
                {
                    "prefix": prefix,
                    "word": str(cue.get("word") or miss.get("word") or prefix),
                    "reason": miss.get("reason") or "wake_miss",
                }
            )
    return {"ticks": ticks, "misses": misses, "miss_count": len(misses)}


def sleep_phase(
    root: Path,
    store_dir: Path,
    state: dict,
    *,
    misses: list[dict[str, Any]],
    headwords: Path | None,
    train_nca: bool,
    max_nca_shards: int,
    min_tokens: int,
    device: str,
    epochs: int,
) -> dict[str, Any]:
    phases: dict[str, Any] = {}

    if misses:
        ingest = process_lexicon_misses(
            state,
            misses,
            store_dir=store_dir,
            headwords_path=headwords,
        )
        phases["cold_ingest"] = ingest
    else:
        phases["cold_ingest"] = {"skipped": True, "reason": "no_misses"}

    stale_before = find_stale_shards(state, store_dir, repair_smoke=False, min_tokens=min_tokens)
    phases["stale_before"] = {"count": len(stale_before), "items": stale_before[:8]}

    if train_nca and stale_before:
        cmd = [
            sys.executable,
            "tools/nca_stale_shards_v0.py",
            "--store-dir",
            str(store_dir),
            "--train",
            "--min-tokens",
            str(min_tokens),
            "--device",
            device,
            "--epochs",
            str(epochs),
        ]
        if max_nca_shards > 0:
            cmd.extend(["--max-shards", str(max_nca_shards)])
        phases["nca_train"] = _run_py(root, cmd)
    else:
        phases["nca_train"] = {"skipped": True, "train_nca": train_nca, "stale_count": len(stale_before)}

    stale_after = find_stale_shards(state, store_dir, repair_smoke=False, min_tokens=min_tokens)
    phases["stale_after"] = {"count": len(stale_after)}
    return phases


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Wake/sleep autonomous tick (lexicon + NCA v0)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--cues", type=Path, default=None, help="JSON list of {prefix, word?}")
    p.add_argument("--headwords", type=Path, default=None)
    p.add_argument("--write", action="store_true")
    p.add_argument("--wake-only", action="store_true")
    p.add_argument("--sleep-only", action="store_true")
    p.add_argument("--train-nca", action="store_true")
    p.add_argument("--max-nca-shards", type=int, default=0)
    p.add_argument("--min-tokens", type=int, default=1)
    p.add_argument("--device", default="cpu")
    p.add_argument("--epochs", type=int, default=25)
    p.add_argument("--top-k", type=int, default=8)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    store = args.store_dir.resolve()
    fs_path = field_state_path(store)
    state = ensure_cylinders(load_field_state(fs_path))
    if not state:
        raise SystemExit(f"field_state missing: {fs_path}")

    cues: list[dict[str, Any]] = []
    if args.cues and args.cues.is_file():
        cues = json.loads(args.cues.read_text(encoding="utf-8"))

    report: dict[str, Any] = {
        "schema_version": 1,
        "tool": "agent_autonomous_tick_v0",
        "store": str(store),
    }

    misses: list[dict[str, Any]] = []
    if not args.sleep_only:
        wake = wake_phase(state, cues=cues, top_k=args.top_k)
        report["wake"] = wake
        misses = list(wake.get("misses") or [])

    if not args.wake_only:
        report["sleep"] = sleep_phase(
            root,
            store,
            state,
            misses=misses,
            headwords=args.headwords,
            train_nca=args.train_nca,
            max_nca_shards=args.max_nca_shards,
            min_tokens=args.min_tokens,
            device=args.device,
            epochs=args.epochs,
        )

    if args.write:
        save_field_state(fs_path, state)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
