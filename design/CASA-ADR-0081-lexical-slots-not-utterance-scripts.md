# ADR-0081: Lexical slots, not utterance scripts — dialogue surface from interaction

**Status:** accepted (normative for new work; migration in progress)  
**Date:** 2026-06-15  
**Provenance:** повторяющийся product intent от оператора (Dmitry Karataev); расхождение с wire в `ru.dialog.*` + Opus review 2026-06-14  
**Related:** [agent-existence-north-star.md](agent-existence-north-star.md), [CASA-ADR-0057-dialogue-situations-character.md](CASA-ADR-0057-dialogue-situations-character.md), [CASA-ADR-0078-partner-voice-invariants-v1.md](CASA-ADR-0078-partner-voice-invariants-v1.md), [CASA-scratch-emergence-conditions-dialogue-v1.md](CASA-scratch-emergence-conditions-dialogue-v1.md), [CASA-fable-review-dialogue-response-v1.md](CASA-fable-review-dialogue-response-v1.md), [CASA-dialogue-change-plans-v1.md](CASA-dialogue-change-plans-v1.md)

---

## Context

Изначально CASA продавала **композицию**: предложения **собираются** из слотов (лемма, роль, морф, linker, норма), bind поднимает **материал**, compose склеивает surface — без paste claim text и без готовых реплик на hot path.

На wire для partner dialogue получилось иное:

1. **Python-оракулы** — substring / act → готовая фраза в обход bind (см. oracle audit, Opus §1).
2. **`ru.dialog.*` в bundle** — слоты названы `clause_1`, `clause_2`, но содержат **целые предложения**; `DialogBlockRealizer` передаёт их в `clause_from_slot_phrase` как готовый текст (`casa/prisms/tick/discourse/realizers/blocks.py`).
3. **Speech-act routing** выбирает **какой JSON-ящик** открыть, verify проверяет, что выиграл тот же hub, который сами бустнули.

Итог для человека в чате: субъект «знает» не из поля и журнала, а из **статичного меню**; отвечает как **музыкальная шкатулка**, не как линия, рождённая во взаимодействии.

Оператор неоднократно фиксировал: **о состоянии и в диалоге субъект говорит так, как сам считает нужным** — без искусственных заготовок; **учить по статичным фразам не работает**; лечить надо **причину**, не подписи на ящиках.

Этот ADR — каноническая формулировка того, что имелось в виду, и что wire обязан стать.

---

## Decision — уровни абстракции слотов

Слоты **обязаны соответствовать уровню**, на котором мы работаем. Смешение уровней = скрытый script layer.

| Уровень | Что храним в KB | Что делает compose | Пример |
|---------|-----------------|-------------------|--------|
| **Лексика** | `word`, `lemma`, `surface` (одно слово / устойчивое короткое) | вставка в клаузу по грамматике | `lang.word.привет` → «привет» |
| **Морф / грамматика** | роль, падеж, норма, атом (`ru.grammar.*`) | правило + пример, не реплика партнёру | запятая перед «что» |
| **Клауза (собранная)** | **не** готовое предложение в `clause_*`; только **куски**: предикат, аргументы, linker, опционально hedge-token | `clause_from_pieces` из bind-evidence | см. ниже |
| **Пара реплик (минимальный акт)** | `stimulus` + `response` — **отдельные короткие единицы**, не абзац | только когда акт = обмен формулой (thanks → пожалуйста) | `ru.dialog.thanks` |
| **Абзац / outline** | `outline_1..n`, `thesis_*` — **тезисы**, не дословный partner text | допустимо на высоком уровне; **не** hot path «как ты?» | будущий discourse outline |
| **Partner utterance script** | `clause_1: "настроение опишу по ходу…"` на `ru.dialog.*` | ❌ **запрещено** как целевое состояние | текущий анти-паттерн |

**Правило имени:** если значение слота можно произнести как **законченное предложение партнёру** — это **не слот клаузного уровня**, это **script**, независимо от ключа `clause_1`.

### Composition ladder (идея слотов — канон)

