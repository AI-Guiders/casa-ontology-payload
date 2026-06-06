# CASA-ADR-0037: Gate — проверка ЗУН / KSA verification (META)

**English (code):** **K**nowledge, **S**kills, **A**bilities — `GateKind.AGENT_KSA` / `"agent_ksa"` in `teacher_gate.py`.  
**Русский (канон в ADR):** знания / умения / навыки.

**Статус:** **канон**  
**Дата:** 2026-06-06  
**Уровень:** META (над доменными ADR и конкретными probe)

**Связано:**

- [CASA-teacher-framework-v1.md](CASA-teacher-framework-v1.md) — META entry point
- [CASA-ADR-0034-executor-learning-loop.md](CASA-ADR-0034-executor-learning-loop.md) — шаг 5 Verify
- [CASA-ADR-0035-multi-layer-routing.md](CASA-ADR-0035-multi-layer-routing.md) — эпистемика / capability / goal
- [CASA-ADR-0036-emergent-morph-agreement.md](CASA-ADR-0036-emergent-morph-agreement.md) — literacy без oracle на read
- [CASA-learning-protocol-vis-math-v1.md](CASA-learning-protocol-vis-math-v1.md) — мосты его; probe = held-out
- `casa/domain/mastery_gate.py` — streak, promote credit

---

## Решение (одной фразой)

**Gate — это шаг 5 цикла исполнителя: честная проверка ЗУН агента на held-out среде через store + predict / capability на поле; pass/fail идёт в mastery journal и promote — не «отчёт учителя» и не регрессия Python sidecar без участия агента.**

---

## Gate = ЗУН

| ЗУН | Вопрос | На поле CASA | Пример gate |
|-----|--------|--------------|-------------|
| **З — знания** | Что знает? | LTM: `grapheme.*`, `syllable.*`, `lang.word.*`, `lang.meta.*`, paradigm links | held-out frame → `predict_*` → нужный **concept_id** |
| **У — умения** | Что умеет применить? | capability routes: `skill.read.analytic`, `skill.compose.slots`, `skill.agree.*`, … | tick / probe исполняет **умение**; verdict по **поведению** на поле |
| **Н — навыки** | Что делает устойчиво? | mastery streak, перенос на novel frame / novel phrase | N× pass gate → `record_gate_attempt` → promote route |

**Не смешивать слои в одном pass:** meta quiz — в основном **З**; phrase compose slots — **У**; стабильный phrase на novel JPEG после streak — **Н**.

Цикл ADR-0034: шаги 1–4 = curriculum + синтез; **gate только шаг 5**.

---

## Честный gate (обязательные свойства)

1. **Held-out** — кадр / контекст **не** был парой в том sleep, который сейчас проверяем (или явно marked held-out в probe spec).
2. **Источник verdict — агент** — `predict`, compose на **store агента**, capability на wake; не подстановка ответа в runtime.
3. **Критерий опубликован** — probe README / ADR: какой concept, слот, grammeme, skill id.
4. **Учёт в биографии** — `record_gate_attempt` / `sync_probe_pass_to_skill_gate` → promote только после streak (CBE).
5. **Провал не чинит ядро** — повтор curriculum (другая подача), не hotfix probe/sleep под зелёное.

---

## Не gate (явные ярлыки)

| Артефакт | Что это | Mastery credit? |
|----------|---------|-----------------|
| **Sidecar regression** | Python сверяет `expected surface` без store (`phrase_numeral`, … v0) | **Нет** — `spec:curriculum-sidecar` |
| **Authoring lint** | JSON event schema, manifest merge | **Нет** |
| **Teacher hint в отчёте** | «ожидали X» для человека после честного predict | часть отчёта, **не** substitute predict |
| **Oracle read** | pymorphy, OCR, expected string в hot path | **Запрещено** |

Sidecar regression **допустим** в lab до появления agent gate; **не** записывать в `gate:skill.*` как pass ЗУН (или помечать отдельным namespace `spec:*`).

---

## Probe → skill → promote (канон)

```text
held-out probe
  → predict / capability на field state
  → pass/fail
  → record_gate_attempt(state, gate:skill.*)
  → mastery_ready (streak ≥ N)
  → promote_capability_route / applicability
```

Маппинг probe id → skill: `mastery_gate.PROBE_GATE_BY_SKILL` (расширять по мере честных probe).

**Phrase pilot v0:** `phrase-compose-pilot` с simulated `analytic_know` и teacher `phrase_*` — **sidecar до** `probe_phrase_agent_store`; не считать полным gate **Н** по согласованию.

---

## Типы gate по домену (частные случаи)

| Домен | З | У | Н | Probe (пример) |
|-------|---|---|---|----------------|
| Grapheme / meta | concept на JPEG | — | streak quiz | `probe_grapheme_quiz`, meta quiz |
| Corpus whole | `lang.word.*` | `skill.read.whole` | streak | corpus quiz |
| R1 analytic | слоги + word id | `skill.read.analytic` | novel frame | `probe_analytic_read_corpus` |
| Phrase slots | words in LTM | `skill.compose.slots` | novel phrase vis | `probe_phrase_agent_store` (цель) |
| Agreement | meta grammeme | `skill.agree.*`, `skill.select.form` | novel + streak | agent store + grammeme |
| Math | math concept | count/compare capability | streak | `predict_math_for_vis_cue` |

Доменные ADR описывают **curriculum** (1–4); этот ADR — **критерий шага 5** для всех доменов.

---

## Anti-patterns

1. Pass gate из teacher Python без read store агента.
2. Promote capability после sidecar regression только.
3. Один gate на «всё сразу» (grapheme + meta + phrase в одном sleep и одном probe).
4. Менять probe threshold после провала вместо смены подачи.
5. Считать ingest moment = уже gate (ingest — шаг 4 в среде, gate — held-out **после**).

---

## Резюме

- **Curriculum** (1–4) — среда; учитель не подставляет ответ на wake.
- **Gate** (5) — **единственный** канонический verifiable ЗУН для promote.
- **Sidecar** — временная регрессия spec, не substitute gate.
