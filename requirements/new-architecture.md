# Agent OS --- Technical Architecture & Implementation Specification

**Status:** Proposed baseline\
**Audience:** Coding agents, technical leads, maintainers\
**Primary goal:** Build a modular, self-hostable, white-label agent
platform for coding, research, automation, data analysis and
orchestration.\
**Deployment targets:** Local Docker deployment and remote server
deployment.\
**Agent runtime:** Pi (TypeScript SDK).\
**LLM gateway:** Marga (existing project, evolved as the platform's
context, policy and model gateway).\
**Observability:** OpenLIT, with OpenTelemetry-compatible
instrumentation.\
**Commercial direction:** Nonprofit-first, free/low-cost by default,
architected for optional paid hosted and dedicated offerings.

------------------------------------------------------------------------

## 1. Executive decisions

This specification establishes the following decisions.

  -----------------------------------------------------------------------
  Area                                Decision
  ----------------------------------- -----------------------------------
  Product architecture                Modular platform with separable
                                      control plane, agent runtime,
                                      gateway and execution plane

  UI                                  React + TypeScript + Vite

  API/control plane                   Python + FastAPI

  Agent engine                        Pi SDK, isolated behind an internal
                                      runtime adapter

  LLM gateway                         Marga, evolved from the existing
                                      `evolvedHow/marga` project

  Provider compatibility              Marga direct adapters first;
                                      optional LiteLLM backend/adapter
                                      where it reduces maintenance

  Observability                       OpenLIT plus OpenTelemetry

  Database                            PostgreSQL

  Queue/cache                         Redis initially

  Execution isolation                 Docker workspaces; stronger
                                      sandboxing as an optional later
                                      tier

  Deployment                          Docker Compose, with local and
                                      server profiles

  Interfaces                          Web UI, CLI and REST API

  Autonomy                            Mixed: automatic for low-risk
                                      actions, approval for consequential
                                      actions

  Tenancy                             Single-user/local, dedicated
                                      organization, and shared
                                      multi-tenant modes

  Agent packaging                     Versioned declarative agent
                                      profiles

  Monetization                        Optional entitlements, usage
                                      metering, billing and signed
                                      self-hosted licenses
  -----------------------------------------------------------------------

### 1.1 Core architectural principle

**Own the product-specific control plane, agent profiles, context/policy
intelligence, Marga enhancements, tenant management and user experience.
Reuse Pi for agent execution, OpenLIT for observability, and mature
infrastructure for persistence, queues and sandboxing.**

Do not build a new general-purpose agent loop, tracing platform,
database, queue or container runtime.

### 1.2 Marga decision

Keep Marga. Do not replace it with a generic proxy.

The current public `main` branch of
`https://github.com/evolvedHow/marga` is a deliberately slim
Python/FastAPI proxy. Its README says that bangtag parsing, virtual
models, the larger configuration system, diagnostics, packs/extensions
and billing/telemetry were removed from the fuller margAI
implementation. The current lightweight code contains:

-   An OpenAI-compatible `/v1/chat/completions` endpoint.
-   Backend configuration and basic model listing.
-   A custom routing callback.
-   Before/after hooks.
-   HTTP transport for streaming and non-streaming calls.
-   In-memory usage counters.

The current implementation is a good small foundation, not yet a
production gateway. Specific gaps to address include streaming usage
accounting and response hooks, durable usage records, robust token
accounting, provider error normalization, authentication, tenant
isolation, retries/fallbacks, request validation, secret management and
policy enforcement.

The repository currently declares Apache License 2.0. Preserve required
license and attribution notices, identify modified files, and maintain a
third-party notices/SBOM process. Confirm rights to all code and
contributions before commercial redistribution.

**Marga's role in Agent OS:** context, policy and model gateway. It
resolves bangtags and context profiles, transforms prompts, applies
model policy, selects a route, enforces budgets and calls a provider
adapter. It exposes an OpenAI-compatible API so Pi and other clients can
use it.

**LiteLLM's role, if used:** optional provider compatibility/routing
backend. Do not let Marga and LiteLLM independently make conflicting
model-selection decisions. Marga remains the policy authority. LiteLLM
may handle provider protocol differences, provider fallback or model API
compatibility behind a Marga adapter. Keep a direct-provider path to
avoid making LiteLLM mandatory.

------------------------------------------------------------------------

## 2. Product scope

### 2.1 Initial agent types

1.  **Coding agent:** repository exploration, implementation,
    refactoring, tests, debugging, Git operations and pull-request
    preparation.
2.  **Research agent:** web research, document analysis, source
    synthesis, citations and structured research outputs.
3.  **Automation agent:** scheduled and event-triggered workflows, API
    integrations, MCP tools and repeatable procedures.
4.  **Data agent:** Python, SQL, DuckDB, CSV/Parquet, geospatial
    workflows, analysis and visualization.
5.  **Orchestrator:** decomposes larger requests, delegates to
    specialized agents, tracks dependencies and assembles verified
    results.

These are logical profiles, not five permanently running services. They
use the same Pi runtime with distinct instructions, tool permissions,
model policies and resource limits.

### 2.2 User interfaces

-   Web application for interactive tasks, configuration, approvals,
    monitoring and administration.
-   CLI for terminal-first workflows, scripting and automation.
-   REST API for integrations and external clients.
-   SSE for task event streaming to browsers and CLI clients.
-   Optional WebSocket only for genuinely bidirectional features.

All interfaces call the same API and authorization layer. The browser
and CLI must not call Pi, Marga, PostgreSQL or Redis directly.

### 2.3 Explicit non-goals for the first release

-   Kubernetes.
-   A large distributed microservice architecture.
-   A proprietary foundation model.
-   A full billing marketplace.
-   Autonomous unrestricted production access.
-   A new vector database.
-   A general-purpose workflow engine before workflow complexity
    requires one.
-   Reimplementation of provider APIs already supported by Marga or an
    optional gateway adapter.

------------------------------------------------------------------------

## 3. System architecture

``` mermaid
flowchart TB
  subgraph Clients
    WEB[React Web UI]
    CLI[CLI]
    API_CLIENT[External API Clients]
  end

  subgraph Control["Control Plane — FastAPI"]
    AUTH[Authentication and RBAC]
    TENANT[Organizations and Workspaces]
    TASKS[Task and Session Service]
    APPROVAL[Approval and Policy Service]
    PROFILES[Agent Profile Registry]
    USAGE[Usage and Entitlements]
  end

  subgraph Agent["Agent Platform"]
    ORCH[Orchestrator]
    PI[Pi Runtime Adapter]
    CONTEXT[Context and Memory Service]
    TOOLS[Tool Registry and Broker]
  end

  subgraph Gateway["Marga Gateway"]
    BANG[Bangtag Parser and Context Resolver]
    POLICY[Prompt and Model Policy]
    ROUTER[Model Selection and Budget]
    ADAPTERS[Provider Adapters]
  end

  subgraph Execution["Execution Plane"]
    SANDBOX[Docker Task Sandboxes]
    GIT[Git Worktrees]
    MCP[MCP and Internal Tools]
  end

  subgraph Infra["Persistence and Operations"]
    PG[(PostgreSQL)]
    REDIS[(Redis)]
    OBJECT[(File / Object Storage)]
    OPENLIT[OpenLIT]
    OTEL[OpenTelemetry Collector]
  end

  subgraph Providers["Model Providers"]
    LOCAL[Ollama]
    OPENROUTER[OpenRouter]
    CLOUD[Other Model APIs]
    LITELLM[Optional LiteLLM]
  end

  WEB --> AUTH
  CLI --> AUTH
  API_CLIENT --> AUTH
  AUTH --> TASKS
  AUTH --> TENANT
  TASKS --> ORCH
  ORCH --> PI
  PI --> CONTEXT
  PI --> TOOLS
  PI --> GATEWAY
  GATEWAY --> BANG
  BANG --> POLICY
  POLICY --> ROUTER
  ROUTER --> ADAPTERS
  ADAPTERS --> LOCAL
  ADAPTERS --> OPENROUTER
  ADAPTERS --> CLOUD
  ADAPTERS -. optional .-> LITELLM
  TOOLS --> SANDBOX
  TOOLS --> GIT
  TOOLS --> MCP
  TASKS --> PG
  TENANT --> PG
  USAGE --> PG
  TASKS --> REDIS
  PI --> OPENLIT
  GATEWAY --> OPENLIT
  OPENLIT --> OTEL
  CONTEXT --> OBJECT
```

