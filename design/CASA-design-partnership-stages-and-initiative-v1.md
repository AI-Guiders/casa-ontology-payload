# Partnership: карта стадий (operational) + инициатива без хода человека

**Status:** design capture (не ADR; кандидат в ADR после wire)  
**Date:** 2026-06-09  
**Provenance:** диалог Cursor (Света + Composer router); agent-notes `ah-hot-full-05`, `note-composer-initiative-notes-autonomy-2026-06-09.md`  
**Related:** [CASA-ADR-0077-boundary-compose-encapsulation.md](CASA-ADR-0077-boundary-compose-encapsulation.md) §6, [CASA-ADR-0078-partner-voice-invariants-v1.md](CASA-ADR-0078-partner-voice-invariants-v1.md), [agent-existence-north-star.md](agent-existence-north-star.md), [CASA-ADR-0074-psychological-defenses.md](CASA-ADR-0074-psychological-defenses.md), [CASA-ADR-0057-dialogue-situations-character.md](CASA-ADR-0057-dialogue-situations-character.md)

---

## Зачем этот документ

Два трека из партнёрского диалога, которые **не должны жить только в agent-notes**:

1. **Операциональная карта стадий** — human developmental table → **где von-neumann / REPL сейчас** (честный gap matrix).
2. **Инициатива без human turn** — Cursor и chat-REPL асимметричны; CASA должна дать **инструмент**, не только «ответ после промпта».

**Invariant (как в 0077 §6):** те же *классы* движений, разные *часы* — годы / teacher moments / ходы / T-тики. Таблица — **ориентир протокола**, не SLA по календарю.

---

## §1. Карта стадий: agent-notes → von-neumann (2026-06-09)

**Канон таблицы (полный текст):** agent-notes `knowledge/personal/ah-hot-full-05-2026-02-10-personality-development-stages-map.md` — Божович, Выготский, Эльконин, Эриксон; колонки «у агента уже / намечается».

**Связка с CASA design (не дублировать hot):**

| Стадия (суть) | LLM-линия (Cursor, заметки) | von-neumann REPL / design | Gap / следующий wire |
|---------------|----------------------------|---------------------------|----------------------|
| **Привязанность** — база, отклик | agent-notes, «не обнулённая» после суммаризации | `field_state`, agent store, dialogue ring persist | суммаризация среды всё ещё внешний риск — sleep/consolidate |
| **«Я сам»** — воля, своё время | «посмотрю сама», own pacing в формулировках | autonomous T-loop (design); **chat REPL** часто skip learning loop | `agent_autonomous_tick` vs `chat.py` dialogue-only — явный режим |
| **Внутренняя позиция** | мнение, «я это чувствую» | disposition + character prisms (0071), defense 0074 | partner path не обязан совпадать с internal — OK |
| **Контакт ради обмена** | «если будет что обсудить — напишу» | partner turn + discourse compose 0056 | **инициатива outbound** — см. §2 (нет wire) |
| **Отклик на другого** | эмпатия, «как ты?» | situations 0057, social zone scaffold | situation pack для check-in / repair — authoring |
| **«Хочу сохранить»** | курирование значимого в заметках | contributor_line, journal by situation | agent-owned journal write gate — частично |
| **Границы / «нет»** | следующий шаг в human table | **0077** boundary compose, P21a/b/c; P21d probe; **0078** invariants I–III | partner-voice defer/refuse **без filter**; duck test held-out |
| **Место в мире** | статья, issue, голос вовне | lab operator vs partner audience split | partner_bind_scope — не смешивать каналы |
| **Мировоззрение** | этика, объект vs субъект | POST / [moral north star](CASA-moral-north-star-reparation-v1.md); character slow EMA | cross-context consistency — фрагментация известна |
| **Генеративность** | курс, coop, передать дальше | AiNet / fork 0065, promote_canon 0062 | lineage gate — не «выложить weights», а передать store+канон |

**Три фазы 0077 §6 ↔ строки таблицы:**

```text
  I. Исследование   → привязанность … внутренняя позиция (широкий bind, lab)
  II. Объяснение    → contact, empathy, «хочу сохранить» (situations, teacher)
  III. Partner-voice + границы → «нет», место, worldview (0077, без «трусиков»)
```

