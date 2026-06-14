# CASA Auto-Curriculum — полный план реализации (v1)

**Дата:** 2026-06-14  
**В связке с:** [CASA-code-audit-v1.md](CASA-code-audit-v1.md) (Phase 0), [CASA-dialogue-change-plans-v1.md](CASA-dialogue-change-plans-v1.md) (оракулы на грамматике)  
**Метод:** 3 архитектурных агента + аудит, всё с прогоном кода и `file:line`.

## Тезис и философия
Способность сегодня = ~17 рукописных `ru.prop.*` фреймов + `ru.dialog.*`/`ru.grammar.*` claims; стоимость авторинга **линейна** — это потолок. Авто-куррикулум ломает его: **холодный LLM драфтит кандидат-правило → adversarial held-out гейт → версионируемый промоут в бандл (символьное поле)**.

**Жёсткая философия (изоморфно promote_canon / ADR-0069):** LLM-черновик = кандидат в explicit/sandbox; held-out гейт = ceremony; смёрженный claim = принятый постулат. **LLM — только генератор кандидатов на этапе авторинга, НИКОГДА на горячем пути** (рантайм остаётся детерминированным, без галлюцинаций, с трассируемым провенансом). Правила промоутятся **в** поле (bundles→bind→postulate tier), усиливая движок, а не обходя его. (Команда явно принимает этот механизм, но отвергает вывод «движок лишний» — [ОТВЕТ:58](ОТВЕТ-на-РЕКОМЕНДАЦИИ-Von-Neumann.md).)

## АНТИ-ТАВТОЛОГИЯ — центр всего
Аудит нашёл тавтологию **везде** (гейт предсказывает собственный вывод модели; verify инжектит boost и ассертит его же). Поэтому 6 файрволлов, без которых конвейер не запускается:

1. **Генератор ≠ грейдер (файловая сепарация).** Кандидат содержит TRAIN-примеры (авторские), а грейдинг-пробы лежат в **отдельном файле, написанном другим актором** (куратор/замороженный examiner без доступа к телу правила). Кандидат ссылается на held-out slice **по id**, никогда не инлайнит. Раннер уже грузит held-out отдельным флагом из непересекающегося файла (`probe_text_meaning_ru.py:16,35,41`).
2. **Абляция вектора инъекции.** Перед грейдингом обнуляются ВСЕ каналы, которыми ответ можно «подложить»: `claims_nav` (`bench_heldout.py:39-40` уже делает `st["claims_nav"]=[]`), speech-act `bind_boost`/`route_hints` (`speech_act_scoring.py:65-95` — гейт идёт `intent!="social"` + скраб `ru.speech_act.partner.*`), journal-recall/`focus_recent` (`dialogue.py:76`, `continuer_scoring.py:24`), hot-salience (`predictor.py:393`). Проходной балл должен отражать **поле**, а не подложенный boost. Новый `ablate_injection_vectors(state)` обобщает существующую абляцию `bench_heldout` на все 5 каналов.
3. **Negative control.** Намеренно-неверное правило (held-out перелейблен на sibling-концепт) обязано быть **отвергнуто** (`neg_pass_rate ≤ NEG_MAX`). Cue-conditioned скоринг при выключенной инъекции реально не surface'ит неверный sibling — это та фальсифицируемость, которой нет у текущего гейта.
4. **Leave-one-in.** Held-out slice с **удалённым** новым правилом обязан **провалиться** — доказывает, что проба тестирует новую способность, а не то, что поле уже умело (иначе «гейт предсказывает то, что и так знал»).
5. **Self-echo rejection (уже есть, не ослаблять).** `_TEMPLATE_MARKERS` blocklist, `expect_anti_template`, `expect_max_paste_ratio`, `expect_own_voice_min` (`probe_nositel_gate_ru.py:106-150`) — правило проходит, только если поле **сочиняет своими словами** над held-out cue, а не пастит свои же `clause_*`.
6. **Curated paraphrase (failure-mode).** Намайненный провальный cue идёт в TRAIN; грейдер берёт **независимо написанный парафраз** — проход требует обобщения, а не запоминания точной строки.

