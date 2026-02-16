# Agent Instructions

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

## Debugging: Native Host & Window Name Detection

Run `npm run diagnose` for automated diagnostics without human intervention. This launches Chromium with the extension, triggers the diagnostic API, captures all pipeline logs, and outputs structured JSON.

### Usage

```bash
# Quick diagnostic dump to stdout
npm run diagnose

# Save to file for analysis
npm run diagnose -- --output /tmp/diag.json

# Custom timeout (default 15s)
npm run diagnose -- --timeout 20000
```

### Output Structure

- **`diagnosis`** — Result from `runDiagnosis()` in background.js:
  - `nativeHost.reachable` — Is the native messaging host responding via Chrome's native messaging?
  - `matching.pairs` — All window matching attempts with `boundsScore` + `titleScore`
  - `matching.totalMatches` — How many windows matched successfully
  - `cache.before` / `cache.after` — Chrome storage state before/after refresh
  - `hostLogTail` — Last 20 lines of the native host debug log (via host API)
- **`directHostTest`** — Direct native host test (bypasses Chrome, spawns host.py directly):
  - `reachable` — Did host.py respond successfully?
  - `response` — Full parsed response from host.py
  - `windowCount` / `customNameCount` — How many windows were detected
  - Note: `diagnosis.nativeHost.reachable` may be false in Playwright Chromium due to extension ID mismatch, but `directHostTest.reachable` confirms the host binary works
- **`serviceWorkerLogs`** — All `[TGWL:*]` tagged log entries from the background service worker, with timestamps
- **`nativeHostLogTail`** — Last 50 lines from `~/.local/lib/tab-groups-window-namer/debug.log`
- **`metadata`** — Capture timestamp, extension ID, platform

### Interpreting Results

Matching scores: `boundsScore` (0 or 1, exact bounds match) + `titleScore` (0 or 2, active tab title match). A `totalScore` of 3 is a strong match; 1 is bounds-only; 0 is no match.

### `[TGWL:*]` Tag Reference

| Tag | Pipeline Stage |
|-----|---------------|
| `native-req` | Outgoing native host request |
| `native-res` | Incoming native host response |
| `ext-windows` | Extension window enumeration |
| `matching` | Individual window match attempt |
| `match-result` | Final match summary |
| `cache-read` | Reading from chrome.storage |
| `cache-write` | Writing to chrome.storage |
| `startup-match` | Restart matching via Jaccard similarity |
| `error` | Error conditions |
| `DIAG` | Diagnostic JSON output (popup.js) |

### Quick Debugging Checklist

1. Run `npm run diagnose -- --output /tmp/diag.json`
2. Check `diagnosis.nativeHost.reachable` — is the host responding?
3. Check `diagnosis.matching.pairs` — are scores > 0? Which windows matched?
4. Check `nativeHostLogTail` — any osascript errors?
5. Check `serviceWorkerLogs` — any `[TGWL:error]` entries?

<!-- bv-agent-instructions-v1 -->

---

## Beads Workflow Integration

This project uses [beads_viewer](https://github.com/Dicklesworthstone/beads_viewer) for issue tracking. Issues are stored in `.beads/` and tracked in git.

### Essential Commands

```bash
# View issues (launches TUI - avoid in automated sessions)
bv

# CLI commands for agents (use these instead)
bd ready              # Show issues ready to work (no blockers)
bd list --status=open # All open issues
bd show <id>          # Full issue details with dependencies
bd create --title="..." --type=task --priority=2
bd update <id> --status=in_progress
bd close <id> --reason="Completed"
bd close <id1> <id2>  # Close multiple issues at once
bd sync               # Commit and push changes
```

### Workflow Pattern

1. **Start**: Run `bd ready` to find actionable work
2. **Claim**: Use `bd update <id> --status=in_progress`
3. **Work**: Implement the task
4. **Complete**: Use `bd close <id>`
5. **Sync**: Always run `bd sync` at session end

### Key Concepts

- **Dependencies**: Issues can block other issues. `bd ready` shows only unblocked work.
- **Priority**: P0=critical, P1=high, P2=medium, P3=low, P4=backlog (use numbers, not words)
- **Types**: task, bug, feature, epic, question, docs
- **Blocking**: `bd dep add <issue> <depends-on>` to add dependencies

### Best Practices

- Check `bd ready` at session start to find available work
- Update status as you work (in_progress → closed)
- Create new issues with `bd create` when you discover tasks
- Use descriptive titles and set appropriate priority/type
- Always `bd sync` before ending session

<!-- end-bv-agent-instructions -->

---

## MANDATORY: CI-Fix-First Policy

**At the start of every session, check CI status:**

```bash
gh run list --limit 1 --json conclusion --jq '.[0].conclusion'
```

**If CI is failing on master, fixing it is the HIGHEST PRIORITY.** Do not start new features, refactors, or any other work until CI is green. Check which job failed:

```bash
gh run view --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'
```

Then fix the failure, push, and confirm CI passes before proceeding with any other work.

**Rationale:** A red CI means every subsequent push is flying blind. Broken CI is a blocking defect.

---

## MANDATORY: Quality Gates Before Push

A pre-push git hook enforces quality gates automatically. If you bypass it or push manually, you MUST run these checks first:

```bash
npx jest --no-coverage          # JavaScript tests
./scripts/verify-python.sh      # ruff + mypy + pytest (100% coverage)
```

**Never push code that fails quality gates.** The `/land` command enforces this automatically.

---

## Landing the Plane (Session Completion)

**Use `/land` to wrap up a work session.** This command automates the full landing sequence: run quality gates, stage, sync beads, commit, push, monitor CI, and verify clean state.

If you need to land manually, complete ALL steps below. Work is NOT complete until `git push` succeeds AND CI is green.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** - `npx jest --no-coverage` and `./scripts/verify-python.sh`
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Monitor CI** - Wait for CI to pass: `gh run watch --exit-status`
6. **If CI fails** - Fix it, re-push, and repeat until green
7. **Clean up** - Clear stashes, prune remote branches
8. **Verify** - All changes committed, pushed, AND CI green
9. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds AND CI is green
- NEVER push without running quality gates first
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
- If CI fails after push, fix and re-push until green
