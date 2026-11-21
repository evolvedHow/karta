# Open questions requiring maintainer input

Items marked **Resolved** are retained for traceability; they no longer block
work. The remaining items require a maintainer decision that must not be guessed.

| # | Question | Status | Blocks | Owner |
|---:|---|---|---|---|
| 1 | Which licence applies to kartā itself? | **Resolved:** MIT. See `LICENSE`. | Distribution, §24 | Maintainer |
| 2 | Is the local dirty `~/codebox/marga` checkout the authoritative gateway baseline, or the public slim `main` described in §1.2? | Open | Gateway design, Milestone 2 | Maintainer |
| 3 | What should happen to the uncommitted `Dockerfile`, `docker-compose.yml`, `marga/models.py`, `marga/proxy.py` and untracked `marga.toml` in that checkout? | Open | Gateway design | Maintainer |
| 4 | Where is the original margAI/bangtag source, and which syntax should be retained for backward compatibility (§5.3, §27)? | Partially resolved: bangtag deferred by maintainer; original source still missing | Milestone 2 | Maintainer |
| 5 | Which Pi SDK version and repository commit is pinned? | **Resolved:** see `docs/architecture/dependency-pins.md`. | Milestone 0 | Maintainer |
| 6 | Which OpenLIT version and installation method is used? | **Resolved:** see `docs/architecture/dependency-pins.md`. | Milestone 0, Milestone 5 | Maintainer |
| 7 | Is LiteLLM needed at all, given direct Marga adapters? (§1.2) | **Resolved:** LiteLLM is in scope, behind a Marga adapter. Marga remains the policy authority. | Provider scope | Maintainer |
| 8 | What product name and domain should appear in CLI help, branding defaults and deployment documentation? | **Resolved:** kartā / कर्ता; ASCII identifiers only. See ADR-011. | Milestone 3, Milestone 7 | Maintainer |
| 9 | When should billing and signed licence support be introduced? §19 defers both. | Open | Milestone 8 | Maintainer |
| 10 | Should `sutracoder` be moved to an archive path, or remain in place with its freeze tag? | Open | Housekeeping only | Maintainer |
| 11 | Which local model backend should the compatibility spike use? | **Resolved:** llama.cpp at `127.0.0.1:8080/v1`, not Ollama. | Milestone 0 | Maintainer |

The Milestone 0 compatibility spike is unblocked. Items 2, 3 and 4 remain open
for Milestone 2; none weakens tenant isolation or sandboxing if left unresolved.
