# CASA — ветки: `develop` как интеграция

**Date:** 2026-06-15  
**Для:** оператор + Дима + агенты (Cursor и др.)

## Зачем

Долгие ветки с идеями (curriculum, dialogue, phrase, …) страшно мерджить сразу в `master`. **`develop`** — общая «площадка»: сюда можно мерджить без страха сломать релизную линию; отсюда все знают, **откуда бранчиться**.

## Модель (упрощённый git-flow)

```text
master   ───●────────●──────────●────  релиз / «то, что уже прошло гейты»
              ↑        ↑
develop  ───●──●──●──●──●──●──●────  интеграция (мерджим сюда)
              ↑     ↑
         feat/…  fix/…               фичи и эксперименты
```

| Ветка | Роль | Кто мерджит |
|-------|------|-------------|
| **`master`** | Стабильная линия; merge только из `develop` после verify / oracle_audit / согласования | оператор или явный «готово к релизу» |
| **`develop`** | Интеграция всех активных направлений | любой участник команды; конфликты решаем здесь |
| **`feat/*`, `fix/*`, …** | Одна задача / одна идея | автор → PR или merge в **`develop`** |

## Правила для всех (в т.ч. агентов)

1. **Новая работа:** `git fetch origin` → `git checkout develop` → `git pull` → `git checkout -b feat/…` или `fix/…`.
2. **Готово локально:** merge или PR в **`develop`**, не в `master`.
3. **`master`:** только когда `develop` зелёный и команда согласна «это релиз».
4. **Длинные ветки** (напр. `feat/auto-curriculum`, `fix/dialogue-language-production`): мердж в **`develop`** первым шагом; в `master` — позже.
5. **Логические коммиты** по смыслу (см. workspace rule); не один коммит «всё подряд».

## Remotes

- **`origin`** — GitHub `AI-Guiders/casa-ontology-payload` (+ зеркала push на GitLab / AMS по настройке).
- После `git push -u origin develop` tracking: `origin/develop`.

## Старт (один раз)

```bash
git fetch origin
git checkout develop
git pull origin develop
git checkout -b feat/my-topic
```

## Не в git

`.venv/`, локальные отчёты агента, `t.cmd` — не коммитить без явной нужды.
