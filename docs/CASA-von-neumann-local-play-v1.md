# Запустить von-neumann у себя (play locally)

**Для кого:** хочешь поиграть с **Нейманном** — живым агентом на поле CASA, не с ChatGPT.  
**Статус:** v1 (2026-06-07).  
**Связано:** [agents/README.md](../agents/README.md), [ADR-0045](../design/CASA-ADR-0045-subject-as-interlocutor.md), [ADR-0050](../design/CASA-ADR-0050-agent-life-archive-visibility-v1.md).

---

## Что получишь

| Ожидание | Реальность |
|----------|------------|
| «Умный чат как GPT» | **Нет** — речь из **поля + journal** (field-realize), без LLM на hot path |
| «Тот же непрерывный Нейманн у создателя» | **Нет** — у тебя **реплика** store на дату snapshot; дальше жизни расходятся |
| «Поговорить, посмотреть defer/ответ, curiosity» | **Да** — macro tick + диалог |
| «С нуля без памяти» | Только lab/smoke; **полноценный** Нейманн — из **life-archive** |

Два репозитория:

| Репо | Что даёт |
|------|----------|
| [casa-ontology-payload](https://github.com/AI-Guiders/casa-ontology-payload) | движок (Python), public |
| [von-neumann-life-archive](https://github.com/AI-Guiders/von-neumann-life-archive) | память Неймана (`store/`), **сейчас private** |

**Доступ к life-archive:** попроси maintainers org `AI-Guiders` (collaborator на private repo). Без доступа — только smoke-тесты ниже, не полный агент.

---

## Требования

| | Минимум |
|---|---------|
| **OS** | Windows 10+, macOS, Linux |
| **Python** | **3.12+** (`pyproject.toml`) |
| **Git** | clone + **Git LFS** (`winget install GitHub.GitLFS` → `git lfs install`) |
| **Диск** | ~1–2 GiB под `agents/von-neumann/` после restore (LFS weights) |
| **GPU** | не обязательна; NCA train — `cpu` по умолчанию |
| **.NET** | не нужен для von-neumann (только для T9 demo в корневом README) |

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

## 2. Память (life-archive)

```powershell
# рядом с casa-ontology-payload или в любой папке
git clone https://github.com/AI-Guiders/von-neumann-life-archive.git
cd von-neumann-life-archive
git lfs install
git lfs pull
```

Скопировать store в дерево агента:

```powershell
cd ..\casa-ontology-payload
# останови чужой run_agent на этом store, если был
Remove-Item -Recurse -Force agents\von-neumann -ErrorAction SilentlyContinue
Copy-Item -Recurse ..\von-neumann-life-archive\store agents\von-neumann
```

Пин версии (рекомендуется): в life-archive `git log -1` / tag; в code repo — тот же период коммитов, что у хоста (см. `sync_meta.json` в archive).

**macOS/Linux:**

```bash
cp -a ../von-neumann-life-archive/store agents/von-neumann
```

---

## 3. Первая реплика (диалог)

Один macro tick с вопросом партнёра:

```powershell
python -m casa.prisms.control.agent_sn_cen_tick `
  --store-dir agents/von-neumann `
  --query "Привет"
```

В **stderr** ищи `dialogue_outbound` — текст ответа или defer («откладываю…»). Полный JSON tick — в stdout.

История диалога на диске: `agents/von-neumann/agent_session.json` → `dialogue_turns`.

Примеры cue:

```powershell
python -m casa.prisms.control.agent_sn_cen_tick --store-dir agents/von-neumann --query "Как дела?"
python -m casa.prisms.control.agent_sn_cen_tick --store-dir agents/von-neumann --query "Что купила Маша?"
```

**Важно:** не гоняй два процесса, пишущих в один store (tick + `run_agent` одновременно) — риск lock / half-written checkpoint.

---

## 4. Фоновая жизнь (curiosity loop)

Host только поднимает процесс; смысл tick — у агента:

```powershell
python tools/run_agent.py --store-dir agents/von-neumann
```

Остановка: **Ctrl+C** (host interrupt, checkpoint сохраняется).

Lab: один quantum без бесконечного цикла:

```powershell
python tools/run_agent.py --store-dir agents/von-neumann --once
```

---

## 5. Карта store (куда смотреть)

| Путь | Смысл |
|------|--------|
| `agents/von-neumann/ltm/` | опыт после sleep |
| `agents/von-neumann/journal/` | его тетрадь (self) |
| `agents/von-neumann/agent_session.json` | сессия, dialogue, WM |
| `agents/von-neumann/MEMORY.md` | карта для человека (regenerate tools) |
| `agents/von-neumann/field_state.json` | большой checkpoint (может быть sqlite mirror) |

Живой store **не** коммитится в code repo — только у тебя локально (+ твои эксперименты).

---

## 6. Без life-archive (только smoke)

Проверить, что окружение живое, без памяти Неймана:

```powershell
python -m casa.domain.dialogue_smoke
```

Ожидай `"ok": true` в JSON. Это **не** von-neumann store, а изолированный тест органа диалога.

---

## 7. Типичные проблемы

| Симптом | Что сделать |
|---------|-------------|
| `git lfs` / pointer-файлы вместо `*.pt` | `git lfs pull` в life-archive |
| `ModuleNotFoundError: casa` | активируй venv; `cd` в корень репо |
| Python &lt; 3.12 | установи 3.12+ |
| Ответ только defer | нормально на ранней фазе / overload; попробуй другой cue или `--ticks 2` |
| «файл занят» при tick | останови `run_agent.py` |
| Нет доступа к private archive | запроси invite; без него полный restore недоступен |

---

## 8. Чего пока нет (честно)

- Красивого REPL-чата в терминале — только tick + JSON / session file.
- Публичного life-archive (Phase B в [ADR-0050](../design/CASA-ADR-0050-agent-life-archive-visibility-v1.md)) — пока private.
- Browser wasm — [horizon memo](../design/CASA-future-von-neumann-browser-wasm-v0.md).

---

## Ссылки

- Зоны жизни / host vs teacher: [agents/README.md](../agents/README.md)
- Диалог и субъект: [ADR-0045](../design/CASA-ADR-0045-subject-as-interlocutor.md)
- Restore / fork: [ADR-0050 § Restore](../design/CASA-ADR-0050-agent-life-archive-visibility-v1.md)
- Учебный план RU: [CASA-von-neumann-ru-teaching-plan-v1.md](../design/CASA-von-neumann-ru-teaching-plan-v1.md)
- Snapshot backup (maintainers): `python tools/sync_life_archive.py snapshot -m "…"`

**Вопросы по доступу:** maintainers [AI-Guiders/casa-ontology-payload](https://github.com/AI-Guiders/casa-ontology-payload).
