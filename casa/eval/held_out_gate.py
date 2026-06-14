#!/usr/bin/env python3
"""Held-out gate — load-bearing, generator!=grader evaluator (ADR-0009/0037/0069).

Lifts the cue-conditioned, injection-ablated scorer from
``casa.cli.bench.bench_heldout`` into a reusable evaluator that the
auto-curriculum and the canon promote ceremony call to decide whether a
candidate rule is *genuinely learned* — not merely self-asserted (the
tautology in ``agent_autonomous_retain.self_verify_predict`` predicts the
model's own output and "verifies" against it).

Anti-tautology guarantees enforced here:

  * generator != grader — grading probes (cue -> curated label) come from a
    *held-out* slice; the candidate never supplies the labels it is graded on.
    ``partition_probe_bank`` subtracts held-out cues from train (the discipline
    in ``lab/visual-curriculum/block_pedagogy.train_cue_set``).
  * injection ablation — channels that can *plant* the answer (``claims_nav``
    lookup, hot salience) are zeroed before scoring, so a pass reflects the
    field, not a planted boost (generalizes ``bench_heldout`` claims_nav ablation).
  * negative control — a deliberately-wrong relabel of the held-out slice must
    be *rejected*; cue-conditioned scoring with injection off genuinely fails to
    surface a wrong sibling, which is the falsifiability the old gate lacked.
  * no regression — staging the candidate must not lower a retained baseline.

This module is pure given the (already-staged) field states; *staging* a
candidate into a field copy and *versioned promotion* are the staging-store's
job (Phase 2). ``gate_decision`` takes the staged + base states and returns a
``GateReport`` that ``agent_promote_canon_lattice`` requires before promoting.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any

from casa.prisms.hippo.wake_util import surface_matches_target, top_surface
from casa.prisms.memory.memory_prisms import episode_vote_for_cue
from casa.prisms.memory.surface import surface_from_sss
from casa.prisms.memory.vocab import norm_word


# --------------------------------------------------------------------------- #
# Policy + report
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class GatePolicy:
    """Thresholds, all anchored to existing project bands.

    ``pass_ratio`` mirrors ``block_pedagogy.gate_pass`` know_min_ratio band;
    ``min_held_out``/``min_passes`` forbid 1/1 trivial passes (require repeated
    evidence on *independent* items, the spirit of ``mastery_ready``);
    ``neg_max`` is the ceiling a deliberately-wrong relabel may reach.
    """

    held_out_ratio: float = 0.3
    pass_ratio: float = 0.80
    min_held_out: int = 4
    min_passes: int = 3
    baseline_tol: float = 0.0  # no regression on the retained baseline
    neg_max: float = 0.25
    top_k: int = 3


DEFAULT_GATE_POLICY = GatePolicy()


@dataclass(frozen=True)
class GateReport:
    passed: bool
    candidate_id: str
    held_out_score: float
    held_out_pass: int
    held_out_n: int
    baseline_delta: float
    negative_control_passed: bool
    neg_pass_rate: float
    provenance: dict
    cases: list = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "candidate_id": self.candidate_id,
            "held_out_score": self.held_out_score,
            "held_out_pass": self.held_out_pass,
            "held_out_n": self.held_out_n,
            "baseline_delta": self.baseline_delta,
            "negative_control_passed": self.negative_control_passed,
            "neg_pass_rate": self.neg_pass_rate,
            "provenance": self.provenance,
            "cases": self.cases,
        }


# --------------------------------------------------------------------------- #
# Candidate identity (ties a GateReport to exactly these claims)
# --------------------------------------------------------------------------- #


def candidate_id_for(claims: list[dict]) -> str:
    """Stable id over the candidate's claims; binds a report to its candidate."""
    norm = sorted(
        (c for c in claims if isinstance(c, dict)),
        key=lambda c: str(c.get("concept_id") or ""),
    )
    payload = json.dumps(norm, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "cand-" + hashlib.sha256(payload).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Probe-bank partition (generator != grader)
# --------------------------------------------------------------------------- #


def _cases_of(probe_bank: Any) -> list[dict]:
    raw = probe_bank.get("cases") if isinstance(probe_bank, dict) else probe_bank
    return [c for c in (raw or []) if isinstance(c, dict)]


def _cue_key(case: dict) -> tuple[str, str]:
    return (str(case.get("lattice") or ""), norm_word(str(case.get("cue") or "")))


def _stable_order_key(case: dict, seed: int) -> str:
    lattice, cue = _cue_key(case)
    raw = f"{seed}:{lattice}|{cue}|{case.get('concept_id') or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def partition_probe_bank(
    probe_bank: Any,
    *,
    held_out_ratio: float = 0.3,
    seed: int = 0,
) -> tuple[list[dict], list[dict]]:
    """Deterministically split into (train, held_out), disjoint by (lattice, cue).

    Held-out cues are *subtracted* from train so the generator (which may be fed
    train) can never see a cue it is graded on — the ``train_cue_set`` discipline.
    """
    cases = _cases_of(probe_bank)
    ordered = sorted(cases, key=lambda c: _stable_order_key(c, seed))
    n = len(ordered)
    if n == 0:
        return [], []
    k = max(1, round(n * held_out_ratio))
    held_out = ordered[n - k :]
    held_keys = {_cue_key(c) for c in held_out}
    train = [c for c in ordered[: n - k] if _cue_key(c) not in held_keys]
    return train, held_out


