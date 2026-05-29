#!/usr/bin/env python3
"""SN (router) and CEN (planner) runtime v1 — digest in, task JSON out."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldDigest:
    """Structured digest after DMN repair + decode."""

    concept_ids: list[str]
    edge_tokens: list[str]
    concept_scores: dict[str, float] = field(default_factory=dict)
    digest_vector: list[float] = field(default_factory=list)
    modules_active: list[str] = field(default_factory=list)

    @property
    def mean_confidence(self) -> float:
        if not self.concept_scores:
            return 0.0
        return sum(self.concept_scores.values()) / len(self.concept_scores)


@dataclass(frozen=True)
class GateState:
    """SN output: which paths are open."""

    gate_vector: list[float]
    ports: dict[str, float]
    mode: str

    @property
    def cen_open(self) -> bool:
        return self.ports.get("p2_sn_to_cen", 0.0) >= 0.35


@dataclass(frozen=True)
class GatedDigest:
    digest: FieldDigest
    gate: GateState
    salience: dict[str, float]


@dataclass(frozen=True)
class TaskEmit:
    """CEN output — planner task band as JSON (not field channels yet)."""

    intent: str
    action: str
    concepts: list[str]
    edges: list[str]
    query_to_dmn: str | None
    confidence: float
    notes: str = ""


def digest_from_decoded(decoded: dict, *, digest_vector: list[float] | None = None) -> FieldDigest:
    cids = list(decoded.get("concept_ids") or [])
    edges_raw = decoded.get("edges") or []
    edge_tokens: list[str] = []
    for e in edges_raw:
        if isinstance(e, dict):
            s, r, d = e.get("src"), e.get("relation"), e.get("dst")
            if s and r and d:
                edge_tokens.append(f"E:{s}|{r}|{d}")
        elif isinstance(e, str):
            edge_tokens.append(e)
    scores = {cid: 1.0 for cid in cids}
    return FieldDigest(
        concept_ids=cids,
        edge_tokens=edge_tokens,
        concept_scores=scores,
        digest_vector=digest_vector or [],
    )


def sn_route(
    digest: FieldDigest,
    *,
    gate_vector: list[float] | None = None,
    gate_threshold: float = 0.35,
) -> GatedDigest:
    """
    SN v1: route digest to CEN when confidence sufficient.

    gate_vector: optional from field gate channels (learned or deterministic).
    """
    if gate_vector and len(gate_vector) >= 4:
        gv = [float(x) for x in gate_vector[:4]]
    else:
        base = digest.mean_confidence
        if digest.digest_vector:
            base = max(base, sum(digest.digest_vector) / max(len(digest.digest_vector), 1))
        gv = [min(1.0, base + 0.1 * i) for i in range(4)]

    conf = max(gv) if gv else digest.mean_confidence
    p2 = conf if conf >= gate_threshold else conf * 0.5
    ports = {
        "p1_dmn_to_sn": 1.0,
        "p2_sn_to_cen": p2,
        "p3_cen_to_dmn": 0.0 if conf >= gate_threshold else 0.25,
    }
    mode = "execute" if p2 >= gate_threshold else "probe"
    gate = GateState(gate_vector=gv, ports=ports, mode=mode)

    salience: dict[str, float] = {}
    for i, cid in enumerate(digest.concept_ids):
        salience[cid] = digest.concept_scores.get(cid, 0.5) * (1.0 + 0.05 * i)
    if digest.modules_active:
        for m in digest.modules_active:
            salience[f"module:{m}"] = conf

    return GatedDigest(digest=digest, gate=gate, salience=salience)


def _match_query_to_concepts(query: str, bundle: dict, concept_ids: list[str]) -> list[str]:
    q = query.lower()
    hits: list[str] = []
    claims = bundle.get("claims") or []
    for c in claims:
        cid = c.get("concept_id")
        if not cid or cid not in concept_ids:
            continue
        text = str(c.get("text") or "").lower()
        section = str(c.get("section") or "").lower()
        if any(w in text or w in section for w in q.split() if len(w) > 3):
            hits.append(str(cid))
    if not hits:
        for cid in concept_ids:
            if cid.lower() in q or q in cid.lower():
                hits.append(cid)
    return hits


def cen_plan(
    gated: GatedDigest,
    *,
    bundle: dict,
    user_query: str | None = None,
    top_k: int = 5,
) -> TaskEmit:
    """CEN v1: rule-based planner from gated digest (LLM hook later)."""
    d = gated.digest
    ranked = sorted(gated.salience.items(), key=lambda kv: kv[1], reverse=True)
    top_concepts = [k for k, v in ranked if not k.startswith("module:")][:top_k]

    if user_query:
        matched = _match_query_to_concepts(user_query, bundle, d.concept_ids)
        action = "answer_from_memory"
        concepts = matched or top_concepts[:3]
        query_back = None if matched else f"clarify:{user_query[:120]}"
        notes = "matched claims" if matched else "no direct concept match; SN probe mode"
        return TaskEmit(
            intent="query",
            action=action,
            concepts=concepts,
            edges=d.edge_tokens[: min(8, len(d.edge_tokens))],
            query_to_dmn=query_back,
            confidence=gated.gate.ports.get("p2_sn_to_cen", 0.0),
            notes=notes,
        )

    if gated.gate.mode == "probe":
        return TaskEmit(
            intent="probe",
            action="request_more_context",
            concepts=top_concepts,
            edges=[],
            query_to_dmn="Which section should I repair or expand?",
            confidence=gated.gate.ports.get("p2_sn_to_cen", 0.0),
            notes="low gate confidence",
        )

    return TaskEmit(
        intent="summarize",
        action="emit_digest",
        concepts=top_concepts,
        edges=d.edge_tokens[: min(8, len(d.edge_tokens))],
        query_to_dmn=None,
        confidence=gated.gate.ports.get("p2_sn_to_cen", 0.0),
        notes="gated digest ready for downstream tool/LLM",
    )


def task_to_dict(task: TaskEmit) -> dict:
    return {
        "intent": task.intent,
        "action": task.action,
        "concepts": task.concepts,
        "edges": task.edges,
        "query_to_dmn": task.query_to_dmn,
        "confidence": task.confidence,
        "notes": task.notes,
    }
