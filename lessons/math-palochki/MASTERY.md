# Mastery: четыре действия, роли, свойства (von-neumann)

**Модель:** урок (teacher ingest) → агент живёт и выводит (`run_agent`) → **ты проверяешь** этим банком.

Oracle только здесь, на проверке — **не** в predict tick агента (ADR-0021).

## Порядок

1. Ingest класса (00–18): `gen_math_palochki_class.py` + `ingest_lesson_class.py`
2. Жизнь агента: `run_agent.py` — Kolb, sleep, тетрадь
3. Проверка:

```powershell
python tools/check_agent_mastery.py --store-dir agents/von-neumann
```

Отчёт: `last-mastery-report.json`. Пороги в `class.manifest.json` → `mastery_threshold`.

## Тiers

| Tier | Что значит «уверенно» |
|------|------------------------|
| **compute** | `?`-drill: sticks → groups → digits, все 4 ops |
| **role** | `math.role.*` по русским словам операндов |
| **property** | `math.prop.*` после уроков 14–16 + sleep на co-scenes |
| **fraction** | `math.frac.*`, числитель/знаменатель, палочечная запись 1/2 2/3 3/4 |

Pass: top или top-3 на поле **без bundle** на read path.

## Уроки свойств (14–17)

| # | Slug | Содержание |
|---|------|------------|
| 14 | `commutative` | `prop:comm_add`, `prop:comm_mul` — палочки и выражения без ответа |
| 15 | `associative-distributive` | группировка `+`, `×`, распределение |
| 16 | `identities-division` | `+0`, `×1`, ÷ ↔ × на кучках |
| 17 | `roles-and-four-ops` | роли + сцены четырёх действий |

Episodes с `"presentation": true` — **нет** numeric oracle в `correct`; структура видна в `cue`.

## Если не прошёл

- Повтор ingest нужного урока + жизнь агента
- Не подкручивать expect в runtime — только teacher probe и сцены