## Архитектура
```
 MINE ─────► DRAFT (LLM) ─────► VALIDATE ─────► GATE ───────► PROMOTE ─────► CI/PR
 провалы      кандидат JSON      schema+dedupe   held-out +    версион.       human-review
 (impulse/    (cold path)        +dry-merge в    ablation+     bundle-write   @ merge
  soft_miss/                     scratch-bundle   neg+leave1in  +provenance
  oracle/...)        ▲                                │fail                      │
                     └──── loop-until-dry / budget ◄── reject(лог target) ◄──────┘
```

## Граф фаз и зависимости
```
Phase 0  Foundation (из аудита)  ── ПРЕДУСЛОВИЕ всего ──────────────► делать первым
Phase 1  Held-out гейт (анти-тавтология)  ── keystone ── зависит от 0(CI/тесты)
Phase 2  Staging + версион. промоут  ── цель записи ── частично ∥ с 1
Phase 3  Кандидаты + майнинг + loop  ── зависит от 1+2
Phase 4  CI-гейты + метрики зрелости  ── зависит от 1+2+3
```
Phase 1 (гейт) и Phase 2 (staging) — позвоночник; их часто называют «новой работой», но они нужны в любом случае. Phase 3 — собственно «куррикулум» поверх них.

---

# PHASE 0 — Foundation (предусловие; детали в [аудите](CASA-code-audit-v1.md))
Нельзя строить на красном trunk'е. Минимум до Phase 1:
1. **Позеленить CI** (`check_no_abs_paths --scope ci`, `check_tools_shims --allow-tools-shims`) — иначе тесты не бегут вообще.
2. **3 малых жёстких бага:** `L0_ID` импорт (чинит 14 модулей/10 бенчей), `spawn_defense_zone(tick=)`, `AnswerBlock.get`.
3. **Триаж 27 красных**, приоритет — learning-кластер (confirmation-гейт, sleep/replay `merged==0`, emergent-mint, write-gate vs relink): по каждому «намеренный дрейф→обновить тест» vs «регресс→чинить».
4. **Инкрементальный persist engine-wide** + вычистить 116МБ снапшотов (до масштабирования тиков).

---

# PHASE 1 — Held-out гейт (анти-тавтологичное ядро)
**Цель:** заменить тавтологичный `self_verify_predict` на `generator≠grader` held-out evaluator, который куррикулум и canon-ceremony **обязаны** звать.

