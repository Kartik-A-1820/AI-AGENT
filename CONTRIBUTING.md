# Contributing to AI-AGENT

Start with the offline tests in [README.md](README.md). A contribution should solve a specific behavior or reproducibility problem.

1. Fork and create a branch in an isolated Python 3.11+ environment.
2. Reproduce the issue without connecting personal accounts where possible.
3. Add focused tests for changed behavior. Use fake provider responses and temporary directories.
4. Run `python -m pytest -q tests`.
5. Describe the problem, implementation, validation, and remaining limitations in the pull request.

Useful starting areas are portable Windows launchers, mocked OAuth/service failures, persistent-memory tests, independently enforced action approval, and a documented task-success benchmark.

Changes to generated-code execution must preserve default denial, explicit container opt-in, no host fallback, bounded resources, and explicit input mounts. A real Docker smoke test is needed for runner changes; mocked command tests alone are insufficient.

Do not use real email, tokens, private documents, or personal memories in fixtures. Redact endpoint keys and OAuth data from logs. Never commit `.env`, `.local/`, `agent_working/`, or saved credentials.

Performance or reliability reports should name the commit, Python/package versions, endpoint/model revision, tool scenario, and failure conditions. Label manual observations separately from automated tests. See [SECURITY.md](SECURITY.md) for limitations.

No standalone LICENSE file is present; identify third-party code and terms in proposed additions.
