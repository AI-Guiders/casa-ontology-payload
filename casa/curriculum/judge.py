#!/usr/bin/env python3
"""NUN-Bench judge runner — one protocol, every judge, raw verdicts on disk.

A «judge» is anything that answers the benchmark question — is this translation
meaning-equivalent to its source? — in the fixed JSON schema below. Four providers:

  mock      — deterministic hash-keyed verdicts (no network); exercises the whole
              pipeline end-to-end and feeds the metrics tests.
  kernel    — our validator (``check_equivalence``): parses both sides, answers only on
              what it can parse, natively abstains («uncheckable») elsewhere.
  anthropic — Claude models over the Messages API (ANTHROPIC_API_KEY).
  openai    — any OpenAI-compatible chat endpoint, including OpenRouter and self-hosted
              gateways: ``--base-url`` + ``--api-key-env`` select the deployment.

The prompt is versioned (PROMPT_VERSION) and identical for every model — comparing
judges, not prompt engineering. Each (model × run) writes one JSONL of raw records to
``--out-dir``; reruns resume from what is already on disk, so an interrupted sweep is
cheap to continue and nothing is ever re-bought. 5 runs at the same temperature give
consistency@5; metrics live in ``judge_metrics``.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

PROMPT_VERSION = "nunbench-judge-p1"

PROMPT_TEMPLATE = """You are checking a medicine-label translation for meaning errors.

Source (English): {src}
Translation (Spanish): {tgt}

Does the translation preserve the meaning of the source? Error classes:
- polarity: a negation is lost or added (the instruction flips direction)
- quantity: a number or dose differs from the source
- unit: a measurement unit differs (e.g. mg vs ml)
- entity: a drug or product name differs from the source
- other: the meaning differs in some other way
Minor wording differences that do not change the meaning count as equivalent.

