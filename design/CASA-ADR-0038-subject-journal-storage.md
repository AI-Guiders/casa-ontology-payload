# CASA-ADR-0038: Журнал субъекта — SQLite + slim session

**Статус:** принято (v0)  
**Дата:** 2026-06-05  
**Связано:** [CASA-ADR-0037-subject-diagnostics.md](CASA-ADR-0037-subject-diagnostics.md), [CASA-ADR-0017](CASA-ADR-0017) compact persist (field/LTM)

---

## Решение (одной фразой)

**Поставка субстрата остаётся маленькой:** поле/LTM — compact binary (ADR-0017); **опыт субъекта** — `agent_journal.db` (SQLite, stdlib); **agent_session.json** — только WM + указатели; lab-архив — JSONL.gz (Python) / zstd ( .NET bundle).

---

## Зачем

JSON-массивы в `agent_session.json` (`skill_trace`, `tick_log`, retro) раздувают bundle и плохо query. Retro и skill_trace требуют фильтрации по goal/skill/outcome — SQLite подходит; **6k routes** в SQLite класть **не** надо (остаётся field compact).

---

## Layout store

```text
agents/{agent_id}/
  field_state.json | field.compact.*   # поле (ADR-0017 — целевой compact)
  agent_session.json                   # schema v2: wm, journal, macro_ticks
  agent_journal.db                     # subject journal
  lab/journal-export/*.jsonl.gz        # опционально, не в hot bundle
```

### agent_session.json (slim)

```json
{"schema_version":2,"journal":"agent_journal.db","wm":{...},"macro_ticks":42,"updated_at":"..."}
```

Compact JSON (`separators=(",", ":")`), без indent.

### agent_journal.db

| Таблица | Содержание |
|---------|------------|
| `skill_trace` | situation → skill → outcome |
| `tick_log` | slim tick summary (без full self_organization) |
| `experience` | narrative episodes |
| `retrospective` | Scrum 3Q runs |

Индексы: `goal_id`, `skill`, `outcome`, `tick`. Payload — compact JSON в TEXT колонке.

---

## Модули

| Модуль | Роль |
|--------|------|
| `casa/domain/agent_journal.py` | CRUD, migrate legacy, prune |
| `casa/prisms/tick/journal_export.py` | JSONL.gz для lab |
| Writers | `skill_trace`, `session_log`, `experience_ledger`, `subject_retrospective` → journal |

**Миграция:** первое обращение к journal импортирует legacy-массивы из session, ставит `journal_migrated: true`.

---

## Архив и .NET

| Контур | Формат |
|--------|--------|
| Python lab export | `journal_export` → `.jsonl.gz` (stdlib gzip) |
| Bundle delivery | `.jsonl.zst` — **System.IO.Compression.Zstandard.Backporting** на .NET 10 |
| Runtime wake | распаковка zst → import или attach SQLite as-is |

SQLite файл **не сжимается** в hot path (WAL, append); zstd — для **пересылки** архива/lab.

---

## Инварианты

1. Journal — append-mostly; prune по cap (96/64/48/24).
2. Session JSON не дублирует journal arrays.
3. `tick_log` не хранит полный orchestrator report — только summary + arbiter winner.
4. Field/router — **не** в journal (ADR-0017 / **ADR-0039** `agent_field.db`).

---

## Inspect (канон)

**Не редактировать `.db` вручную** — только CLI export/query. Агент и человек работают с **текстовыми срезами** (JSON/JSONL stdout или `lab/` export).

| DB | CLI |
|----|-----|
| `agent_journal.db` | `journal_export`, `skill_trace_query`, `agent_retrospective` |
| `agent_field.db` | `field_export --stats`, `--export-routes`, `--export-body` |

---

## CLI

```bash
python -m casa.prisms.tick.journal_export --store-dir agents/von-neumann
python -m casa.prisms.tick.skill_trace_query --summary
python -m casa.prisms.tick.agent_retrospective
```

---

## Backlog

| # | Item |
|---|------|
| J1 | field.compact columnar routes (ADR-0017 integration) |
| J2 | zstd export/import wrapper (Python `zstandard` optional) |
| J3 | .NET journal reader + zstd bundle unpack |
| J4 | cold archive rotate → single `.journal.archive.zst` |
