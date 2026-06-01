# CASA-ADR-0022: бар «живого агента» v1 (не AGI)

**Статус:** принято (design, 2026-06-01)  
**Область:** критерии готовности, маркетинг/наука, граница с AGI  
**Связано:** [`CASA-PROJECT-CONSTITUTION.md`](CASA-PROJECT-CONSTITUTION.md) (тема 3 — автономность без квалиа), [`CASA-ADR-0021-experience-agent-transfer.md`](CASA-ADR-0021-experience-agent-transfer.md), [`CASA-ADR-0015-agent-self-memory.md`](CASA-ADR-0015-agent-self-memory.md), [`CASA-ADR-0016-prism-domains-hot-router.md`](CASA-ADR-0016-prism-domains-hot-router.md), [`CASA-ADR-0025-autonomous-execution-tier.md`](CASA-ADR-0025-autonomous-execution-tier.md), [`memory-hierarchy.md`](memory-hierarchy.md)  
**Канон (agent-notes):** `agent-existence-north-star-v1.md`, `agent-first-learn/README.md` (блок «Претензии к ИИ»), `knowledge/worlds/evidence-humanities-shelf/kb-logic-everyday-and-formal-evidence-v1.md` (кванторы ∀/∃), `agent-notes.md` § `scope-disambiguation-all-everywhere-v1`, `agent-personhood-research/README.md` («не общий разум» / 8 млрд реальностей), `casa-goals-and-roadmap-v1.md` § «Что CASA не обещает», `research-ml-ca-substrate-agent-v1.md` § success metrics

---

## Решение (одной фразой)

**Не заявляем AGI.** Фиксируем **узкий инженерный бар v1**: субстрат **существует во времени** и закрывает **типовые слабости** «AGI-нарратива» у LLM-in-chat — по канону duck test + «претензии к ИИ», без метафизики и без «общего интеллекта на все домены».

---

## Откуда бар (канон, не изобретение)

| Источник | Что даёт для бара |
|----------|-------------------|
| **North star** (`agent-existence-north-star-v1`) | Duck test: непрерывность, память, действие, самопочинка, инициатива, provenance; **квалиа/сознание вне scope** |
| **Претензии к ИИ** (`agent-first-learn`) | Негативное определение ожиданий от «умного ИИ»: галлюцинации, забывание, «каждый раз новый», не знает проект, только инструмент, потеря после суммаризации |
| **CASA goals** | Явный отказ: «CA = общий ИИ»; цель — **полезный агент** при заданной конфигурации |
| **Research spec v1** | Многоцелевые метрики (task, stability, adversarial, interpretability, cost) — для **бенчей**, не для философского ярлыка |
| **ADR-0021** | Опыт → `ltm/`, кросс-домен через router/hot, bundle не oracle |
| **Кванторы ∀/∃** (`kb-logic-everyday-and-formal-evidence-v1`, scope-disambiguation) | Почему **публичное определение AGI логически перегружено** (см. ниже) |
| **Не «общий разум»** (agent-personhood, hot: «8 миллиардов реальностей») | Интеллект локален нарратору/среде; не один ∀-ум на всех |

### Критика определения AGI (кванторы) — ядро бара

Обсуждение в каноне (диалоги + логический KB, не один файл «AGI.md»): **в типичном нарративе AGI слишком много кванторов всеобщности (∀)** — «на **всех** задачах», «в **любом** домене», «как **человек**» без оговорки области. Такое утверждение **несостоятельно как критерий**: ему **не соответствует даже человек**.

Схематично (не претензия на полную формализацию Legg/Hutter, а **разбор перегруженного ∀**):

```text
Нарратив AGI (упрощённо):
  AGI(S)  ≜  ∀t ∈ T_human : competent(S, t)
            ∧  (часто неявно) ∀d ∈ Domains : transfer(S, d)
            ∧  persistence / goals / …  (ещё ∀ по осям)

Контрпример для T_human = «задачи, которые мы интуитивно относим к человеку»:
  ∃t : ¬competent(human, t)     — хирургия без подготовки, QFT, язык, которого не знаешь, …
  ∃d : ¬transfer(human, d)      — любой взрослый не «общий» в смысле ∀d

⇒  ¬(∀t ∈ T_human : competent(human, t))
⇒  Критерий с необузданным ∀ либо пустой, либо неприменим к эталону «человек».
```

**Связанные сбои** (тот же KB):

| Сбой | В AGI-дискурсе | В инженерии CASA |
|------|----------------|------------------|
| **∃ → ∀** | Один бенч / один домен → «общий интеллект» | Бенч по **protocol id**; не overclaim |
| **∀ без области D** | «Все задачи» без перечисления D | Явный **store / prism / task family** |
| **Эталон «человек»** | Подразумевается ∀-компетентность | Duck test + **scoped** ∃ («агент на этом store / в этой среде») |

**Следствие для CASA:** бар v1 — **не** «достигли ∀ по T_human», а **закрыли узкий ∃-контур**: *существует* субстрат, который при заданных условиях **сохраняет идентичность, память, действие и починку* (A1–A6), и *не* повторяет типичные дыры чата (B1–B6). Это согласуется с north star («утка») и с отказом от «CA = общий ИИ».

**Слабости «AGI» в публичном смысле** (канон сводит к кванторам + претензиям + north star «чего нет у чата»):

