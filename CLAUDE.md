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
