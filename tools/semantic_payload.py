#!/usr/bin/env python3
"""
Extract a tiny "semantic payload" from a Markdown document.

Pragmatic step towards "meaning in field":
- Extract *claims* as short text atoms from headings + bullet lists.
- Keep provenance: (doc_path, section heading).
- Add optional normalized concept_id for stable referencing.

No RDF, no reasoner, no embeddings yet.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path


H_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
BULLET_RE = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")
NUM_RE = re.compile(r"^\s*\d+[\).\]]\s+(.*\S)\s*$")


@dataclass(frozen=True)
class Claim:
    concept_id: str | None
    text: str
    doc_path: str
    section: str
    claim_kind: str = "claim"


def _normalize_concept_id(text: str, section: str, doc_path: str) -> str | None:
    t = text.strip()
    p = doc_path.replace("\\", "/").lower()

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
            return "casa.roadmap.v0.substrate_calibration"
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

    return None


def extract_claims(text: str, *, doc_path: str) -> list[Claim]:
    section_stack: list[str] = []
    claims: list[Claim] = []

    def current_section() -> str:
        return " / ".join(section_stack) if section_stack else ""

    for raw in text.splitlines():
        line = raw.rstrip()
        m = H_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            section_stack[:] = section_stack[: max(0, level - 1)]
            section_stack.append(title)
            continue

        for rx in (BULLET_RE, NUM_RE):
            b = rx.match(line)
            if not b:
                continue
            item = b.group(1).strip()
            if len(item) < 6:
                continue
            item = re.sub(r"`([^`]+)`", r"\1", item)
            item = re.sub(r"\*\*([^*]+)\*\*", r"\1", item)
            item = re.sub(r"\*([^*]+)\*", r"\1", item)

            section = current_section()
            claims.append(
                Claim(
                    concept_id=_normalize_concept_id(item, section, doc_path),
                    text=item,
                    doc_path=doc_path,
                    section=section,
                )
            )
            break

    return claims


def main() -> None:
    p = argparse.ArgumentParser(description="Extract semantic payload (claims) from Markdown")
    p.add_argument("md_path", type=Path)
    p.add_argument("--doc-path", default=None, help="knowledge-relative path for provenance")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--max", type=int, default=80, help="cap claims count")
    args = p.parse_args()

    md_text = args.md_path.read_text(encoding="utf-8", errors="replace")
    doc_path = args.doc_path or args.md_path.as_posix()
    claims = extract_claims(md_text, doc_path=doc_path)[: max(0, args.max)]

    payload = {
        "doc_path": doc_path,
        "schema_version": 1,
        "claims": [asdict(c) for c in claims],
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

