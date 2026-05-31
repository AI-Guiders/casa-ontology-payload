#!/usr/bin/env python3
"""End-to-end sleep UC: Use (before) → Extract → Remember (--write) → reload → Use (after)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from casa.cli.bench.bench_sleep_extract_remember_v0 import run_sleep_tick
from casa.prisms.shared.field_write import save_field_state
from casa.prisms.tick.predictor_v0 import predict_t9
from casa.prisms.shared.prism_state_v0 import prism_hippo, prism_memory
from casa.prisms.memory.sss_cylinders_v0 import memory_lattices
from casa.prisms.memory.sss_field_decode_v0 import rule_votes_from_field
from casa.prisms.memory.sss_l2_shard_v0 import concept_votes_l2
from casa.prisms.memory.sss_vocab_v0 import norm_word
from casa.prisms.shared.store_boot_v0 import boot_store

_L2_INDEX_CACHE = "__predictor_l2_prefix_index_v0__"


def sync_memory_lattices(state: dict) -> None:
    lattices = memory_lattices(state)
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices


def use_probe(
    state: dict,
    *,
    prefix: str,
    top_k: int = 12,
    t9_policy: str = "lab",
    watch_lemmas: list[str] | None = None,
) -> dict[str, Any]:
    """T9 fork on prefix — no forced oracle lemma."""
    state.pop(_L2_INDEX_CACHE, None)
    pfx = norm_word(prefix)
    pred = predict_t9(state, pfx, top_k=top_k, t9_policy=t9_policy)  # type: ignore[arg-type]
    ranked = list(pred.get("ranked") or [])
    words = [w for w, _ in ranked]
    votes_map = {w: int(v) for w, v in ranked}
    watch = watch_lemmas or []
    watch_grid: dict[str, Any] = {}
    for w in watch:
        wn = norm_word(w)
        cid = f"lang.word.{wn}"
        gv, _ = concept_votes_l2(state, cid)
        watch_grid[wn] = {
            "prefix_votes": votes_map.get(wn, 0),
            "grid_votes": gv,
            "in_top_k": wn in words,
        }
    return {
        "prefix": pfx,
        "hypothesis": pred.get("hypothesis"),
        "fork_count": len(words),
        "anchors": [{"word": w, "votes": votes_map.get(w, 0)} for w in words[:top_k]],
        "watch_lemmas": watch_grid,
        "rule_votes": dict(rule_votes_from_field(state)),
    }


def _consolidation_view(state: dict) -> dict[str, Any]:
    cons = state.get("consolidation") or {}
    hip = prism_hippo(state)
    episodes = hip.get("episodes") or []
    pending = [e for e in episodes if not e.get("consolidated")]
    last = cons.get("last_sleep") or {}
    return {
        "field_version": int(state.get("field_version") or 0),
        "episodes_merged_total": int(cons.get("episodes_merged_total") or 0),
        "hippo_episode_count": len(episodes),
        "hippo_pending_count": len(pending),
        "last_sleep_merged": int(last.get("merged") or 0),
        "last_sleep_items": list(last.get("items") or []),
    }


def _eval_use(
    item: dict[str, Any],
    use_before: dict[str, Any],
    use_after: dict[str, Any],
    remember: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    use_cfg = item.get("use") if isinstance(item.get("use"), dict) else {}
    mode = str(item.get("mode") or "teacher_rule_only")
    min_fork = int(use_cfg.get("min_fork") or 5)
    watch = [norm_word(w) for w in (use_cfg.get("watch_lemmas_stable") or [])]
    rule_rid = str(use_cfg.get("expect_rule_id") or item.get("rule_id") or "script.no_mixed_alphabet")
    expect_strengthen = norm_word(str(use_cfg.get("expect_strengthen") or "")) or None
    min_grid_delta = int(use_cfg.get("min_grid_delta") or 0)
    expect_pending = bool(use_cfg.get("expect_pending"))

    fork_ok = use_after["fork_count"] >= min_fork
    rule_before = int((use_before.get("rule_votes") or {}).get(rule_rid) or 0)
    rule_after = int((use_after.get("rule_votes") or {}).get(rule_rid) or 0)
    rule_ok = rule_after > rule_before if mode == "teacher_rule_only" else True

    stable_ok = True
    strengthen_ok = True
    stable_detail: list[dict[str, Any]] = []
    for w in watch:
        b = (use_before.get("watch_lemmas") or {}).get(w) or {}
        a = (use_after.get("watch_lemmas") or {}).get(w) or {}
        grid_before = int(b.get("grid_votes") or 0)
        grid_after = int(a.get("grid_votes") or 0)
        if expect_strengthen and w == expect_strengthen:
            delta = grid_after - grid_before
            s_ok = delta >= min_grid_delta
            stable_detail.append({"word": w, "role": "target", "grid_before": grid_before, "grid_after": grid_after, "delta": delta, "ok": s_ok})
            strengthen_ok = strengthen_ok and s_ok
        else:
            grid_stable = grid_after == grid_before
            stable_detail.append({"word": w, "role": "watch", "grid_before": grid_before, "grid_after": grid_after, "stable": grid_stable})
            stable_ok = stable_ok and grid_stable

    pending_ok = True
    if expect_pending or mode == "teacher_lexical_ask":
        pending_ok = int(remember.get("hippo_pending_count") or 0) >= 1 and int(remember.get("surface_merged_count") or 0) == 0

    if mode == "teacher_rule_only":
        use_ok = fork_ok and rule_ok and stable_ok
    elif mode == "teacher_lexical_ask":
        use_ok = fork_ok and stable_ok and pending_ok
    elif mode == "teacher_contextual_surface":
        use_ok = fork_ok and strengthen_ok and stable_ok
    elif mode == "teacher_wait_prefix":
        use_ok = fork_ok and int(remember.get("surface_merged_count") or 0) == 0
    else:
        use_ok = fork_ok and rule_ok

    return use_ok, {
        "fork_ok": fork_ok,
        "rule_ok": rule_ok,
        "lemmas_stable": stable_ok,
        "strengthen_ok": strengthen_ok,
        "pending_ok": pending_ok,
        "stable_detail": stable_detail,
        "rule_votes": f"{rule_before}→{rule_after}",
    }


def run_e2e(
    store_dir: Path,
    item: dict[str, Any],
    *,
    write: bool,
    compact: bool,
    backup: bool,
    top_k: int = 12,
) -> dict[str, Any]:
    expect_preflight_fail = bool(item.get("expect_preflight_fail"))
    use_cfg = item.get("use") if isinstance(item.get("use"), dict) else {}
    use_prefix = str(use_cfg.get("prefix") or item.get("cue") or "")
    watch = list(use_cfg.get("watch_lemmas_stable") or [])

    field_path = store_dir / "field_state.json"
    backup_path: Path | None = None
    if backup and field_path.is_file():
        backup_path = store_dir / "field_state.before_sleep_e2e.json"
        shutil.copy2(field_path, backup_path)

    t0 = time.perf_counter()
    boot_before = boot_store(store_dir, prefer_field_state=True)
    use_before = use_probe(boot_before["state"], prefix=use_prefix, top_k=top_k, watch_lemmas=watch)
    cons_before = _consolidation_view(boot_before["state"])

    remember = run_sleep_tick(
        boot_before["state"],
        cue=str(item.get("cue") or ""),
        surface_attempt=str(item.get("surface_attempt") or item.get("babble") or ""),
        correct=str(item.get("correct") or item.get("word") or ""),
        strength=int(item.get("strength") or 4),
        mode=str(item.get("mode") or "teacher_rule_only"),
        rule_id=item.get("rule_id"),
        rule_hint=str(item.get("rule_hint") or ""),
        expect_lang=item.get("expect_lang"),
        correction_kind=item.get("correction_kind"),
        scene=item.get("scene"),
        question=item.get("question"),
        options=item.get("options") if isinstance(item.get("options"), list) else None,
        structure_tag=item.get("structure_tag"),
        min_recurrence=int(item.get("min_recurrence") or 1),
    )
    state_after_sleep = remember.pop("state")
    remember_ok = bool(remember.get("all_passed"))

    if expect_preflight_fail:
        preflight_failed = not remember_ok and bool(remember.get("preflight") or remember.get("fail_reason"))
        remember_ok = preflight_failed
        all_passed = preflight_failed
        elapsed_ms = round((time.perf_counter() - t0) * 1000)
        return {
            "schema_version": 1,
            "bench": "sleep_uc_e2e_v0",
            "cue_id": item.get("id"),
            "correction_kind": item.get("correction_kind"),
            "store": str(store_dir),
            "written": False,
            "backup": str(backup_path) if backup_path else None,
            "expect_preflight_fail": True,
            "remember": remember,
            "remember_ok": remember_ok,
            "use_ok": True,
            "all_passed": all_passed,
            "elapsed_ms": elapsed_ms,
        }

    sync_memory_lattices(state_after_sleep)
    if write:
        save_field_state(field_path, state_after_sleep, compact=compact)

    if write and field_path.is_file():
        use_state = boot_store(store_dir, prefer_field_state=True)["state"]
    else:
        use_state = state_after_sleep

    use_after = use_probe(use_state, prefix=use_prefix, top_k=top_k, watch_lemmas=watch)
    cons_after = _consolidation_view(use_state)
    use_ok, use_detail = _eval_use(item, use_before, use_after, remember)

    mode = str(item.get("mode") or "teacher_rule_only")
    persisted_ok = True
    if write:
        merged = int(cons_after.get("last_sleep_merged") or 0)
        if mode == "teacher_lexical_ask":
            persisted_ok = cons_after["field_version"] > cons_before["field_version"] and cons_after["hippo_pending_count"] >= 1
        elif mode == "teacher_wait_prefix":
            persisted_ok = cons_after["field_version"] > cons_before["field_version"]
        else:
            persisted_ok = cons_after["field_version"] > cons_before["field_version"] and merged >= 1

    elapsed_ms = round((time.perf_counter() - t0) * 1000)

    return {
        "schema_version": 1,
        "bench": "sleep_uc_e2e_v0",
        "cue_id": item.get("id"),
        "correction_kind": item.get("correction_kind"),
        "store": str(store_dir),
        "written": write,
        "backup": str(backup_path) if backup_path else None,
        "use_prefix": use_prefix,
        "use_before": use_before,
        "use_after": use_after,
        "use_detail": use_detail,
        "consolidation_before": cons_before,
        "consolidation_after": cons_after,
        "remember": remember,
        "remember_ok": remember_ok,
        "use_ok": use_ok,
        "persisted_ok": persisted_ok if write else None,
        "all_passed": remember_ok and use_ok and (persisted_ok if write else True),
        "elapsed_ms": elapsed_ms,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Sleep UC e2e: Use→Extract→Remember→reload→Use")
    p.add_argument("--store-dir", type=Path, default=root / "lab/agent-stores/sss-ru-general-v0")
    p.add_argument("--cues", type=Path, default=root / "lab/exp_sleep_v0/sleep_tick_cues.v1.json")
    p.add_argument("--cue-index", type=int, default=0)
    p.add_argument("--all-cues", action="store_true", help="Run every cue; exit 0 only if all pass")
    p.add_argument("--write", action="store_true")
    p.add_argument("--backup", action="store_true")
    p.add_argument("--compact", action="store_true")
    p.add_argument("--top-k", type=int, default=12)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    if not isinstance(cues, list) or not cues:
        raise SystemExit(f"empty cues: {args.cues}")

    indices = range(len(cues)) if args.all_cues else [min(max(0, args.cue_index), len(cues) - 1)]
    reports: list[dict[str, Any]] = []
    all_ok = True

    for idx in indices:
        item = cues[idx]
        report = run_e2e(
            args.store_dir,
            item,
            write=args.write and not item.get("expect_preflight_fail"),
            compact=args.compact,
            backup=args.backup and idx == indices[0],
            top_k=args.top_k,
        )
        reports.append(report)
        all_ok = all_ok and bool(report.get("all_passed"))

    if len(reports) == 1:
        report = reports[0]
    else:
        report = {
            "schema_version": 1,
            "bench": "sleep_uc_e2e_v0",
            "all_cues": True,
            "count": len(reports),
            "all_passed": all_ok,
            "reports": reports,
        }

    out_path = args.out or (root / "lab/exp_sleep_v0/reports/sleep_uc_e2e_v1.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if len(reports) == 1:
        ub, ua = report["use_before"], report["use_after"]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(
            f"\nSUMMARY: sleep_uc_e2e ok={report['all_passed']} "
            f"written={report.get('written')} "
            f"T9[{report.get('use_prefix', '')}] fork {ub['fork_count']}→{ua['fork_count']} "
            f"hypothesis {ub['hypothesis']!r}→{ua['hypothesis']!r} "
            f"rule {report.get('use_detail', {}).get('rule_votes')} "
            f"lemmas_stable={report.get('use_detail', {}).get('lemmas_stable')} "
            f"fv {report['consolidation_before']['field_version']}→{report['consolidation_after']['field_version']} "
            f"{report['elapsed_ms']}ms",
            file=sys.stderr,
        )
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"\nSUMMARY: sleep_uc_e2e all_cues ok={all_ok} count={len(reports)}", file=sys.stderr)

    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
