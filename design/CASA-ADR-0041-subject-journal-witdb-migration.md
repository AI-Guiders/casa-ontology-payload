# CASA-ADR-0041: Subject journal — sqlite → WitDB (.witdb)

**Статус:** accepted (2026-06-06)  
**Репозиторий:** [casa-ontology-payload](https://github.com/AI-Guiders/casa-ontology-payload)  
**Связано:** ADR-0038 (`agent_journal.py`), ADR-0039 (`agent_field.py`), ADR-0040 (narrative journal WAL)  
**Движок:** [pywitdb ADR-0004](https://github.com/AI-Guiders/pywitdb/blob/main/docs/adr/0004-sql-layer-and-casa-journal.md) — `WitSqlEngine` + native C ABI

---

## Решение (одной фразой)

**Native SQL и C ABI — в pywitdb/WitDatabase; миграция CASA subject journal (`agent_journal.db` → `agent_journal.witdb`) — здесь**, через тонкий backend-флаг и `pywitdb.sql` без дублирования транзакций в Python.

---

## Разделение ответственности

| Слой | Репо | Что делаем |
|------|------|------------|
| `witdb_sql_exec` / `witdb_sql_query`, trim roots, wheels | **pywitdb** + **WitDatabase** | Native SQL path; `backend="auto"` → native, fallback bridge |
| Contract gate (schema, prune, GROUP BY) | **pywitdb** `tests/contract/test_casa_journal_sql.py` | ✅ green на bridge |
| Backend flag, path, one-shot migrate, session meta | **casa-ontology-payload** | `CASA_JOURNAL_BACKEND`, `journal_store.py` |
| Field (`agent_field.db`) | **casa** фаза 2 | после journal prod на witdb |

---

## Почему не свой «купол» в Python

WitDB из коробки:

- **MVCC** (`MvccTransactionalStore`) — snapshot isolation, read не блокирует write.
- **WitSqlEngine** — `Commit()` / `Rollback()` на том же store (bridge: `sql_commit` / `sql_rollback`).
- **Шифрование / reopen** — Tier-1 btree + AES-GCM (ADR-0002 pywitdb).

CASA **не** реализует второй WAL/txn-слой поверх journal SQL: `open_journal` → insert/prune → `commit()` один раз на границе операции. Narrative journal (`journal/`, ADR-0040) остаётся отдельным FS-WAL — это другой домен (agent-owned notes), не subject trace.

---

## Backend и пути

| `CASA_JOURNAL_BACKEND` | Файл | Python |
|------------------------|------|--------|
| `sqlite` (default) | `agent_journal.db` | `sqlite3` |
| `witdb` | `agent_journal.witdb` | `pywitdb.sql.connect(..., backend="auto")` |

`backend="auto"` в pywitdb: когда native SQL готов — без смены CASA-кода; до того — bridge (dev/CI с собранным `WitDbBridge`).

**Session meta:** `"journal": "agent_journal.witdb"` при witdb-backend (как сегодня `"agent_journal.db"`).

---

## One-shot migrate

При первом `open_journal` в режиме `witdb`, если есть только `agent_journal.db`:

1. Открыть sqlite read-only, вычитать таблицы.
2. Записать в `.witdb` через тот же `_CREATE_SQL` + INSERT batch.
3. Переименовать `.db` → `agent_journal.db.bak` (не удалять автоматически).

CLI (optional): `python -m casa.domain.journal_store migrate --store-dir …`

---

## Acceptance (journal на witdb)

Повторить существующие `tests/test_agent_journal.py` + `tests/test_skill_trace.py` под `CASA_JOURNAL_BACKEND=witdb` (skip если bridge/native недоступен).

Матрица SQL — та же, что ADR-0004 § «CASA journal compatibility» (prune subquery — критичный gate).

---

## Field (фаза 2, не в этом ADR)

`agent_field.db` — routes + gzip chunk; `ON CONFLICT DO UPDATE`, BLOB. Варианты:

- **A)** KV pywitdb (близко к семантике keys), или  
- **B)** SQL tables в том же `.witdb` что journal (единый store file per agent).

Решение — отдельный ADR после journal prod на von-neumann.

---

## Browser horizon

Horizon memo (Wasm): OPFS `.witdb` вместо sqlite в браузере — **после** native SQL в Wasm/AOT matrix; Python lab остаётся на sqlite или witdb+bridge локально.

---

## Порядок

1. ✅ pywitdb bridge SQL + contract tests  
2. 🔄 pywitdb native `witdb_sql_*` (соседний трек)  
3. ✅ casa `journal_store` + env flag (этот ADR)  
4. von-neumann opt-in: `CASA_JOURNAL_BACKEND=witdb` + migrate  
5. field phase 2 ADR
