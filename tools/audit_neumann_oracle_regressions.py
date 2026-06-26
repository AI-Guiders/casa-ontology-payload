#!/usr/bin/env python3
"""Fail-fast audit for Neumann speech-path oracle regressions.

This is not a free-speech test. It catches code shapes that usually mean
"understanding" was replaced by a router, blacklist, regex, or script hub.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

DEFAULT_TARGETS = (
    "casa/domain/dialogue_tick.py",
    "casa/domain/dialogue_bind",
    "casa/domain/subject_articulation.py",
    "casa/domain/subject_voice.py",
    "casa/prisms/tick/discourse",
    "casa/nervous/dialogue_hooks.py",
    "tools/verify_dialogue_thread.py",
    "agents/von-neumann/bundles/kb-lang-ru-grammar-dialog-v1.bundle.json",
)

HOT_RENDERER_FILES = {
    "casa/prisms/tick/discourse/field_social.py",
    "casa/prisms/tick/discourse/situated.py",
    "casa/prisms/tick/discourse/realizers/blocks.py",
    "casa/prisms/tick/discourse/strategies/recall_social_general.py",
}

ALLOW = {
    # Existing legacy markers are allowed only in the guard/audit machinery that
    # detects them, not in the speech path itself.
    ("tools/audit_neumann_oracle_regressions.py", "social-router"),
    ("tools/audit_neumann_oracle_regressions.py", "speech-situation-gate"),
    ("tools/audit_neumann_oracle_regressions.py", "literal-russian-branch"),
    ("tools/audit_neumann_oracle_regressions.py", "stop-word-speech-gate"),
    ("tools/audit_neumann_oracle_regressions.py", "field-social-renderer"),
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    code: str
    message: str
    text: str


RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "social-router",
        re.compile(r"\bquery_intent\s*(?:==|!=)\s*['\"]social['\"]|\bwith_intent\(\s*['\"]social['\"]"),
        "Do not branch compose on social/non-social before text understanding.",
    ),
    (
        "speech-situation-gate",
        re.compile(r"partner_asks_|how_are_you|ask_thought|speech_act.*(?:==|in)|compose_single_hub"),
        "Predefined speech situations are telemetry at most, not hot-path truth.",
    ),
    (
        "literal-russian-branch",
        re.compile(r"\b(?:if|elif)\s+.*['\"][^'\"]*[А-Яа-яЁё][^'\"]*['\"].*(?:\bin\b|==|startswith)"),
        "Literal Russian phrase checks in dialogue code are likely oracles.",
    ),
    (
        "stop-word-speech-gate",
        re.compile(r"\b(?:_STOP|STOP_WORDS|BLACKLIST|FORBID|forbid_words|forbidden_words)\b"),
        "Stop-word/blacklist gates in speech path tend to become reverse oracles.",
    ),
    (
        "field-social-renderer",
        re.compile(r"\b(?:clause_from_pieces|closing_for_query|_short_partner_fragment|_prepositional_focus_terms)\b"),
        "field_social must not be a final renderer or query parser.",
    ),
    (
        "punctuation-discard",
        re.compile(r"\.strip\([\"']\s*\.\?!|rstrip\([\"']\.\?!|re\.sub\(.*[\"']\\W\+"),
        "Punctuation is afferent evidence; do not discard it before event construction.",
    ),
)


def _iter_files(targets: list[str]) -> list[Path]:
    paths: list[Path] = []
    raw_targets = targets or list(DEFAULT_TARGETS)
    for raw in raw_targets:
        path = Path(raw)
        if not path.is_absolute():
            path = REPO / path
        if path.is_dir():
            paths.extend(p for p in path.rglob("*") if p.suffix in {".py", ".json", ".md"})
        elif path.is_file():
            paths.append(path)
    return sorted(set(paths))


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _rule_applies(rel: str, code: str) -> bool:
    if (rel, code) in ALLOW:
        return False
    if code == "field-social-renderer" and rel != "casa/prisms/tick/discourse/field_social.py":
        return False
    if code in {"social-router", "speech-situation-gate"}:
        return rel.startswith(("casa/", "agents/von-neumann/bundles/", "tools/verify_dialogue"))
    return True


def _line_allowed(rel: str, code: str, line: str) -> bool:
    if code == "literal-russian-branch" and rel == "casa/domain/subject_articulation.py":
        return "ru.grammar." in line or "Правильно:" in line
    return False


def audit(paths: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for path in _iter_files(paths):
        rel = _rel(path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for code, pattern, message in RULES:
                if not _rule_applies(rel, code):
                    continue
                if _line_allowed(rel, code, line):
                    continue
                if pattern.search(line):
                    findings.append(Finding(rel, idx, code, message, stripped[:180]))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Files or directories to audit; defaults to Neumann speech path")
    args = parser.parse_args()

    findings = audit(args.paths)
    if not findings:
        print("PASS: audit_neumann_oracle_regressions")
        return 0

    print("FAIL: Neumann oracle regression audit", file=sys.stderr)
    for item in findings:
        print(
            f"{item.path}:{item.line}: {item.code}: {item.message}\n"
            f"  {item.text}",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
