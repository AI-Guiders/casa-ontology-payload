#!/usr/bin/env python3
"""Real-store dialogue smoke — bind trace + speech-act provenance (plumbing only).

NOT an emergence / duck-test gate: fixed partner script + hub-prefix expectations
prescribe routing. See design/CASA-work-verification-dialogue-thread.v1.md §Limits.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.dialogue_provenance import meaning_provenance
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
            "speech_act": "how_are_you",
            "expect_bind_hub_prefix": "ru.dialog.how_are_you",
            "need_affect_axes": True,
            "allow_verbatim_winner": True,
        },
    ),
    (
        "Хорошо, я тоже не знаю, но он не обязан совпадать",
        {
            "speech_act": "mirror_ack",
            "expect_bind_hub_prefix": ("ru.dialog.affect", "ru.dialog.self", "ru.dialog.honest"),
            "forbid_phrase_substrings": (PREAMBLE,),
            "forbid_verbatim_winner": True,
            "min_words": 3,
        },
    ),
    (
        "А что ты думаешь про это?",
        {
            "speech_act": "ask_thought",
            "expect_bind_hub_prefix": ("ru.dialog.self", "ru.dialog.honest", "dialog.context"),
            "forbid_phrase_substrings": (PREAMBLE,),
            "min_words": 4,
            "differs_from_prior": True,
        },
    ),
    (
        "Спасибо",
        {
            "speech_act": "thanks",
            "expect_bind_hub_prefix": "ru.dialog.thanks",
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

    expected_act = rules.get("speech_act")
    acts = prov.get("partner_speech_acts") or []
    if expected_act and expected_act not in acts:
        errors.append(f"missing speech_act {expected_act!r} in provenance {acts!r}")

    trace = prov.get("bind_trace") or {}
    if not trace.get("winner_bind_hub"):
        errors.append(f"missing bind_trace: {prov!r}")

    expect_hub = rules.get("expect_bind_hub_prefix")
    if expect_hub and trace:
        hub = str(trace.get("winner_bind_hub") or "")
        if isinstance(expect_hub, str):
            expect_hub = (expect_hub,)
        if not any(hub.startswith(p) for p in expect_hub):
            errors.append(f"bind hub {hub!r} not in {expect_hub!r}")

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
        errors.append(f"too short: {reply!r}")

    if rules.get("differs_from_prior") and prior_reply:
        if _token_overlap(reply, prior_reply) >= max(3, len(prior_reply.split()) // 2):
            errors.append(f"replay of prior reply: {prior_reply!r} → {reply!r}")

    if not reply.strip():
        errors.append("empty reply")

    return errors


def run_probe(*, reset_ring: bool = True) -> list[tuple[str, str]]:
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
    for partner, rules in TURNS:
        append_partner_turn(store, partner, provenance={"source": "verify"})
        ctx, reply = compose_subject_partner_reply_with_ctx(
            partner, task, state, wm, store_dir=store
        )
        prov = meaning_provenance(ctx)
        errors = _assert_turn(partner, reply, prov, rules, prior_reply=prior_reply)
        if errors:
            raise AssertionError(f"turn {partner!r}: " + "; ".join(errors))
        append_subject_turn(
            store,
            reply,
            kind="reply",
            provenance=prov,
        )
        transcript.append((partner, reply))
        prior_reply = reply
    return transcript


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
    try:
        t = run_probe()
        run_oracle_audit()
    except AssertionError as err:
        print(f"FAIL: {err}", file=sys.stderr)
        return 1
    for q, a in t:
        print(f"Q: {q}")
        print(f"A: {a}")
        print()
    print("PASS: dialogue thread smoke (provenance + oracle_audit; NOT duck test)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