### 3.1 Logical layers

1.  **Presentation:** React, CLI, REST API.
2.  **Control plane:** identity, tenant management, task lifecycle,
    approvals, policies, profiles, quotas and billing entitlements.
3.  **Agent platform:** Pi adapter, orchestration, context retrieval,
    tool registry and memory.
4.  **Gateway:** Marga context infusion, bangtags, model routing,
    provider abstraction and budgets.
5.  **Execution:** isolated Docker workspaces, Git worktrees, browser,
    Python, data tools and MCP.
6.  **Persistence/operations:** PostgreSQL, Redis, file/object storage,
    OpenLIT and OpenTelemetry.

### 3.2 Service boundaries

Start with a small number of deployable processes:

-   `web`: static React app served by a lightweight web server.
-   `api`: FastAPI control plane.
-   `runtime`: TypeScript service hosting Pi SDK.
-   `worker`: background task and scheduler worker; can initially share
    Python code with API.
-   `marga`: Python FastAPI gateway.
-   `postgres`: durable relational database.
-   `redis`: queue and cache.
-   `openlit`: observability UI/collector deployment according to the
    selected OpenLIT installation method.
-   `ollama`: optional local model server.
-   `litellm`: optional profile, not required for a minimal
    installation.
-   `proxy`: optional Caddy/Traefik reverse proxy in server deployments.

Do not split every logical module into a separate network service. Keep
modules in a modular monolith until scale or independent operational
requirements justify extraction.

------------------------------------------------------------------------

## 4. Technology stack

  -----------------------------------------------------------------------
  Concern                 Preferred technology    Notes
  ----------------------- ----------------------- -----------------------
  Frontend                React, TypeScript, Vite White-label SPA

  UI components           Tailwind CSS, shadcn/ui Theme through CSS
                                                  variables

  Backend                 Python, FastAPI,        Control plane and API
                          Pydantic                

  Agent runtime           Pi SDK, TypeScript      Dedicated runtime
                                                  process

  Gateway                 Marga, Python, FastAPI, OpenAI-compatible API
                          httpx                   

  Observability           OpenLIT + OpenTelemetry Instrument Pi, Marga,
                                                  API and workers

  Database                PostgreSQL              Authoritative
                                                  application state

  Queue/cache             Redis                   Queue, locks, ephemeral
                                                  cache

  SQL/data                DuckDB                  Optional execution
                                                  image

  Vector search           pgvector                Add only when semantic
                                                  retrieval is needed

  Execution               Docker                  Isolated task
                                                  containers

  Git isolation           Git worktrees           Parallel coding tasks

  Search/indexing         ripgrep, tree-sitter    Incremental repository
                                                  discovery

  Auth                    OIDC-compatible         Local mode may use
                          provider                simple local auth

  Reverse proxy           Caddy or Traefik        TLS and custom domains

  Packaging               Docker Compose          Local/server profiles
  -----------------------------------------------------------------------

Pin versions and images. Avoid floating `latest` tags in production
deployments. Maintain a dependency update process and compatibility
tests.

### 4.1 Language boundary

-   Python owns control plane, Marga, orchestration services, scheduling
    and data utilities.
-   TypeScript owns Pi runtime and runtime-specific adapters.
-   React/TypeScript owns the UI and CLI.
-   Communication between Python and TypeScript uses documented HTTP
    APIs and event schemas, not shared internal code.

------------------------------------------------------------------------

## 5. Marga gateway specification

Marga is a core differentiator and must be treated as a first-class
product component.

### 5.1 Responsibilities

Marga owns:

-   OpenAI-compatible request/response interface.
-   Provider and model catalog.
-   Bangtag parsing.
-   Context profile resolution and infusion.
-   Virtual model aliases.
-   Prompt transformation pipeline.
-   Model policy and selection.
-   Cost estimation and budget preflight.
-   Provider routing and fallback policy.
-   Request correlation and usage events.
-   Provider error normalization.
-   Gateway authentication and tenant context.
-   Optional response post-processing.

Marga does **not** own:

-   User login and interactive identity.
-   Organization membership and role administration.
-   Agent task lifecycle.
-   Agent tool execution.
-   Approval UI.
-   Authoritative subscription billing.
-   Long-term agent session persistence.

Marga receives a signed/internal tenant and task context from the
control plane. It must not trust arbitrary tenant IDs supplied by an
untrusted client.

### 5.2 Request pipeline

``` mermaid
flowchart TD
  A[OpenAI-compatible request] --> B[Authenticate gateway client]
  B --> C[Validate request and tenant context]
  C --> D[Parse bangtags]
  D --> E[Resolve profile and context references]
  E --> F[Apply context and prompt policies]
  F --> G[Estimate tokens and cost]
  G --> H{Budget and policy pass?}
  H -->|No| X[Return structured policy error]
  H -->|Yes| I[Resolve virtual model]
  I --> J[Select provider and model]
  J --> K[Provider adapter]
  K --> L[Normalize response or stream]
  L --> M[Record usage and trace]
  M --> N[Return response]
```

The pipeline must be deterministic where possible. Each stage should
emit structured metadata and timing spans. Never log secret values or
full prompts by default.

### 5.3 Bangtag system

Restore and formalize bangtags as a versioned syntax. Bangtags are
directives for context resolution, not arbitrary executable code.

Illustrative syntax:

``` text
!profile:finance.sales.audit
!profile:supplychain.inventory.replenishment
!context:project.current
!context:tenant.policies
!model:strong
!budget:task.default
```

The final syntax must be documented and backward-compatible with any
existing Marga syntax that the maintainer confirms should be retained.

Requirements:

-   Parse tags before model selection.
-   Support multiple tags with deterministic precedence.
-   Resolve aliases to immutable profile/version references.
-   Distinguish user-visible literal text from directives.
-   Support escaping/quoting so a user can discuss a bangtag without
    executing it.
-   Reject unknown or unauthorized tags with clear errors or treat them
    as literal according to explicit configuration.
-   Enforce organization-level access to profiles.
-   Record which profile versions were applied.
-   Prevent a prompt from escalating its own permissions, budget,
    tenant, or tool access.
-   Allow policy to disable tags for specific API keys, agents or
    tenants.
-   Include unit tests for malformed, nested, duplicated, conflicting
    and escaped tags.

Example request:

``` text
!profile:election.research
Compare the 2022 and 2024 district outcomes and identify the largest shifts.
```

Marga resolves `election.research` to an authorized, versioned context
package and injects only the context needed for this request.

### 5.4 Context profiles

A context profile is distinct from an agent profile.

-   **Agent profile:** defines role, workflow, tools, permissions,
    execution limits and output expectations.
-   **Context profile:** defines reusable domain knowledge, business
    rules, vocabulary, reference material and task-specific guidance.
