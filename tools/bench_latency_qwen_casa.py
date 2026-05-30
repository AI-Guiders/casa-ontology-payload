#!/usr/bin/env python3
"""Compare wall-clock: Ollama Qwen vs CASA DMN repair vs CASA from-field hot path."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _ollama_generate(model: str, prompt: str, *, host: str) -> dict:
    url = f"{host.rstrip('/')}/api/generate"
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    wall_ms = (time.perf_counter() - t0) * 1000
    return {
        "wall_ms": round(wall_ms, 2),
        "load_ms": round(data.get("load_duration", 0) / 1e6, 2),
        "prompt_eval_ms": round(data.get("prompt_eval_duration", 0) / 1e6, 2),
        "eval_ms": round(data.get("eval_duration", 0) / 1e6, 2),
        "eval_count": data.get("eval_count"),
    }


def _run_sn_cen(repo: Path, extra: list[str]) -> tuple[float, float | None]:
    out = repo / "lab/latency_bench_v1/_sn_cen_out.json"
    cmd = [sys.executable, str(repo / "tools/sn_cen_infer.py"), *extra, "--out", str(out)]
    t0 = time.perf_counter()
    subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
    wall = round((time.perf_counter() - t0) * 1000, 2)
    inner = None
    if out.is_file():
        data = _read_json(out)
        inner = data.get("wall_ms")
    return wall, inner


def main() -> None:
    p = argparse.ArgumentParser(description="Latency bench: Qwen vs CASA")
    p.add_argument("--model", default="qwen2.5-coder:7b")
    p.add_argument("--ollama-host", default="http://localhost:11434")
    p.add_argument("--skip-qwen", action="store_true")
    p.add_argument("--query", default="import knowledge delta")
    p.add_argument("--store-dir", type=Path, default=Path("lab/agent-stores/research-agent-lab-v0"))
    p.add_argument("--out", type=Path, default=Path("lab/latency_bench_v1/report.json"))
    args = p.parse_args()

    repo = Path.cwd().resolve()
    out_tmp = repo / "lab/latency_bench_v1/_sn_cen_out.json"

    report: dict = {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": args.query,
        "model": args.model,
    }

    if not args.skip_qwen:
        try:
            ping = _ollama_generate(args.model, "Reply with exactly one word: OK", host=args.ollama_host)
            report["qwen_ping_cold_ms"] = ping["wall_ms"]
            warm = _ollama_generate(args.model, "Reply with exactly one word: OK", host=args.ollama_host)
            report["qwen_ping_warm_ms"] = warm["wall_ms"]
            qa_prompt = (
                "You are a KB assistant. From claims about casa.lab.import_knowledge_delta "
                "(online field write), list concept_ids as JSON only. Question: import knowledge delta?"
            )
            qa = _ollama_generate(args.model, qa_prompt, host=args.ollama_host)
            report["qwen_query_ms"] = qa["wall_ms"]
            report["qwen_query_eval_ms"] = qa["eval_ms"]
            report["qwen_available"] = True
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            report["qwen_available"] = False
            report["qwen_error"] = str(e)
    else:
        report["qwen_available"] = False
        report["qwen_skipped"] = True

    bundle = "lab/kb-perdoc/research-ml.bundle.v1.json"
    dmn_sub, _ = _run_sn_cen(repo, ["--bundle", bundle, "--query", args.query])
    report["casa_dmn_subprocess_ms"] = dmn_sub

    field_state = args.store_dir / "field_state.json"
    if field_state.is_file():
        field_sub, field_inner = _run_sn_cen(
            repo,
            ["--from-field", "--store-dir", str(args.store_dir), "--query", args.query],
        )
        report["casa_field_subprocess_ms"] = field_sub
        report["casa_field_inner_ms"] = field_inner
        report["casa_dmn_ms"] = dmn_sub
        report["casa_field_ms"] = field_inner if field_inner is not None else field_sub
        if report.get("qwen_query_ms") and report["casa_field_ms"]:
            report["speedup_field_vs_qwen_query"] = round(
                report["qwen_query_ms"] / max(report["casa_field_ms"], 0.001), 1
            )
        if report.get("qwen_ping_warm_ms") and report["casa_field_ms"]:
            report["speedup_field_vs_qwen_warm"] = round(
                report["qwen_ping_warm_ms"] / max(report["casa_field_ms"], 0.001), 1
            )
    else:
        report["casa_field_ms"] = None
        report["casa_field_note"] = f"missing {field_state}"

    if report.get("casa_dmn_ms") and report.get("casa_field_ms"):
        report["speedup_field_vs_dmn"] = round(report["casa_dmn_ms"] / max(report["casa_field_ms"], 0.001), 1)

    _write_json(args.out, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