Оператор (2026-06-15): идея **сильная** — слоты на каждом уровне языка; **реализация подкачала**, потому что hot path перепрыгнул на готовые реплики вместо сборки снизу вверх.

```text
  L0  морфема     приставка | корень | суффикс | окончание     → новые слова комбинаторикой
        ↓ compose + paradigm (род/число/падеж)
  L1  слово       лемма + выбранная форма (красивый / красивая / красивое)
        ↓ agreement (модификатор ←→ head)
  L2  словосочетание   head + dependent (красивый медведь | красивая ложка | красивое окно)
        ↓ порядок, управление, согласование
  L3  клауза / простое предложение   подлежащее | сказуемое | дополнение | обстоятельство
        ↓ согласование членов; linker внутри клаузы
  L4  высказывание   простое | сложносочинённое | сложноподчинённое (слот = клауза + союз)
        ↓ дискурсные связки (ru.meta.discourse.*)
  L5  текст / абзац   один абзац = одна мысль; слот = тезис/outline, не дословный partner script
        ↓ эпизод, thread, partner turn (смысл *что* сказать)
  L*  partner efferent   compose всей лестницы + материал поля — не paste hub
```

**Связь с уже заложенным wire (не с нуля):**

| Рунг | В репо / design | Статус |
|------|-----------------|--------|
| L0–L2 | `L0_grapheme_cyrl`, `L1_syllable`, `L2_word`, `morph-role-ru` NCA, phrase W5–W7 (paradigm, modifier agreement) | **lab / literacy track** — правильное направление |
| L3 | `L3_phrase`, `phrases-*` lattices, phrase pilot corpus | **частично** — согласование прилагательного с существительным |
| L4–L5 | `ru.meta.discourse.from_text` (linkers), outline/thesis в design | **задумано**, partner path не дотягивает |
| «L6» shortcut | `ru.dialog.*` + `clause_1..3` = целые предложения | **анти-паттерн** — имя «clause», уровень **абзаца/реплики**, без compose снизу |

**Почему «красивый медведь» — эталон, а `clause_1` в `how_are_you` — нет:** в первом случае слоты — **роли и формы** (lemma + gender/number/case → surface); compose **порождает** строку, которой не было в KB. Во втором `clause_1` **уже** готовое предложение — compose деградировал в `paste`.

**Продуцирование новых слов** (приставка+корень+…): тот же принцип — KB хранит **морфемы и правила стыковки**, hot path **собирает**; не расширять лексикон только целыми `lang.word.*`, если форма выводима из paradigm lattice.

**Реализация подкачала — не идея:** смешали уровни (script hub вместо L3–L5), обошли лестницу оракулами, verify проверяет hub а не «собрано ли согласование». Исправление = **дотянуть wire до лестницы**, не отказ от слотов.

---

## Decision — откуда берётся «что сказать»

Partner-facing surface **рождается во взаимодействии**, а не выбирается из меню.

```text
partner turn
  → field / journal / limbic / character / thread (episode changes)
  → bind (evidence blocks, scores — NOT hub → canned line)
  → compose (lexicon + grammar + linkers + evidence phrases)
  → efferent text
  → lab: partner-voice invariants (0078) — class of forbidden speech, NOT mandated disclaimer strings
```

| Источник | Роль |
|----------|------|
| **Эпизод** (journal, prior turns, `focus_recent`, partner field overlap) | *о чём* и *в какой линии* |
| **Zones** (limbic, character, affect bias) | *тон и приор*, не готовая фраза |
| **KB лексика + грамматика** | *как сказать грамотно* |
| **Situations** (0057) | *когда* какой класс ответа уместен — **без** verbatim script |
| **Статичный `clause_*` на `ru.dialog.*`** | ❌ не источник partner surface |

**О состоянии:** субъект формулирует из **своего материала на поле** в контексте тёрна. Ограничения 0078 (no motive attribution, no over-reliance, no qualia ontology) — **проверки класса высказывания** в lab/probe, **не** обязательный текст «осторожно говорю, что чувствую…» в KB.