-   **Model profile/virtual model:** defines model routing, provider
    preferences, cost ceilings, capabilities and fallback policy.

Example context package:

``` text
contexts/
  election/
    research/
      profile.yaml
      instructions.md
      references/
      tests/
  finance/
    sales/
      audit/
        profile.yaml
        instructions.md
        rules/
```

Example `profile.yaml`:

``` yaml
id: election.research
version: 1.0.0
description: Election research methodology and terminology

access:
  visibility: organization
  allowed_agents: [research, data-analysis, orchestrator]

content:
  instructions: instructions.md
  references:
    - references/methodology.md

retrieval:
  strategy: keyword_then_semantic
  max_chunks: 8
  max_tokens: 5000

policy:
  may_change_tool_permissions: false
  may_change_budget: false
  may_override_system_policy: false
```

Context packages must be versioned and content-hashed. Tasks should
record the exact versions used so a result can be reproduced.

### 5.5 Virtual models and model aliases

Support user-friendly virtual models such as:

-   `local`
-   `economical`
-   `economical-coding`
-   `strong`
-   `research`
-   `long-context`
-   `embedding`

Example:

``` yaml
virtual_models:
  economical-coding:
    candidates:
      - provider: ollama
        model: qwen-coder-local
        priority: 1
      - provider: openrouter
        model: configured-low-cost-coder
        priority: 2
    routing:
      strategy: capability_then_cost
      fallback_on:
        - provider_unavailable
        - rate_limited
        - timeout
    limits:
      max_cost_usd: 0.20
```

Do not hardcode transient vendor model names in agent profiles. Resolve
aliases centrally.

### 5.6 Routing policy

Routing must consider:

-   Required capabilities (tool calling, structured output, vision,
    context size).
-   Tenant allowlist and BYOK configuration.
-   Model availability and health.
-   Estimated request size.
-   Input/output price.
-   Cached input pricing where applicable.
-   Task budget.
-   Latency preference.
-   Provider rate limits.
-   Fallback eligibility.

Never route based solely on least-used backend. Maintain explicit
provider/model metadata and health checks.

### 5.7 Provider adapters

Define a stable adapter contract:

``` python
class ProviderAdapter(Protocol):
    async def list_models(self) -> list[ModelInfo]: ...
    async def complete(self, request: ChatRequest) -> ChatResponse: ...
    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]: ...
    async def health(self) -> ProviderHealth: ...
```

Initial adapters:

1.  OpenAI-compatible generic endpoint.
2.  OpenRouter.
3.  Ollama.
4.  Optional LiteLLM endpoint adapter.
5.  Additional native adapters only when the generic protocol is
    insufficient.

Normalize provider errors into categories: authentication, invalid
request, unsupported capability, rate limit, insufficient balance,
timeout, unavailable, context overflow and unknown.

### 5.8 Streaming correctness

Streaming is a first-class path, not a shortcut around middleware.

-   Emit the same correlation IDs and trace metadata as non-streaming.
-   Capture provider usage when supplied in terminal stream chunks.
-   If provider usage is unavailable, mark usage as estimated; do not
    present estimates as actual.
-   Run supported response hooks in a streaming-safe manner.
-   Ensure client disconnects cancel upstream requests when appropriate.
-   Apply timeouts and backpressure.
-   Preserve SSE framing and `[DONE]` semantics.
-   Record partial/aborted calls distinctly.
-   Do not buffer an entire stream merely to execute an after-hook.

### 5.9 Gateway API

Required initial endpoints:

``` text
GET  /health
GET  /ready
GET  /v1/models
POST /v1/chat/completions
GET  /admin/providers              # internal/admin only
GET  /admin/virtual-models         # internal/admin only
GET  /admin/usage                  # internal/admin only
```

Optional later endpoints:

``` text
POST /v1/embeddings
POST /v1/responses
```

Do not claim support for an API shape until it is implemented and
tested.

### 5.10 Marga security

-   Require authentication for non-local deployments.
-   Use separate internal service credentials and tenant-scoped client
    credentials.
-   Never accept client-provided provider secrets.
-   Retrieve secrets from the secret manager using a scoped reference.
-   Redact authorization headers and sensitive request fields.
-   Rate-limit by tenant and credential.
-   Enforce request size and context limits.
-   Restrict outbound destinations to prevent SSRF.
-   Protect admin endpoints from public exposure.
-   Validate all bangtag profile access server-side.
-   Prevent prompt injection from modifying gateway policy.
-   Use constant-time secret comparison where applicable.
-   Rotate and revoke keys.

------------------------------------------------------------------------

## 6. Pi runtime architecture

### 6.1 Pi integration

Use the Pi TypeScript SDK/programmatic runtime, not shelling out to the
interactive terminal UI as the primary integration.

Create an internal adapter so other services do not depend directly on
Pi-specific types.

``` typescript
export interface AgentRuntime {
  createSession(config: SessionConfig): Promise<SessionRef>;
  executeTask(sessionId: string, task: TaskRequest): Promise<TaskResult>;
  sendMessage(sessionId: string, message: string): Promise<void>;
  interrupt(sessionId: string): Promise<void>;
  getSession(sessionId: string): Promise<SessionState>;
  getEvents(sessionId: string, after?: number): AsyncIterable<AgentEvent>;
  compactSession(sessionId: string): Promise<CompactionResult>;
}
```

This is the platform contract, not a claim about Pi's native method
signatures. The adapter must map the contract to the installed Pi SDK
version and have integration tests.

### 6.2 Runtime responsibilities

-   Load agent profile and immutable version.
-   Load tenant policy and task constraints.
-   Configure Pi model/provider endpoint to use Marga.
-   Load authorized tool definitions.
-   Build task context through the Context Engine.
-   Execute the Pi agent loop.
-   Emit structured events.
-   Handle interruption and approval pauses.
-   Persist references to Pi session state.
-   Enforce iteration, tool-call, time and budget limits.
-   Return structured results.

### 6.3 Runtime/provider connection

Pi should normally send model requests to Marga through a supported
custom model/provider configuration or a custom Pi model adapter.
Validate tool calling, streaming, structured output, usage reporting and
model metadata with the actual Pi SDK version.

Do not assume that every OpenAI-compatible gateway feature maps
perfectly to Pi. Build a compatibility test suite.

### 6.4 Event schema

``` json
{
  "event_id": "uuid",
  "tenant_id": "tenant-uuid",
  "task_id": "task-uuid",
  "session_id": "session-uuid",
  "sequence": 12,
  "event_type": "tool.completed",
  "occurred_at": "2026-01-01T12:00:00Z",
  "payload": {
    "tool_name": "terminal.execute",
    "status": "success",
    "duration_ms": 1200
  }
}
```

Required event types:

-   `task.created`, `task.queued`, `task.started`
-   `agent.status`, `agent.message`
-   `model.requested`, `model.completed`, `model.failed`
-   `tool.requested`, `tool.started`, `tool.completed`, `tool.failed`
-   `approval.required`, `approval.granted`, `approval.denied`
-   `context.resolved`, `context.compacted`
-   `budget.warning`, `budget.exceeded`
-   `task.completed`, `task.failed`, `task.cancelled`

Do not expose private chain-of-thought. User-facing events may contain
status, concise rationale, tool activity, citations, progress and
outputs, but not hidden internal reasoning.

### 6.5 Durable sessions

Pi runtime processes must be replaceable and restartable. Persist
task/session metadata and event history outside the runtime process.
Store Pi session artifacts in a tenant-scoped persistent location. Treat
runtime-local memory as a cache, not the source of truth.

