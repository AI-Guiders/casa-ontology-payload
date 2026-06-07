# Запустить von-neumann у себя (play locally)

**Для кого:** хочешь поиграть с **Нейманном** — живым агентом на поле CASA, не с ChatGPT.  
**Статус:** v1.1 (2026-06-07).  
**Связано:** [agents/README.md](../agents/README.md), [ADR-0045](../design/CASA-ADR-0045-subject-as-interlocutor.md), [ADR-0050](../design/CASA-ADR-0050-agent-life-archive-visibility-v1.md).

---

## Три команды — не путать

| Команда | Когда | Что получишь |
|---------|-------|--------------|
| **`restore_agent_life`** | гость / новая машина | **обученный** Нейманн из snapshot (~0.5–0.7 GiB) |
| **`bootstrap_agent_cold_store`** | lab, новый субъект с нуля | пустая оболочка + journal, **без** ltm/поля |
| **`bootstrap_agent_self_tier`** | дозаполнить Self на существующем store | только `journal/` + `agent/` |

`init_agent_self` — **deprecated** (шим на `bootstrap_agent_self_tier`).

---

## Что получишь

| Ожидание | Реальность |
|----------|------------|
| «Умный чат как GPT» | **Нет** — речь из **поля + journal** (field-realize), без LLM на hot path |
| «Тот же непрерывный Нейманн у создателя» | **Нет** — у тебя **реплика** store на дату snapshot; дальше жизни расходятся |
| «Поговорить, посмотреть defer/ответ, curiosity» | **Да** — macro tick + диалог |
| «С нуля без памяти» | `bootstrap_agent_cold_store` + lessons — **не** тот Нейманн с русским |

Два репозитория:

| Репо | Что даёт |
|------|----------|
| [casa-ontology-payload](https://github.com/AI-Guiders/casa-ontology-payload) | движок (Python), public |
| [von-neumann-life-archive](https://github.com/AI-Guiders/von-neumann-life-archive) | память Неймана (`store/`), **сейчас private** |

**Доступ к life-archive:** попроси maintainers org `AI-Guiders` (collaborator на private repo). Без доступа — только smoke / cold bootstrap, не полный агент.

---

## Требования

| | Минимум |
|---|---------|
| **OS** | Windows 10+, macOS, Linux |
| **Python** | **3.12+** (`pyproject.toml`) |
| **Git** | clone + **Git LFS** (`winget install GitHub.GitLFS` → `git lfs install`) |
| **Диск** | **~0.5–0.7 GiB** под `agents/von-neumann/` сейчас (растёт с жизнью; +запас под git LFS) |
| **GPU** | не обязательна; NCA train — `cpu` по умолчанию |
| **.NET** | не нужен для von-neumann (только для T9 demo в корневом README) |

Snapshot = **сам агент на диске** (`ltm/`, `nca/`, поле, journal), не код CASA.

---

## 1. Движок (code repo)

```powershell
git clone https://github.com/AI-Guiders/casa-ontology-payload.git
cd casa-ontology-payload

python -m venv .venv
.\.venv\Scripts\Activate.ps1   # macOS/Linux: source .venv/bin/activate

pip install -r tools/requirements.txt
```

Опционально (corpora для lab/T9, **не** для restore Неймана):

```powershell
python scripts/download_corpora.py
```

Проверка импорта:

```powershell
python -c "import casa; import torch; print('ok', torch.__version__)"
```

---

## 2. Память — restore (рекомендуется)

```powershell
git clone https://github.com/AI-Guiders/von-neumann-life-archive.git
cd von-neumann-life-archive
git lfs install
git lfs pull
cd ..\casa-ontology-payload

python tools/restore_agent_life.py `
  --from-life-archive ..\von-neumann-life-archive `
  --store-dir agents/von-neumann `
  --force
```

Или через `python -m casa.cli restore_agent_life` с теми же флагами.

Прямой путь к `store/`:

```powershell
python tools/restore_agent_life.py --from-store D:\path\to\store --store-dir agents/von-neumann --force
```

JSON в stdout содержит `next` — команда для первого диалога. При `lfs_pointer_warning` — снова `git lfs pull` в archive.

Пин версии: в life-archive `git log -1` / tag; см. `sync_meta.json`.

---

## 3. Первая реплика (диалог)

```powershell
python -m casa.prisms.control.agent_sn_cen_tick `
  --store-dir agents/von-neumann `
  --query "Привет"
```

В **stderr** — `dialogue_outbound`. История: `agents/von-neumann/agent_session.json` → `dialogue_turns`.

**Важно:** не гоняй два процесса на один store (`run_agent` + tick).

---

## 4. Фоновая жизнь

```powershell
python tools/run_agent.py --store-dir agents/von-neumann
```

Остановка: **Ctrl+C**.

---

## 5. Карта store

| Путь | Смысл |
|------|--------|
| `ltm/` | опыт после sleep |
| `nca/` | веса repair по решёткам |
| `journal/` | тетрадь (self) |
| `agent_session.json` | dialogue, WM |
| `agent_field.db` / `field_state.json` | checkpoint поля |

---

## 6. Без snapshot

**Smoke (окружение):**

```powershell
python -m casa.domain.dialogue_smoke
```

**Необученная оболочка (curriculum с lessons/):**

```powershell
python tools/bootstrap_agent_cold_store.py --store-dir agents/von-neumann-new --force
```

---

## 7. Типичные проблемы

| Симптом | Что сделать |
|---------|-------------|
| `lfs_pointer_warning` в restore | `git lfs pull` в life-archive |
| `store_dir is not empty` | `--force` на restore |
| `ModuleNotFoundError: casa` | venv + корень репо |
| Ответ defer | нормально; другой cue или `--ticks 2` |
| Нет доступа к archive | invite; иначе только cold/smoke |

---

## 8. Чего пока нет

- REPL-чат в терминале.
- Public life-archive (ADR-0050 Phase B).
- Browser wasm.

---

## Ссылки

- [agents/README.md](../agents/README.md)
- [ADR-0050](../design/CASA-ADR-0050-agent-life-archive-visibility-v1.md)
- Backup (maintainers): `python tools/sync_life_archive.py snapshot -m "…"`
