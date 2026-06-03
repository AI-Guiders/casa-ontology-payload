# Visual-curriculum lab

Общая обвязка для **всех** lesson-классов с кадрами и moment/sleep (не только literacy).

| Модуль | Назначение |
|--------|------------|
| `curriculum_lab.py` | `CurriculumLabSession` — load/ingest/save store, отчёты |
| `lab_paths.py` | `setup_lab_paths(__file__)` для скриптов в `micro-*` |
| `lex_steps.py` | `lex_step()` — vis↔lex (любой `class_dir` + lattice) |
| `probe_lex_verdict.py` | вердикт probe по lexical |
| `micro-literacy/` | runners для `lessons/literacy-cards` |
| `micro-geom/` | runners для `lessons/visual-cards` |
| `generated/<subdir>/` | JSON moment + summary (в .gitignore) |

**Классы уроков** (отдельные `lessons/…/class.manifest.json`):

- `literacy-cards` — grapheme, слова, мета на JPEG (`lang.meta.*`, `grapheme.*`, `lang.word.*`)
- `visual-cards` — vis↔math (`geom.*`) и (идея) meta size на фигурах

Метаязык (`lang.meta.*`) — ось **vis↔lex**, общая для literacy и geom; см. `design/CASA-learning-protocol-vis-math-v1.md` § Vis↔lex.

```python
from lab_paths import setup_lab_paths
_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession, IngestJob
from lex_steps import lex_step

lab = CurriculumLabSession(
    class_dir=_REPO / "lessons" / "literacy-cards",  # или visual-cards
    generated_subdir="micro-literacy",
)
```

Совместимость: `micro-literacy/literacy_steps.py` и `literacy_lab.py` — тонкие re-export.
