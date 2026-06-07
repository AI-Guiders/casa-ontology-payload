# Класс «Понимание текста» (Block B11)

**Stage:** `stage-11-text-meaning-ru`  
**Skill:** `skill.read.comprehend`  
**KB:** `kb-lang-ru-lexicon-semantics-v1`  
**Gate:** `probe_text_meaning_ru`

Ось A5 (ADR-0053): passage + question → `ru.prop.*` → articulate. Не keyword routing.

## План

`data/text-meaning-plan-v1.json` — staged сценарии:

1. **extract** — факты из passage  
2. **inference** — мотив реплики  
3. **stance** — позиция автора  
4. **pro_con** — структурированное мнение  
5. **register** — смена регистра с сохранением фактов  

## Обучение (ingest)

```bash
python -m casa.cli.ingest_text_meaning_class --store von-neumann
python -m casa.cli.ingest_text_meaning_class --store von-neumann --probe
```

Каждый moment: dialogue compose → fixate props в journal → emergent prior на следующих ticks.

## Gate

```bash
python lab/visual-curriculum/probe_text_meaning_ru.py --store von-neumann
python lab/visual-curriculum/probe_text_meaning_ru.py --store von-neumann --held-out
python -m casa.cli.ingest_text_meaning_class --store von-neumann --sync-life
```

Pass = все wired сценарии: props из KB + осмысленный reply (не paste/defer).

После двух зелёных gate подряд — `promote_pending_bootstrap_routes` выводит capability `skill.read.comprehend` на `passage_context`.
