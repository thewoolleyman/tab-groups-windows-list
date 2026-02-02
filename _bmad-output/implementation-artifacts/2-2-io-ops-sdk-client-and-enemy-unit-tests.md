# Story 2.2: io_ops SDK Client & Enemy Unit Tests

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an ADWS developer,
I want a thin SDK client wrapper in io_ops.py with Pydantic boundary models,
so that pipeline code interacts with Claude exclusively through a testable I/O boundary.

## Acceptance Criteria

1. **Given** the io_ops boundary from Epic 1, **When** I inspect `adws/adw_modules/io_ops.py`, **Then** `execute_sdk_call` wraps the `claude-agent-sdk` Python API **And** pipeline code never imports `claude-agent-sdk` directly -- only `io_ops.py` does (NFR18).

2. **Given** the types module, **When** I inspect `adws/adw_modules/types.py`, **Then** `AdwsRequest` and `AdwsResponse` are Pydantic models at the SDK boundary.

3. **Given** `execute_sdk_call` is implemented, **When** I run the EUT marked `@pytest.mark.enemy`, **Then** the test makes a REAL API call through the REAL SDK with REAL credentials **And** nothing is mocked -- the test proves actual SDK communication (Decision 1) **And** the test requires `ANTHROPIC_API_KEY` environment variable.

4. **Given** all io_ops SDK functions, **When** I inspect the test suite, **Then** every io_ops SDK function has a corresponding Enemy Unit Test (EUT* constraint) **And** unit tests with mocked io_ops also exist for fast CI feedback.

5. **Given** all code, **When** I run `uv run pytest adws/tests/`, **Then** all tests pass with 100% line + branch coverage (NFR9) **And** `uv run mypy adws/` passes strict mode (NFR11) **And** `uv run ruff check adws/` has zero violations (NFR12).

## Tasks / Subtasks

