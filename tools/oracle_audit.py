#!/usr/bin/env python3
"""Static audit: dialogue hot path must not reintroduce compose oracles.

Canon: design/CASA-scratch-emergence-conditions-dialogue-v1.md
Run: python tools/oracle_audit.py [--strict] [paths...]
Exit 0 = pass, 1 = violations.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WAIVERS_PATH = REPO / "design" / "oracle-audit-waivers.v1.json"

HOT_PREFIXES = (
    "casa/domain/dialogue_bind/",
    "casa/domain/subject_articulation.py",
    "casa/domain/subject_voice.py",
    "casa/domain/boundary_compose.py",
    "casa/prisms/tick/discourse/",
    "casa/prisms/tick/articulation_realize.py",
)

SKIP_REL = frozenset(
    {
        "casa/domain/dialogue_bind/speech_act_scoring.py",
        "casa/domain/dialogue_bind/speech_act_hints.py",
        "casa/domain/dialogue_bind/dialog_bind_policy.py",
        "casa/domain/dialogue_bind/blocks.py",
        "casa/domain/dialogue_bind/model.py",
        "casa/domain/dialogue_bind/collectors/",
        "casa/prisms/tick/articulation_realize.py",
    }
)

@dataclass(frozen=True)
class Rule:
    rule_id: str
    pattern: re.Pattern[str]
    message: str
    strict: bool = False


RULES: tuple[Rule, ...] = (
    Rule("no_ack_span", re.compile(r"acknowledgment_span"), "partner-line echo via acknowledgment_span"),
    Rule("no_act_bias", re.compile(r"_ACT_BIAS"), "Python act→hub bias table"),
    Rule("no_social_act_compose", re.compile(r"social_act_compose"), "removed social_act_compose dispatcher"),
    Rule(
        "no_da_echo",
        re.compile(r"""f?['"]Да —"""),
        "situated «Да — {partner}» echo compose",
    ),
    Rule(
        "no_partner_act_if",
        re.compile(
            r"""if\s+act\s*==\s*['"](?:greeting|how_are_you|thanks|farewell|mirror_ack|intro_self|ask_thought)['"]"""
        ),
        "per-act efferent branch in compose/realize hot path",
    ),
    Rule(
        "no_per_hub_disc_route",
        re.compile(
            r"""if\s+disc\.startswith\(['"]ru\.dialog\.(?:greeting|how_are_you|thanks|affect|farewell|self)"""
        ),
        "per-hub ru.dialog.* if-chain routing (use bundle slots + field overlap)",
    ),
    Rule(
        "no_partner_dialog_templates",
        re.compile(r"_PARTNER_DIALOGUE_ACTS|_compose_partner(?:_|$)"),
        "partner dialogue template table / composer",
        strict=True,
    ),
    Rule(
        "continuer_marker_oracle",
        re.compile(r"_continuer_head|Про это — \{"),
        "hardcoded continuer head template (bundle/thread slot only)",
        strict=True,
    ),
    Rule(
        "phatic_prefix_tuple",
        re.compile(r"_PHATIC_PREFIXES\s*="),
        "phatic hub tuple in Python budget (prefer bundle policy)",
        strict=True,
    ),
    Rule(
        "continuer_query_markers",
        re.compile(r"def partner_continuer_query"),
        "substring continuer markers in Python (prefer speech-act / focus block)",
        strict=True,
    ),
    Rule(
        "recall_cue_substrings",
        re.compile(r"_RECALL_CUE_SUBSTRINGS\s*="),
        "recall cue substring table in Python",
        strict=True,
    ),
    Rule(
        "no_realize_oracle_in_discourse",
        re.compile(r"_realize_compare|_realize_explain"),
        "compare/explain oracle on partner discourse path (CEN-only in articulation_realize)",
        strict=True,
    ),
)


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _hot_file(rel: str) -> bool:
    if not rel.endswith(".py"):
        return False
    for skip in SKIP_REL:
        if skip.endswith("/") and rel.startswith(skip):
            return False
        if rel == skip:
            return False
    return any(rel.startswith(prefix) for prefix in HOT_PREFIXES)


def _load_waivers() -> set[tuple[str, str]]:
    if not WAIVERS_PATH.is_file():
        return set()
    try:
        raw = json.loads(WAIVERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    out: set[tuple[str, str]] = set()
    for row in raw.get("waivers") or []:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("rule_id") or "").strip()
        path = str(row.get("path") or "").strip().replace("\\", "/")
        if rid and path:
            out.add((rid, path))
    return out


def _iter_targets(paths: list[str] | None) -> list[Path]:
    if paths:
        out: list[Path] = []
        for raw in paths:
            p = Path(raw)
            if not p.is_absolute():
                p = REPO / p
            if p.is_file():
                out.append(p)
            elif p.is_dir():
                out.extend(sorted(p.rglob("*.py")))
        return out
    files: list[Path] = []
    for prefix in HOT_PREFIXES:
        root = REPO / prefix
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(sorted(root.rglob("*.py")))
    return files


@dataclass
class Violation:
    rule_id: str
    path: str
    line: int
    excerpt: str
    message: str


def audit(*, strict: bool = False, paths: list[str] | None = None) -> list[Violation]:
    waivers = _load_waivers()
    violations: list[Violation] = []

    for file_path in _iter_targets(paths):
        rel = _rel(file_path)
        if not _hot_file(rel):
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for rule in RULES:
                if rule.strict and not strict:
                    continue
                if (rule.rule_id, rel) in waivers:
                    continue
                if rule.pattern.search(line):
                    violations.append(
                        Violation(
                            rule_id=rule.rule_id,
                            path=rel,
                            line=lineno,
                            excerpt=line.strip()[:120],
                            message=rule.message,
                        )
                    )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CASA dialogue oracle static audit")
    parser.add_argument("paths", nargs="*", help="Files or dirs (default: all hot paths)")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Also fail legacy-debt rules (phatic tuples, continuer markers, …)",
    )
    args = parser.parse_args(argv)

    hits = audit(strict=args.strict, paths=args.paths or None)
    if not hits:
        print("PASS: oracle_audit (dialogue hot path)")
        return 0

    for v in hits:
        print(f"{v.path}:{v.line}: [{v.rule_id}] {v.message}: {v.excerpt}")
    print(f"FAIL: oracle_audit — {len(hits)} violation(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
