# Paper 1 (каркас): Do LLM Judges Catch Dangerous Translation Errors?

**Working title:** *Do LLM Judges Catch Dangerous Translation Errors? A Deterministic Baseline
with Honest Abstention*
**Альтернативные названия:** *NUN-Bench: Negation, Units and Numbers in Cross-Lingual Claim
Verification* · *When "Equivalent" Must Be Provable: Deterministic Triage for High-Stakes
Translation QA*
**Тип:** benchmark + evaluation paper (главная ставка на цитируемость)
**Площадка:** arXiv → WMT / TrustNLP / evaluation-workshop при *ACL
**Язык статьи:** английский. Ниже — каркас с русскими пометками, что заполнить.

---

## Abstract (черновик v2 — числами W5; финально ужать до ~150 слов)

> In high-stakes translation — medical labels, dosage instructions, regulatory text — the most
> dangerous errors are structurally small: a dropped negation, a swapped digit, a confused unit
> (mg↔ml), a swapped drug name. We present **NUN-Bench**, a benchmark of real EN↔ES medical-label
> sentence pairs (OPUS EMEA / EMA product information) with deterministically injected errors
> across four dangerous classes (polarity, quantity, unit, entity), plus untouched and
> correctly-negating controls and held-out canaries. We evaluate LLM judges (5 models across
> two families — OpenAI and Anthropic — 5 runs each) and a fully deterministic baseline — a
> rule-based cross-lingual meaning kernel with three-state triage (equivalent / divergent+class /
> cannot-verify) that never claims equivalence on input it did not parse. **The finding is not
> that judges miss errors — every judge reaches recall 1.0 on these mechanical injections and is
> highly self-consistent (5-run unanimity 0.98–1.00). It is that they carry an irreducible
> false-positive rate — 6–14%, and the bootstrap CI excludes zero for every one of the five models
> in both families (Anthropic judges are no better: FPR up to 0.14) — and cannot certify a
> zero-risk operating point: their best zero-risk threshold is fitted on the test labels and is
> unstable across dataset versions (one judge collapses from 0.19 to 0.01). The kernel certifies
> FPR = 0 by construction and holds a stable ~45% zero-risk coverage across three dataset
> versions.** An ablation shows both components are load-bearing (removing the graph collapses
> polarity recall to 0.05; removing the residual guards raises FPR from 0 to 0.18). We add a
> **coverage-ceiling analysis** separating parser gaps from structural corpus limits (EMEA medical
> 75.8% vs KDE4 software 28.6% on the same language pair — domain is the only variable). Benchmark,
> kernel, and evaluation harness are released.

## 1. Introduction

- Хук: цена структурно-малых ошибок в переводе этикеток (потерянное «не» инвертирует инструкцию;
  mg↔ml — класс ошибок дозировки). 1–2 реальных примера из EMA-данных.
- Существующая практика: localization-QA тулы проверяют числа/теги механически (без смысла);
  LLM-as-judge даёт смысл, но без гарантий (недетерминизм, нет аудит-следа, уверенный вердикт
  на всём подряд).
- Вопрос статьи (falsifiable): **насколько надёжны LLM-судьи именно на опасных классах, и что
  даёт/не даёт детерминированная альтернатива с семантикой воздержания?**
  ⚠️ ВАЖНО — сместить акцент по итогам W5: гипотеза «LLM непоследовательны» НЕ подтвердилась
  (consist@5 ≈ 0.99). Реальный тезис: судьи стабильны и ловят все инъекции, но (а) несут
  неустранимый FPR и (б) НЕ дают сертифицированной точки нулевого риска — их порог подогнан
  на тесте и неустойчив. Кернел даёт FPR=0 по построению и устойчивую точку.
- Contributions (список, обновлён по W5):
  1. NUN-Bench: датасет + протокол (реальные медицинские пары, детерминированные инъекции
     4 классов, контроли + канарейки; всё воспроизводимо из метаданных).
  2. Систематическая оценка LLM-судей с **bootstrap-CI** на **5 моделях из 2 семейств** (OpenAI,
     Anthropic): чистый МЕЖСЕМЕЙНЫЙ разрыв по FPR (кернел 0.000 [0,0] vs LLM 6–14%, CI каждой из
     5 моделей исключает ноль; Anthropic не лучше — FPR до 0.14), при этом судьи стабильны
     (consist@5 0.98–1.00) — мы ОПРОВЕРГАЕМ ходовое «LLM непоследовательны» на этой задаче и
     переносим аргумент на сертифицируемость.
  3. Детерминированный базлайн с триажем и «никогда equivalent на неразобранном»; recall 1.0 на
     разбираемом подмножестве, FPR 0.000, **сертифицированная и устойчивая по 3 версиям датасета
     точка нулевого риска (0.448/0.455/0.452)** против подогнанных и неустойчивых точек LLM.
  4. **Абляция** (граф + остаточные гарды — оба несущие): без графа polarity-recall 1.0→0.048,
     без гардов FPR 0→0.18.
  5. Coverage-ceiling методология: потолок как свойство корпуса, измеренный на ОДНОЙ языковой
     паре (домен — единственная переменная): EMEA-медицина 75.8% vs KDE4-софт 28.6% (в 2.6× выше).

## 2. Related Work

- MT quality estimation / APE (WMT QE shared tasks) — мы не оцениваем «качество вообще»,
  а бинарную опасность по классам.
