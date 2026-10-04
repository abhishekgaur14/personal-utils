# Repository guidance for AI agents

- This repository is a collection of independent utilities. Keep each utility self-contained with its own dependencies, environment, tests, and documentation.
- Avoid adding root-level runtime dependencies or project scaffolding unless multiple utilities need them.
- Treat local sample documents, credentials, and other private data as local-only. Never upload them or include them in commits.
- Do not push changes to a remote unless the user explicitly asks.
- Prefer small, documented changes and run the relevant utility's tests when requested.
