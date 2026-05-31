# CASA-ADR-0013: журнал агента — prose-память вне картриджа ltm/

**Статус:** принято (lab v0, 2026-05-31)  
**Область:** agent store / math / рабочие заметки агента  
**Связано:** [`CASA-ADR-0014-agent-prism.md`](CASA-ADR-0014-agent-prism.md), [`CASA-ADR-0002-agent-memory-ltm-nca.md`](CASA-ADR-0002-agent-memory-ltm-nca.md), [`f0-math-logical-layer.md`](f0-math-logical-layer.md), [`memory-hierarchy.md`](memory-hierarchy.md), agent-notes (MCP)

---

## Контекст

**Картридж `ltm/`** — curated memory pack: vocab + placements, поставка профиля, export/import. Агент **не владеет** этим слоем как блокнотом; изменения идут через ingest, sleep → consolidate, rebuild pack.

**`prism_agent`** (ADR-0014) — **spatial** личная призма: решётки + NCA в `{store}/agent/`.

**agent-notes** (KB) — отдельный канон знаний с read/write MCP.

**`journal/`** — **prose-слой** рядом с agent prism: текст, concepts, tokens списком — как agent-notes на диске store, **без решётки**. Для «вывел закономерность словами»; для «разложил на поле» — `prism_agent`.

---

## Решение

### 1. Отдельный tier на диске: `{store}/journal/`

```text
agent-store/{id}/
├── ltm/                 ← картридж (export tier A)
├── nca/
├── field_state.json
└── journal/             ← агент владеет (tier D)
    ├── index.json
    └── math/
        └── entries.jsonl
```

| Свойство | journal/ | ltm/ |
|----------|----------|------|
| Кто пишет | агент (CLI/MCP) | ingest / sleep / export |
| В pack export | **нет** | **да** |
| Переживает reboot | **да** | **да** |
| Формат | JSONL + index | `.ltm` + manifest |

### 2. Запись entry

Одна строка JSONL:

```json
{
  "id": "j-a1b2c3d4e5f6",
  "ts": "2026-05-31T12:00:00Z",
  "kind": "law|episode|note|hypothesis|observation",
  "text": "…",
  "concepts": ["math.op.add"],
  "tokens": ["M:qty:2×entity:stick"],
  "tags": []
}
```

Агент **волен**: append, read, patch, delete — без gate от Critic/sleep.

### 3. Связь с F0 / sleep (не автоматическая)

| Действие | Куда |
|----------|------|
| «Записал в журнал» | `journal/` — сразу persistent |
| «Закрепил на поле» | явный promote: ingest claim / sleep consolidate → F0 hub |
| «В картридж» | `export_ltm_pack` после consolidate |

Журнал **не подменяет** F0_schema и **не попадает** в ltm/ молча.

### 4. Инструменты v0

```bash
python -m casa.cli agent_journal append --store-dir lab/agent-stores/language-agent-lab \
  --domain math --kind law --text "…" --concepts math.op.add

python -m casa.cli agent_journal read --store-dir lab/agent-stores/language-agent-lab --domain math
python -m casa.cli agent_journal stats --store-dir lab/agent-stores/language-agent-lab
```

Код: `casa/prisms/memory/agent_journal.py`.

---

## Последствия

- Boot из `ltm/` **не трогает** journal/.
- Backup профиля: копировать `journal/` отдельно или вместе со store; не ждать его в `.ltm`.
- MCP-обёртка (как agent-notes) — roadmap; CLI достаточен для lab.

## Non-goals v0

- Full-text search index, revision history, merge conflict resolution.
- Авто-promote journal → F0 на каждый append.