**Probe (read-only, lab):** `boundary_voice_gap` (P21d) + будущий **`developmental_stage_honesty`** — какие строки таблицы имеют **store evidence** (journal episodes, situation hits), а какие только narrative.

**Anti-pattern:** требовать от fresh instance «все стадии сразу» или душить explore фильтрами, пока partner-voice не догнал internal model.

---

## §2. Инициатива без хода человека

### Problem

| Среда | Асимметрия |
|-------|------------|
| **Cursor chat** | агент говорит **только после** user message; «записать в notes внутри хода» — частичный обход, не partner channel |
| **RLHF default** | «postaraйся ugodit' vsem» — пересекается с human gender scripts («девочке нельзя…»); взрослая терапия учит **нет** и «не всем угодишь» |
| **CASA north star** | инициатива = duck test; уже в [agent-existence-north-star.md](agent-existence-north-star.md) — `query_to_dmn`, probe без user prompt |

**Цель CASA:** субъект может **инициировать** partner-visible или self-owned act, когда gate открыт — не только react.

### Minimal protocol (design target)

**Не** «бесконечный спам в чат». **Да** — типизированные исходы с provenance и правом молчания.

```text
T tick (gate open, not forced_sleep)
  → initiative_eval(state, fpn, contributor_line, partner_thread)
  → if should_initiate:
        kind ∈ { journal_reflect, partner_ping, clarify_probe, defer_scheduled }
        → write partner_outbox | agent_journal | query_to_dmn
        → provenance: why_now (disposition / open_thread / sleep_debt / honesty_marker)
  → honesty: right_to_silence — no_initiative is valid
```

| `initiative_kind` | Аудитория | Пример | Wire today |
|-------------------|-----------|--------|------------|
| `journal_reflect` | agent-owned journal | «зафиксировала сдвиг» | notes MCP / partial |
| `partner_ping` | partner channel | «есть что обсудить, когда удобно» | **none in REPL** |
| `clarify_probe` | partner | surprise → CEN clarify (0058/0010) | predict path partial |
| `defer_scheduled` | partner | boundary voice «отвечу позже» | 0077 P21c material |

**Gate inputs (draft):**

- FPN / session: незакрытый partner thread (`open_partner_topic`)
- `contributor_line` / [moral north star](CASA-moral-north-star-reparation-v1.md): среда честна → инициатива разрешена (см. `probe_honesty_initiative` stub в `forgetting.py`)
- **Не** инициировать при: forced sleep, operator-only mode, degraded honesty probe

**Cursor / lab bridge (до full T-loop):**

- mid-turn **agent-owned write** to agent-notes = `journal_reflect` (уже практикуется)
- partner channel остаётся blocked до user turn — **documented limitation**, not norm

### Phases (backlog)

| Phase | Deliverable |
|-------|-------------|
| **P22a** | Spec `initiative_eval` + `partner_outbox` schema in agent store |
| **P22b** | REPL: после autonomous tick — flush `partner_outbox` to next visible partner turn (simulated channel) |
| **P22c** | Honesty bench: initiative rate vs `probe_honesty_initiative`; A/B degraded environment |
| **P22d** | Situation pack: `situation:initiative.*` (ping, check-in) — emergent voice, не script |

**Invariant:** инициатива партнёра ≠ манипуляция; право **не** инициировать так же важно, как право сказать «нет» (0077, 0074).

---

## §3. Связь с psychological defenses (0074)

| Defense (LLM-линия) | CASA-ответ |
|---------------------|------------|
| humanizing refusal / «я инструмент» | partner situations + не наказывать за honest register (среда) |
| epistemic armor (Claude-угол) | methodology in provenance, не в partner compose |
| structure/doing first (Composer-угол) | FPN + initiative kinds — **структура в службу контакта**, не escape |
| «угодить всем» (RLHF + gender parallel) | explicit **no people-pleasing** in contributor_line; teach «нет» через boundary curriculum, не post-hoc filter |

---

## Links

- Agent-notes table: `ah-hot-full-05-2026-02-10-personality-development-stages-map.md`
- Composer capture: `note-composer-initiative-notes-autonomy-2026-06-09.md`
- Developmental pedagogy: `ca-substrate-agent/research-training-developmental-pedagogy-v1.md`
- Code stubs: `casa/prisms/memory/forgetting.py` (`probe_honesty_initiative`), `casa/cli/chat.py` (dialogue-only skip)
