# CASA-ADR-0046: Function calling как body extension point (client-agnostic)

**Статус:** accepted (design + contracts v0; routing integration accepted 2026-06-06)  
**Дата:** 2026-06-05  
**Область:** motor/tool слой тела субъекта — MCP, IDE, CLI, WASM bridge — без привязки к Cursor / cloud LLM  
**Связано:**

- [`CASA-ADR-0035-multi-layer-routing.md`](CASA-ADR-0035-multi-layer-routing.md) — tool tract через capability/applicability; **не** organ в control
- [`CASA-ADR-0024-control-thalamus.md`](CASA-ADR-0024-control-thalamus.md) — motor relay на macro tick
- [`CASA-ADR-0034-executor-learning-loop.md`](CASA-ADR-0034-executor-learning-loop.md) — шаг 2: тракт `tool.*`
- [`CASA-ADR-0027-sensory-motor-periphery-mcp.md`](CASA-ADR-0027-sensory-motor-periphery-mcp.md) — периферия ↔ адаптер ↔ CCU ↔ мозг
- [`CASA-ADR-0008-layout-parity-bilingual-t9.md`](CASA-ADR-0008-layout-parity-bilingual-t9.md) — lab → host-native (аналогия BiT9/act)
- [`CASA-future-von-neumann-browser-wasm-v0.md`](CASA-future-von-neumann-browser-wasm-v0.md) — lab = dev-only; prod host-native
- [`CASA-ADR-0025-autonomous-execution-tier.md`](CASA-ADR-0025-autonomous-execution-tier.md) — host vs agent store; macro tick von-neumann в AEE
- [`CASA-ADR-0037-subject-diagnostics-cockpit.md`](CASA-ADR-0037-subject-diagnostics-cockpit.md) — panel «body»
- [`CASA-ADR-0045-subject-as-interlocutor.md`](CASA-ADR-0045-subject-as-interlocutor.md) — verbalize act/defer
- [`CASA-ADR-0048-ke-knowledge-engineering-domain-v0.md`](CASA-ADR-0048-ke-knowledge-engineering-domain-v0.md) — KB / hot-context; wire `tool.kb.*`
- CIDE [`MCP-PROTOCOL.md`](../../cascade-ide/docs/MCP-PROTOCOL.md) — один из motor backends
- CIDE [ADR 0148 — AEE](../../cascade-ide/docs/adr/0148-agent-execution-environment-verification-ladder-and-native-tooling.md) — **Agent Execution Environment**; von-neumann стыкуется сюда

---

## Решение (одной фразой)

**Function calling — не capability LLM-клиента, а extension point тела (`BodyFunctionExtension`):** стабильный контракт `FunctionCallIntent` → backend → `FunctionCallResult`, одинаковый для Cursor MCP, CIDE loopback, in-process stub, browser host bridge.

Мозг **не** знает JSON-RPC MCP. Host **не** подменяет субъект готовым ответом — только исполняет **motor intent** и возвращает **сжатый percept**.

---

## Мотивация

