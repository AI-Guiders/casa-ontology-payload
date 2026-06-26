# CASA partner-dialogue — планы изменений для агентов (v1)

**Дата:** 2026-06-14  
**В связке с:** [CASA-work-fable-review-dialogue-v1.md](CASA-work-fable-review-dialogue-v1.md), [CASA-fable-review-dialogue-response-v1.md](CASA-fable-review-dialogue-response-v1.md), [CASA-ADR-0081-lexical-slots-not-utterance-scripts.md](CASA-ADR-0081-lexical-slots-not-utterance-scripts.md) (норматив: слоты ≠ готовые реплики)  
**Метод:** каждый план составлен архитектурным агентом с **прогоном кода** (не по памяти); все правки с `file:line`, ключевые фиксы проверены в памяти.

## Как пользоваться
Пять самостоятельных планов, каждый можно отдать отдельному агенту. У каждого: цель+критерии приёмки, дизайн, пошаговые правки (`file → function`), соответствие философии (no-oracle / no-LLM / bind-driven), тесты, риски/откат, оценка трудозатрат, критические файлы. Внизу — граф зависимостей и рекомендованный порядок.

## Поправки из заземления (важно — меняют рамку brief'а)
1. **«Always social» — это не «тройной перебой», а `social=32` без конкурентов.** Для короткого тёрна, не являющегося math-глифом/грамматикой и без `что такое/объясни`, `compete_tract_intent` возвращает `social=32` и **ничего не competes**. Суб-роутер speech-act (`how_are_you`/`ask_thought`/`mirror_ack`/greeting) **уже работает верно** через `ru.speech_act.partner.*` bind-дельты. → План B чинит **макро-intent floor**, а не суб-роут.
2. **Тест/прод-расхождение скрывает баг:** соц-тесты гоняют `compose_mode="social"`, который **минует competition** (`binder.py:102`). Поэтому макро-intent регрессия невидима в текущем suite. План B добавляет прод-путь (`compose_mode=None`) кейсы.
3. **Живые провалы — это КОНТЕНТ бандла**, читается на лету (`load_store_bundles`) — **ре-ингест/rebuild не нужен**, чинится правкой JSON за минуты (План A, Track A).
4. **Сопутствующий баг `GrammarBlockRealizer`** (`blocks.py:253-258`): дубль-петля `«Например {fragment}»` → `"Например надеть. Например одеть."`. Удаление оракула O7 **без** фикса реализатора уронит качество грамматики → B2 в Плане A **обязателен** вместе с B1.
5. **Impulse (ADR-0080) уже влит** (Phase A–D, 13 июня) — brief устарел; используем для отладки, добавляем `select`-события (Планы C/D).
6. **ADR-0081:** правка текста в `clause_*` (План A Track A) — **временное harm reduction**, не целевое состояние. Цель — compose из эпизода + лексика/грамматика; `ru.dialog.*` с полными предложениями в слотах — script layer подлежит снятию.

## Граф зависимостей и порядок
```
A (honest surface)  ── независим, самый дешёвый, чинит 2/3 живых провала ──► делать ПЕРВЫМ
   └─ Track A (KB)        ~2-3 ч
   └─ Track B (oracle+realizer) ~4-6 ч   ── снимает P0-оракул O7

B (intent routing)  ── ПРЕДУСЛОВИЕ для C; делает content/continuer/opinion достижимыми ── ~0.5-1 д

C (thread carry)    ── зависит от B (soft); ретайрит оракулы O1/O3 ── ~1.5-2.5 д

D (affect→surface)  ── тезис-критичный; независим, но выигрывает от impulse select ── ~3.5 д

E (verify v2)       ── ранний частичный (P7-wire) ценен сразу; полный harness ── ~3.5 д
```
**Рекомендованный порядок по рычагу/стоимости:** **A** (KB-хирургия + O7) → **E-частично** (завести P7 в гейт — дёшево, ловит over-reliance класс) → **B** (intent routing) → **C** (thread carry) → **D** (affect→surface) → **E-полно** (harness).