------------------------------------------------------------------------

## 7. Agent profiles

### 7.1 Profile layout

``` text
agent-profiles/
  coding/
    profile.yaml
    instructions.md
    tools.yaml
    permissions.yaml
    context.yaml
    evaluations/
  research/
  automation/
  data-analysis/
  orchestrator/
```

### 7.2 Agent profile example

``` yaml
id: coding
name: Software Development Agent
version: 1.0.0
runtime:
  engine: pi
  execution: isolated_docker

model_policy:
  planning: strong
  implementation: economical-coding
  verification: strong

tools:
  - filesystem.read
  - filesystem.write
  - terminal.execute
  - git.read
  - git.branch
  - git.commit
  - github.read
  - github.pull_request

context:
  repository_map: true
  incremental_files: true
  git_diff: true
  compaction: true

permissions:
  workspace_access: read_write
  external_network: restricted
  git_push: approval
  production_deploy: approval

limits:
  max_iterations: 35
  max_cost_usd: 0.50
  max_execution_minutes: 30
  max_tool_calls: 100

output:
  include_changed_files: true
  include_test_results: true
  include_summary: true
```

The `strong` and `economical-coding` names are Marga virtual model
aliases.

### 7.3 Profile rules

-   Profiles are declarative and versioned.
-   Profile content is validated against a JSON Schema or Pydantic
    schema.
-   A profile cannot grant permissions beyond tenant/platform policy.
-   Profiles may be global, organization-owned or private to a user.
-   Published global profiles are immutable versions.
-   Tasks pin the profile version and content hash.
-   Profiles may declare dependencies on tools, context packages and
    execution images.
-   Import/export must be portable and auditable.

------------------------------------------------------------------------

## 8. Context Engine and token efficiency

Context optimization is a first-class subsystem. Its purpose is to
provide the smallest sufficient context, not to indiscriminately
truncate information.

### 8.1 Context sources

  Source                     Retrieval
  -------------------------- -----------------------------------------------
  Platform/system rules      Always load
  Agent instructions         Always load for the selected profile
  Tenant policies            Load applicable subset
  Context/bangtag profiles   Resolve explicit tags and relevant rules
  Project instructions       Load for the selected project
  Repository map             Task-relevant subset
  Source files               Targeted retrieval
  Session history            Recent messages plus relevant prior decisions
  Task outputs               References and selective excerpts
  External documents         Search/retrieval with source references

### 8.2 Context pipeline

``` mermaid
flowchart TD
  A[Task and profile] --> B[Resolve mandatory instructions]
  B --> C[Resolve bangtags and context packages]
  C --> D[Classify task]
  D --> E[Retrieve repository/docs/memory]
  E --> F[Rank and deduplicate]
  F --> G[Estimate tokens]
  G --> H{Fits model budget?}
  H -->|Yes| I[Assemble request]
  H -->|No| J[Remove low relevance items]
  J --> K[Summarize or compact]
  K --> G
  I --> L[Marga]
```

### 8.3 Coding context

Use ripgrep, tree-sitter and Git:

-   Repository file map.
-   Language and file type.
-   Symbols (classes, functions, methods).
-   Imports and dependencies.
-   Relevant call sites.
-   Recent Git changes.
-   Test locations.
-   Project instructions.

Do not inject the full repository into prompts. Retrieve specific
files/symbols and expand context only when needed.

### 8.4 Tool output management

-   Limit default output size.
-   Preserve exit status and error messages.
-   Return concise excerpts plus a reference to full output.
-   Allow the agent to fetch more output on demand.
-   Do not silently discard potentially relevant diagnostics.
-   Store full tool output outside the model context where policy
    permits.

### 8.5 Compaction

When a context window approaches its configured threshold, create a
structured summary that preserves:

-   Objective and acceptance criteria.
-   Decisions and constraints.
-   Completed actions.
-   Changed files.
-   Outstanding work.
-   Relevant errors and test outcomes.
-   References to original events and artifacts.

Keep original history for audit and replay. Compaction must not destroy
source events.

### 8.6 Token budgets

Use provider/model metadata for context limits and tokenizer-aware
estimates where available. A characters/4 heuristic is acceptable only
as a clearly marked rough preflight estimate.

Example initial policy:

``` yaml
context_policy:
  target_window_tokens: 30000
  compact_at_ratio: 0.80
  preserve_recent_messages: 8
  preserve_decisions: true
  preserve_errors: true
  max_retrieved_chunks: 12
  semantic_retrieval: optional
```

The budget must reserve output capacity and include tool schemas, system
instructions and mandatory policies. Never drop mandatory safety or
authorization instructions to fit a context budget.

### 8.7 Optimization metrics

Track:

-   Input/output tokens.
-   Cached input tokens.
-   Tokens by context category.
-   Tokens per successful task.
-   Repeated-context ratio.
-   Retrieval precision and relevance.
-   Compaction frequency.
-   Context-overflow failures.
-   Estimated versus provider-reported usage.
-   Cost per successful task.

------------------------------------------------------------------------

## 9. OpenLIT and observability

OpenLIT is the preferred AI observability component. Use it with
OpenTelemetry-compatible instrumentation rather than making it the
application database or billing source of truth.

### 9.1 Instrumentation targets

-   Pi runtime: agent/session spans, model calls, tool execution.
-   Marga: request pipeline, bangtag resolution, routing, provider call
    and usage.
-   FastAPI: HTTP requests, database and queue operations.
-   Background workers: task lifecycle and retries.
-   Execution manager: sandbox create/start/stop and resource usage.

### 9.2 Correlation

Every task has a `trace_id`/correlation ID propagated across:

-   Web/CLI request.
-   FastAPI task creation.
-   Queue job.
-   Pi runtime.
-   Marga request.
-   Provider request.
-   Tool calls.
-   Result persistence.

Use tenant ID, task ID, session ID and provider/model as attributes,
subject to privacy and cardinality controls.

### 9.3 Sensitive data

-   Prompt/response content capture disabled by default in shared hosted
    mode.
-   Explicit opt-in diagnostics for self-hosted/local environments.
-   Redact secrets and personal data where possible.
-   Do not store chain-of-thought.
-   Define retention for traces and logs.
-   Separate operational telemetry from financial usage ledger.

### 9.4 Authoritative usage ledger

OpenLIT provides observability; the platform's own append-only usage
ledger is authoritative for tenant reporting and any future billing.
Reconcile provider-reported usage and costs when available. Label
estimates clearly.

------------------------------------------------------------------------

## 10. Tool registry and MCP

### 10.1 Tool categories

1.  Native tools: filesystem, terminal, Git.
2.  MCP tools: external servers and integrations.
3.  Internal tools: platform APIs and services.
4.  Specialized tools: Python, DuckDB, GIS, browser automation, search.

### 10.2 Tool metadata

``` yaml
id: github.create_pull_request
version: 1.0.0
type: mcp
server: github
permissions:
  - github.repository.write
risk: high
approval: required
timeout_seconds: 30
available_to:
  - coding
  - orchestrator
```

### 10.3 Tool broker

All tool execution passes through a broker that:

-   Authenticates the calling task/agent.
-   Checks tenant and project scope.
-   Checks tool permission and risk.
-   Obtains scoped credentials from the secret manager.
-   Requests approval when required.
-   Enforces timeouts and output limits.
-   Executes in the appropriate environment.
-   Records audit and usage events.
-   Redacts secrets from outputs.

Never pass raw MCP/provider credentials to the model.