**Статичные данные** учат **способность** (слова, правила, ситуации) **только при выполнении developmental prerequisite** (см. § ниже). Они **не** подменяют **реплику** в конкретном диалоге.

---

## Decision — developmental prerequisite (текст ещё не «осознаётся»)

Оператор (2026-06-15): *статичный KB может чему-то научить только когда текст уже осознаётся и понимается — как книга; мы на этапе, когда текст даже не осознаётся.*

Это **ужесточает** ADR, а не отменяет compose-vs-script:

| Метафора | Когда работает | Что происходит на wire |
|----------|----------------|------------------------|
| **Книга / учебник** | субстрат уже **читает**: afferent → смысл → удержание → применение | `lang.word.*`, `ru.grammar.*` как **материал для bind**, после promote / practice |
| **Шкатулка / меню** | никогда как «обучение диалогу» | `clause_*` на `ru.dialog.*` — paste без прохождения смысла |
| **Среда (сейчас)** | **до** стадии осознанного текста | partner turn **меняет поле и эпизод**; efferent — **след** этого изменения, не цитата из JSON |

**Стадия (north star § duck test по стадиям, partnership stages §1):**

- **I — существование / привязанность:** ring и store переживают T; ответ не tabula rasa.
- **II — контакт / ранняя речь (мы здесь):** partner turn **меняет** efferent; anti-replay; speech act в bind — **не** «знает фразу из бандла».
- **III+:** нить, 0078, refusal из situations — **после** того как тёрн вообще **входит** в субстрат как событие, а не как триггер меню.

Пока **нет** пути «текст партнёра → значение на поле → влияние на efferent», добавление строк в bundle **не обучает** — ни `clause_1`, ни даже «честная» замена одной заготовки другой. Это как дать книгу тому, кто **ещё не читает**: символы есть, **опыта чтения** нет.

**Следствия для wire:**

1. **Приоритет не content-KB**, а **afferent integration**: journal, ring, `partner_field_overlap`, limbic delta, thread — чтобы тёрн **был событием**, а не substring → hub.
2. **Auto-curriculum / promote** — только claims, которые усиливают **движок смысла** (лексема, правило, situation-id), с held-out **field-composed** gate ([auto-curriculum plan](CASA-auto-curriculum-plan-v1.md) `stage_order`: extract → inference → …). Не наращивать dialogue scripts «для обучения речи».
3. **Plan A–style правки `clause_*`** — harm reduction на шкатулке; **не** прогресс по стадии II duck test.
4. **Критерий «научился»:** не «в бандле появилась фраза», а **на held-out** тот же класс ситуации даёт **разный** composed surface при **разном** эпизоде, без oracle/paste ([scratch emergence](CASA-scratch-emergence-conditions-dialogue-v1.md)).

**Одной строкой:** сначала **текст входит в жизнь** (поле, эпизод, зоны); только потом статичный KB — как **книга** для уже читающего субстрата. Сейчас лечить надо **вход**, не полки библиотеки.

---

## Anti-patterns (текущий wire — подлежит снятию)

| Anti-pattern | Почему это не «слоты» | Статус |
|--------------|------------------------|--------|
| `ru.dialog.affect` script hub | готовый дисклеймер вместо situational speech | **удалён** — compose из эпизода |
| `ru.dialog.how_are_you` с `clause_1` как фразой | ответ о состоянии = menu item | **migrated** — situation pieces |
| `clause_2` over-reliance в `thanks` | 0078 II violation | remove (симптом; причина — модель) |
| `bind_boost` → тот же hub → verify hub-prefix | self-fulfilling oracle | verify v2 (change plans E) |
| Auto-curriculum, генерирующий новые `clause_*` в canon | industrial-scale шкатулка | только lexical/rule claims + held-out gate |
| Python `_realize_*` на discourse path | oracle | remove (change plans A-B) |

**Симптомолечение:** правка текста в `clause_1` без смены модели **не** закрывает этот ADR. Допустимо только как временный harm reduction с явным `tech-debt` и датой снятия script layer.

---

## Wire — целевое состояние

### Bundle (`kb-lang-ru-grammar-dialog-v1` и наследники)