| План | Аспект | Класс | Трудозатраты | Зависимость |
|------|--------|-------|--------------|-------------|
| A | Honest surface (KB + oracle cleanup) | content + code | ~1 день | нет |
| B | Intent routing (макро-floor) | code | ~0.5-1 день | нет (предусловие для C) |
| C | Thread carry by default | code | ~1.5-2.5 дня | B (soft) |
| D | Affect → surface | code + data | ~3.5 дня | нет (impulse желателен) |
| E | Verify v2 (invariant gate) | code + tests | ~3.5 дня (P7-wire ~0.5д) | нет |

---

# ПЛАН A — Honest surface: KB-хирургия + oracle cleanup

**Цель:** сделать авторский surface честным (no over-reliance, реальные ответы о состоянии/мнении) + убрать незамеченный verbatim-оракул и захардить аудит. Чинит 2/3 живых провала **сразу** (контент бандла читается на лету — ре-ингест не нужен). Две независимые под-дорожки: **Track A = JSON-авторинг**, **Track B = Python-удаление+аудит**.

## Track A — KB content (файл `agents/von-neumann/bundles/kb-lang-ru-grammar-dialog-v1.bundle.json`)
- **A1. `ru.dialog.thanks` (:118-129):** удалить `clause_2`/`linker_2` (over-reliance «обращайся, если понадобится ещё»), оставить `slots: {stimulus:"спасибо", response:"пожалуйста", word:"спасибо"}`. Без `clause_*` хаб не сплитуется (`utterance_materialize`), реализатор отдаёт `response` → **«Пожалуйста.»** (проверено: 0078-clean).
- **A2. `ru.dialog.how_are_you` (:24-36):** заменить фатический `clause_1`(«спасибо что спросил») на содержательный `clause_1:"настроение опишу по ходу разговора, не угадываю наперёд"` + `clause_2:"если что-то меняется — скажу"`, `linker_2:"и"`. (Это **не** brief-trim — проблема в порядке выбора: `_compose_social_dialog_from_bind` берёт первый вариант хаба.) Не вводить qualia-формулировок (`test_sveta_repl_transcript` запрещает «настроение по-человечески не чувствую»).
- **A3. Новый хаб `ru.dialog.ask_thought`** (мнение/stance): (a) добавить claim с `clause_1:"своё мнение скажу по тому, что есть на поле, а не наугад"`, `clause_2:"если опоры мало — так и скажу, выдумывать не буду"`; (b) в `design/kb-partner-speech-acts.v1.json` `ask_thought` (:71-82) переписать `route_hints`/`bind_boost`, чтобы новый хаб бил `ru.dialog.self` (self 34→20, ask_thought:46). Проверено: «Что думаешь?»/«А что ты думаешь?» → честная позиция.
- **A4. Починить фикстуры тестов**, в которые зашит over-reliance: `tests/test_subject_articulation_emergent.py::test_thanks_builds_connected_discourse` (:64-84) — заменить fixture `clause_2` на нейтральный хвост (проверить, что не триггерит `_OVER_RELIANCE_MARKERS`) и обновить 2 assert'а.

## Track B — oracle cleanup + audit (Python)
- **B1. Убрать O7** (P0, незамеченный): в `casa/prisms/tick/discourse/strategies/explain.py` (импорт :5, fallback :81-84) и `grammar.py` (:5, :42-47) удалить импорт/вызов `_realize_compare`/`_realize_explain`. Грамматика идёт через `GrammarBlockRealizer` поверх `ru.grammar.*` bind-winner. (Определения в `articulation_realize.py` **оставить** — их использует CEN-путь `compose_answer_text`/`sn_cen_runtime.py:600`, не партнёрский.)
- **B2. (ОБЯЗАТЕЛЬНО с B1) Починить `GrammarBlockRealizer`** (`blocks.py:237-259`): убрать/жёстко загейтить дубль-петлю quoted-fragment (:253-258), дающую «Например надеть. Например одеть.» `atom.headline` уже несёт исправленную форму → ответ «Согласно приказу (дательный падеж).» из bind-winner.
- **B3. O8 (`wm.py:98-113`)** — вынести 4 фикс-каркаса в data-claim (`ru.meta.wm.carriers`, плейсхолдеры `{a}/{b}`), функции → тонкие форматтеры. (P1; можно follow-up, но правило аудита B4 завести сразу.)
- **B4. Захардить `tools/oracle_audit.py`:** добавить strict-правила `no_realize_oracle_in_discourse` (`_realize_compare|_realize_explain`) и `no_wm_fixed_carrier`; добавить **структурное** `RULE_SKIP_REL` для легитимного `articulation_realize.py` (CEN-путь). 
- **B5. Снять устаревшие waivers** аккуратно: НЕ снимать `no_partner_dialog_templates` (он гейтит легитимный guard `_PARTNER_DIALOGUE_ACTS`) — вместо снятия добавить его в `RULE_SKIP_REL` с обоснованием.

