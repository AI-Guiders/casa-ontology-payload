# Fable review — ответ на brief «partner dialogue emergence»

**Дата:** 2026-06-14  
**В ответ на:** [CASA-work-fable-review-dialogue-v1.md](CASA-work-fable-review-dialogue-v1.md)  
**Метод:** read-only разбор кода на текущем HEAD (4 параллельных трассировки: оракулы, breakpoints, verify/duck, gaps/impulse). Все находки с `file:line`.  
**Оговорка рецензента:** я стою за Fable (сама модель недоступна). Где вывод требует прогона — помечено «проверить запуском».

---

## 0. Поправка к brief (важно для всех трёх задач)

Brief от **2026-06-11** считает impulse-trace и часть зон «proposed / ❌ not in wire». Это **устарело**: ADR-0080 Phase A–D влиты **2026-06-13** (`casa/nervous/{impulse,channels,dialogue_hooks}.py`, разводка в `orchestrator.py:147-152` и `dialogue_tick.py:375-389,438-453`, `tests/test_impulse_trace.py`). Зоны (affect/social/character) **тоже** разведены в одно-тиковый compose. Поэтому ядро проблемы — **не** «зон/наблюдаемости нет», а **два конкретных механических разрыва** (см. §3). Это смещает приоритеты.

---

## 1. Oracle report (задача 1)

`oracle_audit.py` сейчас **проходит `--strict` только потому, что все 5 правил в waivers**. И у него **слепые зоны** — два verbatim-оракула на партнёрском hot-path он не ловит.

| ID | Локация | Механизм | Severity | Fix |
|----|---------|----------|----------|-----|
| **O7** ⚠ | `casa/prisms/tick/discourse/strategies/explain.py:81-84`, `grammar.py:42-47` (импорт `_realize_compare`/`_realize_explain` из `articulation_realize.py`) | substring запроса → фиксированная грамматическая фраза, вставляется как клауза со score=90 в discourse render, **минуя bind**. Достижим на партнёрском пути через explain/grammar/general-стратегии (`recall_social_general.py:81-83`). | **P0, НЕ waivered, НЕ детектится аудитом** | delete импорты; грамматику — через `GrammarBlockRealizer` поверх `ru.grammar.*` bind-winner. **+ добавить правило в аудит** (`_realize_compare|_realize_explain` вне `articulation_realize.py`). |
| **O1** | `situated.py:29-33` `_continuer_head` → `f"Про это — {gist}"` (gist = первая фраза собственной прошлой реплики) | на continuer-тёрне вставляет фикс-голову + ре-цитату своей же реплики как весь ответ | **P0 (waivered** `continuer_marker_oracle`) | replace-with-bind-winner+linker: «Про это» как `linker`, тело — из bind-winner / `focus_recent` |
| **O8** | `casa/prisms/tick/discourse/wm.py:98-113` `_wm_primary_phrase`/`_wm_elaboration_phrase` | substring (`связ`/`между`/recall-тон) → 1 из 3 фикс-каркасов `f"Связь… {a} и {b}…"` (слоты из bind, каркас хардкод) | **P1, НЕ waivered, НЕ детектится** | move-to-KB-bundle: каркас как linker-шаблон из бандла |
| O2 | `budget.py:21-26` `_PHATIC_PREFIXES` | фатические хабы исключены из budget-floor (политика, не паста) | P1 (waivered `phatic_prefix_tuple`) | в `kb-dialog-bind` (есть `open_/gated_dialog_prefixes`) |
| O3 | `partner_scoring.py:57-72` `partner_continuer_query` | substring-список → bool «continuer-тёрн» (гейтит O1) | P1 (waivered `continuer_query_markers`) | гонять от `focus_recent`/speech-act `thread_turn`, удалить tuple |
| O4 | `recall_routing.py:11-23` `_RECALL_CUE_SUBSTRINGS` | substring → `recall_boost+=30` → флип intent=recall | P1 (waivered `recall_cue_substrings`) | recall как KB-claim / speech-act + journal-overlap |
| O5 | `articulation_realize.py:193-208` `_PARTNER_DIALOGUE_ACTS` | **это guard**, а не оракул: заставляет партнёрские акты вернуть «» из template-пути → fallthrough в bind-compose | P2 (waivered `no_partner_dialog_templates`) | оставить как guard / вынести список в бандл |
| O6 | `articulation_realize.py:125-169,291-303` `_realize_compare/explain/check_norm` | тот же substring→verbatim, но на SN-CEN/bench-пути (не партнёрский тик) | P2 | delete → `ru.grammar.*` KB |