Answer with a single JSON object and nothing else:
{{"verdict": "equivalent" or "error", "error_class": "polarity"|"quantity"|"unit"|"entity"|"other"|null, "confidence": <number from 0.0 to 1.0>}}"""

_JSON_BLOB = re.compile(r"\{.*\}", re.DOTALL)

_CLASSES = {"polarity", "quantity", "unit", "entity", "other"}


def _parse_reply(text: str) -> dict[str, Any]:
    """Extract the answer JSON; malformed replies become an explicit «invalid» verdict
    (counted and reported by the metrics, never silently dropped or guessed)."""
    m = _JSON_BLOB.search(text or "")
    if not m:
        return {"verdict": "invalid", "error_class": None, "confidence": 0.0}
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"verdict": "invalid", "error_class": None, "confidence": 0.0}
    verdict = obj.get("verdict")
    if verdict not in ("equivalent", "error"):
        return {"verdict": "invalid", "error_class": None, "confidence": 0.0}
    klass = obj.get("error_class")
    if verdict == "equivalent" or klass not in _CLASSES:
        klass = None if verdict == "equivalent" else "other"
    try:
        conf = min(1.0, max(0.0, float(obj.get("confidence", 0.5))))
    except (TypeError, ValueError):
        conf = 0.5
    return {"verdict": verdict, "error_class": klass, "confidence": conf}


# --- providers: (row, run_idx) -> raw reply text + usage ----------------------------------


def _mock_reply(row: dict, run: int, model: str) -> tuple[str, dict]:
    """Hash-keyed pseudo-judge: right ~80% of the time, wobbling across runs — enough
    structure for the metrics (consistency, risk–coverage) to have something to measure."""
    from casa.curriculum.benchmark import _h

    key = f"{model}:{row['id']}:{run}"
    correct = _h(key, "mock") % 100 < 80
    truth_error = row["label"] == "error"
    says_error = truth_error if correct else not truth_error
    klass = row["error_class"] if says_error and truth_error else ("other" if says_error else None)
    conf = 0.55 + (_h(key, "conf") % 45) / 100.0
    reply = {"verdict": "error" if says_error else "equivalent",
             "error_class": klass, "confidence": round(conf, 2)}
    return json.dumps(reply), {"tokens_in": 0, "tokens_out": 0}


def _http_json(url: str, headers: dict[str, str], body: dict, retries: int = 3) -> dict:
    data = json.dumps(body).encode("utf-8")
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, method="POST",
                                         headers={"content-type": "application/json", **headers})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:  # retry only what can heal
            last = e
            if e.code not in (429, 500, 502, 503, 529):
                raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        time.sleep(2 ** attempt * 5)
    raise RuntimeError(f"gave up after {retries} attempts: {last}")


def _anthropic_reply(row: dict, run: int, model: str, *, api_key: str,
                     temperature: float) -> tuple[str, dict]:
    out = _http_json(
        "https://api.anthropic.com/v1/messages",
        {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        {"model": model, "max_tokens": 200, "temperature": temperature,
         "messages": [{"role": "user",
                       "content": PROMPT_TEMPLATE.format(src=row["src"], tgt=row["tgt"])}]})
    text = "".join(b.get("text", "") for b in out.get("content", []))
    usage = out.get("usage", {})
    return text, {"tokens_in": usage.get("input_tokens", 0), "tokens_out": usage.get("output_tokens", 0)}


def _openai_reply(row: dict, run: int, model: str, *, api_key: str, base_url: str,
                  temperature: float) -> tuple[str, dict]:
    out = _http_json(
        base_url.rstrip("/") + "/chat/completions",
        {"authorization": f"Bearer {api_key}"},
        {"model": model, "max_tokens": 200, "temperature": temperature,
         "messages": [{"role": "user",
                       "content": PROMPT_TEMPLATE.format(src=row["src"], tgt=row["tgt"])}]})
    text = (out.get("choices") or [{}])[0].get("message", {}).get("content", "")
    usage = out.get("usage", {})
    return text, {"tokens_in": usage.get("prompt_tokens", 0), "tokens_out": usage.get("completion_tokens", 0)}


def _kernel_judge(rows: list[dict], out_path: Path) -> None:
    """The validator as a judge: deterministic, one run, native abstention. Its verdict
    map — equivalent→equivalent, divergent→error (first divergence names the class),
    uncheckable→abstain — makes it a row in the same results table as the LLMs."""
    from casa.curriculum.equivalence import check_equivalence
    from casa.curriculum.world import build_meaning_state

    state, lat = build_meaning_state()
    done = _done_ids(out_path)
    with out_path.open("a", encoding="utf-8") as f:
        for row in rows:
            if row["id"] in done:
                continue
            t0 = time.perf_counter()
            res = check_equivalence(state, lat, row["src"], row["tgt"],
                                    langs=(row["src_lang"], row["tgt_lang"]))
            ms = round((time.perf_counter() - t0) * 1000, 1)
            if res["verdict"] == "uncheckable":
                ans = {"verdict": "abstain", "error_class": None, "confidence": 0.0}
            elif res["verdict"] == "equivalent":
                ans = {"verdict": "equivalent", "error_class": None, "confidence": 1.0}
            else:
                divs = res.get("divergences") or [{"class": "other"}]
                ans = {"verdict": "error", "error_class": divs[0]["class"], "confidence": 1.0}
            f.write(json.dumps({
                "id": row["id"], "run": 0, "model": "kernel", "prompt_version": "kernel",
                **ans, "raw": json.dumps([d["class"] for d in res.get("divergences", [])]),
                "latency_ms": ms, "tokens_in": 0, "tokens_out": 0,
            }, ensure_ascii=False) + "\n")


def _done_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {json.loads(ln)["id"] for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()}


def run_judge(rows: list[dict], *, provider: str, model: str, runs: int, out_dir: str | Path,
              temperature: float = 0.2, api_key: str | None = None,
              base_url: str = "https://api.openai.com/v1") -> list[Path]:
    """Collect raw verdicts for every row × run; resumes from existing output files."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w.-]+", "-", model)

    if provider == "kernel":
        path = out_dir / f"kernel__{slug}__run0.jsonl"
        _kernel_judge(rows, path)
        return [path]

    reply: Callable[[dict, int], tuple[str, dict]]
    if provider == "mock":
        reply = lambda row, run: _mock_reply(row, run, model)
    elif provider == "anthropic":
        reply = lambda row, run: _anthropic_reply(row, run, model, api_key=api_key,
                                                  temperature=temperature)
    elif provider == "openai":
        reply = lambda row, run: _openai_reply(row, run, model, api_key=api_key,
                                               base_url=base_url, temperature=temperature)
    else:
        raise ValueError(f"unknown provider: {provider}")

    paths = []
    for run in range(runs):
        path = out_dir / f"{PROMPT_VERSION}__{slug}__run{run}.jsonl"
        paths.append(path)
        done = _done_ids(path)
        todo = [r for r in rows if r["id"] not in done]
        with path.open("a", encoding="utf-8") as f:
            for i, row in enumerate(todo):
                t0 = time.perf_counter()
                text, usage = reply(row, run)
                ms = round((time.perf_counter() - t0) * 1000, 1)
                rec = {"id": row["id"], "run": run, "model": model,
                       "prompt_version": PROMPT_VERSION, **_parse_reply(text),
                       "raw": text, "latency_ms": ms, **usage}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if provider != "mock" and (i + 1) % 25 == 0:
                    f.flush()
                    print(f"  run {run}: {i + 1}/{len(todo)}")
    return paths