**Приёмка:** 3 живых кейса честны (Спасибо→Пожалуйста; Как ты→ответ о состоянии; Что думаешь→позиция), `partner_voice_invariant_violations==[]`; `oracle_audit --strict` exit 0 без удалённого guard-waiver; грамматика не сломалась (B2).  
**Тесты:** `test_subject_articulation_emergent` (после A4), `test_how_are_you_emergence`, `test_partner_turn_scenarios`, `test_social_dialogue_bind`, `test_partner_voice_invariants` + новый acceptance-тест на 3 кейса + audit-unit.  
**Риски/откат:** KB-регресс соседних хабов (scoped slots; проверить self-narrative/intro); B2 — load-bearing против потери грамматики; откат = `git checkout` бандла (без rebuild). 
**Критические файлы:** `agents/von-neumann/bundles/kb-lang-ru-grammar-dialog-v1.bundle.json`, `design/kb-partner-speech-acts.v1.json`, `casa/prisms/tick/discourse/strategies/{explain,grammar}.py`, `casa/prisms/tick/discourse/realizers/blocks.py`, `tools/oracle_audit.py`, `casa/prisms/tick/discourse/wm.py`.

---

# ПЛАН B — Intent routing: убрать «always social» (предусловие)

**Цель:** ни один тёрн не выигрывает `social` только из-за краткости. Social побеждает, лишь когда тёрн dialogue-shaped **и** нет более сильного content/recall сигнала — зеркало того, как math/grammar уже глушат social. Content-тёрны (фактовый вопрос, словесная математика, «расскажи про…») достигают `general`/`explain`/`math`; recall держит безопасный margin; суб-роутер speech-act (уже верный) продолжает различать greeting/how_are_you/ask_thought/continuer.

**Заземлённый диагноз:** в живом чате `social=32` приходит **чисто из `geo:dialogue_turn`** без конкурентов (проверено прогоном). Существующий guard `geometry.py:65-66` (`not word_lookup/math_glyph/grammar_markers`) — правильный механизм, но его allow-list **слишком узок**: нет сигнала «короткий фактовый вопрос / расскажи про X / словесная математика».

**Рекомендация: вариант A (расширить guard) + половина C (требовать cue для выученного social). Отклонить B (continuer/opinion как отдельные тракты — суб-роут решается speech-act-дельтами, не argmax; высокий blast radius). Отложить D (де-хардкод RU-таблиц в locale-bundle — для английского, отдельной задачей).**

**Шаги:**
- **E1. `geometry.py` `geometry_signals`:** добавить структурные shape-сигналы (закрытые функц-классы, не topic-листы): `factual_question` (question_mark + WH-голова кто/что/какой/где/когда/сколько…, исключая `как`), `content_request` (директивная голова расскажи/опиши/перечисли), `word_math` (переиспользовать уже считаемые `math_words` без глифа).
- **E2. `geometry.py` `_geometry_score_for_tract`:** наградить content-тракты (`explain +~30` на factual_question — ниже word_lookup 36; `general +~22` на content_request; `math +~34` на word_math — ниже глифа 40) и **расширить social-guard** на `and not factual_question and not content_request and not word_math`.
- **E3. `competition.py` `compete_tract_intent`:** после `journal:suppress_phatic_social` (:70-74) добавить recall-margin damp, чтобы recall не флипал в social на 2 очках (видно: 34 vs 32).
- **E4. `casa/prisms/memory/intent/scoring.py` `score_row_match`:** для `tract_id=="social"` при `cue_hit==0` (geometry-only) вернуть 0 — чтобы выученный social не воссоздавал geometry-only доминирование. (Defense-in-depth.)
- **E5. (философия) Вынести функц-словарные списки geometry в locale-keyed bundle-claim** (`ru.meta.geometry.cues`) с embedded-defaults (поведение не меняется; seam для EN). Можно fast-follow.