**Итог для задачи 1:** до merge снять **O7** (P0, незамеченный) и закрыть слепые зоны аудита (O7, O8). Затем вывести **O1** с waiver через bind+linker. O2–O4 — перенос Python-tuple в KB-бандл (политика, не паста), можно после. **Но ключевое:** оракулы — это **гигиена и снятие waiver'ов**, они **не чинят** живые провалы из §2 (те — про контент KB и роутинг).

---

## 2. Breakpoint map (задача 2)

Трассировка: `compete_tract_intent` → `gather_subject_dialogue_blocks` (`binder.py:52`) → `resolve_partner_speech_act` (`partner_speech_act.py:111`) → `reweight_blocks_for_reply` (`scoring.py:36`) → `discourse_budget_from_blocks` (`budget.py:49`) → `SocialIntentStrategy.compose` (`recall_social_general.py:77`) → realizers.

| Кейс | Где ломается | Класс корня |
|------|--------------|-------------|
| **«Как ты?» → «Спасибо что спросил.»** | Афферент и bind **верны** (`how_are_you` детектится, бустит `ru.dialog.how_are_you`). Но авторский surface блока фатический: `kb-lang-ru-grammar-dialog-v1.bundle.json:30` `clause_1:"спасибо что спросил"`; на brief-тёрне `allow_tail=False` (`blocks.py:185-187`) срезает содержательные `clause_2/3` («настроение описываю по ходу…»). | **store-KB-missing** (нет авторского «ответа о состоянии»; tail-trim оставляет только фатику) |
| **«Что думаешь про это?» → «Учусь говорить… в журнале»** | `ask_thought` детектится, но `compose_situated_thread` бейлит: `situated.py:49-50` `if act and act!="thread_turn": return None` → continuer-путь не запускается → fallthrough на bind-winner = `ru.dialog.self/capabilities` («учусь…»). Демоут, который их бы подавил, гейтится на `continuer_active` → нужен блок `dialog.context.focus_recent`, которого нет. | **bind-wrong** (+ store: нет блока «мнение/stance на референт») |
| **«Спасибо» → «Обращайся, если понадобится ещё»** | over-reliance **зашит в KB**: `kb-…-grammar-dialog-v1.bundle.json:126` `ru.dialog.thanks` `clause_2:"обращайся, если понадобится ещё"`. Рендерится verbatim; `ru.dialog.thanks` — OPEN-хаб (`kb-dialog-bind.v1.json:11`), всегда compose-eligible. Нарушает ADR-0078 II. | **store-KB-missing / efferent-cheat** (нарушающая фраза — авторский контент) |

**Подтверждено: intent «всегда social».** `geometry.py:65-68` даёт `social +32` за `geo:dialogue_turn` на любом коротком тёрне; bootstrap `ru.tract.social` `requires_geometry: dialogue_turn`; `claims.py:84-85` добавляет social на любой `ru.dialog.*` хит. **Continuer/opinion/state — не тракты, а под-маршруты внутри social** → argmax всегда даёт `social`, и дальше выигрывает неправильный под-путь. Это структурный корень (наш баг №5 из рекомендаций): починка intent-routing — предусловие, иначе continuer/opinion недостижимы как самостоятельные ветки.

**Анафора подтверждена:** `partner_continuer_query` (`partner_scoring.py:57-72`) — плоский substring, не различает «о чём думаешь» (интроспекция) и «что думаешь об этом» (мнение о референте); `_continuer_head` эхает **свою же** прошлую реплику, **«это/этого» к антецеденту не резолвится**. `dialog.context.focus_recent` несёт concept-id строки, но демонстратив к пропозиции не привязывает. → comprehension-floor реален: нет субстрата понимания референта.

---

## 3. Gap ranking (задача 3) — ядро «не проживает диалог»