### 10.4 Initial tools

  Tool               Coding   Research   Automation         Data
  ------------ ------------ ---------- ------------ ------------
  Filesystem     Read/write       Read   Read/write   Read/write
  Terminal              Yes   Optional          Yes          Yes
  Git                   Yes       Read     Optional     Optional
  GitHub                Yes       Read          Yes     Optional
  Web search       Optional        Yes          Yes          Yes
  Browser          Optional        Yes          Yes     Optional
  Python                Yes   Optional          Yes          Yes
  DuckDB           Optional   Optional          Yes          Yes
  PostGIS          Optional   Optional          Yes          Yes
  MCP                   Yes        Yes          Yes          Yes

Package data science/GIS dependencies in optional execution images
instead of bloating every worker.

------------------------------------------------------------------------

## 11. Mixed autonomy and approvals

### 11.1 Risk levels

  -----------------------------------------------------------------------
  Level                   Meaning                 Default behavior
  ----------------------- ----------------------- -----------------------
  A0                      Read-only               Automatic

  A1                      Reversible local change Automatic within
                                                  isolated workspace

  A2                      External or             Approval required
                          consequential change    

  A3                      Destructive or          Explicit approval and
                          production-impacting    additional confirmation
  -----------------------------------------------------------------------

Examples:

-   Read repository/search web: A0.
-   Edit files in isolated workspace/run tests/create branch: A1.
-   Push remote branch/create public PR/send email: A2.
-   Delete remote resources/deploy production: A3.

### 11.2 Approval binding

Approval applies to the exact action payload, resource and scope. If the
agent changes the action after approval, request approval again.

Approval records include:

-   Tenant, task and requesting agent.
-   Action and normalized payload hash.
-   Risk level.
-   Resource affected.
-   Reason and expected impact.
-   Requested/expiry timestamps.
-   Approver and decision.
-   Execution result.

Do not hold a worker while waiting for a person. Persist paused state,
release the worker and resume after approval.

### 11.3 Policy precedence

Effective permissions are the intersection of:

1.  Platform hard limits.
2.  Organization policy.
3.  User role and project permissions.
4.  Agent profile permissions.
5.  Task-specific permissions.

A prompt, bangtag or agent profile cannot elevate permissions.

------------------------------------------------------------------------

## 12. Multi-agent orchestration

Use a hierarchical orchestrator, not an unconstrained swarm.

``` mermaid
flowchart TD
  U[User request] --> O[Orchestrator]
  O --> P[Plan and acceptance criteria]
  P --> R[Research child task]
  P --> C[Coding child task]
  P --> D[Data child task]
  P --> A[Automation child task]
  R --> X[Result aggregation]
  C --> X
  D --> X
  A --> X
  X --> V[Verification]
  V --> F[Final result]
```

### 12.1 Delegation rules

-   Delegate only when work is meaningfully parallel or requires a
    specialist.
-   Pass only relevant task context, not the full parent conversation.
-   Give every child task an explicit objective, inputs, output schema
    and budget.
-   Use separate workspaces for concurrent code modifications.
-   Define dependencies between child tasks.
-   Enforce maximum depth, child count, concurrency and aggregate
    budget.
-   Detect cycles and repeated delegation.
-   Record parent/child relationships.
-   Aggregate structured outputs and verify before presenting results.

### 12.2 Child task contract

``` json
{
  "parent_task_id": "uuid",
  "agent_profile": "research",
  "objective": "Investigate the current API behavior",
  "inputs": ["docs/api.md"],
  "expected_output": {
    "format": "markdown",
    "include_sources": true
  },
  "budget": {
    "max_cost_usd": 0.10,
    "max_iterations": 10
  }
}
```

Start with sequential orchestration and bounded parallel child tasks. Do
not introduce a complex workflow engine until durable retries, branching
and long-running workflows justify it.

------------------------------------------------------------------------

## 13. Execution plane and sandbox security

Agents can run untrusted code. Treat execution workspaces as hostile.

### 13.1 Per-task workspace

Each task receives:

-   Unique workspace directory or volume.
-   Unique Git worktree where applicable.
-   Non-root container user.
-   CPU, memory, process and disk limits.
-   Execution timeout.
-   Restricted network policy.
-   Explicit mounted paths.
-   No host Docker socket.
-   No access to other tenants' workspaces.
-   Scoped credentials only when required.

### 13.2 Docker controls

-   Use rootless Docker or a dedicated sandbox host where practical.
-   Drop Linux capabilities.
-   Use read-only root filesystem where possible.
-   Apply seccomp/AppArmor profiles.
-   Limit PIDs, memory and CPU.
-   Avoid privileged containers.
-   Do not mount host home directories.
-   Restrict egress and block cloud metadata endpoints.
-   Pin execution images by version/digest.
-   Clean up expired containers and volumes.

Docker is not a perfect hostile multi-tenant security boundary. For
stronger isolation, evaluate gVisor or Firecracker later.

### 13.3 Network zones

1.  Control plane network.
2.  Internal service network (database, Redis, gateway).
3.  Execution network with explicitly allowed outbound destinations.

Agent sandboxes must not connect directly to PostgreSQL, Redis, Docker
API or other tenants' resources.

### 13.4 Secrets

Use a `SecretManager` interface. Local deployment may use encrypted
local storage; hosted deployment should use KMS/secret-manager-backed
encryption.

-   Never store plaintext API keys in profile/config JSON.
-   Never send credentials to the model.
-   Mask secrets in logs and tool output.
-   Scope secrets to organization, project and task.
-   Support rotation and revocation.
-   Do not mount long-lived credentials into containers when short-lived
    credentials or brokered requests are possible.

------------------------------------------------------------------------

## 14. Data model and tenancy

### 14.1 Deployment modes

1.  **Local/single user:** one operator, local database and local
    workspaces.
2.  **Dedicated organization:** one organization per deployment.
3.  **Shared multi-tenant:** multiple organizations share services with
    strict isolation.

All modes use the same application code and schema.

### 14.2 Core entities

-   `organizations`
-   `users`
-   `memberships`
-   `workspaces`
-   `projects`
-   `repositories`
-   `agent_profiles`
-   `context_profiles`
-   `model_profiles`
-   `provider_configs`
-   `tool_servers`
-   `tasks`
-   `task_dependencies`
-   `sessions`
-   `task_events`
-   `approval_requests`
-   `usage_events`
-   `audit_events`
-   `secrets_metadata`
-   `custom_domains`
-   `branding_configs`
-   `entitlements`
-   `subscriptions` (optional)
-   `licenses` (optional)

### 14.3 Illustrative SQL foundation