# --------------------------------------------------------------------------- #
# Injection-vector ablation (pass reflects the field, not a planted boost)
# --------------------------------------------------------------------------- #


def ablate_injection_vectors(state: dict) -> dict:
    """Deep-copy ``state`` with answer-injection channels zeroed.

    ``claims_nav`` is the load-bearing vector for field/math prediction: the
    CEN plan can match a query against bundle claims and emit the claim concept
    directly (lookup of a planted label). We zero it exactly as
    ``bench_heldout`` does, plus clear hot-salience so a just-seen cue cannot be
    boosted. Dialogue-path injections (speech-act bind_boost, focus_recent) are
    ablated by the dialogue gate variant where they apply.
    """
    st = copy.deepcopy(state)
    st["claims_nav"] = []
    for key in ("hot", "hot_context"):
        cur = st.get(key)
        if isinstance(cur, dict):
            st[key] = {}
        elif isinstance(cur, list):
            st[key] = []
    st["_ablation"] = "injection_off"
    return st


# --------------------------------------------------------------------------- #
# Cue-conditioned scorer (lifted from bench_heldout.eval_case)
# --------------------------------------------------------------------------- #


def _rank_of(concept_id: str, wake: dict) -> int | None:
    for i, row in enumerate(wake.get("active") or [], start=1):
        if str(row.get("concept_id")) == concept_id:
            return i
    return None


def score_case(state: dict, case: dict, *, bundle: dict, top_k: int = 3) -> dict[str, Any]:
    """Score one held-out case against an (already-ablated) field state.

    Cue-conditioned: rank concepts for the *cue* and check the curated label
    appears top-1 / top-k / matches target. ``episode_vote_for_cue`` is a
    coverage guard only (it is NOT cue-discriminating — it returns the concept's
    total field votes regardless of cue), so it never decides the pass.
    """
    lattice = str(case.get("lattice") or "L1_syllable")
    cue = str(case.get("cue") or "")
    target = str(case.get("target") or "")
    concept_id = str(case.get("concept_id") or "")

    wake = surface_from_sss(state, lattice_id=lattice, prompt=cue)
    top = top_surface(wake)
    rank = _rank_of(concept_id, wake) if concept_id else None
    votes = episode_vote_for_cue(state, bundle, cue, lattice, concept_id) if concept_id else 0
    target_ok = surface_matches_target(wake, target, lattice_id=lattice) if target else False
    top_ok = bool(top and concept_id and str(top.get("concept_id")) == concept_id)
    rank_ok = rank is not None and rank <= top_k

    return {
        "id": case.get("id") or cue,
        "cue": cue,
        "concept_id": concept_id,
        "rank": rank,
        "votes": votes,
        "top1_match": top_ok,
        "topk_match": rank_ok,
        "target_match": target_ok,
        "pass": bool(top_ok or rank_ok or target_ok),
    }


def score_probe_bank(
    state: dict,
    cases: list[dict],
    *,
    bundle: dict,
    policy: GatePolicy = DEFAULT_GATE_POLICY,
    ablate: bool = True,
) -> dict[str, Any]:
    """Score a list of cases; ablates injection vectors once unless told not to."""
    st = ablate_injection_vectors(state) if ablate else state
    results = [score_case(st, c, bundle=bundle, top_k=policy.top_k) for c in cases]
    passed = sum(1 for r in results if r["pass"])
    n = len(results)
    return {
        "passed": passed,
        "n": n,
        "pass_rate": round(passed / n, 4) if n else 0.0,
        "cases": results,
    }


