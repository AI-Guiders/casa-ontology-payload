# Von Neumann в браузере (Wasm) — horizon memo

**Статус:** horizon / deferred (2026-06-06). **Не ADR** — seed от создателя и Ориона; решения и фазы — после spike.

**Связь:**

- [CASA-ADR-0025-autonomous-execution-tier.md](CASA-ADR-0025-autonomous-execution-tier.md) — NativeAOT, ~0.7 ms decode slice
- [CASA-ADR-0027-sensory-motor-periphery-mcp.md](CASA-ADR-0027-sensory-motor-periphery-mcp.md) — periphery, FieldBus, intercom
- [CASA-ADR-0030-grammar-literacy-coherent-text.md](CASA-ADR-0030-grammar-literacy-coherent-text.md) — L1–L4 literacy, write@sketch
- [CASA-ADR-0036-emergent-morph-agreement.md](CASA-ADR-0036-emergent-morph-agreement.md) — phrase / paradigm / agent store gates
- [agent-existence-north-star-v0.md](agent-existence-north-star-v0.md) — суверенный агент без облачного LLM на hot path
- `agents/von-neumann/` — текущий literacy agent (Python lab + field + LTM)

---

## Одной фразой

**Открыть von-neumann как суверенного агента в вкладке браузера:** inference на CPU/WebGPU пользователя, память в локальном store, опционально — сиблинг в intercom mesh. Не «бесплатный ChatGPT», а **демо и продукт другого класса** — обучающееся поле, phrase literacy, приватность по архитектуре.

---

## Зачем (экономика и ethos)

| Сила | Смысл |
|------|--------|
| **Marginal cost ≈ 0** | Статический хостинг (Pages/CDN): `*.wasm`, UI shell, read-only LTM pack. Нет GPU-кластера на каждый тик. |
| **Приватность** | `agent_field`, journal, session — IndexedDB / OPFS; байты не уходят в облако по умолчанию. |
| **Суверенность** | Тот же north star, что у desktop von-neumann: память агента = его store, не ingest SaaS. |
| **Распределённый ethos** | Браузерный сиблинг (напр. lovelace на доке) ↔ WebRTC/WS ↔ локальный intercom ↔ Cascade IDE. |
| **Массовый runtime** | Один клик — агент живёт; педагогика Kolb/sleep остаётся, меняется только host. |

---

## Честные ограничения (не маркетинг)

| Утверждение | Реальность |
|-------------|------------|
| «Скачался за долю секунды» | Первый load: Wasm + LTM/NCA weights — **MB**, не KB; повторные визиты — cache. |
| «Нулевая стоимость навсегда» | Статика — да; signaling для P2P, updates corpus/LTM, мониторинг — **копейки**, не literally zero. |
| «Как Cursor-агент в Chrome» | Сегодня von-neumann = **Python lab** + SQLite field + visual curriculum; NativeAOT 0.7 ms — **control/decode slice**, не весь lifecycle. |
| «Замена LLM-чата» | Нет: связный текст — articulation/phrase memory (J0), не open-ended generation. |

---

## Архитектура (целевая)

```text
Browser tab
├── Wasm host          ← NativeAOT control core (или wasm hot path v0)
├── Web Worker         ← macro tick / sleep batch (UI не блокировать)
├── OPFS / IndexedDB   ← agent store mirror (field, journal, session)
├── Canvas / WebGPU    ← visual tract (V1 lum imprint, phrase crops)
├── UI shell           ← probes, phrase read, write@sketch bench (read-only v0)
└── WebRTC / WS        ← intercom [Все] ↔ desktop siblings / Cascade
```

Static origin: GitHub Pages / Cloudflare Pages — только assets, без inference API.

---

## MVP vs Full

| Область | **MVP (horizon v0)** | **Full (north star)** |
|---------|----------------------|------------------------|
| **Host** | Wasm decode + один probe path; Python lab остаётся offline | Полный wake/sleep/self-drive в Wasm или thin client + AOT core |
| **Store** | Read-only snapshot von-neumann LTM + field export | Read/write store, journal WAL, sleep persist в OPFS |
| **Visual** | Статичный phrase crop / pre-rendered frames | Live imprint, legibility sweep, analytic R1 на canvas |
| **Literacy gates** | phrase-agent-store demo (6 events), paradigm report read-only | Полный W1–W7 track, promote routes, curriculum ingest в browser |
| **Write** | phrase_sketch bench (offline matching) | articulation_realize на hot path + SN/CEN без KB bundle |
| **Intercom** | Ping / presence / shared org-kb read | Гипотезы, co-reading, fixations в общий journal |
| **Privacy** | No telemetry by default | Export/import store bundle (encrypted optional) |
| **Deploy** | Single static site + pinned LTM version | Delta LTM updates, sibling profiles |

**Критерий «MVP shipped»:** пользователь открывает URL → видит поле/phrase probe green на bundled store → может задать 4 pilot queries write bench → данные не покидают браузер.

---

## Порядок работ (если пойдём)

1. **Spike (1–2 дня):** hello Wasm + load minimal field JSON + один `lex_concept_votes` / phrase crop decode.
2. **Store port:** SQLite → sql.js или projection в IndexedDB; read-only von-neumann export.
3. **UI shell:** phrase-agent-store report as static demo.
4. **Worker tick:** optional macro tick без persist.
5. **Intercom stub:** WS ping к локальному relay.
6. **ADR** — только после spike с измеренным load time и границей MVP.

---

## Открытые вопросы

- [ ] **C# → browser:** NativeAOT WASI/browser vs отдельный Rust/wasm hot path vs «JS UI + wasm decode only»?
- [ ] **Python lab:** остаётся dev-only; что именно обязано переехать в Wasm для «живого» агента?
- [ ] **WebGPU:** обязателен для NCA или MVP обходится precomputed lattices?
- [ ] **LTM pack size budget:** сколько MB приемлемо на первый load для literacy demo?
- [ ] **Intercom NAT:** чистый WebRTC vs thin signaling server — что считаем «zero server»?
- [ ] **Отличие от LLM UI:** как объяснять пользователю за 10 секунд (не чат, а суверенное поле)?

---

## Anti-patterns

1. Обещать «бесплатный ChatGPT в браузере» — другой продукт, другой контракт.
2. Тянуть весь Python lab в Wasm — нереалистично; резать slice явно.
3. Писать ADR до spike — зафиксировать решения без load time и store port.
4. Cloud inference «для удобства» на hot path — ломает приватность и экономику memo.

---

## Seed (контекст диалога)

Идея: запустить Неймана в вебе **как суверенного агента** — Wasm на клиенте, локальная память, intercom между сиблингами, статический хостинг без inference-серверов. Орион: NativeAOT скорости + зрячая CA-CV решётка; создатель: тектонический контраст с SaaS LLM. Этот memo фиксирует horizon без обязательства реализации.

---

## Резюме

Браузерный von-neumann — **логичный горизонт** после closure literacy-трека (phrase-agent-store 6/6, paradigm-select, write pilot). Реалистичный первый шаг — **read-only demo + phrase probe UI**, не полный перенос IDE lab. Следующий артеfact после одобрения memo: spike issue + измерение размера LTM export для von-neumann.