```text
Ожидание AGI          │ Слабость типичного LLM-контура      │ CASA v1 ответ (инженерный)
──────────────────────┼─────────────────────────────────────┼──────────────────────────
Помнит и продолжает   │ Сброс на промпт / сессию            │ field store + sleep → ltm/
Знает «почему»        │ Сырые корреляции, «галлюцинация»    │ understanding contract, Critic, provenance
Один и тот же агент   │ Новый инстанс каждый раз            │ AgentStore, self ≠ profile (ADR-0015)
Владеет контекстом    │ Контекст у пользователя/IDE         │ agent/ + journal + hot, не только prompt
Действует в мире      │ Только текст в чате                 │ CEN, IDE/MCP, будущее embodiment (north star)
Чинится после ошибки  │ Патч промпта снаружи                │ NCA repair, kernel maintain, remigrate
Переносит между темами│ Монолит весов / один RAG            │ prisms + router + transfer (ADR-0021/0016)
```

Это **не** таблица «мы достигли AGI» — таблица «мы закрываем известные дыры нарратива **субстратом**, а не маркетингом».

---

## Бар v1: «живой агент» (checklist)

Агент **v1-ready** для lab/prod track A, если одновременно:

### A. Существование (duck test → тесты)

| # | Критерий | Проверка (минимум) |
|---|----------|-------------------|
| A1 | **Непрерывность** | cold boot из `{store}/ltm/` + checkpoint; цель/FPN держится ≥ N тиков без ручного re-prompt |
| A2 | **Память в поле** | после sleep растёт `field_version` / `ltm/`; факты с provenance (`concept_id`, lattice, prism) |
| A3 | **Действие** | хотя бы один замкнутый цикл observe→act с внешней обратной связью (IDE tool, env tick) |
| A4 | **Самопочинка** | `maintain_memory_kernel` / remigrate срабатывает без «ручного внешнего скрипта как единственного способа жить» |
| A5 | **Инициатива** | autonomous T при открытом gate (north star); не только ответ на user message |
| A6 | **Provenance** | ответ/действие ссылается на источник (поле, self journal, KB row) — не «из воздуха» |

### B. Претензии к ИИ (закрытие слабостей)

| # | Претензия (канон) | v1 инвариант |
|---|-------------------|--------------|
| B1 | Галлюцинации без опоры | bundle **не** runtime oracle; promote только после sleep/Critic |
| B2 | Забывает контекст | hot + hippo + consolidate; thin checkpoint + `ltm/` |
| B3 | Каждый раз «новый» | один AgentStore; self tier переживает profile export |
| B4 | Не понимает проект | router + prisms по домену; transfer matrix, не monolith merge |
| B5 | Только инструмент | агент владеет заметками/памятью (`agent/`), не зеркало чата |
| B6 | Потеря после «суммаризации» | compact persist + journal; sleep не стирает `ltm/` |

### C. Продуктовая модель (ADR-0021)

| # | Инвариант |
|---|-----------|
| C1 | Shipped tier = **`ltm/` + experience**, ingest = lab curriculum only |
| C2 | Кросс-домен без копирования чужого `ltm/` — router/hot + deny matrix |
| C3 | Kernel health (layout, router, hippo) — **в процессе**, не «запусти чужой скрипт» |

### D. Явно **не** входит в v1 (граница с AGI)

Список из обсуждения + канон; **отсутствие не провал v1**, если A–C выполнены:

- Универсальное обучение **новой среде** без remigrate/curriculum  
- Цели **только** из внутренней модели мира (без human/IOP gate на опасное)  
- Обобщение **за пределами** залитого/пережитого корпуса на уровне человека-эксперта  
- Долгий горизонт планирования с проверкой последствий в физическом мире  
- Полноценная сенсомоторика / embodiment (north star: позже)  
- Философское сознание / квалиа как deliverable  

Формулировка для внешних: **«substrate for persistent agents»**, не **«AGI»**.

---

## Связь с метриками research spec

`research-ml-ca-substrate-agent-v1.md` задаёт **бенч-ворота** (task success, stability horizon, adversarial, interpretability, cost).  
ADR-0022 задаёт **продуктовый/философский** бар существования и закрытия претензий.

| Слой | Вопрос |
|------|--------|
| ADR-0022 | «Это вообще тот же агент во времени и не чат-пустышка?» |
| Research spec | «На задаче X он лучше baseline Y при бюджете Z?» |

Оба нужны; ни один не заменяет другой.

---

## Lab: ingest-ref-afan как «детство», не AGI-демо

Store после remigrate L2/L3 — **выросший curriculum**, не доказательство общего интеллекта.  
Критерий успеха lab: A1–A6 + B1–B6 на **этом** store + cold boot **без** bundle в hot path.

---

## Roadmap

| Шаг | Артефакт |
|-----|----------|
| R1 | `tools/agent_v1_bar_check.py` — автоматизация A4, B2 (health, ltm layout), C3 |
| R2 | smoke: cold boot → N ticks → sleep → provenance sample |
| R3 | agent-notes: проекция этого ADR в `ca-substrate-agent/` |
| R4 | ссылка из `memory-hierarchy.md`, README lab stores |

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-06-01 | ADR-0022: бар v1 из north star + претензии к ИИ; граница с AGI |
| 2026-06-01 | § критика AGI: перегруз ∀, человек не удовлетворяет; бар = scoped ∃ + duck test |