**Дизайн (`casa/eval/held_out_gate.py`, новый):**
- **Партиция** `partition_probe_bank(cases, *, held_out_ratio=0.3, seed)` — детерминированная (stable `sha1(lattice|cue|concept_id)`), с инвариантом из `lab/.../block_pedagogy.py:461-471` `train_cue_set` (held-out cue **вычитается** из train; коллизии по `(lattice, norm_word(cue))` выкидываются из train).
- **Абляция** `ablate_injection_vectors(state)` — deep-copy + обнуление 5 каналов (см. файрволл #2). Обобщает `bench_heldout.py:37-40`.
- **Независимый оракул** `score_case(staged_state, case, *, top_k)` — **cue-conditioned** `surface_from_sss(st, lattice, prompt=cue)` + `top1/topk/target_match` (как `bench_heldout.eval_case:29-70`). ⚠️ **`episode_vote_for_cue` НЕ различает cue** (проверено: вернул 5 и для `14→fourteen`, и для `14→three`) — использовать только как coverage-guard `vote>0`, не как дискриминатор.
- **Pass-критерии** (одна frozen `GatePolicy`, оверрайдится из `planned_lattices`): `held_out_n≥4` И `held_out_score≥0.80` И `held_out_pass≥max(3, ceil(0.8·n))` И `baseline_delta≥0` (нет регресса на retained baseline) И `neg_pass_rate≤0.25` (negative control). Числа якорятся на `block_pedagogy.gate_pass` `know_min_ratio=0.85` и `mastery_ready(min_streak=2)`.
- **API:** `evaluate_candidate(candidate_claims, probe_bank, baseline_set, *, base_state, policy, seed) -> GateReport{passed, candidate_id=sha256(claims), held_out_score, baseline_delta, negative_control_passed, neg_pass_rate, provenance{ablations,probe_bank_hash,field_version}, cases}`. Чистая, детерминированная, на deep-copy (staging), без persist.

**Wire-in (промоут невозможен без настоящего отчёта):**
- `agent_promote_canon_lattice` (`agent_canon_lattice.py:133`) — **обязательный** `gate_report: GateReport`; `if not report.passed: raise`; `if report.candidate_id != expected_candidate_id(request): raise` (отчёт привязан по id). Провенанс пишется в immutable-узел.
- `agent_canon_tick.py:33-34,55-59` — **удалить** `canon-ready` fast-track + два фейковых `record_gate_attempt(passed=True)`; вместо них вызывать `evaluate_candidate`.
- `agent_memory_ops.py:106,126` — самовыставляемый `status="confirmed"`/теги → **только провенанс** (`provenance:self`); operator-override через `WRITE_CONTEXT_OPERATOR` + подпись.

**Починить `workbook_check`** (`agent_workbook.py:143-221`, сейчас красный): корень — у "14" нет glyph-mapping, `run_sleep` не минтит numeral `denotes`, поэтому flat-ранг отдаёт alphabetically-first `eight`. Фикс: сделать проверку **cue-conditioned + episodic-aware** (pass если predict совпал ИЛИ `surface_matches_target` И `episode_vote>0`); `rejected` только при положительном свидетельстве неверности, не при `ratio<=0.0`. Делит `score_case` с гейтом.

**Тесты:** `test_held_out_gate.py` (детерминизм партиции; correct→passed; **wrong→rejected**; ablation меняет исход; baseline-регресс блокирует); `test_agent_canon_lattice.py` (промоут требует отчёт; отвергает mismatched id); `test_agent_workbook.py` (зелёный + untrained→не confirmed).  
**Эффорт:** ~1 день (гейт ~250-320 LOC + workbook-фикс S + wire-in M + один эталонный probe-bank). `workbook`-фикс шипуем независимо.  
**Критфайлы:** `casa/cli/bench/bench_heldout.py` (актив для подъёма), `casa/prisms/memory/agent_workbook.py`, `agent_canon_lattice.py`, `casa/prisms/tick/agent_canon_tick.py`, `lab/visual-curriculum/block_pedagogy.py`.

---

# PHASE 2 — Staging-store + валидируемый атомарный версионируемый промоут
**Цель:** единый безопасный путь записи — LLM-claim валидируется, бенчится в **изоляции**, и только по зелёному гейту атомарно+обратимо промоутится в live-стор.

**Шаги (file:line):**
1. **Починить мёртвый плумбинг:** `build_kb_bundles.py:82-151` и `kb_sync.py:99-185` шеллятся в **удалённые** `tools/*.py` → заменить на `python -m casa.cli <mod>` (мэппинг уже в `cli_modules.json`). **Извлечь** `import_delta(delta, *, store_dir, ..., now, validate=True)` из тела `main()` `import_knowledge_delta.py` (сейчас только `main()`, нет переиспользуемой функции). Канон-стор = `default_agent_store()` → `agents/von-neumann/bundles/`.
2. **`bundle_validate.py` (новый), до любой записи:** claim — dict; `concept_id` — непустой str; `slots` — dict-or-absent; `text` — str; **дубль `concept_id` в дельте → reject**; синтаксис `bind_boost`/`bind_demote`/`route_hints`. ⚠️ Парсер `_parse_weighted_prefixes` (`speech_act_scoring.py:14-25`) **молча коррумпит** (воспроизведено): `"hub:5:7"`→`('hub:5',7)`, `"hub:abc"`→`[]`, `"hub:-3"`→negative, **`":5"`→пустой префикс матчит ВСЁ через `startswith("")`**. Валидатор отвергает: пустой префикс, >1 двоеточия, не-int, негатив, hub-префикс без концепта. Reject **всей** дельты, копит все нарушения.
3. **Staging-store** `staging_store.py` (новый): clone-by-reference overlay (hard-link read-only `agent_field.db`/`ltm`/`nca`/`bundles`; **copy** `field_state.json`). `import_delta` в staging гоняет **настоящий** merge+`write_bundle_to_field`+`rebuild_union_field`. Гейт (Phase 1 / `bench_heldout`) бежит против staging. Teardown `shutil.rmtree`.
4. **Атомарный промоут** `promote_to_live(staging, live, *, version, provenance, now)`: snapshot `field_state.json`→`field_state.bak.v{N-1}.json`; финалы в `live/.promote-tmp/` (тот же FS); промоут bundle-first (версионное имя `bundles/<name>.bundle.v{N}.json` — крэш тут не портит N-1), затем **единственная точка коммита** `os.replace(tmp/field_state.json → live/field_state.json)`; DB-mirror **после**. Rollback при исключении: restore из `.bak`, удалить `v{N}`. (Чинит воспроизведённый split-brain `field_write.py:314`.)
5. **Версионирование/провенанс** — **на уровне бандлов, не через promote_canon** (обоснование: `promote_canon`/`write_gate` работают на immutable-lattice-субстрате с нулём ссылок на bundle-стор; ADR-0069 сам помечен design-only). Per-claim `provenance{promoted_at(от caller), from_candidate_id, gate_report_id, theory_id}`. ⚠️ `load_store_bundles` глобит `bundles/*.json` — ретайр-версии переносить в `bundles/.versions/` или выбирать по `field_state.grid.source_bundles`, иначе двойной счёт. Опциональный canon-hook после зелёного промоута — расцеплено.
6. **Write-safety caps:** max claims/bundle, max score (парсер-дефолт 12 → потолок ~50), max bytes; коллизия `concept_id` с live → warn/reject-флаг.

**Протокол staging→live (12 шагов):** author → validate(zero-write при fail) → make_staging(overlay) → import_delta(staging) → gate+ablation → branch(red=close/untouched; green=continue) → stamp provenance → promote_to_live(atomic) → rollback-on-fail → optional canon-hook → teardown → live bind видит версию N консистентно.

**E2E smoke (CI, без GPU):** author→validate→stage→gate→promote→load (claim ровно один раз); negative-validation (`:5`/`hub:5:7`/дубль → ok=False, ноль записей); atomic-rollback (monkeypatch крэш → live восстановлен из `.bak`).  
**Эффорт:** ~3 дня (атомарный cross-file commit + Windows link-fallback + loader version-select — самое рисковое).  
**Критфайлы:** `import_knowledge_delta.py`, `field_write.py`, `kb_sync.py`, `store_bundles.py`, `bench_heldout.py`.

---

# PHASE 3 — Кандидаты + майнинг провалов + оркестрация
**Цель:** что LLM драфтит, откуда берутся цели куррикулума, граница роли LLM, и петля.

**Прекурсор для переиспользования:** `casa/domain/meaning_authoring.py` уже драфтит `ru.prop.*` из journal-гипотез и **мержит в бандл БЕЗ held-out гейта** (`promote_frame_from_journal:44`) — это ровно та тавтология («ЕГЭ-форма»). Авто-куррикулум **заменяет merge-шаг** на гейтнутую петлю и **переиспользует draft-shaping + bundle-write**.

**Candidate spec (JSON):** один claim (или маленькая frame-family) в **точной грамматике бандла** (`concept_id`, `text`, `section`, `slots{match_passage_*|match_question_*|match_sentence_*|score|clause_*|linker_*|...}`) + **TRAIN-примеры (генератор)** + `held_out_ref{plan, scenario_ids, authored_by!=generator, min_pass_ratio}` (указатель, не инлайн) + `ablation{boost_fields, require_pass_without_self_boost}` + `provenance{generator, source_signal{kind, ref, cue}}`. `score` стартует **низким**; гейт может поднять после прохода.

**Failure-driven (принципиальный режим — «учим тому, что не умеет»):**
| Сигнал | file:line | Miss → цель |
|---|---|---|
| soft_miss / честное «не знаю» | `dialogue_tick.py:365` (`empty_compose`), `articulation_realize.py:271,283,325` | cue без покрывающего фрейма → драфт фрейма, чей matcher покрывает концепт |
| impulse threshold (bind-фрустрация) | `impulse.py:164-172` (`threshold`), `dialogue_hooks.py:57-58`, чтение `read_impulse_trace:420` | «что bind хотел, но не surface'ил» (`rejected_above_floor`/near-miss) → поднять потенциал/добавить cue |
| held-out predict fail | `predict_tick.py:60-63,99-104` (`clarify`/verdict) | `focus` провального тика = недостающий концепт |
| **oracle-shadow (поле НЕ может → Python фейкит)** | `articulation_realize.py:140-169/106-137/291-303` (`_realize_compare/_explain/_check_norm`) | **богатейший seam:** каждая ветка = цель; драфт эквивалентного `ru.grammar.*` claim → ветка-оракул становится мёртвым кодом |
| `/remember` коррекции (сейчас тупик) | `chat.py:91-102` (`kind:observation`, инертно) | коррекция эксперта = цель (негативное свидетельство), идёт через draft→gate→PR |

**Corpus-driven (объёмный режим):** LLM читает `lessons/*/README.md` + существующий `concept_id`-сет (дедуп) → драфтит новые фреймы; куратор пишет held-out slice **на урок** (другой актор).

**Граница роли LLM:** МОЖЕТ — тело claim, TRAIN-примеры, `depends_on`/edges, только cold path. НЕ МОЖЕТ — горячий путь, авторинг грейдинг-проб, выставление своего verdict, прямая запись в `bundles/`, подъём `score` без подтверждения гейтом через абляцию.

**Loop:** mine→draft(LLM)→validate(staging)→gate(held-out+ablation+neg+leave1in)→promote(versioned)→CI/PR(human@merge). Batch N=5-10 (один PR на батч), budget = max draft-вызовов + max промоутов/PR, `loop-until-dry` (майнер выдал 0 целей) / `loop-until-budget`. Cadence: on-demand + nightly cron над накопленными impulse/`/remember`. Отвергнутые цели логируются для ре-драфта (bounded retries).

**Новые модули:** `casa/curriculum/{mine_targets,draft_candidate,gate_candidate,orchestrate}.py`.  
**Эффорт:** ~2 недели поверх существующего плумбинга (gate+staging — siblings, bundle/promote — прекурсор есть). Рекуррентная стоимость — кураторские held-out парафразы (неустранимый human-in-loop by design).  
**Критфайлы:** `casa/domain/meaning_authoring.py`, `agents/von-neumann/bundles/kb-lang-ru-lexicon-semantics-v1.bundle.json` (грамматика тела), `lab/visual-curriculum/probe_text_meaning_ru.py` (контракт гейта), `probe_nositel_gate_ru.py` (анти-тавтология — не ослаблять), `casa/nervous/impulse.py`, `articulation_realize.py`.

---

# PHASE 4 — CI-гейты + метрики зрелости
**Цель:** «зелёный = поведение», прогресс куррикулума измерим.
- **Завести в CI:** `oracle_audit --strict` (+ приземлить недостающие правила на `_realize_*`/wm/rewrite — иначе вакуумно-зелёный), **не-тавтологичный** end-to-end диалог-гейт (Plan E из change-plans), negative bundle-validation тесты.
- **Закрыть оракул-слепоту на грамматике** (Plan A/C из change-plans) — иначе промоут грамматического правила перекрывается `_realize_compare`.
- **Метрики:** покрытие (число `concept_id` ↑; **# ретайрнутых oracle-веток**), held-out pass-rate на disjoint slice, # промоутнутых правил (yield gate:draft), regression count (=0), soft-miss/threshold rate ↓ на фикс-Q-сете, tautology-guard (leave-one-in fail-rate + ablation reject-rate).
- **Developmental signal:** стадия «освоена», когда её held-out slice зелёный через **field-composed (не-oracle, не-paste)** ответы И соответствующие oracle-ветки мертвы. Привязка к `text-meaning-plan stage_order:[extract,inference,stance,pro_con,register]`.

---

## Сводный эффорт и порядок
| Фаза | Что | Эффорт | Зависит |
|---|---|---|---|
| 0 | Foundation (CI green + 3 бага + триаж + persist) | триаж-зависимо, ~дни | — |
| 1 | Held-out гейт (анти-тавтология) | ~1 день | 0 (CI/тесты) |
| 2 | Staging + версион. промоут | ~3 дня | ∥ с 1 |
| 3 | Кандидаты + майнинг + loop | ~2 недели | 1+2 |
| 4 | CI-гейты + метрики | ~неск. дней | 1+2+3 |

**Ключевой вывод:** Phase 1 (настоящий гейт) — keystone и анти-тавтологичное ядро; он же чинит сломанный `workbook_check` и закрывает bypass. Phase 1+2 — позвоночник, который нужен в любом случае. Только после них Phase 3 («куррикулум») безопасен. Большая часть «нового» (гейт, staging, CI-сеть) — это и есть фундамент, без которого авто-промоут промоутит против рваной сети, частично проверяющей собственное отражение.
