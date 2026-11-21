# kartā — Project Rules

## Identity and naming

- Product display name is **kartā**; Devanagari wordmark is **कर्ता**.
- Every machine-facing identifier is ASCII `karta`: repository, binary, Python
  distribution and import module, config directory, data directory, `KARTA_*`
  environment variables and the worker-env vault context.
- Do not introduce `agentos`, `agent-os` or `sutracoder` identifiers in new code,
  paths, topics or environment variables.

## Source of truth and process

- Spec of record: `requirements/new-architecture.md`, adopted verbatim. The
  document's title says "Agent OS"; read that as kartā (`requirements/adoption.md`).
- `requirements/recursive-learn.md` is a separate contract, not a dependency to
  reimplement inside the platform (ADR-012).
- Work milestone by milestone as required by §27 of the spec. Each milestone
  must compile, run and have tests before the next begins.
- **Only Milestone 0 is authorised now.** Do not implement the web UI, tenancy,
  billing or additional agent profiles until the compatibility spike meets its
  exit criteria.
- Never invent Pi SDK or OpenLIT APIs. Pin versions first, inspect the pinned
  source, then write adapters and integration tests against what actually exists.
- Record deviations in `docs/architecture/decisions/`. Never weaken tenant
  isolation or sandboxing to make a test pass.
- If direction is ambiguous, incomplete or missing, stop and ask for a more
  specific instruction rather than guessing.

## Stack and boundaries

- **Python 3.11+ / FastAPI / Pydantic / uv / Ruff** owns the control plane,
  worker and platform packages. Use Google-style docstrings with parameter types
  and return definitions. Do not generate `requirements.txt`.
- **TypeScript** owns the Pi runtime adapter and runtime-specific adapters.
  Use JSDoc for components, hooks and utility functions. Enforce strict typing;
  never use `any`.
- **React 19+ / TypeScript / Vite / Tailwind / npm** owns the web application.
  Mobile-first, 375 / 768 / 1024 breakpoints, 44×44px minimum touch targets.
- **Exception to the codebox frontend default:** the web app is served by the
  kartā deployment, not GitHub Pages. Do not add a `gh-pages` deploy script or a
  repository-relative `base` path.
- Python and TypeScript communicate through documented HTTP APIs and event
  schemas, never shared internal code.
- Start as a modular monolith. Do not split every logical module into a network
  service. No Kubernetes.

## External repository boundaries

- **Marga** lives at `~/codebox/marga` and is separately versioned. The local
  checkout is on `main` at `Phase 6 final` and currently has uncommitted changes
  plus an untracked `marga.toml`. Never modify, reset or commit that tree without
  explicit instruction. Changes to gateway behaviour must be designed with its
  upstream history preserved, not silently forked.
- Marga is Apache-2.0 with a `NOTICE` file. Preserve licence and attribution
  notices, identify modified files and maintain `THIRD_PARTY_NOTICES.md`.
- **sutracoder** at `~/codebox/sutracoder`, tag `sutracoder-v1-final`, is a frozen
  reference. It is not shipped and receives no changes. Design knowledge is
  ported through `docs/architecture/carry-over-from-sutracoder.md`, not by
  reusing its Go packages.
- LiteLLM is optional and only behind a Marga adapter. Marga remains the policy
  authority; do not let two components make conflicting model decisions.

## Secrets

- Credentials come from the environment first, then the worker-env vault using
  context `karta` with fallback to the shared default context.
- `VAULT_URL` and `VAULT_TOKEN` come from the environment or `~/docker/stack/.env`.
- Never commit secrets, secret CSVs or real values in `.env.example`. Never write
  credentials into this file or any documentation. Reference their location only.
- Do not send provider or MCP credentials to the model, log them, or embed them
  in profile or config files.

## Interaction emission

- The schema-1 JSONL contract in `requirements/recursive-learn.md` is preserved
  by a downstream event consumer (ADR-012). Do not add a JSONL emitter to the
  platform or the Pi runtime.
- Emit structured, tenant-scoped task and tool events with sequence numbers and
  correlation IDs; the consumer derives the legacy record from those events.

## Quality bar

- Tests accompany every feature: unit, integration, security and
  tenant-isolation as appropriate. Cross-tenant isolation tests are release
  blockers.
- Pin all dependency versions and container images; no floating `latest`.
- Validate request and response schemas with Pydantic or generated types.
- Do not claim a feature is implemented until a test or reproducible manual
  verification exists.
- At the end of each milestone report changed files, commands run, test results,
  known gaps and the next milestone recommendation.