``` sql
CREATE TABLE organizations (
  id UUID PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  deployment_mode TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  display_name TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE memberships (
  organization_id UUID NOT NULL REFERENCES organizations(id),
  user_id UUID NOT NULL REFERENCES users(id),
  role TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  PRIMARY KEY (organization_id, user_id)
);

CREATE TABLE workspaces (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (organization_id, id)
);

CREATE TABLE projects (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id),
  workspace_id UUID,
  name TEXT NOT NULL,
  repository_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (organization_id, workspace_id)
    REFERENCES workspaces(organization_id, id)
);

CREATE TABLE agent_profiles (
  id UUID PRIMARY KEY,
  organization_id UUID REFERENCES organizations(id),
  profile_key TEXT NOT NULL,
  version TEXT NOT NULL,
  content JSONB NOT NULL,
  content_hash TEXT NOT NULL,
  visibility TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tasks (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id),
  project_id UUID,
  agent_profile_id UUID NOT NULL REFERENCES agent_profiles(id),
  created_by UUID NOT NULL REFERENCES users(id),
  status TEXT NOT NULL,
  objective TEXT NOT NULL,
  input JSONB NOT NULL,
  result JSONB,
  budget JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  FOREIGN KEY (organization_id, project_id)
    REFERENCES projects(organization_id, id)
);

CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id),
  task_id UUID NOT NULL REFERENCES tasks(id),
  runtime TEXT NOT NULL,
  runtime_session_ref TEXT,
  state JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE task_events (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id),
  task_id UUID NOT NULL REFERENCES tasks(id),
  sequence BIGINT NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (task_id, sequence)
);

CREATE TABLE usage_events (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id),
  task_id UUID REFERENCES tasks(id),
  provider TEXT,
  model TEXT,
  input_tokens BIGINT NOT NULL DEFAULT 0,
  output_tokens BIGINT NOT NULL DEFAULT 0,
  cached_tokens BIGINT NOT NULL DEFAULT 0,
  estimated_cost NUMERIC(18,8),
  actual_cost NUMERIC(18,8),
  usage_source TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tasks_org_created
  ON tasks(organization_id, created_at DESC);
CREATE INDEX idx_events_task_sequence
  ON task_events(task_id, sequence);
CREATE INDEX idx_usage_org_created
  ON usage_events(organization_id, created_at DESC);
```

This is a starting point, not a complete migration. Production schema
must add tenant-aware composite foreign keys for all tenant-owned
references, RLS policies, immutable audit records, indexes, retention
and deletion workflows, and constraints for profile versions.

### 14.4 Tenant isolation

-   Backend authorization is mandatory.
-   PostgreSQL RLS is defense in depth.
-   Set tenant context transaction-locally; never rely on a persistent
    pooled connection variable.
-   Composite tenant-aware foreign keys prevent cross-tenant references.
-   Tenant ID from the client is not proof of authorization.
-   Secrets, object storage paths, caches, queue messages and logs must
    be tenant-scoped.
-   Automated cross-tenant isolation tests are release blockers.

### 14.5 Roles

-   Platform admin.
-   Organization owner.
-   Organization admin.
-   Developer.
-   Agent operator.
-   Viewer.
-   Billing admin.

Use RBAC plus resource-level checks for projects, repositories, tools
and approvals.

------------------------------------------------------------------------

## 15. API specification

Use REST for resources and SSE for event streams. Publish OpenAPI.

### 15.1 Namespaces

``` text
/api/v1/auth
/api/v1/organizations
/api/v1/users
/api/v1/memberships
/api/v1/workspaces
/api/v1/projects
/api/v1/repositories
/api/v1/agents
/api/v1/agent-profiles
/api/v1/context-profiles
/api/v1/tools
/api/v1/integrations
/api/v1/tasks
/api/v1/sessions
/api/v1/approvals
/api/v1/models
/api/v1/providers
/api/v1/usage
/api/v1/branding
/api/v1/admin
/api/v1/billing
```

### 15.2 Key endpoints

  Method   Endpoint                     Purpose
  -------- ---------------------------- ----------------------
  POST     `/tasks`                     Create task
  GET      `/tasks/{id}`                Read task
  POST     `/tasks/{id}/cancel`         Cancel task
  POST     `/tasks/{id}/resume`         Resume task
  GET      `/tasks/{id}/events`         SSE events
  GET      `/sessions/{id}`             Session details
  POST     `/sessions/{id}/message`     Continue session
  POST     `/approvals/{id}/decision`   Approve/reject
  GET      `/agents`                    Available agents
  GET      `/agent-profiles`            Profile catalog
  GET      `/usage/summary`             Usage analytics
  GET      `/usage/tasks/{id}`          Task usage
  POST     `/providers`                 Configure provider
  GET      `/organizations/current`     Current organization

### 15.3 Task request

``` json
{
  "agent": "coding",
  "project_id": "project-uuid",
  "objective": "Fix the login validation bug",
  "execution": {
    "mode": "isolated",
    "branch": "agent/fix-login-validation"
  },
  "autonomy": {
    "mode": "mixed"
  },
  "budget": {
    "max_cost_usd": 0.50,
    "max_iterations": 30
  }
}
```

### 15.4 API requirements

-   Idempotency key for task creation.
-   Pagination and stable sorting.
-   Request validation.
-   Tenant authorization middleware.
-   Rate limiting.
-   Structured errors.
-   Correlation IDs.
-   API versioning.
-   Revocable scoped API keys.
-   SSE reconnect using event sequence/Last-Event-ID.
-   No master gateway credentials exposed to clients.

------------------------------------------------------------------------

## 16. CLI specification

The CLI is a first-class client of the API, not a separate agent
implementation.

Initial commands:

``` bash
agentos init
agentos login
agentos status
agentos start
agentos stop
agentos update

agentos agents list
agentos agents inspect coding

agentos task run --agent coding --project my-project "Fix the login bug"
agentos task list
agentos task show <task-id>
agentos task logs <task-id>
agentos task cancel <task-id>
agentos task resume <task-id>

agentos approvals list
agentos approvals approve <approval-id>
agentos approvals reject <approval-id>

agentos config show
agentos config set model.default economical
agentos usage summary
```

CLI must support interactive streaming and non-interactive JSON output
for scripting.

------------------------------------------------------------------------

## 17. Web application specification

### 17.1 Primary navigation

-   Dashboard.
-   New Task.
-   Tasks / History.
-   Agents.
-   Projects / Repositories.
-   Context Profiles.
-   Models / Providers.
-   Tools / Integrations.
-   Usage.
-   Approvals.
-   Organization Settings.
-   Platform Administration (platform admins only).

### 17.2 Task workspace

The task view should show:

-   User objective and selected agent.
-   Status and elapsed time.
-   Progress/event timeline.
-   Tool activity and outcomes.
-   Model/provider and usage metadata.
-   Approval requests.
-   Generated artifacts and changed files.
-   Test results.
-   Final summary.
-   Cost and token usage.

Do not display hidden chain-of-thought. Display concise progress and
action summaries.

### 17.3 White-labeling

Tenant-configurable:

-   Product/organization name.
-   Light/dark logos and favicon.
-   Theme colors through CSS variables.
-   Typography.
-   Custom domain.
-   Visibility of provider/model/cost information.
-   Optional "powered by" branding.

Domain-to-tenant mapping must use verified domains. Never trust an
arbitrary browser-supplied tenant slug for authorization.

------------------------------------------------------------------------

## 18. Local and server deployment

### 18.1 Local profile

-   Web UI.
-   FastAPI.
-   Pi runtime.
-   Marga.
-   PostgreSQL.
-   Redis.
-   Optional Ollama.
-   Optional OpenLIT.

Local URL: `http://localhost:<configured-port>`.

The local profile should work without any paid hosted model provider
when a suitable local model is configured. Explain hardware/model
requirements and that local inference may be slower.

### 18.2 Server profile

-   Reverse proxy with TLS.
-   Web UI.
-   API.
-   Runtime worker(s).
-   Marga.
-   PostgreSQL.
-   Redis.
-   OpenLIT/collector.
-   Optional Ollama or external provider configuration.
-   Execution sandbox manager.

Remote users access the same web UI. Agent execution remains on the
server or designated sandbox host.

### 18.3 Compose files

``` text
compose.yaml
compose.local.yaml
compose.server.yaml
compose.gpu.yaml
compose.dev.yaml
```

Use Compose profiles for optional services. Do not require Kubernetes.

### 18.4 Installation commands

``` bash
agentos init
agentos start
agentos status
agentos stop
agentos update
agentos backup
agentos restore
```

### 18.5 Homelab deployment

