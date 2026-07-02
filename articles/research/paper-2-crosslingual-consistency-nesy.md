# Paper 2 (каркас): Cross-Lingual Consistency Checking with Proof Trees

**Working title:** *Rules in Russian, Facts in English: Deterministic Cross-Lingual Consistency
Checking with Proof Trees from Controlled Natural Language*
**Альтернативные названия:** *Auditable Consistency over Cross-Lingual Claims* · *A Small
Deterministic Inference Engine over a Language-Independent Concept Graph*
**Тип:** system/method paper (меньшая, «авторская» статья; идея понятийной сети — Дмитрия)
**Площадка:** NeSy / CNL / reasoning-workshop при *ACL; arXiv в любом случае
**Зависимость:** ссылается на библиотеку и (желательно) на статью 1; может писаться параллельно
фазе 4. Язык статьи — английский; ниже русские пометки.

---

## Abstract (черновик)

> Business-rule engines check facts against rules, but require formal input. LLMs accept natural
> language, but provide no guarantees: verdicts vary across runs and cannot be audited. We present
> a small deterministic inference engine that accepts **facts and rules in controlled natural
> language across two languages** (rules in Russian may govern facts in English and vice versa),
> compiles them into a language-independent concept graph with a canonical situation fingerprint,
> and detects violations by forward chaining with **full proof trees back to given facts**.
> Contradiction detection covers the dangerous claim classes — polarity, quantity, measurement
> unit — plus functional relations, antonymous state mutexes, and incompatible numeric ranges;
> numeric antecedents are triggered by any entailing value (a dose of 15 ml fires "if the dose
> exceeds 10 ml…"). The system never treats unparsed input as consistent. \[Пример-нарушение
> с proof-tree в одну строку.\] We discuss the honest scope of such kernels and their role as
> deterministic guards beside LLM pipelines.

## 1. Introduction

- Хук: «если файл открыт → кнопка активна» по-русски + факты по-английски → доказуемое
  нарушение с цепочкой. Или сразу медицинский кейс (см. §6): правило дозировки + факты этикетки.
- Ниша между двумя мирами: rule-движки (Drools/OPA — формальный вход) и LLM (естественный язык —
  без гарантий). Наш вход: контролируемый естественный язык, **кросс-язычно**.
- Contributions:
  1. Кросс-язычный CNL-вход для фактов И правил (включая многоусловные «если X и Y, то Z»).
  2. Детерминированная непротиворечивость: кернел опасных классов + мьютексы состояний +
     числовые интервалы + пороговое влечение в антецедентах.
  3. Forward chaining c полным провенансом: proof-tree до «given» фактов (аудит-след).
  4. Семантика честности: unknown/unparsed никогда не считается согласованным.

## 2. Related Work

- CNL: Attempto/ACE, PENG — одноязычные; наш вход двуязычный через язык-независимый граф.
- Rule engines / production systems (RETE), OWL/DL-ризонеры — формальный вход.
- NLI (natural language inference) — статистическое, без гарантий/аудита.
- NeSy-системы; LLM+solver гибриды (LLM переводит в логику — детерминизм только после перевода;
  наша параллель со статьёй 1).

## 3. The Concept Graph and Situation Fingerprint

- Кратко: онтология isa/affords/селективные ограничения; парсинг клауз; канонические рёбра
  с полярностью/количеством/мерой; containment = следование (консервативно, без
  attribute-specialization — объяснить почему).
- Предикативные состояния: has_state как одноместный предикат; антонимные мьютексы.

## 4. Rules and Inference

- `parse_rule`: «если X, то Y» / "if X then Y"; конъюнкция сторон (`split_conditions` —
  правило разделения: сплит только когда каждый фрагмент сам парсится; показать пример
  внутриклаузной координации, которая НЕ разделяется).
- `check_against_rules`: violated / satisfied / fired_unknown / inactive / unparsed_rule.
- Пороговое влечение в антецеденте: «=15ml» удовлетворяет «>10ml»; «>12» влечёт «>10»;
  единицы обязаны совпадать; провенанс указывает на факт-значение.
- `forward_chain`: замыкание, многошаговые нарушения (пример, где прямая проверка слепа);
  монотонность → терминация.
- `explain` / proof trees: формат `has_state(button,active) ⇐ rule ← … ·given`.

## 5. Determinism and Honest Scope

- Гарантии: один вход → один вердикт; каждое нарушение — предъявляемая цепочка.
- Границы (не прятать, это селлинг-поинт честности): покрытие = парсер; локатив не функционален
  («на столе» vs «на полке» — независимы); мьютексы не исчерпывающи; нет конвертации единиц
  (или уже есть — если сделаем к моменту написания); нет defeasible-правил.

## 6. Case Study \[выбрать один, сделать хорошо\]

- **Вариант A (сильнее):** правила дозировки/противопоказаний как CNL-правила (RU) + факты из
  реальной EN-этикетки → нарушения с proof-trees. Требует мини-онтологию домена (пересекается
  с фазой 0–1 статьи 1).
- **Вариант B (дешевле):** софт/UI домен — уже работает (reason-demo), но менее убедителен
  для рецензента.
- Метрики кейса: N правил, M фактов, все вердикты воспроизводимы, время выполнения.

## 7. Evaluation

- Курируемый тест-набор (наши 61+ тестов как основа): по типу нарушения × кросс-язычность ×
  многошаговость. Таблица: какой класс каким механизмом ловится.
- Ablation: без forward-chaining (сколько нарушений теряется), без порогового влечения,
  без мьютексов.
- Сравнение с LLM на том же наборе (маленькое, ссылка на статью 1 за методологией).

## 8. Limitations & Future Work

- Defeasible-правила («обычно Y, но если Z…»), конвертация единиц, третий язык
  (граф язык-независим — проверка тезиса), индукция онтологии.

## 9. Conclusion

---

## Чеклист готовности

- [ ] Выбрать кейс (§6): медицинский требует мини-онтологию — решается после фазы 0
- [ ] Конвертация единиц мл↔л — маленькое расширение, усиливает §5 и кейс
- [ ] Таблица механизмов × классов нарушений из существующих тестов
- [ ] Ablation-скрипты
- [ ] Согласовать авторов с командой до текста