- [x] Task 1: Add Pydantic boundary models to types.py (AC: #2)
  - [x] 1.1 RED: Write tests for `AdwsRequest` model construction, validation, and defaults
  - [x] 1.2 GREEN: Implement `AdwsRequest` Pydantic model in types.py
  - [x] 1.3 RED: Write tests for `AdwsResponse` model construction, defaults, and error state
  - [x] 1.4 GREEN: Implement `AdwsResponse` Pydantic model in types.py
  - [x] 1.5 REFACTOR: Clean up, verify 100% coverage

- [x] Task 2: Implement execute_sdk_call in io_ops.py (AC: #1)
  - [x] 2.1 RED: Write unit tests for `execute_sdk_call` success path (mock SDK)
  - [x] 2.2 GREEN: Implement `execute_sdk_call` -- translate AdwsRequest to SDK types, call SDK, translate response to AdwsResponse
  - [x] 2.3 RED: Write unit tests for `execute_sdk_call` error paths (SDK errors, missing API key, etc.)
  - [x] 2.4 GREEN: Implement error handling -- catch SDK exceptions, return IOFailure with PipelineError
  - [x] 2.5 REFACTOR: Clean up, verify 100% coverage

- [x] Task 3: Write Enemy Unit Tests (AC: #3, #4)
  - [x] 3.1 RED: Write EUT for `execute_sdk_call` full round-trip (REAL SDK, REAL API)
  - [x] 3.2 GREEN: Ensure EUT passes with real ANTHROPIC_API_KEY
  - [x] 3.3 RED: Write EUT for `execute_sdk_call` error handling (invalid model)
  - [x] 3.4 GREEN: Ensure error EUT passes
  - [x] 3.5 REFACTOR: Clean up, verify all quality gates

- [x] Task 4: Verify full integration and quality gates (AC: #5)
  - [x] 4.1 Run `uv run pytest adws/tests/ -m "not enemy"` -- all unit tests pass, 100% coverage
  - [x] 4.2 Run `uv run pytest adws/tests/ -m enemy` -- all EUTs pass (requires ANTHROPIC_API_KEY)
  - [x] 4.3 Run `uv run mypy adws/` -- strict mode passes
  - [x] 4.4 Run `uv run ruff check adws/` -- zero violations

## Dev Notes

### Current State (from Story 2.1)

**io_ops.py** exists with two functions:
```python
def read_file(path: Path) -> IOResult[str, PipelineError]: ...
def check_sdk_import() -> IOResult[bool, PipelineError]: ...
```
- Pattern established: returns `IOResult[SuccessType, ErrorType]` (success first)
- Catches specific exceptions, never raises
- Transforms external types to domain types

**types.py** exists with `WorkflowContext` frozen dataclass. No Pydantic models yet.

**test_io_ops.py** has 6 tests covering read_file and check_sdk_import.

**conftest.py** has `sample_workflow_context` and `mock_io_ops` fixtures.

**pyproject.toml** has all required dependencies:
- `claude-agent-sdk==0.1.27`
- `pydantic==2.12.5`
- `returns==0.26.0`
- `enemy` marker registered in pytest config

**Current test count**: 47 tests, 100% coverage.

### claude-agent-sdk v0.1.27 API Reference

**CRITICAL: The SDK is async-only.** All calls use `async/await`. The io_ops wrapper MUST handle the async boundary.

**Two interfaces available:**
1. `query()` function -- stateless, one-off calls (simpler, use this)
2. `ClaudeSDKClient` class -- stateful conversation sessions

**For Story 2.2, use `query()` function** -- each pipeline step is a fresh SDK call per architecture Decision 1. No conversation continuity needed.

**`query()` signature:**
```python
async def query(
    *,
    prompt: str | AsyncIterable[dict[str, Any]],
    options: ClaudeAgentOptions | None = None
) -> AsyncIterator[Message]
```

**`ClaudeAgentOptions` key fields:**
```python
@dataclass
class ClaudeAgentOptions:
    system_prompt: str | None = None
    model: str | None = None
    allowed_tools: list[str] = []
    disallowed_tools: list[str] = []
    max_turns: int | None = None
    permission_mode: str | None = None  # "acceptEdits", "bypassPermissions"
    cwd: str | Path | None = None
```

**Response types (union):**
```python
Message = UserMessage | AssistantMessage | SystemMessage | ResultMessage | StreamEvent
```

**`ResultMessage` (final response -- what we care about):**
```python
@dataclass
class ResultMessage:
    subtype: str
    duration_ms: int
    duration_api_ms: int
    is_error: bool
    num_turns: int
    session_id: str
    total_cost_usd: float | None
    result: str | None
```

**SDK Exceptions:**
```python
ClaudeSDKError           # Base
├── CLIConnectionError   # Connection failures
│   └── CLINotFoundError # CLI not installed
├── ProcessError         # Process failures (has exit_code, stderr)
└── CLIJSONDecodeError   # JSON parsing errors
```

**API Key**: Set via `ANTHROPIC_API_KEY` env var. mise loads from `.env` file automatically.

### Architecture Compliance

- **NFR18**: `io_ops.py` is the ONLY file that imports `claude_agent_sdk` -- pipeline code never does
- **NFR10**: `io_ops.py` is the single mock point for tests
- **Decision 1**: Thin Pydantic wrapper -- `AdwsRequest`/`AdwsResponse` are OUR types, SDK types stay inside io_ops
- **EUT* constraint**: Every io_ops SDK function must have a corresponding Enemy Unit Test
- **IOResult order**: `IOResult[SuccessType, ErrorType]` -- success first, error second

### Pydantic Model Specifications

**`AdwsRequest`** (what pipeline sends to SDK boundary):
```python
class AdwsRequest(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    system_prompt: str
    prompt: str
    allowed_tools: list[str] | None = None
    disallowed_tools: list[str] | None = None
    max_turns: int | None = None
    permission_mode: str | None = None
```

**`AdwsResponse`** (what pipeline gets back from SDK boundary):
```python
class AdwsResponse(BaseModel):
    result: str | None = None
    cost_usd: float | None = None
    duration_ms: int | None = None
    session_id: str | None = None
    is_error: bool = False
    error_message: str | None = None
    num_turns: int | None = None
```

### Async Handling Strategy

The SDK is fully async but our pipeline uses synchronous `IOResult` from `returns`. Strategy:

1. `execute_sdk_call` is a **synchronous** function (matches io_ops pattern)
2. Internally uses `asyncio.run()` to bridge the async SDK call
3. Returns `IOResult[AdwsResponse, PipelineError]` -- same pattern as all io_ops functions
4. If `asyncio.run()` cannot be used (already in async context), fall back to `asyncio.get_event_loop().run_until_complete()`

```python
def execute_sdk_call(request: AdwsRequest) -> IOResult[AdwsResponse, PipelineError]:
    """Execute SDK call. Synchronous wrapper around async SDK."""
    try:
        response = asyncio.run(_execute_sdk_call_async(request))
        return IOSuccess(response)
    except SpecificSDKException as exc:
        return IOFailure(PipelineError(...))
```

### Enemy Unit Test Strategy

**File location**: `adws/tests/enemy/test_sdk_proxy.py`

**Marking**: `@pytest.mark.enemy`

**Running**: `uv run pytest adws/tests/ -m enemy` (requires ANTHROPIC_API_KEY)

**What to test:**
1. Full round-trip: `AdwsRequest` → `execute_sdk_call` → real SDK → real API → `AdwsResponse`
2. Error handling: invalid model name → `AdwsResponse(is_error=True)`

**Coverage**: EUTs are excluded from `--cov-fail-under=100` if they can't run without API key. Use `pytest.mark.skipif` to skip when `ANTHROPIC_API_KEY` is not set. BUT: the tests MUST exist and run in CI (CI has the secret).

**CRITICAL**: EUTs mock NOTHING. The entire point is testing the real SDK. If you mock anything, it defeats the purpose.

### Unit Test Strategy (Mocked)

**File**: `adws/tests/adw_modules/test_io_ops.py` (add to existing file)

**Mock target**: Mock the `claude_agent_sdk.query` function inside `io_ops.py`

**Tests needed:**
- `test_execute_sdk_call_success` -- mock SDK returns ResultMessage, verify AdwsResponse fields
- `test_execute_sdk_call_sdk_error` -- mock SDK raises ProcessError, verify IOFailure
- `test_execute_sdk_call_connection_error` -- mock SDK raises CLIConnectionError
- `test_execute_sdk_call_cli_not_found` -- mock SDK raises CLINotFoundError
- `test_execute_sdk_call_json_error` -- mock SDK raises CLIJSONDecodeError

### Test Directory for Enemy Tests

Per architecture (`adws/tests/enemy/`), create:
```
adws/tests/enemy/
├── __init__.py
└── test_sdk_proxy.py
```

Ensure `adws/tests/enemy/__init__.py` exists so pytest discovers the tests.

### Coverage Handling for EUTs

EUTs that require API keys may not run in all environments. Options:
1. **Skip when no API key**: Use `@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="No API key")`
2. **Exclude from coverage**: Add `adws/tests/enemy/**` to `[tool.coverage.run] omit` in pyproject.toml
3. **Run separately**: `uv run pytest -m enemy` for EUTs, `uv run pytest -m "not enemy"` for unit tests

Choose option 1 + 2: Skip when no key AND exclude enemy tests from coverage measurement (they test real SDK, not our code coverage).

### Critical Constraints

- **NFR9**: 100% line + branch coverage on all adws/ code (excluding enemy tests)
- **NFR11**: mypy strict mode -- Pydantic models need careful type annotations
- **NFR12**: ruff ALL rules -- zero lint violations
- **Immutability**: Pydantic models with `model_config = ConfigDict(frozen=True)` for consistency
- **No SDK imports outside io_ops.py**: Only `io_ops.py` may `import claude_agent_sdk`
- **No mocking in EUTs**: Enemy tests use REAL SDK with REAL API calls

### What NOT to Do

- Do NOT import `claude_agent_sdk` in types.py -- Pydantic models are OUR domain types
- Do NOT import `claude_agent_sdk` in steps or engine code -- only io_ops.py
- Do NOT mock anything in Enemy Unit Tests
- Do NOT create ClaudeSDKClient class in io_ops.py -- use the `query()` function directly
- Do NOT add conversation session management -- each step is a fresh call
- Do NOT skip async handling -- the SDK is async-only, io_ops must bridge to sync
- Do NOT put AdwsRequest/AdwsResponse in io_ops.py -- they belong in types.py per architecture
- Do NOT change existing test assertions -- add new tests alongside existing ones
- Do NOT use `asyncio.get_event_loop()` (deprecated) -- use `asyncio.run()`

### Project Structure Notes

- All source in `adws/adw_modules/` -- flat layout
- Tests mirror source: `adws/tests/adw_modules/test_io_ops.py` (existing, add to it)
- Enemy tests in: `adws/tests/enemy/test_sdk_proxy.py` (new directory)
- Absolute imports only: `from adws.adw_modules.io_ops import execute_sdk_call`
- Test naming: `test_<unit>_<scenario>` (e.g., `test_execute_sdk_call_returns_success`)

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 1] -- SDK Integration Design, EUT pattern, thin Pydantic wrapper
- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 3] -- Tool config (mypy, ruff, pytest)
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2] -- AC and story definition
- [Source: _bmad-output/implementation-artifacts/2-1-error-types-and-workflowcontext.md] -- Previous story learnings
- [Source: _bmad-output/implementation-artifacts/1-2-skeleton-layer-implementations-and-tdd-foundation.md] -- IOResult type order, module reload pattern
- [Source: adws/adw_modules/io_ops.py] -- Current io_ops implementation (2 functions)
- [Source: adws/adw_modules/types.py] -- Current types (WorkflowContext only)
- [Source: adws/tests/adw_modules/test_io_ops.py] -- Current io_ops tests (6 tests)
- [Source: adws/tests/conftest.py] -- Shared fixtures

### Git Intelligence (Recent Commits)

```
3ea67bf fix: Adversarial code review fixes for Story 2.1 (3 issues resolved)
58118f7 feat: Implement Error Types & WorkflowContext convenience methods (Story 2.1)
70a883c feat: Create Story 2.1 - Error Types & WorkflowContext (ready-for-dev)
6f846f1 feat: Add Python quality gates to CI pipeline (Story 1.3)
17cca59 fix: Adversarial code review fixes for Story 1.2 (6 issues resolved)
```

Pattern: RED commits use prefix `test(RED):`, feature commits use `feat:`, review fixes use `fix:`.

### Previous Story Intelligence

From Story 2.1 learnings:
- **IOResult[Success, Error]**: Success type comes first (corrected from architecture doc)
- **Shallow frozen**: `frozen=True` only prevents attribute reassignment; container fields are shallow-frozen
- **Module reload in tests**: When patching module-level imports, use try/finally with reload
- **Coverage omit**: `conftest.py` omitted from coverage via `[tool.coverage.run]`
- **Code review findings applied**: `to_dict()` handles non-serializable values, `__str__` truncates long contexts, `promote_outputs_to_inputs()` raises ValueError on collision

From Story 1.2 learnings:
- **returns v0.26.0**: Non-breaking release, compatible with mypy 1.19.1
- **ruff S108**: Avoid `/tmp/` literal strings in test data (use `/some/path` instead)
- **ruff E501**: Keep docstrings under 88 chars line length

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- check_sdk_import_failure test required rework: top-level SDK imports in io_ops.py meant module reload approach no longer viable; switched to builtins.__import__ patching
- Consolidated 7 return statements in execute_sdk_call to 3 by using base ClaudeSDKError catch-all (resolves PLR0911)

### Completion Notes List

- Task 1: Added AdwsRequest and AdwsResponse frozen Pydantic models to types.py with ConfigDict(frozen=True), proper defaults, and full test coverage (10 new tests)
- Task 2: Implemented execute_sdk_call in io_ops.py as synchronous wrapper around async SDK query() function. Bridges async/sync via asyncio.run(). Returns IOResult[AdwsResponse, PipelineError]. Catches ValueError (no result) and ClaudeSDKError (all SDK exceptions). 8 new unit tests covering success, options passing, no-result, and all 5 SDK error types
- Task 3: Created adws/tests/enemy/ directory with 2 EUTs: full round-trip and invalid model. Tests skip without ANTHROPIC_API_KEY, excluded from coverage measurement
- Task 4: All quality gates pass: 65 unit tests, 100% coverage, mypy strict clean, ruff zero violations
- Refactored check_sdk_import_failure test to use builtins.__import__ patching instead of module reload (compatible with new top-level SDK imports)

### Change Log

- 2026-02-01: Story created with comprehensive context from all planning artifacts, SDK API research, and previous story intelligence
- 2026-02-01: Implemented all 4 tasks via TDD red-green-refactor. 65 tests pass, 100% coverage, mypy/ruff clean

### File List

- `adws/adw_modules/types.py` -- Modified (added AdwsRequest, AdwsResponse Pydantic models with frozen config)
- `adws/adw_modules/io_ops.py` -- Modified (added execute_sdk_call, _execute_sdk_call_async; added SDK imports; moved Path to TYPE_CHECKING)
- `adws/tests/adw_modules/test_io_ops.py` -- Modified (added 8 execute_sdk_call tests, reworked check_sdk_import_failure test, added SDK imports)
- `adws/tests/adw_modules/test_types.py` -- Modified (added 10 tests for AdwsRequest/AdwsResponse, moved imports to top-level)
- `adws/tests/enemy/__init__.py` -- Created (new test directory)
- `adws/tests/enemy/test_sdk_proxy.py` -- Created (2 Enemy Unit Tests for execute_sdk_call)
- `pyproject.toml` -- Modified (added enemy tests to coverage omit, added ARG001 to test ignores)
