# Open-source readiness & tech-debt — строгий ревью (трекинг)

**Статус:** living note (не ADR; журнал находок и остатка)  
**Дата:** 2026-05-31 (обновлено)  
**Контекст:** стек открыт на GitHub. Это список того, что ревью отметило как риск публичной MIT-репы, что **уже сделано**, и что **осталось**.  
**Связано:** [`CASA-ADR-0009-experience-replay-retention.md`](CASA-ADR-0009-experience-replay-retention.md), [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md), [`../scripts/check_no_abs_paths.py`](../scripts/check_no_abs_paths.py)

---

## Сделано (закоммичено / в рабочем дереве)

| Тема | Что | Почему критично |
|------|-----|------------------|
| **Лицензия** | `LICENSE` holder = AI-Guiders; `THIRD-PARTY-NOTICES.md` | MIT без holder и notices — юридическая дыра |
| **Download-only data** | corpora derived + Gutenberg → gitignore; `download_corpora.py` + `fetch_en_folk_gutenberg_v0.py` | CC BY-SA / PD тексты не в MIT-дереве |
| **UD sidecar** | `ud_lemma_pos.v1.json` download-only; пояснение про SA в notices | разделение code (MIT) vs data |
| **Folk / Afan** | Grimm/Jacobs PG + Afanasyev задокументированы в notices | прозрачность источников |
| **Abs-paths** | `train_sss_nca_v0` → `rel_to_repo`; gitignore report/logs/exp artifacts; `sanitize_abs_paths_in_tree.py`; ps1 → `AGENT_NOTES_KB` env | утечка machine paths |
| **CI guard** | `check_no_abs_paths.py --scope all` в workflow | gate на весь tracked tree |
| **README** | License + `download_corpora` в quick start | onboarding |
| **Predictor / replay / prism** | (ранее) T9Weights, ADR-0009, terminology | см. историю коммитов |

---

## Осталось

### P1 — история git

- [x] **Переписать git-историю от data-блобов.** `git filter-repo --invert-paths` по `scripts/filter_repo_drop_paths.txt` (32 пути: conllu, Gutenberg, headwords, frequency, ud_lemma_pos, lexicon_axes). После `--force-with-lease` push clone не тащит старые объекты.

### P2 — структура

- [x] **Пакет + prism folders.** `casa/prisms/*`, `casa/cli/*`; `tools/` = shims (M2, 2026-05-31).
- [ ] **FieldBus** + M4 shim removal.
- [ ] **Чистка legacy store paths** (`ltm/l2`, …).

---

## Наблюдение про CC BY-SA (UD)

Pipeline **не редактирует** treebank — только строит lemma→UPOS индекс. Юридически спорно, является ли это «производным» SA-объектом; **download-only** снимает вопрос смешения с MIT-кодом в git. При редистрибуции sidecar — соблюдать UD attribution.

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-05-31 | Создан журнал |
| 2026-05-31 | P0 license + download-only + abs-path cleanup; P0 abs-path mass scan закрыт через gitignore + sanitize |
