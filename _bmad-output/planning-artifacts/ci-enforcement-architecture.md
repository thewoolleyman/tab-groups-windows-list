# CI Enforcement Architecture

## Problem Statement

CI has been failing on master for multiple consecutive commits. The root cause is a structural enforcement gap: no mechanism ensures quality gates pass before code reaches the remote, and no mechanism forces agents to fix CI failures when they occur.

## Current State (Failure Path)

```
Agent finishes work → /land → stages, commits, pushes → CI fails → Nobody acts
```

**Three layers exist but don't form a closed loop:**

| Layer | Enforcement | Gap |
|-------|------------|-----|
| GitHub Actions CI | Hard gate on merge/release | Nothing stops direct pushes to master from failing |
| ADWS `/adws-verify` | Runs Jest + Playwright + mypy + ruff | Voluntary; scope doesn't fully match CI |
| `/land` command | Commits and pushes | Never runs any tests |
| Git hooks | N/A | None exist |

## Design: Four-Layer CI Enforcement

### Layer 1: `/land` Runs Quality Gates Before Push

**Change:** Update `.claude/commands/land.md` to include a mandatory quality gate step between "commit" and "push".

- Runs `npx jest --no-coverage` (JS unit tests)
- Runs `./scripts/verify-python.sh` (ruff + mypy + pytest)
- If either fails, `/land` stops and reports what broke
- Push step is conditional on gates passing

**Rationale:** This is the highest-leverage fix. Every agentic session ends with `/land`. Making `/land` verify before pushing blocks the primary failure path.

### Layer 2: `/land` Monitors CI After Push

**Change:** Add a post-push step to `/land` that:
1. Runs `gh run watch` to wait for the CI run triggered by the push
2. If CI fails, reports the failure and instructs the agent to fix it
3. The plane is NOT landed if CI is red

**Rationale:** Even with local gates, CI can catch environment-specific issues. Monitoring CI closes the loop completely.

### Layer 3: Pre-Push Git Hook (Defense in Depth)

**Change:** Create `.githooks/pre-push` that runs the same quality gates as Layer 1. Configure via `git config core.hooksPath .githooks` (set in npm postinstall or documented in README).

**Rationale:** Catches pushes that bypass `/land` — direct `git push`, other tools, human pushes. Defense in depth.

### Layer 4: CI-Fix-First Policy in AGENTS.md

**Change:** Add a mandatory section to `AGENTS.md`:
- At session start, check `gh run list --limit 1` for CI status
- If CI is red on master, fixing it is the highest priority before any other work
- No new features or changes until CI is green

**Rationale:** Prevents CI debt from accumulating across sessions.

## Target State

```
Session start → Check CI status → Fix if red → Do work → /land →
  Local gates pass → Push → CI passes → Plane landed
```

Every link in this chain is enforced, not advisory.

## Files Modified

| File | Change |
|------|--------|
| `.claude/commands/land.md` | Add quality gate + CI watch steps |
| `AGENTS.md` | Add CI-fix-first policy section |
| `.githooks/pre-push` | New: pre-push quality gate hook |
| `.gitignore` | No change needed |
| `adws/` (multiple) | Fix existing ruff/coverage failures |
