# CASA-ADR-0036: Базовая рамка обучения — формы, meta, согласование (без оракула)

**Статус:** **канон** — базовая рамка literacy + phrase (не «фаза B», не опция)  
**Дата:** 2026-06-06  
**Связано:**

- [CASA-teacher-framework-v1.md](CASA-teacher-framework-v1.md) — META entry point
- [CASA-learning-protocol-vis-math-v1.md](CASA-learning-protocol-vis-math-v1.md) — § «Мосты — его, не наши»
- [CASA-ADR-0033-russian-phrase-structure-free-order.md](CASA-ADR-0033-russian-phrase-structure-free-order.md) — слоты, phrase P1 (частный случай этой рамки)
- [CASA-ADR-0030-grammar-literacy-coherent-text.md](CASA-ADR-0030-grammar-literacy-coherent-text.md) — L1–L4
- [CASA-ADR-0035-multi-layer-routing.md](CASA-ADR-0035-multi-layer-routing.md) — capability / applicability / plan
- [CASA-ADR-0037-gate-zun-verification.md](CASA-ADR-0037-gate-zun-verification.md) — gate = проверка ЗУН
- [CASA-ADR-0032-analytic-syllable-reading.md](CASA-ADR-0032-analytic-syllable-reading.md) — R1, corpus LTM

---

## Решение (одной фразой)

**Базовая рамка literacy:** каждая форма — отдельный знак в LTM; meta — категории grammeme; paradigm и согласование — **emergent capability** агента из moment + sleep + phrase curriculum; учитель даёт vis, корpus, meta-карточки и event-схемы слотов — **не** подставляет правильную строку и **не** морфологический парсер.**

Это **тот же** протокол, что vis↔math: среда + held-out probe; навык на поле — **его**.

---

## Рамка (единая для всего literacy)

```text
Учитель                          Агент
────────                         ─────
corpus word cards                lang.word.* (каждая форма отдельно)
meta grammar cards               lang.meta.grammar.*
phrase / agreement moments       paradigm links + skill.agree.*
event schema (слоты, grammeme)   skill.select.form + skill.compose.slots
gate (held-out, store)           predict + capabilities → ЗУН verdict (ADR-0037)
sidecar spec regression          lint JSON / phrase_* v0 — не gate ЗУН
```

---

## Не цель

| Подход | Почему нет |
|--------|------------|
| pymorphy / OpenCorpora / «morph index» в runtime | **Оракул** — подсмотрел форму снаружи |
| `_fem_a_palatal_paradigm(lemma)` + `lemma` в JSON как источник истины | Teacher tract в lab; **не** модель агента |
| Одна lemma на поле, остальное «вычислим» | Нет формы в LTM → **fail / trial**, не подстановка |
| Cartesian sleep «все формы × все meta» | ADR-0030 / ADR-0032 — ложные мосты |
| Два параллельных «режима обучения» (teacher vs agent) | Одна рамка; teacher probe = lab report |

---

## Слои (эпистемика ≠ праксис)

```text
L1  lang.word.*          — поверхности из корpusа (мама, мыла, раму, палки, …)
L2  lang.meta.grammar.*  — категории (род, число, падеж, numeral.class.*, person.*)
L3  lang.paradigm.*      — emergent кластер форм одной лексемы (не lemma string в JSON)
L4  lang.event.*         — схема слотов + требуемые grammeme на слот (не expected surface)

Праксис (capability):
  skill.read.analytic      — восстановить слово R1
  skill.compose.slots      — заполнить роли event
  skill.agree.subjectVerb  — agent↔verb (род/лицо/число/время)
  skill.agree.modifierHead — притяжательное, числительное+head, …
  skill.select.form        — выбрать форму из paradigm-кластера под grammeme слота
  skill.read.phrase        — compose + verify phrase (надстройка)
```

**Не смешивать:** знать «моя» (L1) ≠ уметь «подобрать мою к fem sg head» (`skill.agree.modifierHead`).

---

## Как навык **выводится** (не инжектится)

### 1. Формы в корpusе

Каждая ** attested** форма — свой `lang.word.*` + ingest (как «мыла», «раму»). Агент не «знает палку» абстрактно — знает **набор surfaces**, встреченных в curriculum.

### 2. Meta без лексем

Pure meta ingest: «им. ед.», «род. мн.», «numeral class many», «3sg fem past» — **категории**, не привязка к «палка».

### 3. Paradigm links (emergent L3)

Связь форм одной лексемы — **не** teacher lemma в event:

- **Co-sleep** в phrase moment: «книга» и «книгу» в одном event / chain → мост `paradigm_co_occurs`
- **Meta bridge**: vis «женский род» + head «книга» → укрепление gender trait на word node
- **Question frames**: «кого?» → «раму» якорит **acc** trait на form node

