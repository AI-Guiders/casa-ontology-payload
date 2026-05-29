#!/usr/bin/env python3
"""SN (router) and CEN (planner) runtime v2 — digest in, task JSON + nav targets out."""

from __future__ import annotations

from dataclasses import dataclass, field

from embeddings_layout import salience_from_layout  # type: ignore
from llm_hook import maybe_llm_probe  # type: ignore


@dataclass(frozen=True)
class FieldDigest:
    """Structured digest after DMN repair + decode."""

    concept_ids: list[str]
    edge_tokens: list[str]
    concept_scores: dict[str, float] = field(default_factory=dict)
    digest_vector: list[float] = field(default_factory=list)
    modules_active: list[str] = field(default_factory=list)
    present_tokens: list[str] = field(default_factory=list)

    @property
    def mean_confidence(self) -> float:
        if not self.concept_scores:
            return 0.0
        return sum(self.concept_scores.values()) / len(self.concept_scores)


@dataclass(frozen=True)
class GateState:
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
class NavTarget:
    kind: str
    concept_id: str
    doc_path: str | None = None
    section: str | None = None
    file: str | None = None
    line: int | None = None
    line_end: int | None = None


@dataclass(frozen=True)
class TaskEmit:
    intent: str
    action: str
    concepts: list[str]
    edges: list[str]
    targets: list[NavTarget]
    query_to_dmn: str | None
    confidence: float
    notes: str = ""
    llm_probe: dict | None = None


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
            edge_tokens.append(e if e.startswith("E:") else f"E:{e}")
    present = list(decoded.get("present_tokens_full") or decoded.get("present_token_list") or [])
    if not present:
        vote: dict[str, int] = {}
        for cell in decoded.get("cells") or []:
            for t in cell:
                vote[t] = vote.get(t, 0) + 1
        present = sorted([t for t, v in vote.items() if v >= decoded.get("min_votes", 1)])
    scores = {cid: 1.0 for cid in cids}
    return FieldDigest(
        concept_ids=cids,
        edge_tokens=edge_tokens,
        concept_scores=scores,
        digest_vector=digest_vector or [],
        present_tokens=present,
    )


def sn_route(
    digest: FieldDigest,
    *,
    bundle: dict | None = None,
    gate_vector: list[float] | None = None,
    gate_threshold: float = 0.35,
) -> GatedDigest:
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

    if bundle is not None:
        salience = salience_from_layout(
            concept_ids=digest.concept_ids,
            present_tokens=digest.present_tokens,
            bundle=bundle,
            base_salience=salience,
        )

    return GatedDigest(digest=digest, gate=gate, salience=salience)


def _tokenize_query(query: str) -> list[str]:
    return [w.lower() for w in query.split() if len(w) > 2]


def _score_claim(query: str, words: list[str], claim: dict) -> int:
    score = 0
    cid = str(claim.get("concept_id") or "").lower()
    text = str(claim.get("text") or "").lower()
    section = str(claim.get("section") or "").lower()
    q = query.lower()

    if cid and (cid in q or q in cid):
        score += 12
    for w in words:
        if cid and w in cid:
            score += 4
        if w in section:
            score += 3
        if w in text:
            score += 2
    return score


def _match_query_to_concepts(query: str, bundle: dict, concept_ids: list[str]) -> list[tuple[str, int]]:
    words = _tokenize_query(query)
    hits: list[tuple[str, int]] = []
    cid_set = set(concept_ids)
    for c in bundle.get("claims") or []:
        cid = c.get("concept_id")
        if not cid or cid not in cid_set:
            continue
        s = _score_claim(query, words, c)
        if s > 0:
            hits.append((str(cid), s))
    if not hits:
        for cid in concept_ids:
            if cid.lower() in query.lower() or query.lower() in cid.lower():
                hits.append((cid, 8))
    hits.sort(key=lambda x: x[1], reverse=True)
    return hits


