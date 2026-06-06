# CASA Teacher Framework (v1)

**Статус:** **канон** — единая точка входа для authoring, lab и probe  
**Дата:** 2026-06-06  
**Зачем:** чтобы не спорить заново про oracle, gate и «кто знает ответ» в каждом домене (literacy, math, phrase, grammar).

**Детали по слоям** — в связанных ADR; здесь только **инварианты** и **разделение ролей**.

---

## Одной фразой

**Учитель строит среду и критерии проверки (1–4 + spec gate); агент на поле выращивает мосты и проходит gate ЗУН на held-out; учитель не подставляет ответ на wake и не считает sidecar regression mastery.**

---

## Цикл (всегда один)

```text
1 Goal        — inbox / spec: что учим
2 Classify    — тракт (word, meta, phrase, math, …)
3 Methods     — moment plan, tract, rule episode
4 Synthesize  — ingest, sleep, wake predict (агент)
5 Verify      — GATE = ЗУН (held-out, store агента)
```

Канон шага 5: [CASA-ADR-0037-gate-zun-verification.md](CASA-ADR-0037-gate-zun-verification.md).

META-цикл: [CASA-ADR-0034-executor-learning-loop.md](CASA-ADR-0034-executor-learning-loop.md).

---

## Gate = KSA (Knowledge, Skills, Abilities)

Русский канон: **знания / умения / навыки**. В коде: `GateKind.AGENT_KSA` ([ADR-0037](CASA-ADR-0037-gate-zun-verification.md)).

| ЗУН | Учитель задаёт | Gate проверяет на **агенте** |
|-----|----------------|------------------------------|
| **З** знания | карточки, corpus, meta id | held-out predict → `concept_id` |
| **У** умения | curriculum → `skill.*` | исполнение capability на store |
| **Н** навыки | streak spec, novel contexts | N× pass → promote |

**Pass gate** → `record_gate_attempt` → mastery → promote route.  
**Не pass** → другая подача (шаги 2–4), **не** hotfix probe/sleep.

---

## Две зоны ответственности

| | Учитель (authoring + lab) | Агент (поле) |
|---|---------------------------|--------------|
| **Может** | vis, lex в moment, порядок стадий, event schema (слоты, grammeme), probe README | emergent bridges, sleep co-occurrence, predict, capabilities |
| **Не может** | oracle на read (pymorphy, expected string в wake), подмена шага 4 готовым ответом | — |
| **Probe** | запускает held-out check | **источник verdict** — store + predict |
| **Promote** | не вручную «зачесть» | только после честного gate |

Протокол vis↔math (то же для lex): [CASA-learning-protocol-vis-math-v1.md](CASA-learning-protocol-vis-math-v1.md) § «Мосты — его, не наши».

---

## Три вида артефактов (не путать)

| Вид | Примеры | Gate ЗУН? |
|-----|---------|-----------|
| **Curriculum** | moment, JPEG, meta card, phrase chain, wordlist order | Нет (шаг 4 среды) |
| **Gate probe** | `probe_grapheme_quiz`, `probe_analytic_read_corpus`, `probe_phrase_agent_store` | **Да** |
| **Sidecar / spec regression** | `phrase_numeral.py` v0, JSON `lemma`, lint manifest | **Нет** — только lint curriculum |

Sidecar **допустим** до появления agent probe; **не** писать в `gate:skill.*` без store.

---

## Literacy + grammar (частный случай рамки)

Базовая рамка форм и согласования (без morph-oracle):  
[CASA-ADR-0036-emergent-morph-agreement.md](CASA-ADR-0036-emergent-morph-agreement.md)

- каждая форма — свой `lang.word.*` в corpus;
- meta — категории grammeme, не таблица «палка→палок»;
- paradigm / agree — emergent из phrase sleep + meta;
- phrase event — **слот + grammeme**, не teacher expected surface в hot path.

Phrase slots: [CASA-ADR-0033-russian-phrase-structure-free-order.md](CASA-ADR-0033-russian-phrase-structure-free-order.md).

---

## Lab checklist (authoring)

1. **Один moment = один sleep** — не cartesian batch ([pedagogy lab](CASA-literacy-pedagogy-lab-v1.md)).
2. **Held-out** кадры для probe отделены от ingest train set.
3. **Probe** вызывает predict / capability на **store агента**.
4. **Promote** только из `mastery_gate` после streak.
5. Новый домен → новый probe id + строка в `PROBE_GATE_BY_SKILL`, не ad-hoc oracle в wake.

---

## Карта документов (куда копать дальше)

| Тема | Документ |
|------|----------|
| Gate = ЗУН | ADR-0037 |
| Цикл 1–5 | ADR-0034 |
| Роутинг знания/умения/цели | ADR-0035 |
| Vis↔math / vis↔lex протокол | learning-protocol |
| Literacy roadmap | CASA-literacy-roadmap-v1 |
| Lab ingest порядок | CASA-literacy-pedagogy-lab-v1 |
| R1 read | ADR-0032 |
| Phrase | ADR-0033 |
| Morph / agree рамка | ADR-0036 |
| Mastery code | `casa/domain/mastery_gate.py` |

---

## Anti-patterns (закрыты этим framework)

1. «Probe зелёный — значит агент умеет» при sidecar без store.
2. pymorphy / morph index как источник pass.
3. `expected surface` в wake или в promote path.
4. Ingest moment засчитан как gate.
5. Отдельная «рамка для grammar» без gate ЗУН — grammar **внутри** этого framework.

---

## Резюме

**Teacher-framework** = учитель делает **среду + spec проверки**; gate **единственный** канал ЗУН для promote; всё остальное — curriculum или lint. К этому документу возвращаться при любом новом тракте; доменные ADR только уточняют таблицы и probe id.
