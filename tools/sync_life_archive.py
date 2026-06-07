#!/usr/bin/env python3
"""Sync von-neumann living store → private life-archive git repo (Git LFS for *.pt, *.db)."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_mirror import (
    LIFE_ARCHIVE_STORE_SUBDIR,
    copy_store_tree,
)

DEFAULT_GH_REPO = "AI-Guiders/von-neumann-life-archive"
DEFAULT_ARCHIVE_DIR = _REPO.parent / "von-neumann-life-archive"
TEMPLATE_DIR = _REPO / "life-archive-template"
STORE_SUBDIR = LIFE_ARCHIVE_STORE_SUBDIR


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=False,
        check=check,
    )


def _git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _git_lfs_available() -> bool:
    try:
        subprocess.run(["git", "lfs", "version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def ensure_git_lfs(*, archive_dir: Path) -> None:
    if not _git_lfs_available():
        raise RuntimeError(
            "git-lfs not found. Install: winget install GitHub.GitLFS — then reopen terminal and run: git lfs install"
        )
    _run(["git", "lfs", "install"], cwd=archive_dir, check=False)
    attrs = archive_dir / ".gitattributes"
    if not attrs.is_file() and TEMPLATE_DIR.is_dir():
        shutil.copy2(TEMPLATE_DIR / ".gitattributes", attrs)
    for pattern in ("*.pt", "*.db", "field_state*.json"):
        _run(["git", "lfs", "track", pattern], cwd=archive_dir, check=False)


def sync_store(store_dir: Path, archive_dir: Path) -> dict:
    store_dir = store_dir.resolve()
    if not store_dir.is_dir():
        raise FileNotFoundError(store_dir)
    target = archive_dir / STORE_SUBDIR
    staging = archive_dir / ".sync-staging"
    if staging.exists():
        shutil.rmtree(staging)
    stats = copy_store_tree(store_dir, staging)
    if target.exists():
        shutil.rmtree(target)
    staging.rename(target)
    meta = {
        "synced_at": _utc_now(),
        "source_store": str(store_dir),
        "stats": stats,
    }
    (archive_dir / "sync_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return meta


def _seed_templates(archive_dir: Path) -> None:
    archive_dir.mkdir(parents=True, exist_ok=True)
    for name in ("README.md", ".gitignore", ".gitattributes"):
        src = TEMPLATE_DIR / name
        dst = archive_dir / name
        if src.is_file() and not dst.exists():
            shutil.copy2(src, dst)


def init_archive(
    archive_dir: Path,
    *,
    gh_repo: str,
    clone: bool = True,
) -> None:
    if not _git_available():
        raise RuntimeError("git not found on PATH")
    archive_dir = archive_dir.resolve()
    if archive_dir.exists() and any(archive_dir.iterdir()):
        if not (archive_dir / ".git").is_dir():
            raise FileNotFoundError(f"{archive_dir} exists but is not a git repo — move it or pass empty dir")
    elif clone:
        if archive_dir.exists():
            archive_dir.rmdir()
        _run(["gh", "repo", "view", gh_repo], check=True)
        _run(["git", "clone", f"https://github.com/{gh_repo}.git", str(archive_dir)])
    else:
        archive_dir.mkdir(parents=True, exist_ok=True)
        _run(["git", "init"], cwd=archive_dir)
        _run(["git", "branch", "-M", "main"], cwd=archive_dir, check=False)
        remote = f"https://github.com/{gh_repo}.git"
        _run(["git", "remote", "add", "origin", remote], cwd=archive_dir, check=False)

    _seed_templates(archive_dir)
    ensure_git_lfs(archive_dir=archive_dir)
    _run(["git", "add", "README.md", ".gitignore", ".gitattributes"], cwd=archive_dir, check=False)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=archive_dir, capture_output=True, text=True)
    if status.stdout.strip():
        _run(
            ["git", "commit", "-m", "chore: life archive template and Git LFS tracking"],
            cwd=archive_dir,
        )
        _run(["git", "push", "-u", "origin", "main"], cwd=archive_dir, check=False)


def create_github_repo(gh_repo: str, *, private: bool = True) -> str:
    _run(
        [
            "gh",
            "repo",
            "create",
            gh_repo,
            "--private" if private else "--public",
            "--description",
            "von-neumann private life archive (store snapshots, Git LFS)",
            "--confirm",
        ]
    )
    return f"https://github.com/{gh_repo}"


def commit_and_push(
    archive_dir: Path,
    *,
    message: str,
    remotes: list[str] | None = None,
) -> dict:
    archive_dir = archive_dir.resolve()
    if not (archive_dir / ".git").is_dir():
        raise FileNotFoundError(f"not a git repo: {archive_dir}")
    ensure_git_lfs(archive_dir=archive_dir)
    _run(["git", "add", "-A"], cwd=archive_dir)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=archive_dir)
    if diff.returncode == 0:
        return {"committed": False, "reason": "no_changes"}
    _run(["git", "commit", "-m", message], cwd=archive_dir)
    pushed: list[str] = []
    for remote in remotes or ["origin"]:
        try:
            _run(["git", "push", remote, "HEAD"], cwd=archive_dir)
            pushed.append(remote)
        except subprocess.CalledProcessError:
            pass
    return {"committed": True, "pushed": pushed, "message": message}


def snapshot(
    store_dir: Path,
    archive_dir: Path,
    *,
    message: str | None = None,
    remotes: list[str] | None = None,
) -> dict:
    meta = sync_store(store_dir, archive_dir)
    msg = message or f"life: snapshot {_utc_now()}"
    git_rep = commit_and_push(archive_dir, message=msg, remotes=remotes)
    return {"sync": meta, "git": git_rep}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)
    p.add_argument("--gh-repo", default=DEFAULT_GH_REPO)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="Verify git and git-lfs on PATH")

    sp_create = sub.add_parser("create-repo", help="Create private GitHub repo via gh")
    sp_create.add_argument("--public", action="store_true")

    sp_init = sub.add_parser("init", help="Clone repo and seed LFS + templates")
    sp_init.add_argument("--no-clone", action="store_true")

    sub.add_parser("sync", help="Copy store → archive/store/ only")

    sp_commit = sub.add_parser("commit", help="git add/commit/push (after sync)")
    sp_commit.add_argument("-m", "--message", required=True)
    sp_commit.add_argument("--remote", action="append", default=None, dest="remotes")

    sp_snap = sub.add_parser("snapshot", help="sync + commit + push")
    sp_snap.add_argument("-m", "--message", default="")
    sp_snap.add_argument("--remote", action="append", default=None, dest="remotes")

    args = p.parse_args()
    store_dir = (args.store_dir or default_agent_store()).resolve()
    archive_dir = args.archive_dir.resolve()

    if args.cmd == "check":
        ok = {"git": _git_available(), "git_lfs": _git_lfs_available()}
        print(json.dumps(ok, indent=2))
        return 0 if all(ok.values()) else 1

    if args.cmd == "create-repo":
        url = create_github_repo(args.gh_repo, private=not args.public)
        print(json.dumps({"created": url}, indent=2))
        return 0

    if args.cmd == "init":
        init_archive(archive_dir, gh_repo=args.gh_repo, clone=not args.no_clone)
        return 0

    if args.cmd == "sync":
        print(json.dumps(sync_store(store_dir, archive_dir), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "commit":
        print(
            json.dumps(
                commit_and_push(archive_dir, message=args.message, remotes=args.remotes),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if args.cmd == "snapshot":
        print(
            json.dumps(
                snapshot(
                    store_dir,
                    archive_dir,
                    message=args.message or None,
                    remotes=args.remotes,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