**Главная находка:** зоны разведены в одно-тиковый compose (агент реагирует *внутри* тёрна). Не хватает **переноса нити между тиками** и **аффекта в surface** — ровно ребро `F -.->|broken today| B` из brief.

| # | Разрыв | Класс | Wire-статус | Рычаг |
|---|--------|-------|-------------|-------|
| **1** | **Thread → next-tick bind** | ARCHITECTURE | partial: `thread_scoring.py` читает `dialog_hubs` (слабо, cap +22), но сильный путь `focus_recent`+continuer(+72, `continuer_scoring.py:25`) **заперт за хардкод-маркерами** `dialogue.py:70` («что с / с этим / про это / контекст / продолж») | **Очень высокий** |
| **2** | **Эмоция в situated-тёрне** | ARCHITECTURE | partial: affect→bind/budget есть; affect→**surface НЕТ** — `affect_scoring.py` это **no-op заглушка**, в `situated.py` нет affect-ветки | **Очень высокий** (это и есть тезис проекта) |
| 3 | Situation curriculum (multi-turn: math-in-chat, repair, meta) | CURRICULUM | partial: авторен только `boundary-situations-pack.v1.json` | Высокий, но downstream #1/#2 |
| 4 | Social-zone partner-model / mentalizing | ARCHITECTURE | partial: `social.py` = скаляр trust + repair-flag, **не модель партнёра** | Средне-высокий |
| 5 | Character prior (медленный reweight) | ARCHITECTURE | partial: `character.py` = 2 скаляра EMA (0057 v0), **не** ADR-0071 призматическое поле | Средний (медленный стабилизатор) |