Support deployment on a modest x86-64 Linux host. Keep model inference
optional and separately configurable. A small CPU host can run the
control plane and proxy while using a hosted low-cost model provider.
GPU inference is an optional profile, not a prerequisite.

------------------------------------------------------------------------

## 19. White-label, entitlements and monetization

### 19.1 Entitlements

Feature availability must be expressed as entitlements, not hardcoded
plan-name checks.

``` yaml
entitlements:
  custom_agent_profiles: true
  custom_branding: true
  custom_domain: true
  byok: true
  hosted_models: false
  max_users: 20
  concurrent_tasks: 3
  max_task_runtime_minutes: 60
```

These are example values only.

### 19.2 Deployment/edition modes

-   Community/self-hosted.
-   Nonprofit/dedicated.
-   Hosted shared.
-   Hosted dedicated.

Same application code; configuration and entitlements determine enabled
features.

### 19.3 Billing

Defer payment integration until the platform has real usage. When added,
use a billing-provider adapter (Stripe is a candidate) and
webhook-driven subscription state. Billing must not be required for
self-hosted use.

### 19.4 Self-hosted license

If a commercial edition requires a license, use a signed license
document containing license ID, organization, edition, expiry/renewal,
entitlements and signature. Verify locally with a public key. Do not
require an online licensing call on every startup.

------------------------------------------------------------------------

## 20. Usage accounting and budgets

### 20.1 Per-request usage

Capture:

-   Tenant, user, task, session.
-   Provider and model.
-   Input/output tokens.
-   Cached tokens.
-   Provider-reported usage.
-   Estimated usage if actual unavailable.
-   Estimated and actual cost.
-   Retry/fallback count.
-   Latency.
-   Success/failure.
-   Context profile IDs and versions (not sensitive content).

### 20.2 Budget controls

Each task may define:

-   Maximum cost.
-   Maximum input/output tokens.
-   Maximum iterations.
-   Maximum tool calls.
-   Maximum execution time.
-   Maximum child agents.
-   Maximum aggregate child budget.

The control plane enforces task limits independently of Marga/provider
limits. Provider-side limits are additional protection, not the sole
enforcement mechanism.

### 20.3 Budget exhaustion

When a hard budget is reached:

-   Stop issuing new model calls.
-   Cancel or safely terminate active work where possible.
-   Persist partial results.
-   Mark task `budget_exceeded`.
-   Explain the reason.
-   Allow an authorized user to raise the budget and resume.

Do not silently switch to an unapproved provider or model.

------------------------------------------------------------------------

## 21. Task lifecycle and durable execution

### 21.1 Task states

``` text
queued
initializing
running
awaiting_approval
paused
completed
failed
cancelled
budget_exceeded
timed_out
```

### 21.2 Recovery

-   Queue messages are not the only record of task state.
-   Use durable database state and task leases.
-   Workers send heartbeats.
-   Expired leases can be recovered.
-   Retries must be idempotent where possible.
-   Avoid duplicate external side effects.
-   Persist event sequence numbers.
-   Resume from a known checkpoint or restart a safe step.
-   Record partial completion and provider/tool failures.

Use Redis-backed workers initially. Evaluate a durable workflow engine
such as Temporal only if long-running workflow complexity warrants it.

------------------------------------------------------------------------

## 22. Security and privacy baseline

Security requirements are release blockers.

1.  OIDC or secure local authentication.
2.  Secure session cookies and CSRF protections where applicable.
3.  Tenant-aware authorization on every resource.
4.  PostgreSQL RLS and composite tenant-aware references.
5.  No plaintext secrets in DB configuration or logs.
6.  No Docker socket in agent containers.
7.  No privileged agent containers.
8.  Network egress controls.
9.  Scoped tool credentials.
10. Approval binding to exact action payload.
11. Rate limiting and request-size limits.
12. Audit logs for sensitive operations.
13. Secret and prompt redaction.
14. Dependency and container image scanning.
15. Backup encryption and restore testing.
16. Retention/deletion policy.
17. Cross-tenant security tests.
18. No hidden reasoning exposed in UI or logs.

For shared hosted deployments, default to metadata-only observability
and explicit opt-in for prompt content diagnostics.

------------------------------------------------------------------------

## 23. Testing and quality strategy

### 23.1 Unit tests

-   Bangtag parsing, escaping and precedence.
-   Context profile resolution and authorization.
-   Model alias resolution.
-   Cost estimation.
-   Provider error normalization.
-   Streaming parser and cancellation.
-   Budget enforcement.
-   Approval policy.
-   Agent profile validation.
-   Tenant authorization.

### 23.2 Integration tests

-   Pi → Marga → mock provider.
-   Pi tool calling through Marga.
-   Streaming and non-streaming parity.
-   Provider fallback.
-   Ollama local provider.
-   Optional LiteLLM adapter.
-   PostgreSQL persistence.
-   Redis worker recovery.
-   Docker sandbox lifecycle.
-   OpenLIT/OpenTelemetry trace propagation.

### 23.3 Security tests

-   Cross-tenant task/session/project access.
-   Tenant-scoped secrets.
-   SSRF and outbound network restrictions.
-   Prompt/bangtag privilege escalation.
-   Tool permission bypass.
-   Approval payload mutation.
-   Container escape hardening checks.
-   Public admin endpoint exposure.

### 23.4 Agent evaluations

Coding: - Correct file selection. - Correct implementation. - Build/test
success. - Minimal unrelated changes. - Permission compliance. - Budget
compliance.

Research: - Source relevance. - Citation quality. - Accuracy. -
Unsupported-claim rate. - Completeness.

Data: - Query/calculation correctness. - Reproducibility. - Data
integrity. - Missing-data handling.

Automation: - Correct execution. - Idempotency. - Approval compliance. -
Retry safety.

Orchestration: - Appropriate delegation. - No duplicated work. - Child
budget compliance. - Correct aggregation and verification.

------------------------------------------------------------------------

## 24. Repository structure

Use a monorepo initially.

``` text
agent-os/
  apps/
    web/
    api/
    runtime/
    cli/
    worker/
  services/
    marga/
  packages/
    shared-types/
    api-client/
    agent-profiles/
    context-engine/
    model-router/
    provider-adapters/
    tool-registry/
    permission-engine/
    execution-manager/
    usage-metering/
    branding-engine/
  agent-profiles/
    coding/
    research/
    automation/
    data-analysis/
    orchestrator/
  context-profiles/
    examples/
  infrastructure/
    docker/
    compose/
    postgres/
    redis/
    openlit/
    litellm/
    monitoring/
  migrations/
  tests/
    unit/
    integration/
    security/
    tenant-isolation/
    evaluations/
    e2e/
  docs/
    architecture/
    api/
    deployment/
    security/
    development/
  compose.yaml
  compose.local.yaml
  compose.server.yaml
  compose.dev.yaml
  .env.example
  README.md
  LICENSE
  THIRD_PARTY_NOTICES.md
```

Marga may initially remain a separately versioned package/repository or
be included as a pinned Git submodule/subtree. Choose one approach and
document how changes are synchronized. Do not fork silently or lose
upstream history.

------------------------------------------------------------------------

## 25. Implementation roadmap

Build in milestones. Each milestone must compile, run and have tests
before proceeding.

### Milestone 0 --- Repository and compatibility spike

-   Inspect current Marga repository and identify current
    branch/version.
-   Inventory any fuller margAI/bangtag implementation and confirm which
    features should be restored.
-   Pin Pi SDK version.
-   Prove Pi can call Marga with tool calling and streaming.
-   Prove Marga can route to one hosted provider and Ollama.
-   Prove OpenLIT receives correlated traces.
-   Record protocol gaps and compatibility decisions.

