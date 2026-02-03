# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## MANDATORY: Agentic Layer vs Application Layer Boundary

This project has TWO distinct layers. **Violating this boundary is a blocking defect.**

### Agentic Layer (`adws/`)
The workflow engine. Contains ONLY: pipeline engine, steps, workflows, commands,
hooks, io_ops boundary, dispatchers, and their tests. This code orchestrates
AI-driven development workflows. It is application-agnostic.

### Application Layer (project root)
The actual product. Contains: Chrome extension (`popup.js`, `background.js`,
`manifest.json`), native messaging host (`native-host/`), application tests
(`tests/`), build scripts (`scripts/`), store assets, icons.

### The Rule
**NEVER put application code in `adws/`.** Before adding ANY code to `adws/`, ask:
- Does this code orchestrate AI agent workflows? If no, it doesn't belong.
- Is this a pipeline step the engine executes? If no, it doesn't belong.
- Would this code exist if this were a different application? If no, it doesn't belong.

Read `AGENTIC_VS_APPLICATION.md` (project root) for the complete boundary definition.

---

## MANDATORY: TDD (Red-Green-Refactor)

ALL code in this project MUST be developed using strict TDD:
1. Write a failing test FIRST (RED) — the test MUST fail for the expected reason, not any reason
2. Write minimum code to pass (GREEN)
3. Refactor with tests passing (REFACTOR)
4. No code without a test. No exceptions.

### How TDD is enforced:
- The ADWS workflow engine runs separate agents for each TDD phase
- Test agent writes tests. Implementation agent writes code. Refactor agent cleans up.
- Shell verification steps between phases prove compliance — not self-reported
- Tests MUST fail after RED phase for the EXPECTED REASON (verified by runner)
- Tests MUST pass after GREEN and REFACTOR phases (verified by runner)

Python testing conventions:
- Tests in adws/tests/ mirroring source structure
- All external dependencies behind io_ops.py boundary (mockable)
- 100% line and branch coverage on all code — every line exists because a test demanded it
- Enemy Unit Tests (@pytest.mark.enemy) test REAL SDK with REAL API calls
- Never mock in EUTs — the whole point is testing the real dependency
- All I/O behind io_ops.py — mock in tests, real in production

Testing stack:
- pytest — test framework (primary)
- pytest-mock — mock utilities (mocker fixture)
- pytest-cov — coverage tracking (100% enforced)
- mypy — static type checking (strict mode)
- ruff — linting + formatting

### Testing Pyramid:
- Unit tests (bottom — many, fast, isolated): mock io_ops boundary
- Enemy Unit Tests (integration — fewer, test real SDK): NOTHING mocked, REAL API calls
- Acceptance tests (top — fewest, user perspective): from story AC via /bmad-tea-testarch-atdd

### THE RULE:
If a story's acceptance criteria can fail, a test MUST catch it.

---

## Landing the Plane (Session Completion)

**Use `/land` to wrap up a work session.** This command automates the full landing sequence: stage, sync beads, commit, push, and verify clean state.

If you need to land manually, complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
