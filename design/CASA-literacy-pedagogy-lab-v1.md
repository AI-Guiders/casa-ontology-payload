# Literacy lab: педагогика ingest (v1)

**Статус:** канон lab  
**Связано:** [CASA-ADR-0030-grammar-literacy-coherent-text.md](CASA-ADR-0030-grammar-literacy-coherent-text.md), [CASA-learning-protocol-vis-math-v1.md](CASA-learning-protocol-vis-math-v1.md)

---

## Принцип

Не менять `bridge_lex` / sleep extract в ядре. При **empty** / **ambiguous** на probe — **подача** и **lab reinforce**.

---

## Один writer

| Режим | Правило |
|-------|---------|
| **Inbox reactor** | `agent_inbox_runner` держит store |
| **Batch CLI** | `run_micro_stage` / `run_literacy_stage_pedagogy` — **остановить reactor** перед прогоном |
| **Probe** | после ingest, store свободен |

---

## Один moment = один sleep

- 1× `visual_frame` + 1× `lexical` → `ingest_lesson_moment(..., sleep=True)`
- Не смешивать grapheme + meta + corpus-слово в **одном** sleep
- Стадии раздельно: `stage-07-closed-class`, `stage-08-meta-grammar-person`, `stage-06-…`

---

## Порядок кадров (не `frame_id` по умолчанию для слов)

Сортировка по `frame_id` (hash slug) ≠ порядок учебника. Для служебных слов и корпуса:

```powershell
--order wordlist
```

Источник: `lessons/literacy-cards/data/ru-closed-class-v1.txt`, `ru-wordlist-v1.txt`.

---

## Скрипты

| Скрипт | Назначение |
|--------|------------|
| `run_literacy_stage_pedagogy.py` | ingest → probe → опционально `--reinforce-tail` |
| `run_micro_stage.py` | только ingest (`--order wordlist`) |
| `enqueue_literacy_inbox.py` | очередь в `lab/inbox/` (**wordlist** по умолчанию) |
| `reinforce_literacy_*_tail.py` | ручной хвост после probe |
| `probe_literacy_*.py` | teacher gate |

### Closed-class (полный цикл)

```powershell
cd Financial/software/open/casa-ontology-payload
python lab/visual-curriculum/micro-literacy/run_literacy_stage_pedagogy.py `
  --stage stage-07-closed-class `
  --order wordlist `
  --reinforce-tail
```

### Corpus пачка через inbox

```powershell
python lab/visual-curriculum/micro-literacy/enqueue_literacy_inbox.py `
  --stage stage-06-words-cyrl-corpus --limit 50 --offset 20 --order wordlist
# stop batch CLI if reactor was used for other work; then:
python tools/agent_inbox_runner.py --store-dir agents/von-neumann --inbox-dir lab/inbox
python lab/visual-curriculum/probe_literacy_corpus_quiz.py --offset 20 --limit 50
```

---

## Хвост ingest (0 bridges / ambiguous)

1. Probe, смотреть `empty` / `ambiguous` в JSON.
2. `reinforce_vis_lex_bridge` в lab (`reinforce_*_tail.py` или `--reinforce-tail`).
3. Повторный probe — gate **know** на категорию.

Причина: cartesian `sleep_co_occurs` + pending hippo между moment'ами, не «похожие буквы».

---

## Предупреждение hippo

`run_literacy_stage_pedagogy` логирует `hippo_pending_lex` перед прогоном. Если >0 — лучше не начинать batch, пока reactor/другой writer не закончил.
