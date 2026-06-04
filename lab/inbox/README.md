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

### Literacy word (lesson_moment, один sleep)

Генерация очереди:

```powershell
python lab/visual-curriculum/micro-literacy/enqueue_literacy_inbox.py --stage stage-06-words-cyrl-corpus --limit 20
```

Пример файла в `lab/inbox/`:

```json
{
  "kind": "lesson_moment",
  "class_dir": "lessons/literacy-cards",
  "moment_id": "lex-stage-06-words-cyrl-corpus-word-mama-sans",
  "steps": [
    {"visual_frame": "word-mama-sans"},
    {"lexical": {"cue": "mama", "correct": "мама", "concept_id": "lang.word.mama", "lattice_id": "lexicon-ru"}}
  ],
  "sleep": true
}
```

Стадии: `stage-01-grapheme-cyrl`, `stage-02-grapheme-cyrl-faces`, `stage-06-words-cyrl-corpus`, `stage-07-closed-class`, `stage-11-grapheme-latn`, …

**Педагогика (ADR-0030):** один JSON = один sleep; `--order wordlist` в enqueue; не гонять batch CLI пока крутится reactor. Полный чеклист: [design/CASA-literacy-pedagogy-lab-v1.md](../../design/CASA-literacy-pedagogy-lab-v1.md).

После обработки runner переместит файл в:
- `lab/inbox/_processed/` при успехе
- `lab/inbox/_failed/` при ошибке

