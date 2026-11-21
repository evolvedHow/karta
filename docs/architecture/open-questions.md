# Open questions requiring maintainer input

These items block Milestone 1 or require a decision that must not be guessed.

| # | Question | Blocks | Owner |
|---:|---|---|---|
| 1 | Which licence applies to kartā itself? No `LICENSE` file is created until this is answered. | Distribution, §24 | Maintainer |
| 2 | Is the local dirty `~/codebox/marga` checkout the authoritative gateway baseline, or the public slim `main` described in §1.2? | Gateway design, Milestone 2 | Maintainer |
| 3 | What should happen to the uncommitted `Dockerfile`, `docker-compose.yml`, `marga/models.py`, `marga/proxy.py` and untracked `marga.toml` in that checkout? | Gateway design | Maintainer |
| 4 | Where is the original margAI/bangtag source, and which syntax should be retained for backward compatibility (§5.3, §27)? | Milestone 2 | Maintainer |
| 5 | Which Pi SDK version and repository commit is pinned? | Milestone 0 | Maintainer |
| 6 | Which OpenLIT version and installation method is used? | Milestone 0, Milestone 5 | Maintainer |
| 7 | Is LiteLLM needed at all, given direct Marga adapters? (§1.2) | Provider scope | Maintainer |
| 8 | What product name and domain should appear in CLI help, branding defaults and deployment documentation? | Milestone 3, Milestone 7 | Maintainer |
| 9 | When should billing and signed licence support be introduced? §19 defers both. | Milestone 8 | Maintainer |
| 10 | Should `sutracoder` be moved to an archive path, or remain in place with its freeze tag? | Housekeeping only | Maintainer |

Items 5 and 6 must be answered before the compatibility spikes can produce
verified results. No version numbers are invented in this scaffold.
