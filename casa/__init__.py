"""CASA runtime package (M2+). Legacy CLIs remain as shims under tools/."""

from casa._paths import REPO_ROOT, TOOLS_DIR, ensure_import_paths

__all__ = ["REPO_ROOT", "TOOLS_DIR", "ensure_import_paths"]
