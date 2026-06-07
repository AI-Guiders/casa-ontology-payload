# Living agents (canonical experience)

**Not lab.** One directory per agent instance — **вся жизнь** в `agents/{id}/`.

| `store_id` | Path | Status |
|------------|------|--------|
| `von-neumann` | `agents/von-neumann/` | first agent (bootstrap display «Нейманн») |
| `lovelace` | (reserved) | — |
| `hamilton` | (reserved) | — |

Code: `STORE_AGENT_DEFAULT`, `default_agent_store()` in `casa/prisms/shared/store_layout.py`.

## Четыре зоны — не смешивать

| Зона | Где | Кто решает смысл | Примеры |
|------|-----|------------------|---------|
| **Жизнь агента** | `agents/{id}/` | **агент** | tick, predict, hippo, sleep, journal, тетради, Kolb, curiosity, `ltm/` после consolidate |
| **Host (OS)** | процесс | **только старт/стоп** | `run_agent.py` — поднять процесс, Ctrl+C — остановить. Без cue, notebook, «сделай X» |
| **Учитель** | `lessons/` | human / curriculum | bundle, ingest-событие → episodic input в агента, не «память урока» |
| **Lab** | `lab/`, `tools/agent_autonomous.py` | разработчик | replay, probe, CI — **не** prod life и **не** «от имени агента» |

**Канон (ADR-0021):** после ingest занятия факты становятся **собственным опытом** того же агента в его store. Учебник в predict не читается.

```text
  Учитель (lessons/)          Host (run_agent)
         │                           │
         │ ingest event              │ wake / stop only
         ▼                           ▼
  ┌──────────────────────────────────────────────┐
  │  ЗОНА АГЕНТА — agents/von-neumann/           │
  │  field_state · hippo · journal · agent/ · ltm │
  │  agent_life · curiosity · sleep · retain      │
  └──────────────────────────────────────────────┘
```

## Что входит в жизнь агента

| Артефакт | Путь | Смысл |
|----------|------|--------|
| Runtime | `field_state.json`, `agent_session.json` | очередь, SN, self_drive |
| Self | `journal/`, `agent/` | тетради, гипотезы, spatial self |
| Память | `ltm/`, `nca/` | consolidated опыт после sleep |
| Код жизни | `casa/prisms/memory/agent_life.py` | live loop, life tick |
| Idle drive | `agent_curiosity.py` | «а что будет, если?» когда нет внешнего cue |

**Не жизнь агента:** `MEMORY.md` (карта для человека), `lessons/` (учебник), lab CLI.

## Tree (von-neumann)

```text
agents/von-neumann/
├── ltm/                  ← опыт после sleep
├── field_state.json      ← wake: hippo, prisms, SN
├── agent_session.json    ← self_drive, macro_ticks
├── journal/              ← агент пишет сам
├── agent/                ← agent prism
├── bundles/              ← audit snapshot после ingest
└── memory_manifest.json
```

## Play locally (onboarding)

Полный гайд для гостей (clone, LFS, диалог, troubleshooting): [docs/CASA-von-neumann-local-play-v1.md](../docs/CASA-von-neumann-local-play-v1.md).

## Prod — только поднять жизнь

```powershell
python tools/run_agent.py --store-dir agents/von-neumann
```

Host не участвует в tick'ах. Агент сам: predict, sleep, Kolb, journal. Остановка — Ctrl+C.

Lab/CI: `--once` (один quantum, без смысловых флагов).

## Lab — инструментарий (не жизнь)

```powershell
python tools/agent_autonomous.py rehearse ...   # телеметрия predict/retain
python tools/ingest_lesson_class.py ...         # событие учителя
python tools/init_agent_self.py ...             # cold bootstrap (один раз)
```

Модули: `agent_life.py` (prod), `agent_autonomous_engine.py` (lab).

Design: ADR-0021 (experience), ADR-0025 (autonomous tier), ADR-0013–0015 (journal/self).
