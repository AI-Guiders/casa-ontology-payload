# Tech-debt index (living)

**Статус:** журнал; не ADR  
**Дата:** 2026-06-01  
**Связано:** [`open-source-readiness-and-tech-debt.md`](open-source-readiness-and-tech-debt.md), [`CASA-PROJECT-CONSTITUTION.md`](CASA-PROJECT-CONSTITUTION.md)

Индекс **id → ADR → статус**, чтобы не путать разные шкалы **M*** / **E*** / **R***.

---

## Шкалы id (не смешивать)

| Префикс | Где | Смысл |
|---------|-----|--------|
| **M0–M4** | [ADR-0012](CASA-ADR-0012-cide-parity-fieldbus-and-migration.md) | пакет `casa/`, paths, shims |
| **M0–M4** | [ADR-0020](CASA-ADR-0020-ooad-domain-model.md) | strangler → `casa.domain` |
| **M0–M3** | [ADR-0019](CASA-ADR-0019-control-multi-prism.md) | split control prisms |
| **R1–R6** | [ADR-0023](CASA-ADR-0023-sleep-scale-thin-first.md) | sleep scale (**R1–R2 done**) |
| **R1–R4** | [ADR-0021](CASA-ADR-0021-experience-agent-transfer.md) | transfer / experience |
| **R1–R4** | [ADR-0022](CASA-ADR-0022-agent-v1-existence-bar.md) | bar check automation |
| **E0–E8** | [ADR-0025](CASA-ADR-0025-autonomous-execution-tier.md) | CASA Engine tiers |

---

## ADR-0012 migration (package / paths)

| Id | Задача | Статус |
|----|--------|--------|
| M0–M3 | design, aliases, `casa/`, canonical ltm | **done** |
| M4 | shims removed, `python -m casa.cli` | **done** |
| T12-1 | `.gitignore` / CI canonical paths only | open |
| T12-2 | `design/prisms/*` from store manifest | partial (`tools/sync_design_prisms_from_manifest.py`) |
| T12-3 | prose: no «sss» subsystem name in new docs | open |
| T12-4 | `migrate_lattice_ids_v1.py` (kebab ids) | open |

---

## ADR-0020 domain strangler

| Id | Задача | Статус |
|----|--------|--------|
| M0 | `casa/domain/*`, tests | **done** |
| M1 | `prism_router` → `domain.routing` | **done** |
| M2 | `prism_spawn`, `export_ltm_pack` → domain | **done** |
| M3 | `compact_persist`, tick orchestrator | partial (`compact_persist` → domain; tick uses `tick_prepare_memory`) |
| M4 | no raw `state["prisms"]` outside persistence | partial (`prism_wire` + facade; call sites still migrate) |

## ADR-0016 / 0021 multi-prism (runtime)

| Id | Задача | Статус |
|----|--------|--------|
| MP-1 | `multi_prism_v1` wire + hot/router/hippo/control | **done** |
| MP-2 | transfer matrix + `ensure_multi_prism_bootstrap` | **done** |
| MP-3 | route fallback when domain prism has no lattices | **done** |
| MP-4 | thin checkpoint: hippo cells + `last_sleep.items` trim | **done** (code) |
| MP-5 | shipped store split `prism_lang_ru` / `prism_math` on disk | open (monolith `prism_memory` ok) |

---

## Memory / ltm (ADR-0002, ADR-0017)

| Id | Задача | Статус |
|----|--------|--------|
| T02-1 | hot path boot from `ltm/` without fat cells | open |
| T02-2 | bundle → `ltm/` direct (no field monster) | open |
| T02-3 | NCA_rule v1 (rule patch regrow) | open |

---

## Sleep / autonomy

| Id | Задача | Статус |
|----|--------|--------|
| R1–R6 | batched sleep, ingest mode, SleepJob, parallel ltm | **done** |
| S-v2 | multiprocess sleep by L2 shard | open |
| E0–E8 | Engine T1 (`LatticeSlab`, `casa_engine tick`, …) | open |

---

## Control / thalamus

| Id | Задача | Статус |
|----|--------|--------|
| T24-0 | `thalamus.py` v0 | **done** |
| M2–M3 | ADR-0019 control split, vis tick | open |
| T24-1 | thalamus in autonomous tick / Engine | partial (`tick_prepare_memory`) |

---

## Experience / bar

| Id | Задача | Статус |
|----|--------|--------|
| T21-1 | transfer matrix doc | **done** |
| T21-2 | bootstrap routes from matrix | **done** |
| T22-1 | `agent_v1_bar_check.py` | **done** |

---

## Wake / listen

| Id | Задача | Статус |
|----|--------|--------|
| TWS-1 | `record_listen_surface` + `ingest_episodic_mode` | **done** |
| TWS-2 | mass listen CLI → policy hook | open |
| TWS-3 | `understand_extract()` | open |

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-01 | Первый индекс после flush WIP + sleep R1–R6 |
| 2026-06-01 | M2 domain bind; T22-1 bar check; T24-1 partial |
| 2026-06-01 | T21-2 transfer matrix bootstrap; MP-2–4 multi-prism; thin checkpoint trim |
| 2026-06-01 | M4 partial: `prism_ids`, `prism_wire`, `prism_state` facade |