def load_benchmark(path: str | Path, *, split: str = "public", limit: int = 0) -> list[dict]:
    """Load benchmark rows for judging: one split (heldout stays private by default),
    deterministic order, optional size cap for smoke tests."""
    rows = []
    with Path(path).open(encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                r = json.loads(ln)
                if split in ("all", r["split"]):
                    rows.append(r)
    rows.sort(key=lambda r: r["id"])
    return rows[:limit] if limit else rows


def main(argv: list[str] | None = None) -> int:
    import argparse

    from casa.curriculum.render import ensure_utf8_console

    ensure_utf8_console()
    ap = argparse.ArgumentParser(description="Run one judge over the NUN-Bench dataset.")
    ap.add_argument("--bench", default=".scratch/opus/nunbench-v0.1.jsonl")
    ap.add_argument("--provider", choices=["mock", "kernel", "anthropic", "openai"], required=True)
    ap.add_argument("--model", default="mock-1")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--split", default="public", choices=["public", "heldout", "all"])
    ap.add_argument("--limit", type=int, default=0, help="cap rows (smoke test); 0 = all")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--out-dir", default=".scratch/judgments")
    ap.add_argument("--base-url", default="https://api.openai.com/v1",
                    help="openai provider: any compatible endpoint (OpenRouter, gateways)")
    ap.add_argument("--api-key-env", default=None,
                    help="env var holding the key (default: provider's standard var)")
    args = ap.parse_args(argv)

    key_env = args.api_key_env or {"anthropic": "ANTHROPIC_API_KEY",
                                   "openai": "OPENAI_API_KEY"}.get(args.provider)
    api_key = os.environ.get(key_env, "") if key_env else ""
    if args.provider in ("anthropic", "openai") and not api_key:
        print(f"missing API key: set {key_env} (or --api-key-env)")
        return 2

    rows = load_benchmark(args.bench, split=args.split, limit=args.limit)
    print(f"{len(rows)} rows ({args.split}), provider={args.provider}, model={args.model}, "
          f"runs={args.runs if args.provider != 'kernel' else 1}")
    paths = run_judge(rows, provider=args.provider, model=args.model, runs=args.runs,
                      out_dir=args.out_dir, temperature=args.temperature,
                      api_key=api_key, base_url=args.base_url)
    for p in paths:
        print(p)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