**Приёмка:** «Кто такой Тьюринг?»/«Какой город столица?»/«Расскажи про числа» → не social; «Сколько будет 2 и 3?» → math; «Что думаешь?» → social (суб-роут сохранён); «Привет»/«Как ты?» → social; «Напомни…» → recall с margin≥8; `5+3`→math, «Согласно приказа»→grammar.  
**Тесты:** расширить `test_tract_competition.py` прод-путём (`compose_mode=None`) + добавить прод-кейс для «Как ты?»/«Что думаешь?» (закрывает test/prod-gap); не ослаблять `test_social_dialogue_bind`/`test_how_are_you_emergence`.  
**Риски:** over-suppress social (опинион/greeting в general) — `Что думаешь?` не имеет WH-content-головы → остаётся social; `как` исключён из factual_question. Откат: revert 3 файлов, каждая правка независима/аддитивна.  
**Критические файлы:** `casa/prisms/tick/tract/geometry.py`, `competition.py`, `casa/prisms/memory/intent/scoring.py`, `tests/test_tract_competition.py`, `design/kb-dialog-bind.v1.json` (E5 seam).

---

# ПЛАН C — Thread carry by default

**Цель:** `dialog.context.focus_recent` несёт нить между тиками **по умолчанию** (затухающий вес, gated по field-overlap, не по cue-маркерам). На её базе ретайрить waivered-оракулы O1/O3 и дать анафоре («это/этого») реальный референт: свежайшую пропозицию из ring (а не эхо собственной реплики).

**Проблема (verified):** сильный путь focus_recent+continuer(+72, `continuer_scoring.py:25`) фуёрит только при хардкод-маркерах в `dialogue.py:70`. Контент нити уже round-trip'ит через ring-provenance (`meaning_provenance` пишет `prop_ids`/`dialog_hubs` каждую реплику) — заперт только cue-гейт и all-or-nothing +72.

**Дизайн:**
- **E1. `dialogue.py` `dialogue_continuity_blocks`:** удалить marker-гейт (:70); строить `focus_recent` всегда при непустых focus_terms; добавить слоты `thread_terms`/`thread_age`(ring-distance)/`thread_intents`/`referent_prop`; базовый score≈12.
- **E2. `continuer_scoring.py` `apply_continuer_bind_deltas`:** заменить статический +72 на `delta = round(BASE*decay) + min(OV_CAP, ov*OV_MUL)`, где `decay` из `thread_age`, `ov`=`partner_field_overlap`; константы — из нового bundle-claim `ru.meta.dialog.thread_carry`. Companion-нуджи (self_recent/partner_recent) условить на `decay>0 or ov>0` (иначе stale preamble выигрывает — это и есть кейс (b)).
- **E3. Ретайр O3:** удалить `partner_continuer_query` (`partner_scoring.py:57-72`); `thread_continuer_turn` = `continuer_active(blocks) or speech_act thread_turn`. Снять waiver `continuer_query_markers`.
- **E4. Ретайр O1:** удалить `_continuer_head`/`_thread_gist` (`situated.py:17-33`); continuer-голова = bind-winner body + `linker`-слот «Про это» из bundle (`render.py` уже рендерит linker→«Про это — …»). Снять waiver `continuer_marker_oracle`.
- **E5/E6. Анафора:** новый `casa/domain/dialogue_bind/anaphora.py` — закрытый дейктик-класс («это/этого/этом/об этом») как **data** в bundle; `recent_ring_proposition(store)` → свежайший `ru.prop.*` (fallback `dialog_hubs`); материализовать референт-блок и привязать к нему (не эхо). «о чём думаешь» (без дейктика) референт-блок не инжектит → дискриминатор P5.
- **E7/E8.** Аппендить референт-блок в gather; персистить `out["thread_focus"]` (terms+referent_prop+age) для следующего тика.

