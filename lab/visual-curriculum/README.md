# Visual-curriculum lab

Общая обвязка для **всех** lesson-классов с кадрами и moment/sleep (не только literacy).

| Модуль | Назначение |
|--------|------------|
| `curriculum_lab.py` | `CurriculumLabSession`, `IngestJob`, `jobs_from_json_files` |
| `runner_infra.py` | `LessonPack`, `jobs_*`, `run_*`, CLI (`cli_*`, `cli_lab_main`) |
| `manifest_steps.py` | manifest frame → steps, `jobs_manifest_frame_rounds` |
| `probe_infra.py` | teacher probe → `generated/*.json`, `verdict_lex_probe` |
| `probe_lex_verdict.py` | know / ambiguous / wrong / empty |
| `vc_paths.py` | `install(__file__)` — repo + lab на sys.path (micro `_ensure_paths` — shim) |
| `lab_paths.py` | `setup_lab_paths` (+ `chdir` repo) в `bootstrap` |
| `lex_steps.py` | `lex_step()` — vis↔lex |
| `generated/` | moment/summary (в .gitignore); legacy `reports/` тоже ignored |

**Lesson packs:** `LITERACY`, `VISUAL`, `NLINE`, `VENN` — см. `runner_infra.py`.

**Runners:** `import _ensure_paths` → `bootstrap(__file__)` → `cli_*` или `cli_lab_main`.

**Probes:** `python lab/visual-curriculum/probe_grapheme_quiz.py` (и `probe_meta_pure`, geom, nline, venn).

**Smoke:** `python lab/visual-curriculum/_verify_runners.py`

Совместимость: `literacy_steps.py`, `literacy_lab.py`, `literacy_moment.py` — re-export.
