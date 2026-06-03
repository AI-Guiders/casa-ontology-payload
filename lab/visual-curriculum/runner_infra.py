"""Инфраструктура micro-runners: lesson pack, расписания, run_main."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from curriculum_lab import (
    CurriculumLabSession,
    IngestJob,
    ensure_repo_paths,
    jobs_from_json_files,
    jobs_from_steps,
)
from lex_steps import lex_step

# repo root задаётся при первом lab_session / bootstrap
_REPO: Path | None = None


@dataclass(frozen=True)
class LessonPack:
    """Lesson-класс + подкаталог generated/."""

    rel_dir: str
    generated_subdir: str
    tools: bool = False


LITERACY = LessonPack("lessons/literacy-cards", "micro-literacy", tools=True)
VISUAL = LessonPack("lessons/visual-cards", "micro-geom")
NLINE = LessonPack("lessons/visual-cards", "micro-nline")
VENN = LessonPack("lessons/visual-cards", "micro-venn")


def repo() -> Path:
    if _REPO is None:
        raise RuntimeError("call bootstrap() or lab_session() first")
    return _REPO


def bootstrap(caller_file: str | Path) -> Path:
    """sys.path + chdir; вернуть repo root (как setup_lab_paths)."""
    global _REPO
    from lab_paths import setup_lab_paths

    root, _ = setup_lab_paths(caller_file)
    _REPO = root
    return root


def class_dir_for(pack: LessonPack, root: Path | None = None) -> Path:
    base = root or repo()
    return (base / pack.rel_dir).resolve()


def lab_session(
    pack: LessonPack,
    *,
    micro_dir: Path | str | None = None,
    extra_sys_paths: Sequence[Path | str] = (),
    store_id: str = "von-neumann",
    root: Path | None = None,
) -> CurriculumLabSession:
    base = root or repo()
    paths: list[Path] = []
    cd = class_dir_for(pack, base)
    if pack.tools:
        paths.append(cd / "tools")
    if micro_dir is not None:
        paths.append(Path(micro_dir))
    paths.extend(Path(p) for p in extra_sys_paths)
    return CurriculumLabSession(
        store_id=store_id,
        class_dir=cd,
        generated_subdir=pack.generated_subdir,
        extra_sys_paths=tuple(paths),
    )


def add_rounds_modes_args(
    p: argparse.ArgumentParser,
    *,
    default_rounds: int = 5,
    default_modes: list[str] | None = None,
) -> None:
    modes = default_modes or ["lex_only", "phrase_vis"]
    p.add_argument("--rounds", type=int, default=default_rounds)
    p.add_argument("--modes", nargs="*", default=modes, choices=["lex_only", "phrase_vis"])


def parse_rounds_modes(args: argparse.Namespace) -> tuple[int, tuple[str, ...]]:
    return int(args.rounds), tuple(args.modes)


@dataclass(frozen=True)
class PureMetaPhrase:
    concept_id: str
    surface: str
    frame_id: str
    slug: str


def jobs_pure_meta(
    items: Sequence[PureMetaPhrase],
    *,
    rounds: int,
    modes: Sequence[str],
    moment_prefix: str = "lex-meta-pure",
) -> list[IngestJob]:
    jobs: list[IngestJob] = []
    for r in range(1, rounds + 1):
        for item in items:
            tag = item.slug or item.concept_id.rsplit(".", 1)[-1]
            if "lex_only" in modes:
                jobs.append(
                    IngestJob(
                        f"{moment_prefix}-{tag}-lex-r{r}",
                        [lex_step(item.surface, item.concept_id, cue=item.surface)],
                        {"mode": "lex_only"},
                    )
                )
            if "phrase_vis" in modes:
                jobs.append(
                    IngestJob(
                        f"{moment_prefix}-{tag}-vis-r{r}",
                        [{"visual_frame": item.frame_id}, lex_step(item.surface, item.concept_id)],
                        {"mode": "phrase_vis"},
                    )
                )
    return jobs


def jobs_register_category_pure(
    phrases: Sequence[tuple[str, str, str, str]],
    *,
    rounds: int,
    modes: Sequence[str],
) -> list[IngestJob]:
    items = [
        PureMetaPhrase(concept_id=c, surface=s, frame_id=f, slug=slug)
        for c, s, f, slug in phrases
    ]
    jobs: list[IngestJob] = []
    for r in range(1, rounds + 1):
        for item in items:
            reg = item.concept_id.rsplit(".", 1)[-1]
            if "lex_only" in modes:
                jobs.append(
                    IngestJob(
                        f"lex-cat-pure-{reg}-lex-{item.slug}-r{r}",
                        [lex_step(item.surface, item.concept_id)],
                        {"mode": "lex_only"},
                    )
                )
            if "phrase_vis" in modes:
                jobs.append(
                    IngestJob(
                        f"lex-cat-pure-{reg}-vis-{item.slug}-r{r}",
                        [{"visual_frame": item.frame_id}, lex_step(item.surface, item.concept_id)],
                        {"mode": "phrase_vis"},
                    )
                )
    return jobs


def jobs_from_round_files(
    steps_dir: Path | str,
    round_files: Sequence[tuple[str, str]],
    *,
    rounds: int,
    moment_id_fmt: str,
    extra_key: str = "tag",
) -> list[IngestJob]:
    """round_files: (json_file, tag); moment_id_fmt с {round} и {tag}."""
    root = Path(steps_dir)
    jobs: list[IngestJob] = []
    for r in range(1, rounds + 1):
        for fname, tag in round_files:
            steps = json.loads((root / fname).read_text(encoding="utf-8"))
            mid = moment_id_fmt.format(round=r, tag=tag)[:80]
            jobs.append(IngestJob(mid, steps, {extra_key: tag}))
    return jobs


def jobs_json_alternation(
    steps_dir: Path | str,
    steps_cycle: Sequence[tuple[str, str]],
    *,
    rounds: int,
    moment_id_fmt: str,
    extra_key: str = "granule",
) -> list[IngestJob]:
    """Чередование файлов по циклу (grapheme↔word). moment_id_fmt: {round},{stem},{granule}."""
    root = Path(steps_dir)
    jobs: list[IngestJob] = []
    for r in range(1, rounds + 1):
        for steps_file, granule in steps_cycle:
            stem = steps_file.replace(".json", "").replace("lex-granule-", "")
            mid = moment_id_fmt.format(round=r, stem=stem, granule=granule)[:80]
            steps = json.loads((root / steps_file).read_text(encoding="utf-8"))
            jobs.append(IngestJob(mid, steps, {extra_key: granule}))
    return jobs


def run_jobs(
    pack: LessonPack,
    jobs: Sequence[IngestJob],
    *,
    summary_file: str,
    log_start: dict[str, Any] | None = None,
    summary_builder: Callable[[CurriculumLabSession], dict[str, Any]] | None = None,
    micro_dir: Path | str | None = None,
    root: Path | None = None,
) -> None:
    lab = lab_session(pack, micro_dir=micro_dir, root=root)

    def _run(session: CurriculumLabSession) -> None:
        row = {"moments": len(jobs)}
        if log_start:
            row.update(log_start)
        session.log(row)
        session.run_jobs(iter(jobs))

    lab.run_main(_run, summary_file=summary_file, summary_builder=summary_builder)


def run_json_batch(
    pack: LessonPack,
    steps_dir: Path | str,
    schedule: Sequence[tuple[str, str] | tuple[str, str, dict[str, Any]]],
    *,
    summary_file: str = "summary.json",
    log_start: dict[str, Any] | None = None,
    micro_dir: Path | str | None = None,
) -> None:
    jobs = jobs_from_json_files(steps_dir, schedule)
    run_jobs(pack, jobs, summary_file=summary_file, log_start=log_start, micro_dir=micro_dir or steps_dir)


def ensure_tools_on_path(tools_dir: Path | str) -> Path:
    p = Path(tools_dir).resolve()
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)
    return p


def import_tools_module(tools_dir: Path | str, module: str) -> Any:
    ensure_tools_on_path(tools_dir)
    return __import__(module)


def jobs_meta_phrase_vis(
    cards: Sequence[tuple[str, str, str]],
    *,
    moment_prefix: str = "lex-meta2",
) -> list[IngestJob]:
    """cards: (slug, surface, concept_id) → phrase_vis moment."""
    items: list[tuple[str, list[dict[str, Any]], dict[str, Any]]] = []
    for slug, surface, concept_id in cards:
        items.append(
            (
                f"{moment_prefix}-{slug}"[:80],
                [{"visual_frame": f"word-{slug}-sans"}, lex_step(surface, concept_id)],
                {"concept_id": concept_id},
            )
        )
    return jobs_from_steps(items)


def jobs_json_round_pairs(
    steps_dir: Path | str,
    pairs: Sequence[tuple[str, str]],
    *,
    rounds: int,
    moment_id_fmt: str,
) -> list[IngestJob]:
    """На каждый round — пары (moment_id, json_file). moment_id_fmt: {round}, {tag}."""
    schedule: list[tuple[str, str]] = []
    for r in range(1, rounds + 1):
        for tag, fname in pairs:
            schedule.append((moment_id_fmt.format(round=r, tag=tag), fname))
    return jobs_from_json_files(steps_dir, schedule)


def _cli(description: str | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=description)
    return p.parse_args()


def cli_json_batch(
    pack: LessonPack,
    steps_dir: Path | str,
    schedule: Sequence[tuple[str, str] | tuple[str, str, dict[str, Any]]],
    *,
    summary_file: str = "summary.json",
    description: str | None = None,
    log_start: dict[str, Any] | None = None,
    micro_dir: Path | str | None = None,
) -> None:
    _cli(description)
    run_json_batch(
        pack,
        steps_dir,
        schedule,
        summary_file=summary_file,
        log_start=log_start,
        micro_dir=micro_dir or steps_dir,
    )


def cli_run_jobs(
    pack: LessonPack,
    build_jobs: Callable[[], list[IngestJob]],
    *,
    summary_file: str,
    description: str | None = None,
    log_start: dict[str, Any] | None = None,
    summary_builder: Callable[[CurriculumLabSession], dict[str, Any]] | None = None,
    micro_dir: Path | str | None = None,
) -> None:
    _cli(description)
    run_jobs(
        pack,
        build_jobs(),
        summary_file=summary_file,
        log_start=log_start,
        summary_builder=summary_builder,
        micro_dir=micro_dir,
    )


def cli_rounds_modes_jobs(
    pack: LessonPack,
    build_jobs: Callable[[int, tuple[str, ...]], list[IngestJob]],
    *,
    summary_file: str,
    description: str | None = None,
    default_rounds: int = 5,
    default_modes: list[str] | None = None,
    log_start: Callable[[int, tuple[str, ...], list[IngestJob]], dict[str, Any]] | None = None,
    summary_builder: Callable[[CurriculumLabSession, int, tuple[str, ...]], dict[str, Any]] | None = None,
    micro_dir: Path | str | None = None,
) -> None:
    p = argparse.ArgumentParser(description=description)
    add_rounds_modes_args(p, default_rounds=default_rounds, default_modes=default_modes)
    args = p.parse_args()
    rounds, modes = parse_rounds_modes(args)
    jobs = build_jobs(rounds, modes)
    start = log_start(rounds, modes, jobs) if log_start else {"modes": list(modes), "rounds": rounds, "moments": len(jobs)}

    def _summary(session: CurriculumLabSession) -> dict[str, Any]:
        if summary_builder is not None:
            return summary_builder(session, rounds, modes)
        return {"modes": list(modes), "rounds": rounds, "moments": session.summary_rows}

    run_jobs(
        pack,
        jobs,
        summary_file=summary_file,
        log_start=start,
        summary_builder=_summary if summary_builder or log_start else None,
        micro_dir=micro_dir,
    )


def jobs_register_category(
    categories: Sequence[tuple[str, tuple[str, ...], str]],
    *,
    exemplar_cues: Sequence[str],
    names_rounds: int,
    exemplar_rounds: int,
    face: str = "sans",
) -> list[IngestJob]:
    """(concept_id, surface phrases, register slug) + exemplar letter frames."""
    out: list[IngestJob] = []
    for concept_id, surfaces, register in categories:
        reg = concept_id.rsplit(".", 1)[-1]
        for r in range(1, names_rounds + 1):
            out.append(
                IngestJob(
                    f"lex-cat-{reg}-names-r{r}",
                    [lex_step(s, concept_id) for s in surfaces],
                    {"concept_id": concept_id, "kind": "names", "cue": None},
                )
            )
        for cue in exemplar_cues:
            exemplar_fid = f"letter-{cue}-{register}-{face}"
            for r in range(1, exemplar_rounds + 1):
                mid = f"lex-cat-{reg}-exemplar-{cue}-r{r}"
                steps: list[dict[str, Any]] = [{"visual_frame": exemplar_fid}]
                steps.extend(lex_step(s, concept_id) for s in surfaces)
                out.append(
                    IngestJob(
                        mid,
                        steps,
                        {
                            "concept_id": concept_id,
                            "kind": "exemplar",
                            "cue": cue,
                            "frame_id": exemplar_fid,
                        },
                    )
                )
    return out


def cli_lab_main(
    pack: LessonPack,
    run: Callable[[CurriculumLabSession, argparse.Namespace], None],
    *,
    summary_file: str,
    description: str | None = None,
    parser_setup: Callable[[argparse.ArgumentParser], None] | None = None,
    summary_builder: Callable[[CurriculumLabSession, argparse.Namespace], dict[str, Any]] | None = None,
    micro_dir: Path | str | None = None,
) -> None:
    p = argparse.ArgumentParser(description=description)
    if parser_setup is not None:
        parser_setup(p)
    args = p.parse_args()
    lab = lab_session(pack, micro_dir=micro_dir)

    def _run(session: CurriculumLabSession) -> None:
        run(session, args)

    sb = (lambda s: summary_builder(s, args)) if summary_builder is not None else None
    lab.run_main(_run, summary_file=summary_file, summary_builder=sb)


def cli_pure_meta(
    pack: LessonPack,
    items: Sequence[PureMetaPhrase],
    *,
    summary_file: str,
    description: str | None = None,
    moment_prefix: str = "lex-meta-pure",
    default_rounds: int = 5,
    log_start: Callable[[int, tuple[str, ...], list[IngestJob]], dict[str, Any]] | None = None,
) -> None:
    def _build(rounds: int, modes: tuple[str, ...]) -> list[IngestJob]:
        return jobs_pure_meta(items, rounds=rounds, modes=modes, moment_prefix=moment_prefix)

    cli_rounds_modes_jobs(
        pack,
        _build,
        summary_file=summary_file,
        description=description,
        default_rounds=default_rounds,
        log_start=log_start,
    )
