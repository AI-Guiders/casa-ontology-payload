#!/usr/bin/env python3
"""Cursor hook: Neumann speech guard + oracle audits after CASA hot-path edits."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

def _casa_repo() -> Path:
    """Script lives in casa-ontology-payload/.cursor/hooks — repo root is parents[2]."""
    root = Path(__file__).resolve().parents[2]
    if (root / "tools" / "oracle_audit.py").is_file():
        return root
    raise RuntimeError(f"casa repo not found at {root}")


REPO = _casa_repo()

HOT_MARKERS = (
    "casa-ontology-payload/casa/",
    "casa-ontology-payload/design/kb-",
    "financial/software/open/casa-ontology-payload/casa/",
    "financial/software/open/casa-ontology-payload/design/kb-",
    "casa/domain/",
    "casa/prisms/tick/discourse/",
    "/design/kb-partner",
    "/design/kb-dialog",
    "/design/oracle-audit",
)

SPEECH_MARKERS = (
    "casa/prisms/tick/discourse/",
    "casa/domain/dialogue",
    "casa/domain/subject_articulation.py",
    "casa/domain/subject_voice.py",
    "agents/von-neumann/bundles/",
    "tools/verify_dialogue_thread.py",
    "tools/oracle_audit.py",
    "tools/audit_neumann_oracle_regressions.py",
)

RISK_PATTERNS = (
    "query_intent == \"social\"",
    "query_intent == 'social'",
    "with_intent(\"social\"",
    "with_intent('social'",
    "partner_asks_",
    "compose_single_hub",
    "_STOP",
    "STOP_WORDS",
    "BLACKLIST",
    "clause_from_pieces",
    "closing_for_query",
    "_short_partner_fragment",
)

RISK_REGEXES = (
    re.compile(r"\b(?:if|elif)\s+.*['\"][^'\"]*[А-Яа-яЁё][^'\"]*['\"].*(?:\bin\b|==|startswith)"),
    re.compile(r"\bquery_intent\s*(?:==|!=)\s*['\"]social['\"]"),
    re.compile(r"\bre\.search\(\s*r?['\"][^'\"]*[А-Яа-яЁё][^'\"]*['\"]"),
)


def _paths_from_payload(data: dict) -> list[str]:
    paths: list[str] = []
    for key in ("path", "file_path", "target_file"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            paths.append(val.strip())
    tool_input = data.get("tool_input") or data.get("arguments") or data.get("input")
    if isinstance(tool_input, dict):
        for key in ("path", "file_path", "target_file"):
            val = tool_input.get(key)
            if isinstance(val, str) and val.strip():
                paths.append(val.strip())
    return list(dict.fromkeys(paths))


def _is_casa_hot(path: str) -> bool:
    norm = path.replace("\\", "/").lower()
    return any(marker in norm for marker in HOT_MARKERS)


def _is_speech_hot(path: str) -> bool:
    norm = path.replace("\\", "/").lower()
    return any(marker in norm for marker in SPEECH_MARKERS)


def _proposed_text(data: dict) -> str:
    parts: list[str] = []
    for key in ("content", "new_string", "patch", "text", "code"):
        val = data.get(key)
        if isinstance(val, str):
            parts.append(val)
    tool_input = data.get("tool_input") or data.get("arguments") or data.get("input")
    if isinstance(tool_input, dict):
        for key in ("content", "new_string", "patch", "text", "code"):
            val = tool_input.get(key)
            if isinstance(val, str):
                parts.append(val)
    return "\n".join(parts)


def session_start() -> int:
    print(
        json.dumps(
            {
                "additional_context": (
                    "Neumann/CASA speech path guard: do not start from social/non-social, "
                    "speech_act, ru.dialog hub, phrase regex, or stop-word blacklist. "
                    "Preserve punctuation as afferent evidence. Use impulse-first debugging: "
                    "surface is secondary to afferent event, field delta, material candidates, "
                    "and renderer decision. Run tools/audit_neumann_oracle_regressions.py "
                    "after speech-path edits."
                )
            },
            ensure_ascii=False,
        )
    )
    return 0


def pre_edit() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}
    paths = _paths_from_payload(data)
    if not any(_is_speech_hot(p) for p in paths):
        print(json.dumps({"permission": "allow"}))
        return 0
    proposed = _proposed_text(data)
    hits = [pat for pat in RISK_PATTERNS if pat in proposed]
    hits.extend(f"regex:{idx}" for idx, pattern in enumerate(RISK_REGEXES, start=1) if pattern.search(proposed))
    if hits:
        print(
            json.dumps(
                {
                    "permission": "ask",
                    "user_message": (
                        "Neumann speech guard: proposed edit contains oracle-risk patterns: "
                        + ", ".join(hits)
                    ),
                    "agent_message": (
                        "Do not patch Neumann speech with social/non-social routing, "
                        "speech situations, ru.dialog surface, phrase regex, or stop lists. "
                        "Show the impulse/material hypothesis first."
                    ),
                },
                ensure_ascii=False,
            )
        )
        return 0
    print(
        json.dumps(
            {
                "permission": "allow",
                "additional_context": (
                    "Neumann speech path edit: preserve punctuation, avoid predefined social/"
                    "speech-situation routing, and run audit_neumann_oracle_regressions."
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


def post_edit() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}

    audited: list[str] = []
    for raw_path in _paths_from_payload(data):
        if not _is_casa_hot(raw_path):
            continue
        candidate = Path(raw_path)
        resolved = candidate.resolve() if candidate.is_absolute() else (REPO / candidate).resolve()
        if not resolved.is_file():
            cwd_try = (Path.cwd() / candidate).resolve()
            if cwd_try.is_file():
                resolved = cwd_try
        if not resolved.is_file() or not _is_casa_hot(str(resolved)):
            continue
        try:
            rel = resolved.relative_to(REPO.resolve())
        except ValueError:
            continue
        proc = subprocess.run(
            [sys.executable, str(REPO / "tools" / "oracle_audit.py"), str(rel)],
            cwd=str(REPO),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            detail = ((proc.stdout or "") + (proc.stderr or "")).strip()
            print(
                json.dumps(
                    {
                        "additional_context": (
                            f"oracle_audit FAILED ({rel}):\n{detail}\n"
                            "Исправь или добавь waiver с reason в "
                            "design/oracle-audit-waivers.v1.json"
                        )
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        speech_proc = subprocess.run(
            [sys.executable, str(REPO / "tools" / "audit_neumann_oracle_regressions.py"), str(rel)],
            cwd=str(REPO),
            capture_output=True,
            text=True,
        )
        if speech_proc.returncode != 0:
            detail = ((speech_proc.stdout or "") + (speech_proc.stderr or "")).strip()
            print(
                json.dumps(
                    {
                        "additional_context": (
                            f"Neumann oracle regression audit FAILED ({rel}):\n{detail}\n"
                            "Do not continue with surface patches; inspect impulse/material path first."
                        )
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        audited.append(str(rel).replace("\\", "/"))

    if audited:
        print(
            json.dumps(
                {
                    "additional_context": (
                        f"oracle_audit PASS: {', '.join(audited)}. "
                        "Если hot context ещё не читался — read_hot_context (agent-notes)."
                    )
                },
                ensure_ascii=False,
            )
        )
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "post-edit"
    if mode == "session":
        return session_start()
    if mode == "pre-edit":
        return pre_edit()
    return post_edit()


if __name__ == "__main__":
    raise SystemExit(main())
