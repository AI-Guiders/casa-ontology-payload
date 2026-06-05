# North star: существование агента (не квалиа)

**project-id:** `ca-substrate-agent` (CASA)  
**Status:** канон позиции (lab mirror)  
**Date:** 2026-05-28 (autonomy wiring 2026-06-05)  
**KB canonical:** `knowledge/work/projects/door-to-singularity/ca-substrate-agent/agent-existence-north-star-v1.md`

---

## Одна строка

**Строим субстрат существования во времени в богатой среде; квалиа — не слой проектирования; критерий «живости» — наблюдаемое поведение (duck test).**

---

## Автономия (инженерия v0, 2026-06-05)

| Орган | Модуль | Роль |
|-------|--------|------|
| Macro loop | `agent_sn_cen_tick` | `run_learning_tick` × N, persist, session |
| Intent seed | `autonomy_intent.py` | цель без inbox: practice → spacing → progression → interleave |
| Subject | `subject_agency.py` | inbox = proposal (defer/refuse) |
| Decompose | `wake_decompose.py` | phrase → word queue + `step_focus` на wake |
| Interleave | `interleaving_queue.py` | literacy/math/meta на пустом WM |
| Self-check | `self_check_tick.py` | metacog до CEN |
| Self-drive | `agent_self_drive_tick` | seek + promote после verify |
| Diagnostics | `subject_diagnostics.py` | experience / body / memory / skill_trace / retro |
| Journal | `agent_journal.db` (ADR-0038) | SQLite: trace, tick_log, experience, retro |
| Field | `agent_field.db` (ADR-0039) | routes table + gzip field body |

**Запуск:** `python -m casa.prisms.control.agent_sn_cen_tick --store-dir agents/von-neumann --ticks 10 --body-check-on-wake --retro-on-wake`

**Body check:** `python -m casa.prisms.tick.agent_body_check --store-dir agents/von-neumann --save`

**Skill trace query:**

```bash
python -m casa.prisms.tick.skill_trace_query --store-dir agents/von-neumann --goal-id goal.read.phrase
python -m casa.prisms.tick.skill_trace_query --store-dir agents/von-neumann --skill skill.read.analytic --summary
python -m casa.prisms.tick.agent_retrospective --store-dir agents/von-neumann
python -m casa.prisms.tick.journal_export --store-dir agents/von-neumann
python -m casa.prisms.tick.field_export --store-dir agents/von-neumann --stats
```

---

## Duck test (кратко)

Непрерывность (field + session), память, действие, самопочинка, **инициатива** (автономный T), provenance.

**Rich medium:** IDE/KB сейчас; embodiment позже. Субъект на поле — см. ADR-0034 § agent-first-learn.

---

## Ссылки

- [CASA-ADR-0034-executor-learning-loop.md](CASA-ADR-0034-executor-learning-loop.md)
- [CASA-ADR-0036-agent-self-organization.md](CASA-ADR-0036-agent-self-organization.md)
- [casa-agent-existence-philosophy-v0.md](../../../knowledge/work/casa-agent-existence-philosophy-v0.md)
