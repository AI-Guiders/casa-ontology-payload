#!/usr/bin/env python3
"""
Extract a tiny "semantic payload" from a Markdown document.

Pragmatic step towards "meaning in field":
- Extract *claims* from bullets, tables, and prose paragraphs (sentence split).
- Keep provenance: (doc_path, section heading).
- Add optional normalized concept_id for stable referencing.

No RDF, no reasoner, no embeddings yet.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path


H_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
BULLET_RE = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")
NUM_RE = re.compile(r"^\s*\d+[\).\]]\s+(.*\S)\s*$")
CODE_REF_RE = re.compile(
    r"`([^`\s]+\.(?:cs|py|tsx?|jsx?|md|json))(?::(\d+)(?:-(\d+))?)?`",
    re.IGNORECASE,
)
FENCE_FILE_RE = re.compile(r"^\s*//\s*file:\s*(\S+)\s*$", re.IGNORECASE)
CONCEPT_INLINE_RE = re.compile(
    r"(?:\(concept:\s*([a-zA-Z0-9_.-]+)\)|\*\*id:\*\*\s*([a-zA-Z0-9_.-]+))",
    re.IGNORECASE,
)
TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
SKIP_SECTION_MARKERS = ("provenance", "metadata", "происхождение")
SOURCE_LINE_RE = re.compile(r"^\*+(?:Источник|Sources?)", re.IGNORECASE)


@dataclass(frozen=True)
class CodeAnchor:
    file: str
    line: int | None = None
    line_end: int | None = None
    symbol: str | None = None


@dataclass(frozen=True)
class Claim:
    concept_id: str | None
    text: str
    doc_path: str
    section: str
    claim_kind: str = "claim"
    code_anchors: tuple[CodeAnchor, ...] = ()


def _slug_part(s: str, *, max_len: int = 48) -> str:
    t = s.strip().lower()
    t = re.sub(r"[^\w\u0400-\u04ff]+", "_", t, flags=re.UNICODE)
    t = re.sub(r"_+", "_", t).strip("_")
    return (t[:max_len] if t else "root")


def _classify_claim_kind(text: str) -> str:
    tl = text.lower()
    if tl.startswith(("ошибочно", "верно", "не ", "неверно")) or " | " in text and "ошиб" in tl:
        return "rule"
    if "?" in text or tl.startswith(("как ", "когда ", "почему ", "зачем ")):
        return "question"
    if tl.startswith(("пример", "например", "e.g.", "напр.")):
        return "example"
    if tl.startswith(("определ", "это ", "— ")):
        return "definition"
    return "claim"


def _generic_concept_id(doc_path: str, section: str, text: str, ordinal: int) -> str:
    stem = _slug_part(Path(doc_path.replace("\\", "/")).stem, max_len=32)
    sec = _slug_part(section, max_len=40)
    return f"lang.ru.{stem}.{sec}.{ordinal:03d}"


def _extract_code_anchors(text: str) -> tuple[CodeAnchor, ...]:
    anchors: list[CodeAnchor] = []
    seen: set[tuple[str, int | None]] = set()
    for m in CODE_REF_RE.finditer(text):
        f = m.group(1).replace("\\", "/")
        line = int(m.group(2)) if m.group(2) else None
        line_end = int(m.group(3)) if m.group(3) else None
        key = (f, line)
        if key not in seen:
            seen.add(key)
            anchors.append(CodeAnchor(file=f, line=line, line_end=line_end))
    return tuple(anchors)


def _clean_md_inline(text: str) -> str:
    t = text.strip()
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    return t.strip()


def _split_sentences(text: str, *, min_len: int = 22) -> list[str]:
    parts = re.split(r"(?<=[.!?…])\s+", text)
    out: list[str] = []
    for p in parts:
        s = p.strip()
        if len(s) >= min_len:
            out.append(s)
    if not out and len(text.strip()) >= min_len:
        out.append(text.strip())
    return out


def _should_skip_section(section: str) -> bool:
    s = section.lower()
    return any(m in s for m in SKIP_SECTION_MARKERS)


def _claim_to_dict(c: Claim) -> dict:
    d = asdict(c)
    if c.code_anchors:
        d["code_anchors"] = [
            {k: v for k, v in asdict(a).items() if v is not None} for a in c.code_anchors
        ]
    else:
        d.pop("code_anchors", None)
    return d


def _normalize_concept_id(
    text: str,
    section: str,
    doc_path: str,
    *,
    ordinal: int = 0,
) -> str | None:
    t = text.strip()
    p = doc_path.replace("\\", "/").lower()

    m = CONCEPT_INLINE_RE.search(t)
    if m:
        return (m.group(1) or m.group(2) or "").strip() or None

    if "russian-language-rules" in p or "evidence-humanities-shelf/kb-russian" in p:
        sec_num = re.match(r"^(\d+)\.", section.strip())
        if sec_num:
            return f"ru.grammar.sec{sec_num.group(1)}.{ordinal:02d}"
        sec = _slug_part(section, max_len=36)
        if "согласован" in section.lower():
            return f"ru.grammar.soglasovanie.{ordinal:02d}"
        if "числительн" in section.lower() or "порядков" in section.lower():
            return f"ru.grammar.chislitelnye.{ordinal:02d}"
        if "предлог" in section.lower() or "управлен" in section.lower():
            return f"ru.grammar.upravlenie.{ordinal:02d}"
        if "пароним" in section.lower() or "надеть" in t.lower() or "одеть" in t.lower():
            return f"ru.grammar.paronimy.{ordinal:02d}"
        if "ошибк" in section.lower() or "частые" in section.lower():
            return f"ru.grammar.chastye_oshibki.{ordinal:02d}"
        if "пунктуац" in section.lower() or "запят" in section.lower():
            return f"ru.grammar.punktsuaciya.{ordinal:02d}"
        if "дефис" in section.lower() or "тире" in section.lower() or "черта" in section.lower():
            return f"ru.grammar.defis_tire.{ordinal:02d}"
        if "частиц" in section.lower() or "не с" in t.lower():
            return f"ru.grammar.chastitsy.{ordinal:02d}"
        if "сказуем" in section.lower() or "подлежащ" in section.lower():
            return f"ru.grammar.skazuemoe.{ordinal:02d}"
        if "орфограф" in section.lower() and "слитн" in section.lower():
            return f"ru.grammar.slitno_razdelno.{ordinal:02d}"
        if "местоим" in section.lower():
            return f"ru.grammar.mestoimenie.{ordinal:02d}"
        if sec and sec != "root":
            return f"ru.grammar.{sec}.{ordinal:02d}"

    if "pre-revolutionary-russian" in p or "дореволюцион" in p:
        return f"ru.orthography.doreform.{ordinal:02d}"

    if "regex-mre3-ru" in p or "mre3-ru-chapter" in p:
        return f"ru.regex.mre3_map.{ordinal:02d}"

    # CASA goals card
    if "ca-substrate-agent" in p and "casa-goals-and-roadmap" in p:
        tl = t.lower()
        if tl.startswith("цель 1"):
            return "casa.goal.ca_substrate_locality"
        if tl.startswith("цель 2"):
            return "casa.goal.ainet_kb_exchange_via_field"
        if tl.startswith("цель 3"):
            return "casa.goal.imitation_with_error_and_fix"
        if tl.startswith("v0:"):
            return "casa.roadmap.substrate_calibration"
        if tl.startswith("v1:"):
            return "casa.roadmap.v1.meaning_in_field"
        if tl.startswith("v2:"):
            return "casa.roadmap.v2.agent_loop"
        if tl.startswith("v3:"):
            return "casa.roadmap.v3.ainet_exchange"

    # Research spec metrics (condensed example)
    if "ca-substrate-agent" in p and "research-ml-ca-substrate-agent" in p:
        tl = t.lower()
        if tl.startswith("task success"):
            return "casa.metric.task_success"
        if tl.startswith("stability horizon"):
            return "casa.metric.stability_horizon"
        if tl.startswith("adversarial resistance"):
            return "casa.metric.adversarial_resistance"
        if tl.startswith("interpretability score"):
            return "casa.metric.interpretability"
        if tl.startswith("compute cost"):
            return "casa.metric.compute_cost"
        if tl.startswith("ca-world"):
            return "casa.prototype.ca_world_read_write"
        if tl.startswith("internal memory field"):
            return "casa.prototype.memory_field"
        if tl.startswith("action head"):
            return "casa.prototype.action_head"
        if tl.startswith("loop observe"):
            return "casa.prototype.loop_observe_update_act"

    if ordinal > 0 and (
        "russian-language" in p
        or "pre-revolutionary-russian" in p
        or "mre3-ru-chapter" in p
        or "evidence-humanities-shelf" in p
    ):
        return _generic_concept_id(doc_path, section, text, ordinal)
    return None


def extract_claims(text: str, *, doc_path: str) -> list[Claim]:
    section_stack: list[str] = []
    claims: list[Claim] = []
    seen_text: set[str] = set()
    fence_file: str | None = None
    claim_ordinal = 0

    def current_section() -> str:
        return " / ".join(section_stack) if section_stack else ""

    def emit(item: str, *, kind: str | None = None) -> None:
        nonlocal claim_ordinal
        item = _clean_md_inline(item)
        if len(item) < 12:
            return
        key = item.lower()[:200]
        if key in seen_text:
            return
        seen_text.add(key)
        claim_ordinal += 1
        section = current_section()
        anchors = _extract_code_anchors(item)
        if fence_file and not anchors:
            anchors = (CodeAnchor(file=fence_file),)
        cid = _normalize_concept_id(item, section, doc_path, ordinal=claim_ordinal)
        if not cid:
            cid = _generic_concept_id(doc_path, section, item, claim_ordinal)
        claims.append(
            Claim(
                concept_id=cid,
                text=item,
                doc_path=doc_path,
                section=section,
                claim_kind=kind or _classify_claim_kind(item),
                code_anchors=anchors,
            )
        )

    for raw in text.splitlines():
        line = raw.rstrip()
        fm = FENCE_FILE_RE.match(line)
        if fm:
            fence_file = fm.group(1).replace("\\", "/")
            continue
        m = H_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            section_stack[:] = section_stack[: max(0, level - 1)]
            section_stack.append(title)
            continue

        tr = TABLE_ROW_RE.match(line)
        if tr and not line.strip().startswith("|---"):
            cells = [c.strip() for c in tr.group(1).split("|")]
            if len(cells) >= 2 and cells[0].lower() not in ("ошибочно", "error", "---"):
                note = cells[2].strip() if len(cells) >= 3 else ""
                item = f"{cells[0]} → {cells[1]}"
                if note:
                    item = f"{item} ({note})"
                emit(item, kind="rule")
            continue

        for rx in (BULLET_RE, NUM_RE):
            b = rx.match(line)
            if b:
                emit(b.group(1).strip())
                break
        else:
            if _should_skip_section(current_section()):
                continue
            stripped = line.strip()
            if not stripped or stripped in ("---", "***"):
                continue
            if SOURCE_LINE_RE.match(stripped):
                continue
            if stripped.startswith("**Источники:**") or stripped.startswith("**Источник:**"):
                continue
            prose = _clean_md_inline(stripped)
            if len(prose) < 28:
                continue
            for sent in _split_sentences(prose):
                emit(sent)

    return claims


def main() -> None:
    p = argparse.ArgumentParser(description="Extract semantic payload (claims) from Markdown")
    p.add_argument("md_path", type=Path)
    p.add_argument("--doc-path", default=None, help="knowledge-relative path for provenance")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--max", type=int, default=300, help="cap claims count")
    args = p.parse_args()

    md_text = args.md_path.read_text(encoding="utf-8", errors="replace")
    doc_path = args.doc_path or args.md_path.as_posix()
    claims = extract_claims(md_text, doc_path=doc_path)[: max(0, args.max)]

    payload = {
        "doc_path": doc_path,
        "schema_version": 1,
        "claims": [_claim_to_dict(c) for c in claims],
        "count": len(claims),
    }
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data, encoding="utf-8")
    else:
        print(data)


if __name__ == "__main__":
    main()