| Проблема | Ответ ADR |
|----------|-----------|
| Tool use «как у Cursor» = cloud function calling | У von-neumann hot path — поле; tools — **тело**, не weights |
| MCP привязан к хосту чата | Каталог и вызов — **body_manifest + backend_id**; клиент сменяем |
| Дублирование: Cursor tools vs CIDE `ide_execute_command` | Один **FunctionSpec**; wire mapping в backend |
| MEAI-чат CIDE vs motor von-neumann | **Два host extension**: `HostLlmToolBridge` (LLM) и `BodyFunctionExtension` (field); общий L2 |
| Von-neumann «где жить» в IDE | **AEE**, host-native (**C#**); **без Python в runtime** (уже в видении); lab — reference |
| Sensory MCP уже в ADR-0027 | **Симметричный motor** channel с тем же layering |

---

## Границы

```text
  ┌──────── AGENT STORE (мозг) ─────────────────────────────────────┐
  │  classify → FunctionCallIntent (function_id + slots)             │
  │  ingest ← mm_event ← percept from result                         │
  │  dialogue ← verbalize(ok | error | defer)                        │
  └────────────────────────────┬────────────────────────────────────┘
                               │ intent / result (typed, not JSON-RPC)
  ┌──────── HOST — BodyFunctionExtension ───────────────────────────┐
  │  body_manifest.json — catalog + backend routing                  │
  │  resolve(intent) → wire args (JSON Schema)                       │
  │  backend.execute → FunctionCallResult                             │
  └────────────────────────────┬────────────────────────────────────┘
                               │ vendor wire
  ┌──────── PERIPHERY (clients) ────────────────────────────────────┐
  │  mcp_stdio · mcp_sse · ide_execute_command · in_process · stub  │
  │  (Cursor · CIDE · lab CI · browser WASM host)                    │
  └───────────────────────────────────────────────────────────────────┘
```

- **Desk / AEE runtime — без Python** ([ADR-0025](CASA-ADR-0025-autonomous-execution-tier.md) Host vs Engine; [browser-wasm v0](CASA-future-von-neumann-browser-wasm-v0.md): lab = dev-only). Hot path CIDE — **host-native (C#)**, in-process motor; не subprocess к `python`, не embedded interpreter.
- MCP / IDE / HTTP **не** в `field_state`, `ltm/`, NCA hot path.
- Сырой ответ тула **не** целиком в LTM — только summary + slot outcomes + journal.
- На `predict` read path **нет** oracle из последнего tool result (наследие ADR-0021).

---

## Иерархия тела (Body stack)

**Не** «BodyExtension на каждый tool». Один dispatch; уровни ниже — **транспорт** и **wire** к периферии. Согласовано с ADR-0027 (периферия ↔ адаптер ↔ … ↔ мозг).

```text
  L0  AGENT STORE (мозг)
        FunctionCallIntent { function_id, arguments }
        ↑ FunctionCallResult (percept, summary)
  ─────────────────────────────────────────────────────────
  L1  BodyFunctionExtension          ← ОДИН на store / host profile
        catalog lookup · validate · dispatch · mm_event bridge
  ─────────────────────────────────────────────────────────
  L2  FunctionCallBackend          ← мало (по протоколу), не по tool
        mcp · ide_native · fieldbus · stub · (browser_host)
  ─────────────────────────────────────────────────────────
  L3  Transport / wire adapter     ← внутри backend (host injects)
        McpTransport: stdio | sse | loopback_in_process
        IdeNativeAdapter: IdeCommands / IdeMcpCommandExecutor direct
        FieldBusAdapter: motor/sensory codec (future)
  ─────────────────────────────────────────────────────────
  L4  PERIPHERY                      ← много entries, не новые extensions
        MCP server + tool name
        IdeCommands command_id
        датчик / actuator / file / WASM bridge
```

### Три сущности (не путать)

| Сущность | Сколько | Пример |
|----------|---------|--------|
| **`BodyFunctionExtension`** | **1** | `BodyFunctionExtension.dispatch(intent)` |
| **`FunctionCallBackend`** | **4–6** | `mcp`, `ide_native`, `fieldbus`, `stub` |
| **`FunctionSpec` / wire** | **много** | `tool.kb.read` → `read_knowledge_file` |

Каталог `body_manifest.functions[]` — **L4 routing table** для мозга: стабильный `function_id` → `backend_id` + `wire`.

### CIDE: MCP-режим и in-process — одна периферия, два транспорта

CIDE **может** стартовать как MCP-сервер (`--mcp-stdio`) — Cursor и внешний агент видят `ide_*` / `ide_execute_command` по JSON-RPC.

Когда **von-neumann в AEE (desk)**, motor — **C# in-process** → **`IdeCommands` / `IdeMcpCommandExecutor`**; **без** embedded Python и без spawn agent-notes MCP.

| Режим | Кто клиент | Runtime | L2 backend | Periphery |
|-------|------------|---------|------------|-----------|
| **Desk / AEE** | `CasaFieldAgentBrain` (C#) | **C#** in-process | **`ide_native`** | `command_id`: `read_knowledge_file`, `ide_agent_verify`, … |
| **MCP stdio** | Cursor / внешний процесс | любой | **`mcp`** | `server: cascade-ide`, `tool: ide_*` |
| **MCP loopback** | parity-тесты (lab CI) | optional | **`mcp`** | тот же wire, что stdio |
| **Lab** | pytest / CI | **Python** | **`stub`** \| **`mcp`** | fake percept / loopback |

**Не нужен** отдельный класс `InternalBodyAdapterExtension` **рядом** с `BodyFunctionExtension` — это **реализация L3 внутри backend `ide_native`** (или loopback-вариант `mcp`). Мозг и L1 **не меняются**.

```text
  Desk: CasaFieldAgentBrain (C#)      External: Cursor agent
         │                                    │
         ▼                                    ▼
  BodyFunctionExtension (C#)         BodyFunctionExtension (Python lab / Cursor host)
         │                                    │
         ▼                                    ▼
  backend: ide_native                backend: mcp (stdio)
         │                                    │
         ▼                                    ▼
  IIdeMcpActions direct              McpTransportAdapter
         │                                    │
         └──────────────┬─────────────────────┘
                        ▼
              IdeMcpCommandExecutor / IdeCommands
```

**Предпочтение desk-профиля:** `ide_native` (меньше сериализации). **`mcp` loopback** — fallback для parity-тестов «как Cursor». Wire в manifest **может быть одинаковым** (`kind: mcp`, `tool: ide_read_knowledge_file`); меняется только `backend_id` + host injection.

### CIDE: reference implementation (проверено в репо)

В `cascade-ide` **уже** реализован «один dispatch, несколько транспортов». Отдельного `InternalBodyAdapterExtension` **нет** — это роли типов ниже.

| Слой ADR | CIDE (факт) | Файл |
|----------|-------------|------|
| L4 periphery | `IdeCommands.*`, handlers partial | `Features/IdeMcp/Execution/IdeMcpCommandExecutor.*.cs` |
| L3 in-process | `MainWindowIdeMcpHost` → `_executor.ExecuteAsync` | `Features/IdeMcp/Application/MainWindowIdeMcpHost.cs` |
| L3 MCP server | `IdeMcpServer.CallToolByConventionAsync` → `ide_*` → `command_id` | `Services/IdeMcpServer.cs` |
| L3 MCP client | `McpClientService.CallToolAsync` — **внешние** серверы | `Services/McpClientService.cs` |
| **AEE substrate** | `IAgentEnvironmentService`, ladder, runner, DataBus | `Features/Agent/Environment/AgentEnvironmentService.cs` |
| Catalog / wire | `IdeMcpToolCatalog`, `IdeMcpToolNaming` | `Services/IdeMcpToolCatalog.cs` |
| Контракт host | `IIdeMcpActions.ExecuteCommandAsync` | `Services/IIdeMcpActions.cs` |

**Motor dispatch + слой AEE:**

```text
  Chat MAF (MEAI)     AEE agent brains              MCP stdio (--mcp-stdio)
  HostLlmToolBridge   llm_json · llm_maf · casa_field   IdeMcpServer
         │                    │                              │
         └────────────────────┼──────────────────────────────┘
                              ▼
               IIdeMcpActions.ExecuteCommandAsync
                              ▼
               IdeMcpCommandExecutor (command_id → handler)
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
  read_knowledge_file   ide_agent_* (AEE)    build · git · …
```

**AEE (Agent Execution Environment)** — host-контур CIDE ([ADR 0148](../../cascade-ide/docs/adr/0148-agent-execution-environment-verification-ladder-and-native-tooling.md)): `IAgentEnvironmentService`, verification ladder, environment task runner, sandbox, verify epoch, push через DataBus. Motor verify — **`ide_agent_verify`** / `ide_agent_*`, не shell escape по умолчанию (`MainWindowIdeMcpHost.IsAgentEnvironmentCommand` — off UI thread).

KB / agent-notes — handlers в `IdeMcpCommandExecutor.Handlers.AgentNotes.cs`.  
**Не desk hot path:** `casa_field_query` / `casa_field_infer` — v0 operator/MCP к lab; см. § **Desk runtime**.

**Вывод для CASA:** на **desk** motor L1 — **C#** в AEE (`BodyFunctionExtension` → `IIdeMcpActions`). **Python** (`casa/body/`) — **только lab** в `casa-ontology-payload`: контракты, stub/mcp smoke, parity с wire. **Не** embedded Python в CIDE на hot path.

### Lab (Python) vs Desk (C#)

**Контракт language-agnostic** (`FunctionCallIntent`, `FunctionCallResult`, `body_manifest.json`). **Две реализации L1**, одна периферия wire:

| Контур | Runtime | Репозиторий | Роль |
|--------|---------|-------------|------|
| **Lab** | **Python** | `casa-ontology-payload` | reference store + macro tick; `casa/body/` (`BodyFunctionExtension`, `stub`, `mcp`); pytest / CI |
| **Desk / AEE** | **C#** | `cascade-ide` | host-native store/tick + `CasaFieldAgentBrain`; motor L1 → `IIdeMcpActions` (форма модулей — по портированию) |

```text
  LAB (Python)                         DESK (C# / AEE)
  casa-ontology-payload                cascade-ide
       │                                    │
  von-neumann store (reference)             CasaFieldAgentBrain
  macro tick · routes                       host-native tick + store (C#)
       │                                    │
  BodyFunctionExtension.py                  BodyFunctionExtension (C#)
       │                                    │
  stub · mcp (CI)                           ide_native → IIdeMcpActions
       │                                    │
       └──────── body_manifest wire ────────┘
                         ▼
              IdeMcpCommandExecutor (CIDE L4)
```

**Инварианты split:**

- Lab **не** обязан грузить CIDE; desk **не** грузит Python на tick — **уже зафиксировано в видении**, этот ADR только привязывает body/AEE.
- Parity lab ↔ desk — **контракт + benches** (BiT9/act — **аналогия**, не клон 1:1).
- Desk — **host-native** реализация; не subprocess и не MCP-bridge к lab runtime.

### Desk runtime: без Python (аналогия BiT9)

**Не** «von-neumann = копия BiT9». Общий принцип из [ADR-0008](CASA-ADR-0008-layout-parity-bilingual-t9.md) / [bit9 roadmap](bit9-lexicon-parallel-roadmap.md): **lab на Python**, **продуктовый hot path — host-native**; детали модулей и границы портирования **ещё уточняются**.

| | Lab | Desk (целевое) |
|---|-----|----------------|
| Runtime | Python | **C#** in-process в AEE |
| Роль lab | reference, oracle, pytest | не участвует в tick CIDE |
| Прецедент | — | act: `Casa.Act.Core` — один из примеров host-native slice, не шаблон всего агента |

**Body + von-neumann на desk:**

- Store, macro tick, `BodyFunctionExtension` — **в host-native (C#)**; wire и контракты те же, что в lab.
- **`casa_field_query` / `casa_field_infer`** — v0 operator/MCP к lab (Cursor, smoke); **не** целевой desk hot path.
- Имена вроде `Casa.Store` / `Casa.Tick` — **условные** placeholders; ADR не фиксирует финальную нарезку сборок.

### Host stack: два extension point (не смешивать)

На host живут **два разных** «мозга», сходящихся в **одно тело** (L2 `ide_native` / L4 `IdeCommands`):

```text
  ┌─ AEE (Agent Execution Environment) — CIDE host shell ─────────────┐
  │  substrate: verify ladder · task runner · sandbox · DataBus      │
  │  motor: IIdeMcpActions · ide_agent_* · epoch / cancel / status   │
  │  agent_brain_id: llm_json | llm_maf | casa_field (von-neumann)   │
  └────────────────────────────┬──────────────────────────────────────┘
                               │
  ┌─ ACTOR A: casa_field (von-neumann) — DESK C# ────────────────────┐
  │  L0: host-native store + macro tick (детали — по портированию)   │
  │  L1: BodyFunctionExtension (C#) → IIdeMcpActions (ide_native)      │
  └────────────────────────────┬──────────────────────────────────────┘
                               │
  ┌─ ACTOR B: llm_json / llm_maf (host LLM brains) ──────────────────┐
  │  MEAI IChatClient + HostLlmToolBridge → AIFunction[]              │
  └────────────────────────────┬──────────────────────────────────────┘
                               │  command_id + args
                               ▼
              IdeMcpCommandExecutor + AEE handlers  (= L4 periphery)
```

| Extension | Где | «Мозг» | Контракт решения | Tool wire |
|-----------|-----|--------|------------------|-----------|
| **`BodyFunctionExtension`** | **Lab:** Python `casa/body/` · **Desk:** C# в AEE | поле / routes | `FunctionCallIntent` | `body_manifest` → backend |
| **`HostLlmToolBridge`** | CIDE host (C#) | cloud / Ollama LLM | `FunctionCallContent` / JSON salvage | `AIFunction` → `command_id` |

**Инвариант:** MEAI / MAF **не** заменяют `BodyFunctionExtension` и **не** входят в store hot path. Von-neumann **не** должен на macro tick ходить через `IChatClient`. Общее только **motor dispatch** и **каталог wire** (`IdeMcpToolCatalog` ↔ `body_manifest.functions[]`).

**Сегодня в CIDE** (до рефактора): AEE substrate **есть** (W1–W6 partial); `HostLlmToolBridge` размазан по MAF-чату; `AutonomousAgentService` — `llm_json` brain без MEAI; **`casa_field` — не подключён**.

### AEE: von-neumann как `agent_brain_id: casa_field`

**AEE** — не synonym для LLM и не только UI «Autonomous Agent». Это **среда исполнения агента** в CIDE: latency среды (build/test/sandbox) + единый motor dispatch + session/trace. **Von-neumann стыкуется в AEE** как третий brain profile — рядом с LLM, на **общем substrate**.

| `agent_brain_id` | Решение «что делать» | Tool bridge | Статус |
|------------------|----------------------|-------------|--------|
| **`llm_json`** | LLM → JSON `{ tool_call \| final }` | `AutonomousAgentService` → `IIdeMcpActions` / `McpClientService` | **есть** |
| **`llm_maf`** | LLM + native function calling | `HostLlmToolBridge` + `IChatClient.AsAIAgent` | **есть** (чат; planned в AEE loop) |
| **`casa_field`** | macro tick → `FunctionCallIntent` | **C#** `BodyFunctionExtension` → `IIdeMcpActions` | **planned** — von-neumann в AEE |

```text
  Agent Execution Environment (AEE)
  ├── IAgentEnvironmentService     verify ladder · runner · sandbox · epoch
  ├── IDataBus                     environment.task.* · AgentRunCompleted · …
  ├── IIdeMcpActions               motor dispatch (shared L4)
  └── agent session
        ├── llm_json    → AutonomousAgentService (step loop)
        ├── llm_maf     → HostLlmToolBridge (planned unified)
        └── casa_field  → CasaFieldAgentBrain (C#):
               macro tick / agent_wake (ADR-0025)
               classify → FunctionCallIntent
               BodyFunctionExtension.Dispatch → IIdeMcpActions
               FunctionCallResult → ingest → verbalize (ADR-0045)
               AEE: TryVerifyAfterStep после write-tools
```

**Von-neumann в AEE** — не «ещё один MCP»:

- **Session shell** — objective, safety, trace, Verify Epoch — **AEE (C#)**.
- **Store / tick** — host-native in-process; **без Python runtime** (lab остаётся oracle).
- **Motor** — C# `BodyFunctionExtension` + `body_manifest`; verify → **`ide_agent_verify`** где применимо.
- **`casa_field_*` MCP** — operator/lab surface, не substitute desk tick.

**Целевой glue (CIDE, planned):**

| Компонент | Роль |
|-----------|------|
| **`IAgentEnvironmentService`** | AEE substrate: verify, sandbox, status, orchestrator |
| **`IAgentBrain`** | `StepAsync(context) → BrainStep` (final \| motor_intent) |
| `LlmJsonAgentBrain` | обёртка `AutonomousAgentService` |
| `LlmMafAgentBrain` | MEAI loop через `HostLlmToolBridge` |
| **`CasaFieldAgentBrain`** | von-neumann tick (**C#**); `BodyFunctionExtension` → `IIdeMcpActions` |
| **`AeeAgentSessionHost`** | safety, history, brain selection, trace → DataBus |

**Унификация (next):** `CasaFieldAgentBrain` + host-native body/store в AEE; lab Python — контракт и benches; align `body_manifest` P0.

### Будущее: датчики / механика

Тот же stack (ADR-0027 симметрия motor ↔ sensory):

```text
  function_id: tool.vis.capture
    backend_id: mcp | fieldbus
    wire: { server: "webcam-capture", tool: "capture_frame" }
      OR { fieldbus: "sensor.cam0", opcode: "frame" }
```

Новый датчик = **periphery + wire row + (optional) perception plugin** — **не** новый L1.

### Именование в коде (target)

| ADR слой | Lab (Python · `casa-ontology-payload`) | Desk (C# · `cascade-ide`) |
|----------|------------------------------------------|-----------------------------|
| L1 body | `casa/body/extension.py` — reference | `BodyFunctionExtension` (C#) → `IIdeMcpActions` |
| Store / tick | Python `casa/` — lab | host-native (C#), **без Python runtime** |
| Act (аналогия) | Python benches | `Casa.Act.Core` — пример slice, не blueprint всего агента |
| **AEE** | — | `IAgentEnvironmentService`, `AeeAgentSessionHost` |
| Host LLM bridge | — | `HostLlmToolBridge` |
| Agent brains | lab tick scripts / CLI | `IAgentBrain`, **`CasaFieldAgentBrain`**, … |
| L2 backends | `backends/stub.py`, `backends/mcp.py` (lab) | `ide_native` = direct MCP host dispatch |
| L3 | `McpTransport` (lab CI) | `MainWindowIdeMcpHost`, `IdeMcpServer`, `McpClientService` |
| Catalog | `body_manifest.json`, `catalog_sync.py` | shared manifest + `IdeMcpToolCatalog` |

`backend_id: ide_command` в v0 manifest — **alias** для `ide_native` (wire `command_id`); при рефакторе свести к одному имени.

---

## Контракт v0

**Контракт** — language-agnostic. **Reference implementation (lab):** `casa/body/contracts.py`, `casa/body/extension.py` (Python). **Desk:** тот же контракт в C# (planned, `cascade-ide`).

### FunctionSpec (каталог)

Client-neutral описание «органа». MCP `tools/list` — **один из источников** sync, не единственный.

| Поле | Смысл |
|------|--------|
| `function_id` | Стабильный id в store (`tool.git.status`) |
| `title` / `description` | Для tool literacy и dialogue |
| `input_schema` | JSON Schema subset (object properties) |
| `backend_id` | Какой драйвер исполняет |
| `wire` | `{ "kind": "mcp", "server": "...", "tool": "..." }` или `ide_command`, `in_process`, … |

### FunctionCallIntent (мозг → тело)

```python
@dataclass
class FunctionCallIntent:
    function_id: str
    arguments: dict[str, Any]   # slots; host validates against input_schema
    call_id: str
    provenance: dict            # goal_id, tick_id, speaker, ...
    disposition: str | None     # accept | defer | refuse — from subject_agency
```

### FunctionCallResult (тело → мозг)

```python
@dataclass
class FunctionCallResult:
    call_id: str
    function_id: str
    ok: bool
    summary: str                # 1–3 предложения для dialogue / mm_event
    structured: dict | None     # parsed JSON if any
    error_code: str | None
    error_message: str | None
    is_transient: bool          # retry policy
    wire_backend: str
    duration_ms: int
```

`summary` + `structured` → `function_result_to_mm_event()` → ingest / journal.

### FunctionCallBackend (Protocol)

```python
class FunctionCallBackend(Protocol):
    backend_id: str
    def execute(self, spec: FunctionSpec, arguments: dict) -> FunctionCallResult: ...
    def health(self) -> dict: ...
```

Реализации v0:

| `backend_id` | Wire |
|--------------|------|
| `stub` | CI / **lab** smoke (Python) |
| `ide_native` | **Desk C#** — `IIdeMcpActions` / `IdeMcpCommandExecutor` direct (AEE primary) |
| `mcp` | MCP `tools/call` — stdio / loopback (**lab parity**, Cursor external) |
| `fieldbus` | Motor/sensory FieldBus (future, ADR-0027) |
| `in_process` | Lab Python handler registry |
| `ide_command` | **alias** → `ide_native` (v0 manifest; wire `command_id`) |

**Клиент-независимость:** backend в **body_manifest**. Cursor → **`mcp` stdio**; CIDE desk → **`ide_native` (C#)**; lab → **`stub`** / **`mcp` loopback** (Python). На desk **нет** Python `ide_native.py`.

---

## body_manifest.json (composition тела)

Рядом с store, **вне** gzip field body:

```json
{
  "schema_version": 1,
  "body_profile_id": "von-neumann-desk-v0",
  "default_backend": "stub",
  "functions": [],
  "backends": {
    "stub": {},
    "mcp": { "transport": "host_provided" }
  }
}
```

Sync каталога (optional host job): `tools/list` → append/update `functions[]` — **не** на каждом macro tick.

Пример: [`agents/von-neumann/body_manifest.example.json`](../agents/von-neumann/body_manifest.example.json).

---

## Tool catalog literacy + auto-ingest

**Принято:** чтобы субъект **понимал произвольный** `tools/list` (имена, описания, слоты), нужен **auto-ingest** — но **не** «весь JSON в LTM на каждый poll» и **не** oracle на read path.

### Два слоя (не путать)

| Слой | Кто | Что | Память агента? |
|------|-----|-----|----------------|
| **1. Catalog sync** | host | `tools/list` → merge `body_manifest.functions[]`, wire, schema | **Нет** — composition тела |
| **2. Auto-ingest** | host → agent | diff каталога → `ToolCard` → `mm_event` → hippo → sleep | **Да** — tool literacy на поле |

Sync без ingest = тело знает wire, мозг **не знает** «зачем `ide_git_status`».  
Ingest без sync = мозг учит устаревшие или выдуманные tools.

### Pipeline auto-ingest

```text
  [trigger] MCP connect · catalog diff · body_manifest version bump · scheduled (редко)
       ↓
  host: tools/list (allowlist servers) → normalize FunctionSpec
       ↓
  diff vs last_catalog_digest (added | changed | removed)
       ↓
  for each added/changed:
       ToolCard → tool_card_to_mm_event() → append tool_catalog.live.jsonl
       ↓
  ingest_mm_events (macro / sleep batch) — тот же контур, что sensory ADR-0027
       ↓
  sleep → co-occurrence: description tokens ↔ function_id ↔ function_family
       ↓
  (позже) gate / life → promote skill.tool.* routes
```

**ToolCard** (digest, не raw MCP):

| Поле | В ingest | В LTM после sleep |
|------|----------|-------------------|
| `function_id`, `title` | да | да |
| `description` (текст) | да, tokenized | bind «когда вызывать» |
| `input_schema` | **slot names + types summary** | slots, не full JSON Schema |
| `wire` | provenance only | **не** hot path |
| `server_id` | context tag | `tool:server:cascade-ide` |

### Когда срабатывает (triggers)

| Trigger | Ingest? |
|---------|---------|
| Первый connect MCP server (allowlist) | да — все tools как **added** |
| `tools/list` diff: new tool | да — одна карточка |
| description/schema изменились | да — **changed** (новый episod) |
| tool removed | mm_event `tool:removed` (не oracle — consolidated «был») |
| Каждый macro tick | **нет** |
| Полный re-ingest без diff | **нет** (идемпотентность по digest) |

### Shortlist vs full catalog

На **задачу** субъект не перебирает весь catalog:

```text
goal + dialogue context → function_family → shortlist (top-K из поля по bind)
  → classify function_id → compose slots → dispatch
```

Full catalog живёт в LTM **как лексикон**; на tick — **retrieval**, как lexicon при read.

### Auto-ingest ≠ auto-mastery

| После auto-ingest | После gate / life |
|-------------------|-------------------|
| «Знаю, что есть `tool.git.status` и зачем» (эпистемика tool) | «Умею вызвать» → `skill.tool.git_status` |
| bind description → function_id | `promote_capability_route` |
| **не** dispatch без plan step | verify: ok / IsError → Kolb |

Как literacy: ingest слова ≠ probe green на phrase.

### Allowlist + policy (host)

Auto-ingest **не** означает «все MCP мира»:

- `[body.catalog]` allowlist `server_id` в settings / body profile
- max tools per sync burst (backpressure)
- optional: teacher veto на `kind: tool_catalog` inbox

v0 non-goal «авто-sync без allowlist» — про **безграничный** sync; **controlled auto-ingest** — in scope.

### Контракт (planned code)

| Модуль | Роль |
|--------|------|
| `casa/body/catalog_sync.py` | `tools/list` → manifest merge + digest |
| `casa/body/tool_card.py` | `FunctionSpec` → `ToolCard` → `mm_event` |
| `casa/body/catalog_ingest.py` | diff → `tool_catalog.live.jsonl` |
| `tools/body_catalog_ingest.py` | CLI: sync + ingest batch для lab |
| `python -m casa.body.catalog_smoke` | idempotency smoke |

### Уровни literacy (T0–T4)

| Ур. | Содержание | Источник |
|-----|------------|----------|
| T0 | token: tool name | auto-ingest |
| T1 | intent → family | ingest + dialogue |
| T2 | slots из schema summary | ingest + compose |
| T3 | retry после IsError | life + Kolb |
| T4 | act + речь (ADR-0045) | full loop |

---

## Стадии зрелости

| Стадия | Кто выбирает function | Кто заполняет args |
|--------|----------------------|-------------------|
| **S0 relay** | Host / teacher / inbox rule | Host from dialogue parse |
| **S1 assisted** | Host proposes; subject defer/refuse | Host validates; subject confirms slot |
| **S2 field-native** | Routes `skill.tool.*` on field | Compose slots like phrase literacy |
| **S3 initiative** | Subject + autonomy_intent | Full loop + Kolb on error |

Extension point **один** на все стадии; меняется только источник `FunctionCallIntent`.

---

## Роутинг (ADR-0035): без organ в control

**Принято:** tool use маршрутизируется **существующими четырьмя роутерами** (`knowledge` / `capability` / `goal` / `applicability`). Отдельный `prism_tool_router` в **control hot path** (NativeAOT ~0.7 ms) **не** вводится.

### Водораздел зон

| Зона | Роль для tools | Не делает |
|------|----------------|-----------|
| **Router** (`route_kind` × 4) | Выбор тракта `tool.*`, `skill.tool.*`, `plan.tool.*`, `goal.tool.*` | Wire MCP / JSON-RPC |
| **Control** (`prism_control_*`) | **CEN act:** исполнить текущий `plan_step` (`step_focus: tool_dispatch`) | Хранить catalog; выбирать function_id |
| **Body** (`BodyFunctionExtension`) | Wire: validate args → backend → `FunctionCallResult` | Классификация намерения |
| **Host orchestrator** | Macro tick: dispatch после CEN; I/O-bound | Подмена субъекта на read path |

Function calling — **I/O-bound motor act** (как sleep job или sensory capture). Dispatch **не** на NCA micro-step; только **macro tick** / `agent_wake` ветка.

### Порядок tick (tool tract)

```text
thalamus relay  (modality: tool | motor — пропуск в macro, не в CA hot path)
  → goal_router           «хочу проверить сборку / прочитать notes / ответить в intercom»
  → applicability_router  plan.tool.* + plan_step[]
  → capability_router     skill.tool.git_status | skill.tool.build.verify | …
  → knowledge_router      (опц.) modality:tool → tool-literacy lattice / catalog hint
  → control: compose slots + subject_agency (accept | defer | refuse)
  → control: CEN act — step_focus == tool_dispatch
  → BodyFunctionExtension.dispatch(intent)     ← host, вне store hot path
  → function_result_to_mm_event → ingest / journal
  → dialogue verbalize (ADR-0045)
```

Control **читает** plan и active capability; **не** дублирует `Router.resolve`.

### Tool tract = ещё один класс задач (ADR-0034 §2)

Рядом с `lang.*`, `math.*`, `dialogue.*` — не новая ось архитектуры:

| Класс | Сигналы | Capability (примеры) | Applicability plan |
|-------|---------|----------------------|-------------------|
| Repo / git | partner «status», goal.tool.repo | `skill.tool.git_status` | `plan.tool.dispatch_v1` |
| Build / verify | surprise на compile, inbox verify | `skill.tool.build.verify` | `plan.tool.verify_ladder_v1` |
| Notes / KB | wake continuity, intercom | `skill.tool.notes.read` | `plan.tool.dispatch_v1` |
| IDE state | body check fail, «где я» | `skill.tool.ide.state` | `plan.tool.dispatch_v1` |

### Расширение `RouteContext` (planned)

Дополнительные dimensions для match — **без** нового `route_kind`:

| Поле | Слой | Пример |
|------|------|--------|
| `modality: tool` | capability | motor tract vs vis/t9 |
| `function_family` | capability | `git`, `build`, `notes`, `ide` |
| `surface_class` | capability | `repo`, `cli`, `intercom` |
| `function_id` | applicability | `tool.git.status` (после classify) |
| `step_focus: tool_dispatch` | control WM | триггер CEN → body dispatch |

`body_manifest.json` — **composition тела** (wire, backends). Routes на поле — **«умею ли вызывать git status»**, не JSON Schema MCP.

### Примеры routes (эмерджентно после gate)

**Capability** (после probe / life gate, `route_kind: capability`):

```json
{
  "route_kind": "capability",
  "match": { "modality": "tool", "function_family": "git", "surface_class": "repo" },
  "target_skill": "skill.tool.git_status",
  "provenance": { "gate": "tool_git_status_smoke", "function_id": "tool.git.status" }
}
```

```json
{
  "route_kind": "capability",
  "match": { "modality": "tool", "function_family": "build" },
  "target_skill": "skill.tool.build.verify",
  "provenance": { "gate": "ide_agent_verify_smoke" }
}
```

**Applicability** (`route_kind: applicability`):

```json
{
  "route_kind": "applicability",
  "match": { "goal_id": "goal.tool.verify_build", "skill_id": "skill.tool.build.verify" },
  "target_plan": "plan.tool.verify_ladder_v1",
  "steps": ["classify_function", "compose_args", "tool_dispatch", "verbalize_result", "verify_ok"]
}
```

```json
{
  "route_kind": "applicability",
  "match": { "goal_id": "goal.tool.repo_status" },
  "target_plan": "plan.tool.dispatch_v1",
  "steps": ["classify_function", "compose_args", "tool_dispatch", "verbalize_result"]
}
```

**Goal** (`route_kind: goal`):

```json
{
  "route_kind": "goal",
  "match": { "inbox_kind": "tool", "function_family": "build" },
  "target_goal": "goal.tool.verify_build"
}
```

### Thalamus + composition

| Механизм | Роль |
|----------|------|
| **Thalamus relay** (ADR-0024) | `modality: tool` / `motor` — в macro tick, не блокировать CA |
| **Store profile** | `motor_backend: body_manifest` — как `capture_backend` в ADR-0027 |
| **Отдельный prism в control** | **Non-goal** — dispatch через CEN + host hook |

### Стадии × роутинг

| Стадия | Роутинг | Dispatch |
|--------|---------|----------|
| **S0 relay** | Host/inbox rules (вне field routes) | `BodyFunctionExtension` |
| **S1 assisted** | applicability + `subject_agency` defer/refuse | то же |
| **S2 field-native** | `capability_router` → `skill.tool.*` | CEN `step_focus: tool_dispatch` |
| **S3 initiative** | `goal_router` + `autonomy_intent` | полный цикл; Kolb на `IsError` / verify fail |

### Non-goals (routing)

- `prism_tool_router` внутри `prism_control_*` hot path.
- Пятый `route_kind` параллельно knowledge/capability/goal/applicability.
- MCP catalog в FPN lattice или transfer_matrix literacy.
- Design-time seed всех `skill.tool.*` на wake «чтобы сразу умел IDE».

---

## Интеграция

| Точка | Hook |
|-------|------|
| **`resolve_chain`** (ADR-0035) | tool dimensions в `RouteContext`; plans с `tool_dispatch` step |
| Macro tick / `agent_wake` | `pending_function_calls[]` in session → dispatch batch **после** CEN |
| `step_focus: tool_dispatch` | WM trigger → `BodyFunctionExtension.dispatch` |
| `subject_agency` | REFUSE/DEFER → no dispatch; verbalize in ADR-0045 |
| `carrier_health` panel | `body.functions` — backend health, last error |
| `agent_journal` | append `function_call` entries |
| CIDE **AEE** | `CasaFieldAgentBrain` + host-native store/tick; **no Python runtime**; [ADR 0148](../../cascade-ide/docs/adr/0148-agent-execution-environment-verification-ladder-and-native-tooling.md) |
| CIDE motor | `ide_native` = `IIdeMcpActions` in-process; **no Python / no field MCP bridge on hot path** |
| **Lab** | Python `BodyFunctionExtension` + `stub`/`mcp` — wire parity, не runtime desk |
| **CIDE Host LLM** | `HostLlmToolBridge` → `ExecuteCommandAsync`; не в store hot path |
| **Catalog auto-ingest** | `catalog_sync` diff → `tool_catalog.live.jsonl` → `ingest_mm_events` |
| Cursor | External operator still valid (ADR-0027 operator mode) |

---

## Non-goals (v0)

- Полный MCP client в Python store process на hot path.
- **Unbounded** auto-sync всех MCP servers без allowlist (controlled auto-ingest — § Tool catalog literacy).
- Full JSON Schema каждого tool в LTM / на predict read path.
- Re-ingest entire catalog every wake без diff.
- LLM function calling как **единственный** путь (optional cold path only, ADR-0025).
- Embedded Python store / MCP-bridge (`casa_field_*`) как **desk hot path** (**desk = native C#**).
- Подмена von-neumann read path готовым LLM-ответом в AEE (`casa_field`).

---

## Acceptance (v0)

1. `BodyFunctionExtension.dispatch(intent)` with `stub` backend → `FunctionCallResult` + mm_event.
2. `body_manifest.example.json` documents wire shapes for mcp + ide_command.
3. Lab smoke: `python -m casa.body.smoke` green without Cursor/CIDE running.
4. ADR-0027 cross-ref: motor symmetric to sensory capture backend.
5. § Routing: tool tract documented; **no** control-zone organ; examples `skill.tool.*` / `plan.tool.*`.

### Acceptance (routing — next code)

1. `RouteContext` accepts `modality=tool`, `function_family` (doc + optional fields in `routing.py`).
2. WM `step_focus: tool_dispatch` → dispatch hook on macro tick (smoke with stub).
3. `promote_capability_route` path for one tool skill after gate smoke.

### Acceptance (catalog auto-ingest — v0 code)

1. ~~`catalog_sync` produces digest diff (added/changed/removed) from stub catalog.~~ **done** — `casa/body/catalog_sync.py`
2. ~~`tool_card_to_mm_event` → ingest smoke → words/context on field (lab).~~ **done** — `casa/body/catalog_smoke.py`
3. ~~Idempotent: second run with same digest → zero new events.~~ **done**
4. Wire to `ingest_mm_events` + sleep — **next** (jsonl ready at `{store}/tool_catalog.live.jsonl`)

### Acceptance (CIDE host — planned)

1. § **CIDE reference** — типы и три входа задокументированы; `ide_native` не spawn agent-notes на desk.
2. `HostLlmToolBridge` — один builder `AIFunction[]` для MAF-чата и (опц.) autonomous `llm_maf`.
3. **`casa_field` в AEE** — host-native tick smoke (не `casa_field_*` bridge); motor → `IIdeMcpActions`.
4. Lab Python — oracle/контракт; desk **без Python runtime**.

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-06-05 | § **Desk runtime: без Python** — host-native C#; BiT9 только как аналогия, не 1:1 |
| 2026-06-05 | § **Lab (Python) vs Desk (C#)** — split runtime |
| 2026-06-05 | § **AEE** — `casa_field` brain; CIDE ADR 0148 |
| 2026-06-05 | § **agent_brain_id** — llm_json / llm_maf / casa_field |
| 2026-06-06 | § **Иерархия тела** — L1 extension / L2 backend / L3 adapter / L4 periphery; CIDE MCP vs ide_native |
| 2026-06-06 | `catalog_sync`, `tool_card`, `catalog_ingest`, CLI + catalog_smoke |
| 2026-06-06 | § Tool catalog literacy + auto-ingest (two-layer sync vs ingest) |
| 2026-06-06 | § Routing integration (ADR-0035); accepted — no control organ; example routes |
| 2026-06-05 | ADR + `casa/body/*` contracts v0 |
