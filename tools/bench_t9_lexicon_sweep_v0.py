#!/usr/bin/env python3
"""Sweep T9 predict over large L2 lexicon: full words + prefix anchors."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

from lexicon_usage_axes_v0 import T9Policy  # type: ignore
from predictor_v0 import _prefix_from_index, l2_prefix_index, l2_prefix_candidates  # type: ignore
from sss_l2_shard_v0 import L2_CONCEPT_PREFIX, lattice_digest_l2_network  # type: ignore
from sss_segment_v0 import norm_word  # type: ignore
from store_boot_v0 import boot_store  # type: ignore


def all_lexicon_words(state: dict) -> list[str]:
    out: list[str] = []
    for cid, _votes in lattice_digest_l2_network(state):
        if cid.startswith(L2_CONCEPT_PREFIX):
            out.append(cid[len(L2_CONCEPT_PREFIX) :])
    return sorted(set(out))


def run_sweep(
    state: dict,
    words: list[str],
    *,
    index: dict[str, list[tuple[str, int]]] | None = None,
    axes: dict | None = None,
    top_k: int = 8,
    prefix_lens: tuple[int, ...] = (2, 3),
    seed: int = 42,
    t9_policy: T9Policy = "prod",
) -> dict:
    rng = random.Random(seed)
    pfx_index = index if index is not None else l2_prefix_index(state)
    full_ok = 0
    prefix_ok = 0
    prefix_total = 0
    failures: list[dict] = []
    samples: list[dict] = []

    for word in words:
        w = norm_word(word)
        if len(w) < 2:
            continue

        if t9_policy == "lab" and index is not None:
            ranked_full = _prefix_from_index(pfx_index, w, top_k=top_k, axes=axes or None)
        else:
            ranked_full = l2_prefix_candidates(state, w, top_k=top_k, t9_policy=t9_policy)
        ranked_words_full = [x[0] for x in ranked_full]
        hyp = ranked_words_full[0] if ranked_words_full else None
        ok_full = hyp == w
        if ok_full:
            full_ok += 1
        elif len(failures) < 25:
            failures.append(
                {
                    "kind": "full",
                    "cue": w,
                    "expect": w,
                    "hypothesis": hyp,
                    "ranked_top5": ranked_words_full[:5],
                }
            )

        for plen in prefix_lens:
            if plen >= len(w):
                continue
            prefix = w[:plen]
            if t9_policy == "lab" and index is not None:
                ranked = _prefix_from_index(pfx_index, prefix, top_k=top_k, axes=axes or None)
            else:
                ranked = l2_prefix_candidates(state, prefix, top_k=top_k, t9_policy=t9_policy)
            ranked_words = [x[0] for x in ranked]
            in_top = w in ranked_words
            prefix_total += 1
            if in_top:
                prefix_ok += 1
            elif len(failures) < 25:
                failures.append(
                    {
                        "kind": "prefix",
                        "cue": prefix,
                        "expect": w,
                        "ranked_top8": ranked_words,
                        "match_count": len(ranked),
                    }
                )

        if len(samples) < 12 and rng.random() < 0.15:
            prefix_demo = w[: min(2, len(w) - 1)] if len(w) > 2 else w[:1]
            ranked_demo = _prefix_from_index(pfx_index, prefix_demo, top_k=top_k)
            ranked_demo_words = [x[0] for x in ranked_demo]
            samples.append(
                {
                    "cue": prefix_demo,
                    "target_word": w,
                    "anchors": [{"word": rw, "votes": v} for rw, v in ranked_demo[:6]],
                    "target_in_anchors": w in ranked_demo_words,
                }
            )

    word_n = len(words)
    return {
        "schema_version": 1,
        "bench": "t9_lexicon_sweep_v0",
        "t9_policy": t9_policy,
        "words_tested": word_n,
        "full_word": {
            "passed": full_ok,
            "total": word_n,
            "pass_rate": round(full_ok / max(1, word_n), 4),
        },
        "prefix_in_top_k": {
            "top_k": top_k,
            "prefix_lens": list(prefix_lens),
            "passed": prefix_ok,
            "total": prefix_total,
            "pass_rate": round(prefix_ok / max(1, prefix_total), 4),
        },
        "samples": samples,
        "failures": failures,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Sweep T9 over lexicon words")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument(
        "--prefer-field-state",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use field_state.json when present (needed for full L2 vocab stats)",
    )
    p.add_argument("--sample", type=int, default=0, help="0 = all words")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--top-k", type=int, default=8)
    p.add_argument("--prefix-lens", type=str, default="2,3", help="comma-separated prefix lengths")
    p.add_argument("--manual-cues", type=Path, default=None, help="JSON array of {cue, expect}")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument(
        "--t9-policy",
        choices=("prod", "lab", "modern_all"),
        default="prod",
        help="prod=active_for_t9 only; lab=all L2; modern_all=era modern",
    )
    p.add_argument(
        "--min-full-rate",
        type=float,
        default=None,
        help="Exit 1 if full_word pass_rate below this (default: 1.0 when no --out thresholds)",
    )
    p.add_argument(
        "--min-prefix-rate",
        type=float,
        default=None,
        help="Exit 1 if prefix_in_top_k pass_rate below this (default: 1.0)",
    )
    args = p.parse_args()

    prefix_lens = tuple(int(x.strip()) for x in args.prefix_lens.split(",") if x.strip())
    t0 = time.perf_counter()
    boot = boot_store(args.store_dir, prefer_field_state=args.prefer_field_state)
    state = boot["state"]
    vocab = all_lexicon_words(state)
    boot_ms = round((time.perf_counter() - t0) * 1000)
    t_idx = time.perf_counter()
    pfx_index = l2_prefix_index(state)
    index_ms = round((time.perf_counter() - t_idx) * 1000)
    axes = state.get("lexicon_axes") or {}

    if args.sample and args.sample < len(vocab):
        rng = random.Random(args.seed)
        words = sorted(rng.sample(vocab, args.sample))
    else:
        words = vocab

    report = run_sweep(
        state,
        words,
        index=pfx_index,
        axes=axes,
        top_k=args.top_k,
        prefix_lens=prefix_lens,
        seed=args.seed,
        t9_policy=args.t9_policy,
    )
    sweep_ms = round((time.perf_counter() - t_idx) * 1000) - index_ms
    report["boot"] = {
        "source": boot.get("source"),
        "ms": boot_ms,
        "index_ms": index_ms,
        "sweep_ms": sweep_ms,
        "vocab_size": len(vocab),
    }
    report["passed"] = (
        report["full_word"]["passed"] == report["full_word"]["total"]
        and report["prefix_in_top_k"]["passed"] == report["prefix_in_top_k"]["total"]
    )

    min_full = args.min_full_rate
    min_prefix = args.min_prefix_rate
    if min_full is not None or min_prefix is not None:
        report["thresholds"] = {
            "min_full_rate": min_full,
            "min_prefix_rate": min_prefix,
        }
        ok_full = min_full is None or report["full_word"]["pass_rate"] >= min_full
        ok_prefix = min_prefix is None or report["prefix_in_top_k"]["pass_rate"] >= min_prefix
        report["passed"] = ok_full and ok_prefix
        report["threshold_ok"] = {"full_word": ok_full, "prefix_in_top_k": ok_prefix}

    if args.manual_cues:
        manual = json.loads(args.manual_cues.read_text(encoding="utf-8"))
        manual_rows: list[dict] = []
        manual_pass = 0
        for item in manual:
            cue = str(item.get("cue") or "")
            expect = item.get("expect")
            expect_in = item.get("expect_in") or []
            ranked_pairs = _prefix_from_index(pfx_index, cue, top_k=args.top_k, axes=axes or None)
            ranked = [x[0] for x in ranked_pairs]
            hyp = ranked[0] if ranked else None
            if expect_in:
                wanted = {norm_word(str(w)) for w in expect_in}
                found = wanted & {norm_word(w) for w in ranked}
                ok = len(found) >= 1 and len(ranked) >= 2
            elif expect is not None:
                exp = norm_word(str(expect))
                if len(norm_word(cue)) < len(exp):
                    ok = exp in {norm_word(w) for w in ranked}
                else:
                    ok = norm_word(hyp or "") == exp
            else:
                ok = len(ranked) >= 2
            if ok:
                manual_pass += 1
            manual_rows.append(
                {
                    "id": item.get("id"),
                    "cue": cue,
                    "expect": expect,
                    "expect_in": expect_in or None,
                    "hypothesis": hyp,
                    "anchors_top8": ranked[:8],
                    "ok": ok,
                }
            )
        report["manual"] = {
            "passed": manual_pass,
            "total": len(manual),
            "items": manual_rows,
        }
        report["passed"] = report["passed"] and manual_pass == len(manual)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    fw = report["full_word"]
    px = report["prefix_in_top_k"]
    thr = report.get("threshold_ok")
    thr_note = ""
    if thr:
        thr_note = f" thresholds full={thr['full_word']} prefix={thr['prefix_in_top_k']}"
    print(
        f"\nSUMMARY: vocab={len(vocab)} tested={report['words_tested']} "
        f"index={index_ms}ms sweep={sweep_ms}ms "
        f"full={fw['passed']}/{fw['total']} ({fw['pass_rate']:.1%}) "
        f"prefix@{args.top_k}={px['passed']}/{px['total']} ({px['pass_rate']:.1%})"
        f" passed={report['passed']}{thr_note}",
        file=sys.stderr,
    )
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
