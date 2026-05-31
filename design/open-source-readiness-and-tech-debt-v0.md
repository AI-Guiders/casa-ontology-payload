# Open-source readiness & tech-debt — строгий ревью (трекинг)

**Статус:** living note (не ADR; журнал находок и остатка)  
**Дата:** 2026-05-31  
**Контекст:** стек открыт на GitHub. Это список того, что ревью отметило как риск публичной MIT-репы, что **уже сделано**, и что **осталось**.  
**Связано:** [`CASA-ADR-0009-experience-replay-retention.md`](CASA-ADR-0009-experience-replay-retention.md), [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md), [`../scripts/check_no_abs_paths.py`](../scripts/check_no_abs_paths.py)

---

## Сделано (закоммичено)

| Тема | Что | Почему критично |
|------|-----|------------------|
| **Лицензия** | `LICENSE` holder = AI-Guiders; добавлен `THIRD-PARTY-NOTICES.md` | MIT без holder и без notices — юридически дыра при публикации |
| **Сторонние данные** | corpora untracked; `scripts/download_corpora.py`; манифесты относительные; provenance | CC BY-SA 4.0 корпуса в MIT-репе без пометки = нарушение copyleft |
| **Predictor** | именованный `T9Weights`; удалён мёртвый `nca_repair` | magic numbers → читаемый конфиг |
| **t9 runtime** | полный `raw` payload за `--debug` | hot-path stdio не тащит лишнее по умолчанию |
| **Naming collision** | `agent_autonomous_tick.py` → `agent_sn_cen_tick.py` | различить SN→CEN tick и wake/sleep tick |
| **Scratch artifacts** | `lab/_bench_*` выкинуты из tracking | регенерируемый мусор не в git |
| **Тесты** | `tests/test_predictor_smoke.py` + pytest в CI; `pyproject.toml` | детерминированный assert-gate ранжирования T9 |
| **Guard** | `scripts/check_no_abs_paths.py` | pre-publish защита от утечки абсолютных путей |
| **Replay (ADR-0009)** | `replay_buffer_v0.py` + тесты | борьба с забыванием коррекций |

---

## Осталось (приоритезировано)

### P0 — до публичного анонса

- [ ] **Массовая санитация абсолютных путей.** `check_no_abs_paths.py` ловит ~1190 вхождений `D:\Experiments\…`. Разделить:
  - *безопасно* — текст в design/доках и логах: автозамена на repo-relative / `<repo>`;
  - *осторожно* — store-манифесты (`pack.manifest.json`, `nca_train_registry.v0.json`): пути читаются на boot → менять **с валидацией `store_boot_v0`**, не текстовой заменой.
  - Превратить guard в CI-gate (fail при новом абсолютном пути в tracked).

### P1 — гигиена истории и структуры

- [ ] **Переписать git-историю от data-блобов.** Ранее трекались крупные `.conllu` (UD). Удалить из истории (`git filter-repo`) — **деструктивно, нужен явный аппрув пользователя и согласование с remote**. До тех пор клон тащит тяжёлые объекты.
- [ ] **Пакет вместо плоского `tools/`.** Десятки модулей с `sys.path`-зависимостью. Перевести в `casa/…` подпакеты (predictor, sss, nca, bench), оставив тонкие shim-точки входа. Высокий риск (трогает импорты везде) → отдельной веткой, после стабилизации lattice-naming v1.

### P2 — единообразие

- [ ] **Чистка суффиксов `_v0` / `_v1`.** Версия в имени файла — анти-паттерн; версионировать содержимым/ADR. Делать массово только вместе с пакетным рефактором (P1), иначе мердж-боль с активным WIP.

---

## Наблюдение про WIP (2026-05-31)

На момент ревью в submodule **большой незакоммиченный WIP** пользователя: миграция lattice-id v1, teacher-correction protocol, wake/sleep, `bench_sleep_extract_remember`, выходы NCA-шардов (`lab/agent-stores/**`). Это **не** сторонняя активность — фоновых процессов нет. Рекомендация: зафиксировать WIP логическими коммитами (миграция / протокол / bench / store-выходы отдельно), чтобы ценная работа не висела вне git. Пакетный рефактор (P1) и `_v0`-чистку (P2) делать **после** этого коммита.

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-05-31 | Создан журнал: сделанное в ревью + остаток (abs-paths, history rewrite, package, `_v0`) |