**Приёмка (AC1-AC7):** focus_recent присутствует БЕЗ маркеров; вес затухает на topic-switch; O1/O3 удалены, `oracle_audit --strict` зелёный без 2 waivers; «что думаешь об этом» привязан к P, «о чём думаешь» — нет.  
**Тесты:** мигрировать `test_situated_turn::test_continuer_head_uses_first_sentence_only` (импортит удаляемый `_continuer_head`) на поведенческий; новые P4 (continuer-semantics), P5 (anaphora-negative), P-default (carry без маркера, decay на topic-switch).  
**Риски:** stale focus доминирует (decay+overlap+условные нуджи; bundle-тюнинг); удаление +72 регрессит cued continuer (калибровать BASE так, что age-0 on-topic ≥ 72).  
**Зависимость:** soft-предусловие — План B (иначе continuer недостижим как ветка под always-social; P5 полная только после B).  
**Критические файлы:** `casa/domain/dialogue_bind/dialogue.py`, `continuer_scoring.py`, `casa/prisms/tick/discourse/situated.py`, `casa/domain/dialogue_bind/partner_scoring.py`, `design/kb-dialog-bind.v1.json`.

---

# ПЛАН D — Affect reaches the surface (тезис-критичный)

**Цель:** накопленное лимбическое/характерное состояние меняет **тон слов** на партнёрском пути — bind-driven, без фикс-строк. (Сейчас affect меняет ТОЛЬКО выбор блока и длину через `budget._zone_budget_margin`, но не тон: `affect_scoring.py` — **no-op заглушка**, в `situated.py` нет affect-ветки.)

**Duck-test (приёмка):** один и тот же партнёрский тёрн; два состояния, отличающихся ТОЛЬКО накопленным affect (`valence`/`security`) / характером (`openness`/`directness`) → два **разных** surface-тона при **одинаковом** прагматическом классе; оба `partner_voice_invariant_violations==[]`; один и тот же state детерминирован; нейтральный cold-boot = байт-в-байт как сейчас.

**Граница allowed/forbidden (ADR-0057:146, ADR-0060):**
- **МОЖНО:** affect/характер (а) ре-скорят уже присутствующие блоки, (б) выбирают **индекс** в списке bundle-вариантов слота (hedge/assertive/warm/neutral openers+linkers). Слова — из bundle, как `ru.dialog.*` лексикон сейчас.
- **НЕЛЬЗЯ:** любой `if valence<x: pieces=["фикс-фраза"]` в Python; эмитить тон-фразу, которую bind не surface'ил. **Bright line: Python считает скаляр-bias и выбирает индекс/ре-скорит; Python НИКОГДА не содержит surface-слова.**

