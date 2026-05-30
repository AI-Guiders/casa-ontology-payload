#!/usr/bin/env python3
"""Full bilingual T9 demo cycle: init stores → boot → benches (train optional)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from store_layout_v0 import STORE_EN_FOLK_V0, STORE_RU_LEXICON_V0, agent_store_dir  # type: ignore


def _run(cmd: list[str], *, cwd: Path, label: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")
    ms = round((time.perf_counter() - t0) * 1000)
    ok = proc.returncode == 0
    return {
        "label": label,
        "ok": ok,
        "exit_code": proc.returncode,
        "ms": ms,
        "cmd": cmd,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    py = sys.executable
    p = argparse.ArgumentParser(description="Run full bilingual T9 demo cycle")
    p.add_argument("--skip-init", action="store_true", help="Skip store init if ltm/ exists")
    p.add_argument("--train-nca", action="store_true", help="Optional short NCA train (slow, needs torch)")
    p.add_argument("--device", type=str, default="cpu")
    args = p.parse_args()

    ru_store = agent_store_dir(STORE_RU_LEXICON_V0, root=root)
    en_store = agent_store_dir(STORE_EN_FOLK_V0, root=root)
    steps: list[dict[str, Any]] = []

    if not args.skip_init or not (ru_store / "ltm").is_dir():
        steps.append(
            _run(
                [py, "tools/init_ru_dev_store_v0.py"],
                cwd=root,
                label="init_ru_dev_store",
            )
        )
    else:
        steps.append({"label": "init_ru_dev_store", "ok": True, "skipped": True})

    if not args.skip_init or not (en_store / "ltm").is_dir():
        steps.append(
            _run(
                [py, "tools/init_en_folk_store_v0.py"],
                cwd=root,
                label="init_en_folk_store",
            )
        )
    else:
        steps.append({"label": "init_en_folk_store", "ok": True, "skipped": True})

    core_ltm = root / "lab/agent-core/vk-layouts-v0/ltm/pack.manifest.json"
    if not core_ltm.is_file():
        steps.append(_run([py, "tools/vk_layout_ingest_v0.py"], cwd=root, label="vk_layout_ingest"))
    else:
        steps.append({"label": "vk_layout_ingest", "ok": True, "skipped": True})

    if args.train_nca:
        for store, name in ((ru_store, "train_ru_nca"), (en_store, "train_en_nca")):
            steps.append(
                _run(
                    [
                        py,
                        "tools/train_sss_nca_shards_v0.py",
                        "--store-dir",
                        str(store),
                        "--device",
                        args.device,
                        "--epochs",
                        "20",
                    ],
                    cwd=root,
                    label=name,
                )
            )

    benches = [
        (
            "bench_ambiguous_prefix",
            [py, "tools/bench_ambiguous_prefix_v0.py"],
        ),
        (
            "bench_t9_manual",
            [
                py,
                "tools/bench_t9_predict_v0.py",
                "--store-dir",
                str(ru_store),
                "--cues",
                "lab/exp_t9_v0/t9_manual_cues.v1.json",
            ],
        ),
        (
            "bench_unified_tick",
            [py, "tools/bench_unified_tick_v0.py"],
        ),
        (
            "bench_bilingual_linked",
            [
                py,
                "tools/bench_bilingual_linked_v0.py",
                "--ru-store",
                str(ru_store),
                "--en-store",
                str(en_store),
            ],
        ),
        (
            "bench_layout_parity",
            [py, "tools/bench_layout_parity_v0.py"],
        ),
        (
            "bench_vk_layout_field",
            [py, "tools/bench_vk_layout_field_v0.py"],
        ),
    ]
    for label, cmd in benches:
        steps.append(_run(cmd, cwd=root, label=label))

    steps.append(
        _run(
            [py, "tools/t9_runtime_v0.py", "once", "--prefix", "co"],
            cwd=root,
            label="runtime_once_co",
        )
    )

    report = {
        "schema_version": 1,
        "cycle": "t9_demo_v0",
        "all_ok": all(s.get("ok") for s in steps),
        "steps": steps,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
