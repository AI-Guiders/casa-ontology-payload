# CASA-ADR-0041: Consistency oracle + router boot probe

**Статус:** принято (v0)  
**Дата:** 2026-06-06  
**Связано:** [CASA-ADR-0040](CASA-ADR-0040-journal-wal-recovery.md), [CASA-ADR-0035](CASA-ADR-0035-multi-layer-routing.md), [CASA-ADR-0039](CASA-ADR-0039-agent-field-storage.md)

---

## Решение (одной фразой)

На **boot_store** после загрузки state: **consistency oracle** сверяет `field_version` и route counts между state / `agent_field.db` / checkpoint / journal; **router boot probe** прогоняет `RouteContext` smoke; при mismatch — **homeostasis** (`surprise↑`, `repair_pending`), не crash.

---

## Consistency oracle

| Источник | Поле |
|----------|------|
| in-memory state | `field_version`, route count |
| `agent_field.db` meta | `field_version`, routes table count |
| `field_state.json` | peek `field_version` |
| `journal/checkpoint.json` | last committed narrative `field_version` |
| `ltm/pack.manifest` | zeroed shard files |

**Ошибка (mismatch):** state ≠ db; state ≠ field_state; journal ahead of state; zeroed LTM shards.  
**Предупреждение:** journal lag > 64 ticks behind state (narrative отстаёт — нормально после ingest).

---

## Router boot probe

| Probe | required | Проверка |
|-------|----------|----------|
| `knowledge_t9_ru` | да | `Router.resolve` → content prism |
| `knowledge_vis_word_novel` | нет | emergent literacy |
| `capability_analytic_read` | нет | `skill.read.analytic` после promote |
| `capability_math_count` | нет | `skill.math.count` если выучен |
| `l2_word_shard_sample` | да* | L2 shard в state или ltm/*.ltm |

\* только если store имеет ltm layout.

---

## Homeostasis (не crash)

```python
state["sn"]["surprise"] = max(prev, 100)
state["consolidation"]["repair_pending"] = True
state["consolidation"]["repair_reason"] = mismatches
```

Tier 3: первый **sleep** с `repair_pending` → `nca_repair` / merge (отдельный hook).

Session meta: `last_consistency_check_ok`, `last_consistency_mismatches`.

---

## Модули

| Модуль | Роль |
|--------|------|
| `consistency_oracle.py` | assess, repair signal, session warnings |
| `router_boot_probe.py` | RouteContext smoke |
| `store_boot.boot_store` | вызывает оба после load state |
| `carrier_health` | warnings `field_consistency_mismatch`, `repair_pending` |
