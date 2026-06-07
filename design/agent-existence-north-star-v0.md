# North star: существование субъекта (не квалиа)

**project-id:** `ca-substrate-agent` (CASA)  
**Status:** канон позиции (lab mirror)  
**Date:** 2026-05-28 (autonomy wiring 2026-06-05; subject-as-interlocutor 2026-06-06; articulate без LLM 2026-06-07)  
**KB canonical:** `knowledge/work/projects/door-to-singularity/ca-substrate-agent/agent-existence-north-star-v1.md`

---

## Одна строка

**Строим субстрат существования субъекта во времени в богатой среде; квалиа — не слой проектирования; критерий «живости» — наблюдаемое поведение (duck test), включая диалог и инициативу.**

---

## Субъект ≠ агент-исполнитель

| | **Субъект** (von-neumann) | **Агент-исполнитель** (узкое) |
|---|---------------------------|-------------------------------|
| **Кто** | Собеседник, партнёр на поле | Headless worker одного цикла 1–5 |
| **Цель inbox** | Предложение — accept / defer / refuse | Приказ к исполнению |
| **Речь** | Ответ **и** инициатива; позиция в диалоге | Probe verdict, sketch answer |
| **Время** | Длинные session, macro ticks, автономные задачи | Один lab run |
| **Кanon** | agent-first-learn, ADR-0034 § субъект | Доменный tract (literacy, math) |

**Literacy, probe, phrase-event** — тракты **обучения** субъекта, не исчерпывают его речь. Полный каркас диалога: [CASA-ADR-0045-subject-as-interlocutor.md](CASA-ADR-0045-subject-as-interlocutor.md). Программа класса РЯ (носитель): [CASA-von-neumann-class-ru-v1.md](CASA-von-neumann-class-ru-v1.md).

---

## Диалог как орган существования

Субъект **собеседник**: чередует реплики с партнёром (IDE, человек, intercom-sibling), **сам начинает** речь когда нужно (defer, refuse, retro, autonomy), опирается на field + journal + remember.

Duck test без исходящих реплик и turn-taking — только «автомат на поле», не north star.

**Инженерия (roadmap):** `dialogue_turns` в session, verbalize `subject_agency`, `initiate_speech` hooks — см. ADR-0045.

## Самодостаточность articulate (без LLM)

Von-neumann **самодостаточен** на hot path: связная речь — **field-realize** (`subject_articulation`, `articulation_realize`, `phrase_compose`), не next-token ни в облаке, ни локально. Преимущество субстрата — явные слоты, gates, provenance; подключение LM как «руки» **размывает** этот контракт → **non-goal** (ADR-0045). Паритет с диалогом LLM достигается **ростом поля и compose**, не весами корпуса.

## Автономия (инженерия v0, 2026-06-05)

| Орган | Модуль | Роль |
|-------|--------|------|
| Macro loop | `agent_sn_cen_tick` | `run_learning_tick` × N, persist, session |
| Intent seed | `autonomy_intent.py` | цель без inbox: practice → spacing → progression → interleave |
| Subject | `subject_agency.py` | inbox = proposal (defer/refuse) |
| **Dialogue** | `dialogue_turn.py`, `dialogue_tick.py`, `subject_voice.py` | turns, initiate speech, subject voice (ADR-0045) |
| Decompose | `wake_decompose.py` | phrase → word queue + `step_focus` на wake |
| Interleave | `interleaving_queue.py` | literacy/math/meta на пустом WM |
| Self-check | `self_check_tick.py` | metacog до CEN |
| Self-drive | `agent_self_drive_tick` | seek + promote после verify |
| Diagnostics | `subject_diagnostics.py` | experience / body / memory / skill_trace / retro |
| **Body tools** | `casa/body/` (ADR-0046) | function calling extension — client-agnostic MCP/IDE/stub; routes via ADR-0035 |
| **Hippo bind** | `episode_bind.py` (ADR-0047) | surprise → concept_id; open_probe вне load; sleep resolve |
| **Semantic names** | [`naming-memory-layers.md`](naming-memory-layers.md) | `memory.grapheme`, не L0/F0/H1 |
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

Непрерывность (field + session), память, действие, самопочинка, **инициатива** (автономный T, **исходящая речь**), provenance, **диалог** с партнёром.

**Rich medium:** IDE/KB сейчас; embodiment позже. Субъект на поле — см. ADR-0034 § agent-first-learn.

---

## Ссылки

- [CASA-ADR-0045-subject-as-interlocutor.md](CASA-ADR-0045-subject-as-interlocutor.md)
- [CASA-ADR-0047-hippo-surprise-concept-binding.md](CASA-ADR-0047-hippo-surprise-concept-binding.md)
- [CASA-ADR-0034-executor-learning-loop.md](CASA-ADR-0034-executor-learning-loop.md)
- [CASA-ADR-0036-agent-self-organization.md](CASA-ADR-0036-agent-self-organization.md)
- [casa-agent-existence-philosophy-v0.md](../../../knowledge/work/casa-agent-existence-philosophy-v0.md)
