# Inbox (continuous learning)

Сюда учитель может “бросать уроки”, пока агент крутится в фоне.

Runner: `python tools/agent_inbox_runner.py --store-dir agents/von-neumann --inbox-dir lab/inbox`

## Формат файла

Положи в `lab/inbox/` файл `*.json` такого вида:

### Math class lesson (math-palochki)

```json
{
  "kind": "lesson_class",
  "class_dir": "lessons/math-palochki",
  "lesson_ids": ["lesson-18-fraction-heaps"],
  "sleep_after_each_lesson": true,
  "persist": true
}
```

### Lang bridge lesson (lang-ru-math-bridge)

```json
{
  "kind": "lang_lesson_class",
  "class_dir": "lessons/lang-ru-math-bridge",
  "lesson_ids": ["lesson-08-fractions"],
  "sleep_after_each_lesson": true,
  "persist": true
}
```

### Arithmetic stream (generated)

```json
{
  "kind": "arithmetic_stream",
  "count": 50,
  "max_value": 50,
  "sleep": true,
  "persist": true
}
```

После обработки runner переместит файл в:
- `lab/inbox/_processed/` при успехе
- `lab/inbox/_failed/` при ошибке