**Exit criteria:** an end-to-end minimal Pi → Marga → model call works,
with streaming, tool calling and trace correlation demonstrated.

### Milestone 1 --- Foundation

-   Monorepo.
-   Compose local profile.
-   PostgreSQL and migrations.
-   Redis.
-   FastAPI health/auth skeleton.
-   Pi runtime adapter.
-   Marga service.
-   One provider.
-   Basic coding agent profile.

**Exit criteria:** a CLI/API request runs a coding task against a local
test repository.

### Milestone 2 --- Marga core

-   Bangtag parser.
-   Context profile resolver.
-   Virtual model aliases.
-   Provider adapter contract.
-   Routing and fallback policy.
-   Streaming-safe usage tracking.
-   Persistent usage events.
-   Gateway authentication and limits.
-   Tests for parsing, policy and streaming.

**Exit criteria:** a request with a bangtag injects an authorized
context profile and routes through a virtual model, with durable usage
records.

### Milestone 3 --- Task lifecycle and UI

-   Task/session persistence.
-   Event schema and SSE.
-   React dashboard.
-   Task detail/timeline.
-   Task history.
-   CLI streaming.
-   Cancellation and resume.

**Exit criteria:** create, monitor, cancel and inspect tasks through
both UI and CLI.

### Milestone 4 --- Execution and autonomy

-   Docker sandbox manager.
-   Git worktrees.
-   Tool broker.
-   Permission policy.
-   Approval workflow.
-   Secret manager abstraction.
-   Audit events.

**Exit criteria:** agent edits a sandboxed repository, runs tests and
requests approval before a remote push.

### Milestone 5 --- Context efficiency and OpenLIT

-   Repository map.
-   Targeted source retrieval.
-   Context budgeting.
-   Compaction.
-   Tool-output filtering.
-   OpenLIT instrumentation across runtime, Marga and API.
-   Token/cost dashboard.

**Exit criteria:** token usage can be attributed to a task and context
optimization is measured against a baseline.

### Milestone 6 --- Additional agent profiles

-   Research.
-   Automation.
-   Data.
-   Orchestrator.
-   Agent evaluation harness.
-   Bounded child tasks.

**Exit criteria:** all five initial profiles complete representative
evaluation tasks.

### Milestone 7 --- Tenancy and white-label

-   Organizations and memberships.
-   RLS and tenant-aware foreign keys.
-   Tenant-scoped providers/secrets/tools.
-   Branding.
-   Custom domains.
-   BYOK.
-   Tenant budgets and quotas.
-   Cross-tenant test suite.

**Exit criteria:** two organizations share one deployment without
cross-tenant data or secret access.

### Milestone 8 --- Distribution and commercial readiness

-   Dedicated deployment profile.
-   Installation wizard.
-   Backup/restore.
-   Entitlements.
-   Optional billing adapter.
-   License mechanism if needed.
-   SBOM and license review.
-   Operational documentation.

**Exit criteria:** a second organization can install or be provisioned
from documented procedures.

------------------------------------------------------------------------

## 26. Initial acceptance criteria

The first usable release is complete when:

1.  Local Docker Compose installation works from a clean machine.
2.  User can configure a local or hosted model provider.
3.  Pi executes a coding task through Marga.
4.  Marga supports OpenAI-compatible streaming and non-streaming
    requests.
5.  Bangtags resolve authorized context profiles.
6.  Virtual models resolve to configured providers/models.
7.  Usage events persist across restarts.
8.  Web UI and CLI can create and inspect the same task.
9.  Agent code runs in an isolated workspace.
10. Tool permissions and approval gates are enforced.
11. Task state survives API/runtime worker restarts.
12. OpenLIT shows correlated agent/model/tool traces.
13. No prompt content or secrets are logged by default in shared mode.
14. Provider can be changed without changing agent profile code.
15. Automated tests cover tenant boundaries and budget enforcement.

------------------------------------------------------------------------

## 27. Coding-agent instructions

The coding agent implementing this specification must follow these
rules:

1.  **Do not implement the entire platform in one pass.** Work milestone
    by milestone.
2.  Begin by inspecting the existing Marga repository and documenting
    its actual code, license, tests, current feature set and missing
    features.
3.  Do not assume the removed bangtag or virtual-model implementation
    exists in the current lightweight Marga branch. Ask for or locate
    the original source before attempting to restore it. If unavailable,
    implement the documented behavior with tests.
4.  Do not replace Marga with LiteLLM. Integrate LiteLLM only as an
    optional provider adapter/backend after proving a need.
5.  Do not invent Pi SDK method signatures. Inspect the pinned SDK
    version and write an adapter with integration tests.
6.  Do not invent OpenLIT APIs. Follow the pinned OpenLIT version's
    documented setup and validate trace ingestion.
7.  Keep Python control plane and TypeScript runtime boundaries
    explicit.
8.  Use migrations for schema changes.
9.  Keep secrets out of source control, fixtures and logs.
10. Write tests with each feature.
11. Use typed request/response schemas and generated API clients where
    practical.
12. Maintain `.env.example`, setup instructions and architecture
    decision records.
13. Pin dependencies and container images.
14. Record deviations from this specification in
    `docs/architecture/decisions/`.
15. Never weaken tenant isolation or execution sandboxing to make a test
    pass.
16. Do not claim a feature is implemented until there is a test or a
    reproducible manual verification.
17. At the end of each milestone, provide changed files, commands run,
    test results, known gaps and the next milestone recommendation.

### First coding-agent task

Start with **Milestone 0 only**.

Produce:

-   `docs/architecture/current-state-marga.md`
-   `docs/architecture/pi-compatibility-spike.md`
-   `docs/architecture/openlit-instrumentation-spike.md`
-   A minimal end-to-end proof of concept.
-   A list of decisions or missing source artifacts requiring maintainer
    input.

Do not begin the full UI or multi-tenant implementation until the
compatibility spike is complete.

------------------------------------------------------------------------

## 28. Architecture decision records to maintain

Create an ADR for each significant decision:

-   ADR-001: Pi SDK integration boundary.
-   ADR-002: Marga as context/policy/model gateway.
-   ADR-003: Optional LiteLLM adapter and routing ownership.
-   ADR-004: OpenLIT and OpenTelemetry instrumentation.
-   ADR-005: Python control plane / TypeScript runtime split.
-   ADR-006: Docker sandbox isolation model.
-   ADR-007: PostgreSQL tenant isolation and RLS.
-   ADR-008: Task/event durability and recovery.
-   ADR-009: Bangtag syntax and context profile resolution.
-   ADR-010: Local, dedicated and shared deployment profiles.

------------------------------------------------------------------------

## 29. Reference repositories and documentation

-   Marga: https://github.com/evolvedHow/marga
-   Pi: https://github.com/badlogic/pi-mono
-   OpenLIT: https://github.com/openlit/openlit
-   OpenLIT documentation: https://docs.openlit.io/
-   LiteLLM: https://github.com/BerriAI/litellm
-   LiteLLM documentation: https://docs.litellm.ai/
-   FastAPI: https://fastapi.tiangolo.com/
-   PostgreSQL: https://www.postgresql.org/docs/
-   Redis: https://redis.io/docs/
-   Docker: https://docs.docker.com/
-   OpenTelemetry: https://opentelemetry.io/docs/

**Final principle:** Agent OS should be a platform, not a hardcoded
collection of agents. Pi executes; Marga supplies context, policy and
model routing; OpenLIT observes; the control plane governs identity,
tasks, permissions, budgets and tenants. The platform owns the contracts
that make these components replaceable.
