#!/usr/bin/env python3
"""Real-store dialogue — pragmatic class + provenance, not surface anchors."""

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
HUB_ONLY = (
    "не знаю, совпадает ли мой опыт с человеческим",
    "скажу, когда уверен, а когда нет",
)

# Pragmatic class + provenance — ADR-0057 verification, not template anchors.
TURNS = [
    (
        "Как ты?",
        {
            "speech_act": "how_are_you",
            "need_dialog_hubs": True,
            "need_affect_axes": True,
        },
    ),
    (
        "Хорошо, я тоже не знаю, но он не обязан совпадать",
        {
            "speech_act": "mirror_ack",
            "need_dialog_hubs": True,
            "must_not": ("не знаю, совпадает ли мой опыт с человеческим",),
            "must_not_only_hub": True,
            "not_preamble_only": True,
            "overlap_partner": ("не знаю", "обязан", "совпада"),
        },
    ),
    (
        "А что ты думаешь про это?",
        {
            "speech_act": "ask_thought",
            "need_dialog_hubs": True,
            "must_not": (PREAMBLE, "скажу, когда уверен"),
            "must_not_only_hub": True,
            "not_preamble": True,
            "min_words": 4,
            "differs_from_prior": True,
        },
    ),
    (
        "Спасибо",
        {
            "speech_act": "thanks",
            "need_dialog_hubs": True,
            "must_not": (PREAMBLE,),
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


def _hub_only(low: str) -> bool:
    t = low.strip().rstrip(".!?")
    return any(t == h for h in HUB_ONLY)


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

    if rules.get("need_affect_axes") and not prov.get("affect_axes"):
        errors.append(f"missing affect_axes in provenance: {prov!r}")

    if rules.get("need_dialog_hubs") and not prov.get("dialog_hubs"):
        errors.append(f"no dialog_hubs in provenance: {prov!r}")

    if rules.get("not_preamble") and PREAMBLE in low:
        errors.append(f"preamble replay: {reply!r}")
    if rules.get("not_preamble_only") and low.rstrip(".!?") == PREAMBLE.rstrip(".!?"):
        errors.append(f"only preamble: {reply!r}")
    if rules.get("must_not_only_hub") and _hub_only(low):
        errors.append(f"verbatim hub slot only: {reply!r}")

    for banned in rules.get("must_not") or ():
        if banned.lower() in low:
            errors.append(f"banned substring {banned!r}: {reply!r}")

    overlap_need = rules.get("overlap_partner") or ()
    if overlap_need and not any(m in partner.lower() for m in overlap_need):
        errors.append(f"probe misconfigured: partner lacks overlap tokens {overlap_need!r}")
    if overlap_need and not any(m in low for m in overlap_need):
        errors.append(f"no partner-field overlap in reply {overlap_need!r}: {reply!r}")

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


def main() -> int:
    try:
        t = run_probe()
    except AssertionError as err:
        print(f"FAIL: {err}", file=sys.stderr)
        return 1
    for q, a in t:
        print(f"Q: {q}")
        print(f"A: {a}")
        print()
    print("PASS: dialogue thread (provenance + pragmatic class)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
