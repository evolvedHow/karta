# Adoption of the architecture specification

This record declares how `requirements/new-architecture.md` applies to kartā.

The architecture document was imported verbatim from the frozen `sutracoder`
repository. Its working title is "Agent OS". That title is a placeholder, not a
product decision. Every occurrence of "Agent OS" in the imported document is
read as **kartā (कर्ता)**, and the CLI examples using `agentos` are read as
`karta` until the CLI surface is implemented and this record is updated.

All other requirements in the imported document stand as written. Technical
substance is not changed by renaming; where a future edit changes behaviour, the
edit is made here first and then propagated into the specification.

## Decisions taken at adoption

| Decision | Outcome |
|---|---|
| Product name | kartā (कर्ता), "doer / agent" |
| Machine identifiers | ASCII `karta` for repo, binary, module, config, data dir, env prefix and vault context |
| Fate of sutracoder | Frozen at `sutracoder-v1-final`, reference only, never shipped, no further changes |
| Recursive-learn contract | Ported as a downstream event consumer, not as an in-platform JSONL emitter (ADR-012) |
| New repository | `~/codebox/karta`, initialised on `main`, no code yet |
| Scope now | Scaffold and Milestone 0 documentation only |

## Deliberately not decided yet

The following remain open and are tracked in `docs/architecture/open-questions.md`:
the kartā source licence, whether the local Marga checkout or the public slim
`main` is the gateway baseline, the original margAI/bangtag source artifact,
pinned Pi SDK and OpenLIT versions, and whether LiteLLM is needed at all.
