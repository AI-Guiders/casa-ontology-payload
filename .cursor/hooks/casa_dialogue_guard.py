#!/usr/bin/env python3
"""Cursor hook: L0 reminder on session + oracle_audit after CASA hot-path edits."""

from __future__ import annotations

import json
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


def session_start() -> int:
    print(
        json.dumps(
            {
                "additional_context": (
                    "CASA payload: перед правками casa/** или design/kb-* — "
                    "agent-notes read_hot_context; INVARIANT одной строкой в ответе. "
                    "Готово только если verify И python tools/oracle_audit.py зелёные. "
                    "Канон: design/CASA-scratch-emergence-conditions-dialogue-v1.md"
                )
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
    return post_edit()


if __name__ == "__main__":
    raise SystemExit(main())
