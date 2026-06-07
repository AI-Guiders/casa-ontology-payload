# RU-α — Material→Verbal bridge (Гальперин)

**Блок:** 5α · **Фаза:** между Phase I exit и Phase II phrase  
**Gate:** `probe_material_verbal_ru`  
**ADR:** [CASA-ADR-0054](../../design/CASA-ADR-0054-agent-world-model-v1.md) · [native-writer-criteria](../../design/CASA-native-writer-criteria-v1.md)

## Зачем

Геометрические и math moments без **письменной артикуляции** дают green predict, но не «громкую социальную речь». RU-α учит субъекта **проговаривать пережитое на поле** в journal и в ответе партнёру — до абстрактного phrase/syntax и до B11 meaning graph.

## Цикл moment

```text
vis/math cue на поле → surprise/sleep
  → journal remember (compose_from_field или teacher text)
  → partner recall: «опиши своими словами»
  → articulate: field tokens + own voice, anti-paste
```

## Файлы

| Файл | Назначение |
|------|------------|
| `data/material-verbal-moment-plan-v1.json` | Train moments (ingest) |
| `data/material-verbal-held-out-plan.json` | Disjoint gate scenarios |
| `class.manifest.json` | Umbrella link |

## Команды

```bash
python lab/visual-curriculum/probe_material_verbal_ru.py --store von-neumann
python lab/visual-curriculum/probe_material_verbal_ru.py --store von-neumann --held-out
```

После green: `python tools/sync_life_archive.py snapshot -m "life: RU-α material-verbal green"`
