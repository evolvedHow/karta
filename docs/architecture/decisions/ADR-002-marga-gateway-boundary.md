# ADR-002: Marga as context, policy and model gateway

Status: Accepted after the Milestone 0 compatibility spike.

## Context

The architecture specification places Marga between the runtime and model
providers. The local checkout at `~/codebox/marga` is separately versioned,
Apache-2.0, and has uncommitted work. Kartā must not fork it silently or edit
that tree without instruction.

## Decision

- Marga remains a separately versioned service. Kartā imports it at runtime
  through a documented OpenAI-compatible surface and does not copy its source.
- The Milestone 0 launcher imports the local checkout read-only and wraps its
  ASGI app; it does not modify files, reset the branch or commit anything there.
- Marga is the sole policy and routing authority. LiteLLM, when added, is used
  only behind a Marga adapter and never makes an independent model decision.
- The local model backend is llama.cpp at `127.0.0.1:8080/v1`, not Ollama.
- Modifications to Marga, if any, must be identified in
  `THIRD_PARTY_NOTICES.md` with the upstream licence and notice preserved.

## Consequences

- Gateway behaviour that needs changes must be designed with Marga's upstream
  history preserved.
- The authoritative baseline (dirty local checkout versus public slim `main`)
  and the fate of its uncommitted files remain open questions for Milestone 2.
- The spike used a deterministic tool-call backend because the loaded llama.cpp
  model did not emit tool calls reliably; that limitation is recorded in the
  spike results.