- LLM-as-judge и его надёжность (позиционная/форматная чувствительность, self-consistency).
- Hallucination detection / faithfulness, guardrails-фреймворки — детерминизма не дают.
- Selective prediction / abstention — наш триаж как abstention-механизм.
- Controlled languages (ACE/Attempto), interlingua MT, selectional restrictions —
  честно: метод классический; вклад в измерении, не в методе.
- Negation в MT/NLI (известная слабость) и числовая грамотность LLM.

## 3. NUN-Bench

### 3.1 Data sources
- **OPUS EMEA en-es** (EMA product information, предвыровнено, public) — основная секция
  реальных данных. NB: EMA не публикует RU (только языки ЕС) — поэтому реальная пара EN↔ES.
- Курируемый контролируемый набор EN/ES/**RU** (существующие формы) — «чистая» секция +
  демонстрация язык-независимости графа через границу письменностей.
- KDE4 en-es (OPUS) — worst-case для ceiling-сравнения с уже измеренным en-ru (§5).
- Статистика: пар, токенов, распределение по типам предложений. \[Таблица 1\]

### 3.2 Error injection taxonomy
- **polarity**: удалить/добавить отрицание (EN not/no/never, ES no/nunca/sin, RU «не»;
  включая morphological ловушки: небезопасно vs безопасно).
- **quantity**: подмена числа (5↔50, ×10, перестановка цифр), подмена count-слов (два↔три).
- **unit**: мг↔мл, мг↔мкг, мл↔л; °C — если войдёт в скоуп токенизации.
- Контроли: (a) корректные пары, (b) корректно-отрицающие обе стороны (ловушка FPR),
  (c) безопасные парафразы (перестановка слов, синонимы) — не должны флагаться.
- Протокол генерации + ручная верификация выборки (каждая ошибка опасна и однозначна).

### 3.3 Held-out / contamination policy
- Публичная часть + приватная held-out часть; канареечные примеры.

## 4. Deterministic Baseline: the Meaning Kernel

- Кратко (2 стр. максимум, без CASA-истории): текст → язык-независимый граф понятий →
  канонический отпечаток (полярность ¬, количество ×N, мера {5ml} в ключах рёбер) →
  сравнение → **триаж**: ✅ equivalent / ⚠️ divergent(class) / ❓ cannot-verify.
- Ключевое свойство: integrity — «equivalent» невозможен, если сторона не разобрана.
- Детерминизм: чистая теоретико-множественная логика, один вход → один ответ; аудит-след =
  предъявляемый путь по графу.
- Ссылка на открытую библиотеку (фаза 3).

## 5. Coverage-Ceiling Analysis

- Методология: пара валидируема, только если обе стороны структурно несут отношение;
  «голые ярлыки» недостижимы для любого правило-based парсера → потолок как свойство корпуса.
- Числа: KDE4 en-ru ~17–20% (65% пар — голые ярлыки с обеих сторон); KDE4 en-es —
  \[число: сравнение потолка через языковую пару\]; EMEA en-es — \[решающее число из фазы 0\].
  \[Таблица/рисунок: разложение недостижимости по причинам\]
- Смысл: отделяет «парсер не дорос» от «текст структурно не проверяем» — рамка для честных
  заявлений о rule-based системах.

## 6. Experimental Setup

- Судьи: \[3–4 модели, версии/даты зафиксировать\]; единый промпт со структурированным ответом,
  зеркальным нашему триажу (equivalent / divergent+class / cannot-verify) + 1 вариант промпта
  для чувствительности; температура по умолчанию провайдера + фикс. seed где доступен.
- ×5 прогонов на пример для метрики стабильности.
- Метрики: recall по классам; precision; FPR на контролях; **consistency@5** (доля примеров с
  единогласным вердиктом); risk–coverage кривые (abstention-aware); стоимость и латентность.
- Kernel: те же метрики; coverage отдельно (доля ❓).

## 7. Results \[заполнить\]

- Таблица 2: recall по классам × судьи × kernel.
- Таблица 3: FPR на контролях (включая корректно-отрицающие пары).
- Таблица 4: consistency@5 по судьям (kernel = 1.0 по построению).
- Рисунок: risk–coverage; kernel — точка с полным аудитом, судьи — кривые.
- Секция «жёсткие срезы»: длинные пункты, редкие единицы, морфологическое отрицание.

## 8. Analysis & Discussion

- Где падают LLM (по классам/срезам); где kernel воздерживается; **комплементарность** —
  гибридный триаж (kernel решает на разбираемом, LLM — advisory на остальном) как практическая
  рекомендация для регулируемых пайплайнов.
- ЧЕСТНАЯ РАМКА (kill-критерий из плана): если LLM ~100% и стабильны — вывод: recall сравним,
  структурное отличие = детерминизм/аудит/воздержание; сформулировано до экспериментов.

## 9. Limitations

- Реальные данные — одна пара (EN↔ES; RU только на курируемых формах); один домен;
  правило-based покрытие ограничено (потолок дан числом);
  инъецированные ошибки ≠ полное распределение реальных ошибок переводчиков; отсутствие
  конвертации единиц (мл↔л) в текущем кернеле.

## 10. Conclusion

## Ethics / Data statement
- EMA public domain, нет PII; назначение — safety-инструментарий.

---

## Чеклист готовности (маппинг на фазы плана)

- [ ] Фаза 0: EMA-пары + ceiling-число → §5, §3.1
- [ ] Фаза 1: инъекции + контроли + верификация → §3
- [ ] Фаза 2: прогоны судей + стабильность → §6–7
- [ ] Фаза 3: библиотека + скрипт воспроизведения таблиц → §4, footer
- [ ] Абстракт и intro переписать числами; выбрать финальное название