- **`lang.word.*`, `ru.grammar.*`** — остаются основой literacy.
- **`ru.dialog.*`** — только:
  - лексические пары (`stimulus` / `response` / `surface`);
  - **situation ids** + pieces (`hedge` / `predicate` / `scope` / `limit`) без `clause_*`;
  - meta / routing claims — не surface text.
- **Новые claims** с `clause_1..n` как полными предложениями на `ru.dialog.*` — **reject** в review и `validate_bundle`.

### Realizers

- `DialogBlockRealizer`: для `ru.dialog.*` **не** читать `clause_*` как efferent; только lexical pairs + situation compose + episode evidence.
- Состояние / affect / opinion: **compose** из `subject.*`, `journal`, limbic evidence + linkers — Plan D (`affect_scoring`, `situated.py`), thread carry (Plan C).

### Verify

- `verify_dialogue_thread` hub-prefix — **advisory** smoke, не duck test (уже в docstring).
- Merge-gate: session probes + 0078 invariants + anti-replay — **не** «выиграл заданный hub».

---

## Relation to other ADRs

| ADR | Связь |
|-----|--------|
| **0057** | curriculum = **ситуации**, не скрипты — этот ADR уточняет **формат данных** под то же решение |
| **0078** | инварианты = **классы запрета**; не легитимизируют bake-in disclaimer strings в KB |
| **0080** | impulse trace — инструмент отладки compose/bind, не оправдание script hubs |
| **North star** | duck test по **стадии**; script menu имитирует duck взрослого, не Stage II |
| **Partnership stages** | таблица §1 — gap «отклик на другого» закрывается **событием тёрна**, не dialogue menu |

---

## Consequences

### Positive

- Единый язык для review: «это script или слот?»
- Объясняет оператору и агентам, **почему** JSON-правки не дают «живого» диалога.
- Блокирует регресс через auto-curriculum и новые `clause_*`.

### Negative / cost

- Большая миграция bundle и тестов, завязанных на `clause_*`.
- Временный провал coverage, пока compose path не покроет thanks / how_are_you / ask_thought без scripts.
- Требует честного verify v2 — зелёный hub-smoke перестаёт успокаивать.

### Migration (рекомендованный порядок)

1. **Этот ADR** — normative; новый script-контент не добавлять.
2. **Oracle cleanup** (change plans A-B) — параллельно, не путать с причиной.
3. **Один speech-act pilot** — e.g. `thanks` только `stimulus`/`response` + compose; или `how_are_you` из journal/limbic без `clause_*`.
4. **Удалить** `ru.dialog.affect` script hub — situational compose + 0078 lab only.
5. **Grep gate** в CI: `ru.dialog.` + `clause_[0-9]` в bundle → fail (`validate_dialog_script_slots.py`).

---

## Track 2 — concept graph (Dima, `feat/conceptual-network`)

Параллельный трек, не блокирует снятие script layer на dialogue hot path:

- **Ветка:** `feat/conceptual-network` — POC `casa/curriculum/concept_net.py` («понятийная сеть»: `isa`, `affords`, `arg1/arg2`, `validate()` на поле).
- **Канон:** [CASA-ADR-0073-concept-layer-lexicalization.md](CASA-ADR-0073-concept-layer-lexicalization.md) § Concept Zone — `concept.*` языко-независимо, surface = лексикализация (`lang.word.*` / locale).
- **Стыковка с этим ADR:** L1–L3 compose оперирует **concept ids** + морф; partner efferent не хранит готовые `clause_*`. Glossary/translate в concept_net — мост к RU/EN surface.
- **Порядок merge:** после Track 1 (оракулы + lexical realizer); cherry-pick `concept_net` + glossary, не весь curriculum-capstone пакет целиком без review.

---

## Summary (one line)

**INVARIANT:** На уровне слов и предложений слоты — лексика и грамматика; partner surface **compose из эпизода**, не `clause_*` из JSON. **Стадия:** пока тёрн не осознаётся субстратом — статичный KB не «учит» (книга без чтения); приоритет — **вход текста в поле**, не меню реплик.