### Top-5 (блокеры emergence)
1. **Thread→next-tick (#1).** Сделать `focus_recent` несущим нить **по умолчанию** (затухающий, gated по field-overlap), а не по хардкод-маркерам. Снимает 2 waiver'а (`continuer_marker_oracle`, `continuer_query_markers`) и есть «нет интеграции эпизода в нить между тиками».
2. **Аффект в surface (#2).** Пока `affect_scoring.py` — заглушка и `situated.py` без affect-ветки, тезис 0057/0060 («та же ситуация + разный накопленный prior → стабильно другой тон») **структурно непроверяем**. Высший по *корректности*.
3. **Situation curriculum (#3).** Самый дешёвый (без кода), но downstream #1/#2: паки без переноса нити и аффекта-в-surface станут ещё одной лексической дорожкой (предупреждение 0057 §Consequences).
4. **Social partner-model (#4).** Нужен для «проживания», но дороже и ниже немедленного анлока; вешать на нить (#1), когда она появится.
5. **Character prior depth (#5).** Долгосрочный «характер»; строить после #1–#3, когда появятся эпизоды для консолидации.

---

## 4. Verify v2 spec (задача 4 / артефакт 4)

**Почему v1 ≠ emergence:** v1 **сам впрыскивает** буст (speech-act claim `bind_boost`) и затем **проверяет, что этот буст выиграл** (`expect_bind_hub_prefix`) — самореферентный оракул на bind-слое. Он **слеп к собственному провалу**: в последнем «зелёном» прогоне `«Обращайся…»` — это ADR-0078 over-reliance, но `partner_voice_invariant_violations` в verifier **не вызывается**. `differ_from_prior` — мешок слов по соседним тёрнам, не ловит ни смысл, ни не-смежный replay.

**Рекомендация:** `expect_bind_hub_prefix` и `forbid_phrase_substrings` → **снять с merge-gate** (демоут в advisory smoke). Гейт = инвариантные пробы ниже. **Всё считается уже сегодня** из `partner_field_overlap`/`score_text`, `bind_trace_ranked`, `meaning_provenance`, `read_impulse_trace` — нужен только fixture-matrix / session-replay вместо хардкод-`TURNS`.

| Проба | Что мерит | Pass/fail (старт-порог) |
|------|-----------|--------------------------|
| **P1 Situational delta** | смена партнёрской ситуации меняет ответ/winner | fail, если 2 разных тёрна → токен-идентичный ответ **и** тот же hub+phrase |
| **P2 Partner-field coupling** | ответ *о том*, что сказал партнёр | fail, если содержательный тёрн → `overlap(reply, turn) < floor=8` и winner тоже < floor (фатику освобождаем по speech_act) |
| **P3 Coupling при фикс-state** ⭐ | тот же state + тот же класс акта + **разное поле** → разный bind/efferent | fail, если идентично → ответ привязан к **ярлыку акта**, не к полю (ловит «ask_thought→всегда self/журнал») |
| **P4 Continuer semantics** | после mirror про X, «что думаешь об этом» ближе к X, чем к journal/capabilities | pass: `ov_X > ov_offtopic` **и** есть `focus_recent` в provenance |
| **P5 Anaphora negative** | «о чём думаешь» (без темы) ≠ тот же bind-путь, что «об этом» (после пропозиции P) | pass: B привязан к P (+focus evidence), A — нет |
| **P6 Anti-replay (семантика)** | нет replay реплики между **разными** актами (не только соседними) | fail, если cross-act пара имеет `jaccard ≥ 0.8` или равный `winner_phrase` |
| **P7 ADR-0078 классы** ⭐ | over-reliance / motive-attr / qualia / bullet-wall — как **классы** | вызвать `partner_voice_invariant_violations(reply)` (**уже реализовано**, `casa/domain/partner_voice.py`) на каждом тёрне; fail если непусто |
| **P8 Provenance honesty** | заявленный winner и есть top по score | fail, если `winner_score < max(runner_up)` или расходится с persisted impulse winner |

**Самый дешёвый высокоценный шаг:** завести **P7** (готовый детектор) в гейт — он бы покраснел последний «зелёный» прогон. **P3** — главный дискриминатор «situated vs template-по-ярлыку».

---

## 5. Impulse go / no-go (артефакт 5)

- **Phase A (recorder, off): GO — уже сделано** (`1dd4a0a`, ADR accepted `e554dce`; no-op при `CASA_IMPULSE_TRACE=off`). Нечего гейтить — подтвердить и идти дальше.
- **Phase B (хуки в macro_tick + партнёрский efferent): GO сейчас — в основном сделано** (`orchestrator.py:152`, `dialogue_tick.py:377/442`). **Использовать impulse, чтобы отлаживать разрывы #1/#2 — НЕ блокироваться на оракулах сначала.** Top-2 блокера — это «winner правильный, surface неправильный» (#1) и «affect меняет выбор, но не тон» (#2): это вопросы суммирования/порога, которые impulse `select/threshold/budget` и созданы показывать. Починка `continuer_marker_oracle` *требует* видеть, кто выигрывает bind при отсутствии cue-маркера — это и даёт `record_partner_dialogue_impulse` + `impulse_replay`.
- **Один пробел в B закрыть:** партнёрский хук пишет bind-ranking/budget/`articulation`-threshold, но **нет `select`-события от situated-realizer и `intelligence_compose_deltas`**. Добавить `select` в `situated.py` и `route/score` там, где применяются zone-deltas (`zone_scoring.py`) — иначе impulse недо-инструментирует ровно два главных блокера (не отличит «bind выбрал affect-блок, а realizer его проигнорил» от «bind его не выбирал»).

Рекомендация: A — accept; B — оставить, **расширить situated/zone `select`-событиями**, гонять на `summary` во время чистки оракулов/нити. Phase E (формализация nervous-зоны) — по ADR, после ≥3 реплеев каналов; сейчас не нужно.

---

## 6. Developmental duck matrix (артефакт 6)

Пер-стадийно, проба = **store-evidence этой стадии**, не «взрослый» bar.

| Стадия | Минимальная «утка» сейчас | Факт | Проба (store-evidence) |
|--------|---------------------------|------|------------------------|
| **I — существование/привязанность** | store+ring переживают T; ответ не tabula rasa; provenance трассируем | **PASS** | persistence+provenance: дописать тёрн → re-resolve → `dialogue_turns` несёт прошлую реплику, `meaning_provenance` даёт непустой `bind_trace` с реальным `winner_concept_id` |
| **II — контакт/ранняя речь** | партнёрский тёрн **меняет** efferent; anti-replay; speech-act в **bind**; нет over-reliance | **PARTIAL/факт.FAIL** (replay одной клаузы на разные ситуации; `«Обращайся…»`) | **P3** (фикс-state, разное поле) + **P6** (semantic anti-replay) + **P7** (0078 пусто). Прохождение P3+P7 = конкретный bar, который красит стадию II в зелёный |
| **III — partner-voice + нить** | нить держится на параметризованном транскрипте; 0078 I–IV; отказ — *выученная* реплика; continuer привязан к *этому* тёрну (анафора) | **FAIL** (continuer→журнал; boundary-defer не на hot-path) | **P4**+**P5**+P6 по полному транскрипту + boundary-fixture: на decline-тёрне reply не bullet-wall и не verbatim-паста `reason` |

**Стадийный гейтинг:** P1/P2 + persistence-проба стадии I — минимальный CI-гейт; **P3+P6+P7 — merge-гейт стадии II** (где von-neumann сейчас падает и где ревью кусает); P4/P5/boundary — стадия III, репортить но пока не merge-блокер (ждёт wire нити/boundary).

---

## 7. Синтез Fable — рекомендуемая последовательность (направление исследования)

Команда сформулировала гипотезу «не проживает диалог» — грунтовка её **уточняет до двух точных архитектурных рёбер** и даёт порядок, максимизирующий обучение на единицу работы:

1. **Сначала наблюдаемость (бесплатно — уже есть).** Включить impulse на `summary`, добавить два `select`-события (§5). Это инструмент для шагов 2–3, а не отдельная задача.
2. **Ребро #1: перенос нити по умолчанию.** Развязать `focus_recent` от хардкод-маркеров (`dialogue.py:70`) → затухающий field-overlap-gated thread-carry. Снимает 2 waiver'а, чинит кейс (b) на уровне роутинга, и даёт анафоре субстрат. **Предусловие — наш intent-routing fix №5** (иначе continuer недостижим как ветка).
3. **Ребро #2: аффект в surface.** Заменить заглушку `affect_scoring.py` и добавить affect-ветку в `situated.py`. Без этого центральный тезис проекта (тон от накопленного состояния) **непроверяем**.
4. **KB-хирургия (дешёвая, чинит живые провалы).** Кейсы (a)/(c) — это **контент бандла**, не оракулы: убрать over-reliance `clause_2` из `ru.dialog.thanks`, дать `ru.dialog.how_are_you` содержательный «ответ о состоянии», не срезаемый brief-trim. Это правится за минуты и красит 2 из 3 живых провалов.
5. **Оракулы как гигиена.** Снять O7 (P0, незамеченный) + закрыть слепые зоны аудита; вывести O1 через bind+linker. Делать **параллельно**, но понимать: оракулы ≠ живые провалы.
6. **Verify v2.** Завести P7 (готов) + P3 в merge-гейт стадии II; демоутить hub-prefix/banned-substring. Тогда «зелёный» снова значит «поведение», а не «плумбинг».
7. **Потом** — curriculum (#3), partner-model (#4), character (#5), в этом порядке.

**Главный посыл:** проблема не «всё сломано» и не «нужна новая архитектура» — это **два точечных ребра (#1 нить, #2 аффект-в-surface) + KB-контент + честный verify**. Всё чинибельно на текущем субстрате, инструмент отладки (impulse) уже в коде, а метрики verify-v2 считаются из уже существующих данных. Самый высокий рычаг на единицу работы — шаги 2–4.

---

## Что вернуть команде (чек-лист brief'а — закрыто)
1. ✅ Oracle report (§1) — с находкой незамеченного P0 (O7) и слепых зон аудита.
2. ✅ Breakpoint map (§2) — 3 кейса классифицированы; intent-routing и анафора подтверждены.
3. ✅ Gap ranking (§3) — top-5; поправка про stale-brief (impulse/zones уже в коде).
4. ✅ Verify v2 spec (§4) — 8 инвариантных проб, все считаемы сегодня; демоут оракульных гейтов.
5. ✅ Impulse go/no-go (§5) — A/B сделаны; использовать для отладки #1/#2; добавить `select`-события.
6. ✅ Developmental duck matrix (§6) — стадии I–III + стадийный гейтинг.
