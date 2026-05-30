#!/usr/bin/env python3
"""SN (router) and CEN (planner) runtime v2 — digest in, task JSON + nav targets out."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from articulation_grammar_v0 import compose_answer_text  # type: ignore
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
class AnswerBlock:
    concept_id: str
    text: str
    section: str
    doc_path: str
    score: int
    claim_kind: str = "claim"


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
    answer_blocks: tuple[AnswerBlock, ...] = ()
    answer_text: str = ""


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
    wm_mode: str | None = None,
    wm_salience_bias: dict[str, float] | None = None,
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

    if wm_salience_bias:
        for cid, boost in wm_salience_bias.items():
            salience[cid] = salience.get(cid, 0.0) + boost
    if wm_mode == "probe" and gate.mode == "execute":
        gate = GateState(gate_vector=gate.gate_vector, ports={**gate.ports, "p2_sn_to_cen": gate.ports.get("p2_sn_to_cen", 0.0) * 0.85}, mode="probe")

    return GatedDigest(digest=digest, gate=gate, salience=salience)


def _tokenize_query(query: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[\w\u0400-\u04FF]+", query, flags=re.UNICODE) if len(w) > 2]


# Слова, которые не должны тянуть случайный claim (иначе «как дела» → C#).
_SCORE_STOPWORDS = frozenset(
    {
        "как",
        "что",
        "это",
        "для",
        "при",
        "без",
        "или",
        "когда",
        "если",
        "мне",
        "тебе",
        "лучше",
        "нужно",
        "можно",
        "будет",
        "очень",
        "просто",
        "словами",
        "такой",
        "такая",
        "такое",
        "такие",
        "тоже",
        "ещё",
        "еще",
        "уже",
        "все",
        "всё",
    }
)

_CODE_QUERY_MARKERS = (
    "c#",
    "csharp",
    "программ",
    "приложен",
    "консоль",
    "компил",
    "readline",
    "console",
    "writeline",
    "tryparse",
    "emit",
    "dotnet",
    "visual studio",
    "namespace",
    "int.parse",
    "stdin",
    "stdout",
    "код ",
    " код",
    "целых",
    "int ",
    " loop",
    "guess number",
    "вводит",
    "вывести",
    "сложи",
    "сумм",
    "умнож",
    "таблиц",
    "угадай",
    "наибольш",
)

_GRAMMAR_QUERY_MARKERS = (
    "согласно",
    "запят",
    "пароним",
    "орфограф",
    "граммат",
    "пунктуац",
    "придаточ",
    "сложнопод",
    "течение",
    "течении",
    "надеть",
    "одеть",
    "надел",
    "русски",
    "дефис",
    "тире",
    "половинк",
    "ихний",
    "ихн",
    "половинк",
    "очки",
    "ребенк",
    "ребёнк",
    "распоряжен",
    "договор",
    "ввиду",
    "вследствие",
    "однако",
    "числительн",
    "управлен",
    "согласован",
)

_CODE_CLAIM_MARKERS = _CODE_QUERY_MARKERS + (
    "два целых",
    "с ввода",
    "компилятор",
    "grade8",
    "code.sum",
    "code.",
)

_MIN_TOP_CLAIM_SCORE = 10
_MIN_TOP_CLAIM_SCORE_GRAMMAR = 2


def _query_has_grammar_intent(query: str) -> bool:
    q = query.lower()
    return any(m in q for m in _GRAMMAR_QUERY_MARKERS)


def _significant_words(words: list[str]) -> list[str]:
    return [w for w in words if w not in _SCORE_STOPWORDS and len(w) >= 4]


def _query_wants_code(query: str) -> bool:
    q = query.lower()
    return any(m in q for m in _CODE_QUERY_MARKERS)


def _query_is_dialogue(query: str) -> bool:
    """Приветствие, self, бытовые слова (мама), «как сказать» — dialogue KB, не отказ."""
    q = query.strip().lower()
    if not q or _query_wants_code(q):
        return False
    social = (
        "привет",
        "здравствуй",
        "здарова",
        "добрый день",
        "добрый вечер",
        "добрый утро",
        "как дела",
        "что умеешь",
        "кто ты",
        "как ты",
        "мама",
        "папа",
        "позвонить",
        "набрать",
        "вечером",
        "красиво сказать",
        "как сказать",
        "сформулировать",
    )
    if not any(m in q for m in social):
        return False
    if _query_has_grammar_intent(q) and not any(
        x in q for x in ("привет", "мама", "дела", "умеешь", "кто ты", "позвонить", "сказать", "сформулировать")
    ):
        return False
    if any(x in q for x in ("верно ли", "запят", "согласно", "пароним", "орфограф")):
        return False
    if any(x in q for x in ("фильм", "кино", "сериал", "рецепт", "погода")):
        return False
    return True


def _is_dialogue_claim(claim: dict) -> bool:
    cid = str(claim.get("concept_id") or "")
    return cid.startswith("ru.dialog.") or cid.startswith("ru.lang.word.")


def _is_code_bridge_claim(claim: dict) -> bool:
    if claim.get("code_anchors"):
        return True
    blob = f"{claim.get('text', '')} {claim.get('section', '')}".lower()
    if any(m in blob for m in _CODE_CLAIM_MARKERS):
        return True
    if "кластер" in blob and ("программ" in blob or "console" in blob or "readline" in blob):
        return True
    cid = str(claim.get("concept_id") or "").lower()
    return cid.startswith("code.") or ".code." in cid


def _claim_has_significant_overlap(words: list[str], claim: dict) -> bool:
    sig = _significant_words(words)
    if not sig:
        return True
    text = str(claim.get("text") or "").lower()
    section = str(claim.get("section") or "").lower()
    return any(w in text or w in section for w in sig)


def _soft_fallback_hits(bundle: dict) -> list[tuple[dict, int]]:
    for c in bundle.get("claims") or []:
        if c.get("concept_id") == "ru.dialog.soft_miss.01":
            return [(c, 8)]
    return []


def _dialogue_claim_hits(query: str, bundle: dict) -> list[tuple[dict, int]]:
    words = _tokenize_query(query)
    hits: list[tuple[dict, int]] = []
    for c in bundle.get("claims") or []:
        if not _is_dialogue_claim(c):
            continue
        s = _score_claim(query, words, c)
        if s > 0:
            hits.append((c, s))
    hits.sort(key=lambda x: x[1], reverse=True)
    return hits


def _filter_claim_hits(query: str, hits: list[tuple[dict, int]]) -> list[tuple[dict, int]]:
    wants_code = _query_wants_code(query)
    grammar = _query_has_grammar_intent(query)
    words = _tokenize_query(query)
    out: list[tuple[dict, int]] = []
    for claim, score in hits:
        if not wants_code and _is_code_bridge_claim(claim):
            continue
        if not grammar and not _claim_has_significant_overlap(words, claim) and score < 14:
            continue
        out.append((claim, score))
    return out


def _min_top_score(query: str) -> int:
    if _query_is_dialogue(query):
        return 1
    if _query_wants_code(query) or _query_has_grammar_intent(query):
        return _MIN_TOP_CLAIM_SCORE_GRAMMAR
    return _MIN_TOP_CLAIM_SCORE


def _score_claim(query: str, words: list[str], claim: dict) -> int:
    score = 0
    cid = str(claim.get("concept_id") or "").lower()
    text = str(claim.get("text") or "").lower()
    section = str(claim.get("section") or "").lower()
    q = query.lower()

    if cid and (cid in q or q in cid):
        score += 12
    for w in words:
        if w in _SCORE_STOPWORDS:
            continue
        if cid and w in cid:
            score += 4
        if w in section:
            score += 3
        if w in text:
            score += 2
        elif len(w) >= 5:
            stem = w[:5]
            if stem in text or stem in section:
                score += 2
    if len(q) >= 12:
        chunk = q[:48]
        if chunk in text or chunk in section:
            score += 8
    if ("по русски" in q or "по-русски" in q) and ("по-русски" in text or "по русски" in text):
        score += 18
    if "также" in q and "так же" in q and ("также" in text or "так же" in text):
        score += 16
    if "знаю" in q and " что " in q and "запят" in text:
        score += 14
    if _is_dialogue_claim(claim) and _query_is_dialogue(query):
        score += 20
    elif _is_dialogue_claim(claim) and not _query_is_dialogue(query):
        return 0
    return score


def _match_claims(query: str, bundle: dict, *, concept_ids: list[str] | None = None) -> list[tuple[dict, int]]:
    words = _tokenize_query(query)
    cid_set = set(concept_ids) if concept_ids else None
    hits: list[tuple[dict, int]] = []
    for c in bundle.get("claims") or []:
        cid = c.get("concept_id")
        if not cid:
            continue
        if cid_set is not None and cid not in cid_set:
            continue
        s = _score_claim(query, words, c)
        if s > 0:
            hits.append((c, s))
    hits.sort(key=lambda x: x[1], reverse=True)
    return hits


def _match_query_to_concepts(query: str, bundle: dict, concept_ids: list[str]) -> list[tuple[str, int]]:
    hits = _match_claims(query, bundle, concept_ids=concept_ids)
    out = [(str(c["concept_id"]), s) for c, s in hits]
    if not out:
        for cid in concept_ids:
            if cid.lower() in query.lower() or query.lower() in cid.lower():
                out.append((cid, 8))
    return out


def _answer_blocks_from_claims(
    matched: list[tuple[dict, int]],
    *,
    top_k: int = 3,
) -> tuple[AnswerBlock, ...]:
    blocks: list[AnswerBlock] = []
    seen: set[str] = set()
    for c, score in matched[:top_k]:
        cid = str(c.get("concept_id") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        blocks.append(
            AnswerBlock(
                concept_id=cid,
                text=str(c.get("text") or "")[:400],
                section=str(c.get("section") or ""),
                doc_path=str(c.get("doc_path") or ""),
                score=score,
                claim_kind=str(c.get("claim_kind") or "claim"),
            )
        )
    return tuple(blocks)


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
    claims_nav_enabled: bool = True,
) -> TaskEmit:
    d = gated.digest
    ranked = sorted(gated.salience.items(), key=lambda kv: kv[1], reverse=True)
    top_concepts = [k for k, v in ranked if not k.startswith("module:")][:top_k]

    if user_query and not claims_nav_enabled:
        concepts = top_concepts[:top_k] or list(d.concept_ids)[:top_k]
        labels = ", ".join(concepts[:4]) if concepts else "…"
        sketch = f"Из поля (digest): {labels}."
        return TaskEmit(
            intent="query",
            action="emit_digest",
            concepts=concepts,
            edges=d.edge_tokens[: min(8, len(d.edge_tokens))],
            targets=[],
            query_to_dmn=None,
            confidence=gated.gate.ports.get("p2_sn_to_cen", 0.0),
            notes="digest-only (claims_nav disabled)",
            answer_blocks=(),
            answer_text=sketch,
        )

    if user_query:
        claim_hits = _filter_claim_hits(user_query, _match_claims(user_query, bundle, concept_ids=None))
        if _query_is_dialogue(user_query):
            dlg = _dialogue_claim_hits(user_query, bundle)
            if dlg:
                seen = {str(c.get("concept_id")) for c, _ in dlg}
                rest = [(c, s) for c, s in claim_hits if str(c.get("concept_id")) not in seen]
                claim_hits = dlg + rest
        if claim_hits and claim_hits[0][1] < _min_top_score(user_query):
            claim_hits = _dialogue_claim_hits(user_query, bundle) or _soft_fallback_hits(bundle)
        if not claim_hits:
            claim_hits = _soft_fallback_hits(bundle)
        matched = [(str(c["concept_id"]), s) for c, s in claim_hits]
        concepts = [cid for cid, _ in matched[:top_k]] or top_concepts[:3]
        targets = _nav_targets_for_concepts(bundle, concepts)
        action = "open_code" if targets and targets[0].kind == "code" else "open_kb"
        if any(t.kind == "code" for t in targets):
            action = "open_code"
        elif any(t.kind == "kb" for t in targets):
            action = "open_kb"
        if claim_hits and not targets:
            action = "answer_from_memory"
        answers = _answer_blocks_from_claims(claim_hits, top_k=3)
        if not answers and concepts:
            answers = _answer_blocks_from_claims(
                _match_claims(user_query, bundle, concept_ids=concepts),
                top_k=3,
            )
        query_back = None if matched else f"clarify:{user_query[:120]}"
        llm = maybe_llm_probe(query_back, enabled=llm_enable and query_back is not None)
        act = action if targets else "answer_from_memory"
        sketch = compose_answer_text(user_query, answers, action=act)
        return TaskEmit(
            intent="query",
            action=act,
            concepts=concepts,
            edges=d.edge_tokens[: min(8, len(d.edge_tokens))],
            targets=targets,
            query_to_dmn=query_back,
            confidence=gated.gate.ports.get("p2_sn_to_cen", 0.0),
            notes="matched claims v2" if matched else "no direct concept match; SN probe mode",
            llm_probe=llm,
            answer_blocks=answers,
            answer_text=sketch,
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


def task_to_dict(task: TaskEmit, *, fpn: dict | None = None) -> dict:
    out = {
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
        "answer_blocks": [
            {
                "concept_id": b.concept_id,
                "text": b.text,
                "section": b.section,
                "doc_path": b.doc_path,
                "score": b.score,
                "claim_kind": b.claim_kind,
            }
            for b in task.answer_blocks
        ],
        "answer_text": task.answer_text,
    }
    if fpn is not None:
        out["fpn"] = fpn
    return out