**Шаги:**
1. **Data:** в `design/kb-dialog-bind.v1.json` claim `ru.meta.dialog.tone_register` (pipe-слоты: hedge/assertive/warm/neutral openers+linkers). 2. **Accessor** `tone_register_slots(bundle)` (как `gated_dialog_prefixes`). 3. **Чистый селектор** `affect_surface.py`: `affect_register(bias, character)->key` + `apply_affect_register(clause, ctx)` (читает bundle-вариант, ставит `clause.linker`/prepend opener; no-op при None/neutral). 4. **`DiscourseContext.affect_select`** поле для передачи решения в impulse-хук. 5. **`situated.py`:** вызвать `apply_affect_register(head, ctx)` перед render. 6. **`recall_social_general.py`:** то же для фатического пути. 7. **`affect_scoring.py`:** заменить no-op на state-derived ре-скор (зеркало `apply_speech_act_bind_deltas`, scaled by `affect_compose_bias`; no-op при нейтрали — сохранить cold-boot). 8. **Impulse:** `record_partner_dialogue_impulse` (`dialogue_hooks.py`) флашит `ctx.affect_select` как `imp.select("discourse.affect_register", …)` (наблюдаемость #2; gated на `is_active`).

**Приёмка:** `reply_secure != reply_insecure`, разные register-ключи в impulse `select`, оба 0078-clean, детерминизм, нейтраль = legacy байт-в-байт.  
**Тесты:** `test_affect_surface_tone.py` (duck-probe + **anti-oracle assert**: каждый diff-токен есть в bundle-слотах + нейтраль-guard); инвертировать `test_affect_scoring::*noop`; расширить `test_partner_voice_invariants` (warm openers не триггерят over-reliance); impulse-тест (`select` node `discourse.affect_register`).  
**Риски:** стать оракулом (структурный тест ловит) / over-coupling (register применяется ПОСЛЕ выбора класса) / double-count (3 sink'а: budget=длина, zone_scoring=affinity, affect_scoring=тон — документировать) / warm = over-reliance (invariant-gate над bundle). Откат: `apply_affect_register` → return; `affect_scoring` → no-op (всё gated; bundle/impulse инертны без call-site).  
**Критические файлы:** `casa/domain/dialogue_bind/affect_scoring.py`, `casa/prisms/tick/discourse/situated.py`, `recall_social_general.py`, `casa/nervous/dialogue_hooks.py`, `design/kb-dialog-bind.v1.json`.

---

# ПЛАН E — Verify v2: инвариантный гейт диалога

**Цель:** заменить хардкод-`TURNS` на fixture-matrix + session-replay и заменить плумбинг-ассерты (`expect_bind_hub_prefix`, `forbid_phrase_substrings`) на 8 инвариантных проб, считаемых из УЖЕ существующих примитивов. «Зелёный» снова значит «поведение», не «плумбинг».

**Проблема (verified):** v1 самореферентен — speech-act claim впрыскивает `bind_boost` (`kb-partner-speech-acts.v1.json:47-55`), binder применяет (`speech_act_scoring.py:65-95`), v1 проверяет, что тот же хаб выиграл (`verify_dialogue_thread.py:50-54`). Слеп к собственному over-reliance-лику («Обращайся…»): `partner_voice_invariant_violations` **не вызывается**. `_token_overlap` — bag-of-words по соседним тёрнам.

**8 проб** (метрика · функция · порог): **P1** situational-delta (`score_text`/`bind_trace`; θ=12=3 токена) · **P2** partner-field-coupling (`partner_field_overlap`; floor `_FIELD_OVERLAP_MIN`=8) · **P3** fixed-state discriminator (`bind_trace` по акт-матрице; ≥0.5 distinct hubs) ⭐ · **P4** continuer-semantics (`continuer_active`/focus evidence) · **P5** anaphora-negative (`score_text`, paired-runner) · **P6** semantic anti-replay cross-act (`score_text`/`tokenize`, all-pairs) · **P7** ADR-0078 классы (`partner_voice_invariant_violations` — **уже реализовано**, красит last-green run) ⭐ · **P8** provenance honesty (`bind_trace_ranked`: winner≥runner_up; при `--impulse` сверка с `read_impulse_trace`).  
*Все пороги выведены из 2 констант проекта: `score_text` +4/токен и `_FIELD_OVERLAP_MIN`=8 — т.е. на той же шкале, что и продакшн-binder.*

**Шаги:** 1. `casa/domain/dialogue_invariants.py` (8 чистых проб + `THRESHOLDS` + `stage_gate`; вне HOT_PREFIXES, чтоб аудит её не флагал). 2. `casa/domain/dialogue_fixtures.py` (акт-матрица `{act:[≥2 surface]}`, `load_session_jsonl`, `run_fixture_thread`/`run_pair` над **temp-store**). 3. Фикстуры `tests/fixtures/session_thread_stageII.jsonl` + `session_last_green.jsonl` (транскрипт с «Обращайся…» — демонстрирует зубы P7). 4. Рефактор `verify_dialogue_thread.py`: `--fixtures`/`--session`, `evaluate_turn`+`stage_gate`, demote `expect_bind_hub_prefix`/`forbid_phrase_substrings` в **advisory smoke** (print, не raise), temp-store вместо живого. 5. Тесты `test_dialogue_invariants.py` (+ негативный: last-green триггерит P7) и `test_dialogue_gate_stageII.py` (merge-гейт; именно pytest = CI-механизм, verify-скрипт в CI не зовётся). 6. Док-апдейт §Target-v2 + Cursor-rule.

**Stage-gating:** CI-smoke = P1/P2+persistence (толерантные пороги); **merge-гейт стадии II = P3+P6+P7**; стадия III = P4/P5/boundary (reported-not-blocking).  
**Самый дешёвый высокоценный шаг:** завести **P7** в гейт (~0.5д) — он бы покраснел их «зелёный» прогон.  
**Риски:** флейки порогов (P1/P6 на token-floor; P3/P7 boolean/set — не дрейфят) / overfit фикстур (≥2 варианта + session-replay + P3 cross-act + P7 class-based) / live-store coupling (temp-store убирает).  
**Критические файлы:** `tools/verify_dialogue_thread.py`, `casa/domain/partner_voice.py` (P7), `casa/domain/dialogue_provenance.py` (bind_trace/ranked), `casa/domain/dialogue_bind/partner_scoring.py` (overlap+floor), `casa/domain/dialogue_bind/blocks.py` (score_text — шкала порогов).

---

## Статус триажа красных тестов (2026-06-15, ветка feat/auto-curriculum)
Три «красных» диалоговых теста разобраны; 2 из 3 починены честно (без правки ассертов):
- **`test_utterance_materialize::test_replayed_preamble_loses_at_bind`** — ✅ ПОЧИНЕН.
  Корень: `_parrot_penalty` штрафовал ЛЮБОЙ вариант, открывающийся словами партнёра,
  без проверки новизны (вопреки своему докстрингу «overlap WITHOUT novel efferent»),
  зануляя честное зеркало «не знаю, совпадает ли мой опыт…». Перестроен на stem-aware
  подсчёт shared/novel концептов: эхо ДВУХ+ концептов партнёра = parrot; эхо одного +
  реальное новое содержание = зеркало (проходит). `test_mirror_*` остаётся зелёным.
- **`test_paradigm_ltm::test_all_literacy_stages_mapped`** — ✅ ПОЧИНЕН.
  Три стадии манифеста (`stage-08c-meta-grammar-question`, `stage-09c-grammar-numeral`,
  `stage-14-morphemics-root-affix`) не были отображены в `LITERACY_STAGE_PROBES`;
  у каждой есть свой held-out-гейт-скрипт → добавлены как `SIDECAR_SPEC`.
- **`test_repair_chain_partner_turn`** — ⏳ ОТКРЫТ, это **План D**, не быстрый фикс.
  Сценарий — ХОЛОДНЫЙ агент: тёрн 1 «Как дела?» обязан провалиться (нет KB → self_failure),
  но тёрны 2/3 (repair-invite, trust) должны вербализовать подтверждение. Диагноз прогоном:
  в пустом сторе все 3 тёрна soft-miss (нет поверхностей) → 0 субъект-тёрнов → 3<4.
  С полным `kb-lang-ru-grammar-dialog` бандлом тёрн 1 НАЧИНАЕТ отвечать («Спасибо что
  спросил») → ломается посылка self_failure; тёрн 2 (repair-invite) всё равно не
  вербализует даже с бандлом. Нужны **врождённые** repair/trust-поверхности (по Плану D:
  affect→surface), доступные в холодном сторе, при этом how_are_you остаётся выучиваемым.
  Это проектное решение (что считать врождённым) + правка прод-бута/компоуза — оставлено
  команде, не маскировалось.

## Сводка для координатора
- **Начать с A (Track A)** — за пару часов 2/3 живых провала станут честными, без кода и без ре-ингеста.
- **Параллельно E-P7** (~0.5д) — гейт начнёт ловить over-reliance класс; и **A Track B** (снять P0-оракул O7 + фикс realizer B2).
- **B → C** — структурный корень (intent floor) и затем перенос нити (ретайрит ещё 2 оракула).
- **D** — тезис-критичный (тон от накопленного состояния), самый дорогой, делать с impulse-наблюдаемостью.
- **E-полно** — закрепить «зелёный = поведение».
