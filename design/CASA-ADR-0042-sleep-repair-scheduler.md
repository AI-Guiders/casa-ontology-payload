# CASA-ADR-0042: Sleep repair scheduler (Tier 3)

**Статус:** принято (v0)  
**Дата:** 2026-06-06  
**Связано:** [CASA-ADR-0041](CASA-ADR-0041-consistency-oracle-boot-probe.md), `nca_repair.py`, `run_sleep`

---

## Решение (одной фразой)

Когда `consolidation.repair_pending` (из oracle на boot), **следующий sleep** с `store_dir` выполняет **sync routes из agent_field.db** + **NCA regrow** stale/L2 shards; затем re-check oracle; `surprise` снижается — carrier продолжает жить.

---

## Триггер

```text
boot_store → assess_field_consistency → mismatch
  → apply_repair_homeostasis (surprise=100, repair_pending=true)
  → … ingest / life ticks …
  → run_sleep(..., store_dir=…) → run_consistency_repair_on_sleep
```

---

## Шаги repair (один sleep)

| Шаг | Условие | Действие |
|-----|---------|----------|
| 1 | `field_db` / `routes_db` в repair_reason | `Router.set_routes` из `load_field_from_db`, dual-write |
| 2 | always (cap 8 shards) | `find_stale_shards` или sweep L2 с model.pt → `nca_regrow_lattice` |
| 3 | finish | `assess_field_consistency`; clear `repair_pending` если нет critical mismatch |
| 4 | homeostasis | `surprise` 100 → 24; session meta `last_consistency_repair_*` |

Critical mismatch (оставляет pending): `field_db`, `routes_db`, `ltm_zeroed`.

---

## Prod wiring

| Call site | `store_dir` |
|-----------|-------------|
| `run_sleep` | hook после kernel maintain |
| `agent_self_tick` | `store_dir` passed |
| `ingest_lesson_moment` | `store_dir` passed |

---

## Модуль

`casa/domain/boot_repair_scheduler.py` — `repair_pending()`, `run_consistency_repair_on_sleep()`.
