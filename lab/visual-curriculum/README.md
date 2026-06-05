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

**Literacy ingest (педагогика, ADR-0030):** `literacy_pedagogy.py`, `micro-literacy/run_literacy_stage_pedagogy.py` (ingest → probe → `--reinforce-tail`), `run_micro_stage.py --order wordlist`, `enqueue_literacy_inbox.py`. Канон: [CASA-literacy-pedagogy-lab-v1.md](../../design/CASA-literacy-pedagogy-lab-v1.md).

**Font legibility (32×32 sweep):** `probe_font_legibility_sweep.py` — порог PIL pt без записи в store. Канон: [CASA-literacy-font-legibility-experiment-v1.md](../../design/CASA-literacy-font-legibility-experiment-v1.md).

**Фонология (гласная/согласная):** `build_phonology_meta_cards.py` → `run_phonology_meta_stage.py` → `probe_meta_phonology_quiz.py` (`lang.meta.phonology.*`). Порядок ingest — `data/ru-phonology-ingest-order-v1.txt`.

**Слоги (отдельный трек):** `stage-05-syllable-cyrl` → `run_micro_stage.py` + `probe_syllable_quiz.py` (`syllable.*`, lattice `syllables-ru`). Не сборка слова из слогов в runtime.

**Аналитическое чтение R1:** после stage-05 + corpus-слова в LTM — `run_analytic_breakdown_pilot.py` (цепочка слогов + corpus frame), затем `probe_analytic_read_corpus.py` (novel `analytic-probe-*`, без правок `bridge_lex`). В отчёте: `r1_novel_bind` / `r1_novel_via` (`novel_whole` = мост на probe-id; `novel_compose` = chain know + ink + LTM). См. ADR-0032.

**Phrase pilot (RU P1):** закрытие R1 для «мыла»/«раму» — `micro-literacy/run_phrase_pilot_words.py` → `probe_phrase_compose_pilot.py --store von-neumann`. Слоты agent/verb/patient — ADR-0033; согласование как «вопрос→ответ» — §6 того же ADR (L2+, не v1 gate).

**Compare (больше/меньше):** [CASA-compare-greater-less-v1.md](../../design/CASA-compare-greater-less-v1.md)

| S | Runner |
|---|--------|
| S1 math | `micro-nline/run_nline_compare_micro.py` |
| S4 length | `micro-nline/run_nline_length_micro.py`, `micro-geom/run_meta_nline_length_pure.py`, `run_s4_length_chain.py` |
| S2 meta+nline | `micro-geom/run_meta_compare_nline_pure.py` |
| S3 meta+segments | `micro-geom/run_meta_compare_segments_pure.py` |
| S3b spatial LR | `micro-geom/run_meta_spatial_segments_pure.py` |
| S3c spatial AB | `micro-geom/run_meta_spatial_vertical_pure.py` |
| S3 mirror contrast | `micro-geom/run_meta_spatial_mirror_contrast.py` |
| S3d between | `micro-geom/run_meta_spatial_between_pure.py` |
| S4 length | `run_s4_length_chain.py`, lesson-22 |
| S4e angles | `run_meta_geom_angle_pure.py` |
| S4f ∥/⊥ | `run_meta_geom_orientation_pure.py` |
| S5s sweep | `run_meta_geom_sweep_pure.py` |
| S5 width | `run_meta_measure_width_pure.py` |
| **chain 1–4** | `run_geom_stages_1_4_chain.py` (S4e→S4f→S5s→S5) |
| S3 mirror reinforce | `micro-geom/run_meta_spatial_mirror_reinforce.py` (tie-break 4:4) |
| S4 meta+circles | `micro-geom/run_meta_compare_circles_pure.py` |
| S5 center/radius | `micro-geom/run_geom_center_radius.py` |

**Probes:** `probe_nline_compare_quiz.py`, `probe_meta_compare_quiz.py`, `probe_meta_compare_segments_quiz.py`, `probe_meta_spatial_segments_quiz.py`, `probe_meta_pure` (register/size text)

**Meta size (w2 текст):** `run_meta_size_pure.py` — отдельно от compare

**Smoke:** `python lab/visual-curriculum/_verify_runners.py`

Совместимость: `literacy_steps.py`, `literacy_lab.py`, `literacy_moment.py` — re-export.