def _nav_targets_for_concepts(bundle: dict, concept_ids: list[str]) -> list[NavTarget]:
    targets: list[NavTarget] = []
    seen: set[str] = set()
    by_cid: dict[str, dict] = {}
    for c in bundle.get("claims") or []:
        cid = c.get("concept_id")
        if cid:
            by_cid[str(cid)] = c

    for cid in concept_ids:
        if cid in seen:
            continue
        seen.add(cid)
        c = by_cid.get(cid)
        if not c:
            continue
        dp = c.get("doc_path")
        sec = c.get("section")
        if dp:
            targets.append(
                NavTarget(kind="kb", concept_id=cid, doc_path=str(dp), section=str(sec or ""))
            )
        for a in c.get("code_anchors") or []:
            if isinstance(a, dict) and a.get("file"):
                targets.append(
                    NavTarget(
                        kind="code",
                        concept_id=cid,
                        file=str(a["file"]),
                        line=a.get("line"),
                        line_end=a.get("line_end"),
                    )
                )
    return targets


def task_band_dict(task: TaskEmit) -> dict[str, float]:
    """Layout task.* channel stub (values 0..1 for downstream field write)."""
    conf = min(1.0, max(0.0, task.confidence))
    return {
        "task.intent.query": 1.0 if task.intent == "query" else 0.0,
        "task.intent.probe": 1.0 if task.intent == "probe" else 0.0,
        "task.action.open_kb": 1.0 if any(t.kind == "kb" for t in task.targets) else 0.0,
        "task.action.open_code": 1.0 if any(t.kind == "code" for t in task.targets) else 0.0,
        "task.confidence": conf,
    }


def cen_plan(
    gated: GatedDigest,
    *,
    bundle: dict,
    user_query: str | None = None,
    top_k: int = 5,
    llm_enable: bool = False,
) -> TaskEmit:
    d = gated.digest
    ranked = sorted(gated.salience.items(), key=lambda kv: kv[1], reverse=True)
    top_concepts = [k for k, v in ranked if not k.startswith("module:")][:top_k]

    if user_query:
        matched = _match_query_to_concepts(user_query, bundle, d.concept_ids)
        concepts = [cid for cid, _ in matched[:top_k]] or top_concepts[:3]
        targets = _nav_targets_for_concepts(bundle, concepts)
        action = "open_code" if targets and targets[0].kind == "code" else "open_kb"
        if any(t.kind == "code" for t in targets):
            action = "open_code"
        elif any(t.kind == "kb" for t in targets):
            action = "open_kb"
        query_back = None if matched else f"clarify:{user_query[:120]}"
        llm = maybe_llm_probe(query_back, enabled=llm_enable and query_back is not None)
        return TaskEmit(
            intent="query",
            action=action if targets else "answer_from_memory",
            concepts=concepts,
            edges=d.edge_tokens[: min(8, len(d.edge_tokens))],
            targets=targets,
            query_to_dmn=query_back,
            confidence=gated.gate.ports.get("p2_sn_to_cen", 0.0),
            notes="matched claims v2" if matched else "no direct concept match; SN probe mode",
            llm_probe=llm,
        )

    targets = _nav_targets_for_concepts(bundle, top_concepts)
    if gated.gate.mode == "probe":
        llm = maybe_llm_probe("Which section should I repair or expand?", enabled=llm_enable)
        return TaskEmit(
            intent="probe",
            action="request_more_context",
            concepts=top_concepts,
            edges=[],
            targets=targets,
            query_to_dmn="Which section should I repair or expand?",
            confidence=gated.gate.ports.get("p2_sn_to_cen", 0.0),
            notes="low gate confidence",
            llm_probe=llm,
        )

    return TaskEmit(
        intent="summarize",
        action="emit_digest",
        concepts=top_concepts,
        edges=d.edge_tokens[: min(8, len(d.edge_tokens))],
        targets=targets,
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
        "targets": [
            {k: v for k, v in {
                "kind": t.kind,
                "concept_id": t.concept_id,
                "doc_path": t.doc_path,
                "section": t.section,
                "file": t.file,
                "line": t.line,
                "line_end": t.line_end,
            }.items() if v is not None}
            for t in task.targets
        ],
        "task_band": task_band_dict(task),
        "query_to_dmn": task.query_to_dmn,
        "confidence": task.confidence,
        "notes": task.notes,
        "llm_probe": task.llm_probe,
    }
