"""Общая обвязка visual-curriculum lab: store, lesson moment ingest, отчёты."""

from __future__ import annotations

import json
import os
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Iterator, Sequence
from typing import Any, Self

_CURRICULUM = Path(__file__).resolve().parent
_REPO = _CURRICULUM.parents[1]


def ensure_repo_paths(*, extra_sys_paths: tuple[Path, ...] = ()) -> Path:
    """Repo root + lab/visual-curriculum на sys.path, casa import paths."""
    if str(_REPO) not in sys.path:
        sys.path.insert(0, str(_REPO))
    if str(_CURRICULUM) not in sys.path:
        sys.path.insert(0, str(_CURRICULUM))
    for p in extra_sys_paths:
        s = str(p.resolve())
        if s not in sys.path:
            sys.path.insert(0, s)
    from casa._paths import ensure_import_paths

    ensure_import_paths()
    os.chdir(_REPO)
    return _REPO


@dataclass
class IngestJob:
    moment_id: str
    steps: list[dict[str, Any]]
    summary: dict[str, Any] = field(default_factory=dict)


def jobs_from_json_files(
    steps_dir: Path | str,
    schedule: Sequence[tuple[str, str] | tuple[str, str, dict[str, Any]]],
) -> list[IngestJob]:
    """(moment_id, json_file) или (moment_id, json_file, summary_extra)."""
    root = Path(steps_dir)
    jobs: list[IngestJob] = []
    for item in schedule:
        moment_id = item[0]
        fname = item[1]
        extra: dict[str, Any] = dict(item[2]) if len(item) > 2 else {}
        steps = json.loads((root / fname).read_text(encoding="utf-8"))
        jobs.append(IngestJob(moment_id, steps, extra))
    return jobs


def jobs_from_steps(
    schedule: Sequence[tuple[str, list[dict[str, Any]] | tuple[str, list[dict[str, Any]], dict[str, Any]]]],
) -> list[IngestJob]:
    """(moment_id, steps) или (moment_id, steps, summary_extra)."""
    jobs: list[IngestJob] = []
    for item in schedule:
        moment_id = item[0]
        steps = item[1]
        extra: dict[str, Any] = dict(item[2]) if len(item) > 2 else {}
        jobs.append(IngestJob(moment_id, steps, extra))
    return jobs


class CurriculumLabSession:
    """Один writer на agent store: load → ingest* → save (literacy, geom, sets, …)."""

    def __init__(
        self,
        *,
        store_id: str = "von-neumann",
        class_dir: Path | str | None = None,
        reports_subdir: str = ".",
        extra_sys_paths: tuple[Path | str, ...] = (),
    ) -> None:
        extra = tuple(Path(p) for p in extra_sys_paths)
        ensure_repo_paths(extra_sys_paths=extra)
        self.repo = _REPO
        self.store_dir = (self.repo / "agents" / store_id).resolve()
        self.class_dir = Path(class_dir).resolve() if class_dir is not None else None
        self.reports_dir = self.repo / "lab" / "visual-curriculum" / "reports" / reports_subdir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self._state: dict[str, Any] | None = None
        self.summary_rows: list[dict[str, Any]] = []

    @property
    def state(self) -> dict[str, Any]:
        if self._state is None:
            raise RuntimeError("call load() first")
        return self._state

    def log(self, payload: dict[str, Any]) -> None:
        print(json.dumps(payload, ensure_ascii=False), flush=True)

    def load(self, *, phase_extra: dict[str, Any] | None = None) -> dict[str, Any]:
        from casa.cli.ingest_state import resolve_ingest_state

        row = {"phase": "load_store", "store": str(self.store_dir)}
        if phase_extra:
            row.update(phase_extra)
        self.log(row)
        self._state = resolve_ingest_state(self.store_dir, None)
        return self._state

    def save(self, *, sync_ltm: bool = True) -> None:
        from casa.prisms.shared.store_persist import save_runtime_state

        save_runtime_state(
            self.store_dir,
            self.state,
            force=True,
            thin=True,
            sync_ltm_on_save=sync_ltm,
        )
        self.log({"phase": "saved", "store": str(self.store_dir)})

    def ingest(
        self,
        job: IngestJob | str,
        steps: list[dict[str, Any]] | None = None,
        **summary: Any,
    ) -> dict[str, Any]:
        from casa.cli.ingest_lesson_moment import ingest_lesson_moment

        if self.class_dir is None:
            raise RuntimeError("class_dir is required for ingest")
        if isinstance(job, IngestJob):
            moment_id, steps, extra = job.moment_id, job.steps, dict(job.summary)
        else:
            moment_id, extra = str(job), dict(summary)
            if steps is None:
                raise TypeError("steps required when first arg is moment_id")
        rep = ingest_lesson_moment(
            self.store_dir,
            self.class_dir,
            moment_id=moment_id,
            steps=steps,
            sleep=True,
            persist=False,
            state=self.state,
            report_path=self.reports_dir / f"moment-{moment_id}.json",
        )
        row = {
            "moment_id": moment_id,
            "bridges_emergent": rep.get("bridges_emergent"),
            **extra,
        }
        self.summary_rows.append(row)
        self.log(row)
        return row

    def run_jobs(self, jobs: Iterator[IngestJob]) -> list[dict[str, Any]]:
        for job in jobs:
            self.ingest(job)
        return list(self.summary_rows)

    def write_summary(self, filename: str, payload: dict[str, Any]) -> Path:
        out = self.reports_dir / filename
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.log({"done": len(self.summary_rows), "summary": str(out)})
        return out

    def load_manifest(self, name: str = "class.manifest.json") -> dict[str, Any]:
        if self.class_dir is None:
            raise RuntimeError("class_dir is required for load_manifest")
        return json.loads((self.class_dir / name).read_text(encoding="utf-8"))

    def run_main(
        self,
        fn,
        *,
        summary_file: str | None = None,
        summary_builder: Any = None,
    ) -> None:
        """load → fn(session) → save; при ошибке — JSON traceback."""
        try:
            self.load()
            fn(self)
            self.save()
            if summary_file:
                if callable(summary_builder):
                    payload = summary_builder(self)
                elif isinstance(summary_builder, dict):
                    payload = summary_builder
                else:
                    payload = {"moments": self.summary_rows}
                self.write_summary(summary_file, payload)
        except Exception as exc:
            self.log({"error": repr(exc), "traceback": traceback.format_exc()})
            raise

    def __enter__(self) -> Self:
        self.load()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self.save()
