# lexical-cards-ru — букварь с картинками (field-native)

**Класс языка**, не математики. Отдельно от `visual-cards` / `math-palochki`.

## Идея

Классический букварь «А — апельсин, Б — белка» предполагает, что ребёнок **видел** апельсины и белок. Von-neumann пока нет — у него есть **точки, фигуры, сетка, прямая, Venn**.

Поэтому на карточке:

1. **Буква** (крупно) — связь с `grapheme.cyrl.*` / `alphabet-ru`
2. **Якорь** — простая **синтетическая** картинка из того же визуального языка, что и math curriculum (не stock photo)
3. **Слово** (подпись) — учитель **произносит/пишет** рядом в moment; episodic lexical, не oracle на predict

Примеры якорей (не зоопарк):

| Буква | Слово | Якорь на карточке |
|-------|-------|-------------------|
| А | арка | дуга |
| Б | два | две точки |
| В | вверх | две грани как у буквы В |
| Г | угол | угол L |
| … | … | фигура / счёт / знакомый паттерн |

Слова подобраны так, чтобы **картинка была честной**: не «белка», а «два» там, где на полотне две точки.

## Ingest

Как visual-cards, но moment = **visual + lexical** (не math):

```bash
python lessons/lexical-cards-ru/tools/build_abc_cards.py
python -m casa.cli.ingest_lesson_moment \
  --class-dir lessons/lexical-cards-ru \
  --stage stage-01-a-ya \
  --moment-id lexical-abc-v1
```

Мост vis↔буква — **его** (sleep co-occurrence / self_promote). Учитель не перепрошивает.

## Lab

`concept_id`, `word`, `anchor` в manifest — только authoring / teacher plan, не runtime oracle.