# --------------------------------------------------------------------------- #
# Negative control (a wrong rule must be rejected)
# --------------------------------------------------------------------------- #


def negative_control_relabel(cases: list[dict]) -> list[dict]:
    """Relabel each case to a deterministic sibling concept (wrong label).

    A sibling shares the concept_id prefix family but differs in the leaf, so
    the relabeled bank asks "does the cue surface the *wrong* concept?" — which a
    genuine field must answer no. Cases with no available sibling are dropped.
    """
    by_prefix: dict[str, list[str]] = {}
    for c in cases:
        cid = str(c.get("concept_id") or "")
        prefix = cid.rsplit(".", 1)[0] if "." in cid else cid
        by_prefix.setdefault(prefix, []).append(cid)

    out: list[dict] = []
    for c in cases:
        cid = str(c.get("concept_id") or "")
        prefix = cid.rsplit(".", 1)[0] if "." in cid else cid
        siblings = [s for s in sorted(dict.fromkeys(by_prefix.get(prefix, []))) if s != cid]
        if not siblings:
            continue
        wrong = siblings[0]
        d = dict(c)
        d["concept_id"] = wrong
        d["target"] = ""  # the (wrong) concept_id is the label under test
        out.append(d)
    return out


# --------------------------------------------------------------------------- #
# Gate decision
# --------------------------------------------------------------------------- #


def gate_decision(
    staged_state: dict,
    base_state: dict | None,
    probe_bank: Any,
    *,
    bundle: dict,
    candidate_id: str,
    baseline_set: list[dict] | None = None,
    policy: GatePolicy = DEFAULT_GATE_POLICY,
    seed: int = 0,
) -> GateReport:
    """Decide whether a staged candidate is genuinely learned.

    ``staged_state`` is a field copy with the candidate already applied (staging
    is the caller's / staging-store's job). ``base_state`` is the field *before*
    the candidate, used only for the baseline-regression check.
    """
    _, held_out = partition_probe_bank(probe_bank, held_out_ratio=policy.held_out_ratio, seed=seed)

    held = score_probe_bank(staged_state, held_out, bundle=bundle, policy=policy)
    n = held["n"]
    held_pass = held["passed"]
    held_rate = held["pass_rate"]

    baseline_delta = 0.0
    if baseline_set and base_state is not None:
        after = score_probe_bank(staged_state, baseline_set, bundle=bundle, policy=policy)
        before = score_probe_bank(base_state, baseline_set, bundle=bundle, policy=policy)
        baseline_delta = round(after["pass_rate"] - before["pass_rate"], 4)

    neg_cases = negative_control_relabel(held_out)
    neg = score_probe_bank(staged_state, neg_cases, bundle=bundle, policy=policy) if neg_cases else {"pass_rate": 0.0}
    neg_rate = neg["pass_rate"]
    negative_control_passed = neg_rate <= policy.neg_max

    required_passes = max(policy.min_passes, math.ceil(policy.pass_ratio * n)) if n else policy.min_passes
    passed = bool(
        n >= policy.min_held_out
        and held_rate >= policy.pass_ratio
        and held_pass >= required_passes
        and baseline_delta >= -policy.baseline_tol
        and negative_control_passed
    )

    provenance = {
        "policy": {
            "pass_ratio": policy.pass_ratio,
            "min_held_out": policy.min_held_out,
            "min_passes": policy.min_passes,
            "baseline_tol": policy.baseline_tol,
            "neg_max": policy.neg_max,
            "top_k": policy.top_k,
            "held_out_ratio": policy.held_out_ratio,
        },
        "seed": seed,
        "ablations": ["claims_nav", "hot"],
        "generator": "staged",
        "grader": "curated_labels",
        "scorer": "surface_from_sss(cue)+top1/topk/target",
        "baseline_checked": bool(baseline_set and base_state is not None),
    }

    return GateReport(
        passed=passed,
        candidate_id=candidate_id,
        held_out_score=held_rate,
        held_out_pass=held_pass,
        held_out_n=n,
        baseline_delta=baseline_delta,
        negative_control_passed=negative_control_passed,
        neg_pass_rate=neg_rate,
        provenance=provenance,
        cases=held["cases"],
    )