Идентификатор: `lang.paradigm.<cluster_id>` (hash стабильного кластера или promoted id после N успешных phrase passes). **Не** pymorphy normal_form.

### 4. Выбор формы на wake (skill.select.form)

```text
goal + active_plan step → слот требует grammeme G
predict на поле / WM → кандидаты lang.word.* из LTM
filter: word.linked_meta ⊇ G  ИЛИ  word ∈ paradigm P и P.has_form(G) в LTM
pick → surface в слот
```

Если формы с нужным G **нет в LTM** → `skill.select.form` fail → decompose / trial episode (ADR-0035), **не** oracle inflect.

### 5. Согласование (skill.agree.*)

Проверка **между уже выбранными** slot fills:

- subjectVerb: traits agent ↔ verb (как `check_agreement`, но traits из **LTM word nodes**, не hardcoded «мама→мыла»)
- modifierHead: meta rule «numeral class many → head needs gen pl» + **есть ли** такая form в paradigm кластере head

Meta rule = ** applicability condition**; pass только если агент **реально выбрал** совместимые формы из своего store.

---

## Curriculum (минимальный путь)

| Шаг | Что | Probe / promote |
|-----|-----|-----------------|
| W1 | Формы корpusa в LTM | `skill.read.whole` / `skill.read.analytic` |
| W2 | Meta grammar (род, число, падеж, numeral class) | meta quiz probes |
| W3 | Phrase P1: слоты без oracle string | `skill.compose.slots` |
| W4 | Phrase + agreement pairs (мама/мыла, она/мыла, …) | `skill.agree.subjectVerb` |
| W5 | Paradigm co-ingest (книга+книгу, палка+палки+палок) | `skill.select.form` |
| W6 | Numeral / possessive phrase | `skill.agree.modifierHead` |
| W7 | Agent phrase read без teacher expected surface | `skill.read.phrase` на **agent store** |

**Paradigm co-ingest:** отдельные moment'ы на каждую форму + **один** phrase/chaining episode, где все формы одного кластера участвуют в разных ролях — sleep строит `paradigm_co_occurs`, без pymorphy.

---

## Gate и probe

**Канон:** [CASA-ADR-0037-gate-zun-verification.md](CASA-ADR-0037-gate-zun-verification.md) — gate = проверка **ЗУН** на held-out (store + predict / capability). Promote только после честного gate.

| Компонент | Роль |
|-----------|------|
| Честные probe (grapheme, meta, R1, …) | Gate **З/У/Н** → `record_gate_attempt` |
| `phrase_*` teacher modules (v0) | **Sidecar regression** spec curriculum — **не** gate ЗУН до agent store probe |
| `probe_phrase_agent_store` | Gate **У/Н** phrase по store агента |
| Wake tick | Синтез (шаг 4); gate — отдельно, held-out |

Curriculum (корpus, meta, phrase moments) — шаги 1–4 той же рамки ([ADR-0036](CASA-ADR-0036-emergent-morph-agreement.md)).

---

## Anti-patterns

1. **Morph oracle** в hot path или в gate B.
2. **Lemma в phrase-events** как обязательное поле (только optional lab illustration, deprecated в B).
3. **Одна таблица на существительное** (10 events на палка/книга/…).
4. **Promote** `skill.agree.*` из teacher pass без agent-side verify на novel frame.

---

## Открытые вопросы

- [ ] Канон id paradigm cluster: co-occurrence graph vs promoted `lang.paradigm.*` token
- [ ] Traits на word node: explicit после meta bridge vs только через co-occurrence
- [ ] `skill.select.form` vs один `skill.inflect.ru` — granularity capability
- [ ] Как phrase self-drive (ADR-0033 queue) ставит subgoal «найти form G для head»

---

## Следующая реализация (в той же рамке)

1. **`paradigm_ltm.py`** — co_occurs / paradigm view из store
2. **Paradigm co-moments** — книга + книгу в phrase chain (curriculum, не oracle)
3. **`probe_phrase_agent_store.py`** — held-out pass по LTM (реализовано)
4. Event JSON: **`grammeme` on slot**, deprecate `lemma` / teacher-only fields

---

## Резюме

Агент **выводит навык**, когда:

1. знает **несколько форм** из корpusa;
2. знает **meta-категории** grammeme;
3. на phrase sleep **связал** формы в paradigm;
4. на wake **выбирает** form из LTM под слот;
5. **согласовывает** выбор между слотами по meta rules + traits.

Sidecar `phrase_*` v0 — регрессия spec curriculum; **gate ЗУН** — только probe с store ([ADR-0037](CASA-ADR-0037-gate-zun-verification.md)).
