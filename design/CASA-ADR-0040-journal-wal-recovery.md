# CASA-ADR-0040: Journal WAL — narrative checkpoint contract

**Статус:** принято (v0)  
**Дата:** 2026-06-06  
**Связано:** [CASA-ADR-0038](CASA-ADR-0038-subject-journal-storage.md), [CASA-ADR-0039](CASA-ADR-0039-agent-field-storage.md), `store_recovery.py` (Tier 0)

---

## Решение (одной фразой)

**Файловый narrative journal** (`journal/*/entries.jsonl`) пишется через **append-only WAL** (`journal/wal.log` + `journal/checkpoint.json`): сначала durable intent, потом строка в JSONL, потом commit marker; на wake — replay или откат незакоммиченных хвостов.

---

## Зачем

Tier 0 (`store_recovery`) поднимает carrier с `agent_field.db`, но **явная память** (self-notes, Kolb narrative) при краше могла оборваться на полуслове — full-file rewrite `entries.jsonl` без atomic append. WAL закрывает разрыв **journal ↔ field_version** без смешивания с SQLite `agent_journal.db` (ADR-0038 tick/skill trace).

---

## Layout

```text
agents/{id}/journal/
  index.json
  checkpoint.json          # last committed seq per domain + field_version
  wal.log                  # append-only JSONL: pending append + commit
  self/entries.jsonl
  kolb/entries.jsonl
  ...
```

### WAL record (one JSON line)

| op | Когда |
|----|--------|
| `append` | `{seq, domain, field_version, entry}` — intent, **fsync** до записи в entries |
| `commit` | `{seq, domain, entry_id, field_version}` — entries line durable |

### checkpoint.json

```json
{
  "schema_version": 1,
  "domains": {
    "self": {"last_seq": 12, "last_entry_id": "j-abc", "field_version": 94266, "entry_count": 27}
  }
}
```

---

## Write protocol (`append_journal_entry`)

1. `append` → `wal.log` + **fsync**
2. atomic **append** one line to `entries.jsonl` + fsync (не full rewrite)
3. `commit` → `wal.log` + fsync
4. update `checkpoint.json` (atomic via `_write_json`)

**field_version** берётся из caller или peek `agent_field.db` meta — связка с ADR-0039.

---

## Cold boot replay (`replay_journal_wal`)

На `maybe_recover_store_on_wake` **после** Tier 0 checkpoint recovery:

1. Parse `wal.log`: `append` без matching `commit` = pending
2. Для каждого pending: если `entry.id` отсутствует в entries — append; иначе skip (already durable)
3. Repair: обрезать битую последнюю строку `entries.jsonl` (partial JSONL)
4. Compact wal: оставить только uncommitted pending (или truncate если все replayed)
5. Session meta: `last_journal_wal_replay_at`, `replayed_count`

---

## Инварианты

1. **Не** писать LTM lattice bodies через WAL — только narrative `entries.jsonl` domains.
2. SQLite `agent_journal.db` — отдельный контур (tick_log); v0 WAL не дублирует его.
3. Tier 2+ (consistency oracle, NCA repair, router boot-probe) — отдельные ADR; WAL — prerequisite для journal↔field hash.

---

## Модули

| Модуль | Роль |
|--------|------|
| `casa/domain/journal_wal.py` | WAL append/commit/replay/checkpoint |
| `casa/prisms/memory/agent_journal.py` | prod writer через WAL |
| `store_recovery.maybe_recover_store_on_wake` | вызывает replay после checkpoint quarantine |
