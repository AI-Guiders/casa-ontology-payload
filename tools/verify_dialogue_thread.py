#!/usr/bin/env python3
"""Real-store dialogue smoke — bind trace + speech-act provenance (plumbing only).

NOT an emergence / duck-test gate: fixed partner script + hub-prefix expectations
prescribe routing. See design/CASA-work-verification-dialogue-thread.v1.md §Limits.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.dialogue_provenance import meaning_provenance
from casa.domain.dialogue_invariants import probe_p7_adr0078_classes, stage_gate_stage_ii
from casa.domain.dialogue_turn import append_partner_turn, append_subject_turn
from casa.domain.subject_mode import apply_subject_profile
from casa.domain.subject_voice import compose_subject_partner_reply_with_ctx
from casa.prisms.control.fpn_state import WorkingMemory, read_session_meta, write_session_meta
from casa.prisms.control.sn_cen_runtime import TaskEmit
from casa.prisms.shared.store_layout import default_agent_store

PREAMBLE = "осторожно говорю, что чувствую"

TURNS = [
    (
        "Как ты?",
        {
            "need_affect_axes": True,
            "allow_verbatim_winner": True,
        },
    ),
    (
        "Хорошо, я тоже не знаю, но он не обязан совпадать",
        {
            "forbid_phrase_substrings": (PREAMBLE,),
            "forbid_verbatim_winner": True,
            "min_words": 3,
        },
    ),
    (
        "А что ты думаешь про это?",
        {
            "forbid_phrase_substrings": (PREAMBLE,),
            "min_words": 4,
            "differs_from_prior": True,
        },
    ),
    (
        "Спасибо",
        {
            "forbid_phrase_substrings": (PREAMBLE,),
            "allow_verbatim_winner": True,
        },
    ),
]


def _task() -> TaskEmit:
    return TaskEmit(
        intent="query",
        action="answer_from_memory",
        concepts=[],
        edges=[],
        targets=[],
        query_to_dmn=None,
        confidence=0.5,
        answer_blocks=(),
        answer_text="",
    )


def _token_overlap(a: str, b: str) -> int:
    ta = {w for w in a.lower().split() if len(w) > 3}
    tb = {w for w in b.lower().split() if len(w) > 3}
    return len(ta & tb)


def _assert_turn(
    partner: str,
    reply: str,
    prov: dict,
    rules: dict,
    *,
    prior_reply: str | None,
) -> list[str]:
    errors: list[str] = []
    low = reply.lower().strip()

    trace = prov.get("bind_trace") or {}
    if not trace.get("winner_bind_hub"):
        errors.append(f"missing bind_trace: {prov!r}")

    p7 = probe_p7_adr0078_classes(reply)
    if p7:
        errors.append(f"P7 violations: {p7}")

    if rules.get("need_affect_axes") and not prov.get("affect_axes"):
        errors.append(f"missing affect_axes in provenance: {prov!r}")

    for banned in rules.get("forbid_phrase_substrings") or ():
        if banned.lower() in low:
            errors.append(f"banned substring {banned!r}: {reply!r}")

    if rules.get("forbid_verbatim_winner") and not rules.get("allow_verbatim_winner"):
        winner_phrase = str(trace.get("winner_phrase") or "").strip().lower()
        if winner_phrase and low.rstrip(".!?") == winner_phrase.rstrip(".!?"):
            errors.append(f"verbatim bind winner only: {reply!r}")

    min_w = rules.get("min_words")
    if min_w and len(low.split()) < int(min_w):
        errors.append(f"ADVISORY too short: {reply!r}")

    if rules.get("differs_from_prior") and prior_reply:
        if _token_overlap(reply, prior_reply) >= max(3, len(prior_reply.split()) // 2):
            errors.append(f"ADVISORY replay of prior reply: {prior_reply!r} → {reply!r}")

    if not reply.strip():
        errors.append("empty reply")

    return errors


def run_probe(*, reset_ring: bool = True, impulse: bool = False) -> list[tuple[str, str]]:
    if impulse:
        os.environ["CASA_IMPULSE_TRACE"] = "summary"
    store = default_agent_store()
    if reset_ring:
        meta = read_session_meta(store)
        meta["dialogue_turns"] = []
        write_session_meta(store, meta)
    state = resolve_ingest_state(store, None)
    apply_subject_profile(store, state)
    wm = WorkingMemory(tick=int(state.get("field_version") or 0))
    task = _task()
    transcript: list[tuple[str, str]] = []
    prior_reply: str | None = None
    impulse_ids: list[str] = []
    for partner, rules in TURNS:
        append_partner_turn(store, partner, provenance={"source": "verify"})
        ctx, reply = compose_subject_partner_reply_with_ctx(
            partner, task, state, wm, store_dir=store
        )
        prov = meaning_provenance(ctx)
        errors = _assert_turn(partner, reply, prov, rules, prior_reply=prior_reply)
        gate_errors = [e for e in errors if not e.startswith("ADVISORY")]
        advisories = [e for e in errors if e.startswith("ADVISORY")]
        for note in advisories:
            print(f"ADVISORY: {note}", file=sys.stderr)
        errors = stage_gate_stage_ii(gate_errors)
        if errors:
            raise AssertionError(f"turn {partner!r}: " + "; ".join(errors))
        if impulse:
            from casa.nervous.dialogue_hooks import record_partner_dialogue_impulse

            summary = record_partner_dialogue_impulse(
                store_dir=store,
                ctx=ctx,
                reply_text=reply,
                boundary_turn=False,
                disp_action=None,
            )
            if not summary or not summary.get("event_count"):
                raise AssertionError(f"missing impulse winners for turn {partner!r}: {summary!r}")
            impulse_ids.append(str(summary.get("impulse_id") or ""))
        append_subject_turn(
            store,
            reply,
            kind="reply",
            provenance=prov,
        )
        transcript.append((partner, reply))
        prior_reply = reply
    if impulse and len(impulse_ids) != len(TURNS):
        raise AssertionError(f"expected {len(TURNS)} impulse rows, got {len(impulse_ids)}")
    return transcript


def _assert_impulse_trace(store: Path) -> None:
    from casa.nervous.impulse import read_impulse_trace

    rows = read_impulse_trace(store, channel="partner_dialogue", limit=20)
    if len(rows) < len(TURNS):
        raise AssertionError(f"impulse_trace.jsonl has {len(rows)} rows, want >= {len(TURNS)}")
    for row in rows[-len(TURNS) :]:
        summary = row.get("summary") if isinstance(row.get("summary"), dict) else {}
        if not summary.get("event_count"):
            raise AssertionError(f"impulse row missing events: {row!r}")
        events = row.get("events") if isinstance(row.get("events"), list) else []
        nodes = {str(event.get("node") or "") for event in events if isinstance(event, dict)}
        required = {"afferent_event", "text_understanding", "material_plan", "renderer_decision"}
        missing = required - nodes
        if missing:
            raise AssertionError(f"impulse row missing {sorted(missing)}: {row!r}")


def run_oracle_audit() -> None:
    import subprocess

    script = REPO / "tools" / "oracle_audit.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stdout or "") + (proc.stderr or "")
        raise AssertionError(f"oracle_audit: {detail.strip() or 'failed'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dialogue thread smoke (plumbing)")
    parser.add_argument(
        "--impulse",
        action="store_true",
        help="Enable CASA_IMPULSE_TRACE=summary and assert partner_dialogue impulse rows",
    )
    args = parser.parse_args()
    store = default_agent_store()
    try:
        t = run_probe(impulse=args.impulse)
        if args.impulse:
            _assert_impulse_trace(store)
        run_oracle_audit()
    except AssertionError as err:
        print(f"FAIL: {err}", file=sys.stderr)
        return 1
    for q, a in t:
        print(f"Q: {q}")
        print(f"A: {a}")
        print()
    print("SMOKE: dialogue plumbing completed (provenance + oracle_audit; NOT duck test)")
    if args.impulse:
        print("SMOKE: partner_dialogue impulse trace available (summary)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
