# CASA-ADR-0039: Field store — agent_field.db

**Статус:** принято (v0)  
**Дата:** 2026-06-05  
**Связано:** [CASA-ADR-0038-subject-journal-storage.md](CASA-ADR-0038-subject-journal-storage.md), ADR-0017 compact persist

---

## Решение (одной фразой)

**Второй SQLite — `agent_field.db`**: routes таблично, остальное поля — один gzip+JSON chunk; **dual-write** с `field_state.json` на переходе; load **prefer db** если файл есть.

---

## Layout

```text
agents/{id}/
  agent_session.json    # wm, journal, field_db pointers
  agent_journal.db      # опыт субъекта (ADR-0038)
  agent_field.db        # носитель: routes + field_body chunk
  field_state.json      # legacy mirror (compact JSON), постепенно optional
```

### agent_field.db

| Таблица | Содержание |
|---------|------------|
| `routes` | ADR-0035 match + targets (нормализовано) |
| `chunks.field_body` | gzip(JSON state без routes) |
| `meta` | field_version, schema_version, updated_at |

---

## Dual-write / load

- **save** (`save_field_state`): JSON + `save_field_to_db`; при thin checkpoint в JSON — **полное** in-memory state в db (`field_db_state`)
- **load** (`load_field_state`): thin JSON + ltm **раньше** db; иначе db; иначе JSON
- Session: `field_db`, `field_db_at`

---

## Inspect (канон, shared с 0038)

**Не редактировать `.db` вручную.** Только CLI:

```bash
python -m casa.prisms.tick.field_export --store-dir agents/von-neumann --stats
python -m casa.prisms.tick.field_export --export-routes lab/out/routes.json
python -m casa.prisms.tick.field_export --export-body lab/out/field_body.json
python -m casa.prisms.tick.field_export --import-json agents/von-neumann/field_state.json
```

---

## Backlog

| # | Item |
|---|------|
| F1 | Split field_body into grid / prisms / cognitive chunks |
| F2 | Drop JSON mirror when .NET reads db only |
| F3 | zstd chunk codec + .NET parity |
| F4 | Incremental route upsert (emergent promote) |

---

## Модули

| Модуль | Роль |
|--------|------|
| `casa/domain/agent_field.py` | save/load, stats, import from JSON |
| `casa/prisms/shared/field_write.py` | hooks load/save |
| `casa/prisms/tick/field_export.py` | inspect CLI |
