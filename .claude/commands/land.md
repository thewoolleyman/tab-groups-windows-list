---
name: land
description: "Land the plane: commit all changes, push, and confirm clean state"
---

# Land the Plane

> Based on Steve Yegge's "Landing the Plane" workflow from the Beads agent memory system.
> See: https://github.com/steveyegge/beads/blob/ff67b88/AGENT_INSTRUCTIONS.md#landing-the-plane

You are wrapping up a work session. Your job is to leave the repo in a clean, committed, pushed state with nothing left dangling.

**The plane is NOT landed until `git push` succeeds AND CI is green.** Do not stop before pushing. Do not say "ready to push when you are" -- that is a failure. YOU must push. YOU must confirm CI passes.

## Steps

Follow these steps IN ORDER. Do not skip any step. Do not ask for confirmation between steps -- just execute the full sequence and report the results at the end.

### 1. Check for uncommitted work

Run `git status` and `git diff --stat` to see what's changed. If there are NO changes (working tree clean, nothing untracked), skip to step 6 (quality gates) — quality gates still run to catch pre-existing CI failures.

### 2. Stage changes

Stage all modified and untracked files. Use `git add` with specific file paths -- do NOT use `git add -A` or `git add .`. Review the list and exclude:

- `.env` files or anything that looks like secrets/credentials
- Large binary files that shouldn't be in git
- Runtime/temp files (`.pid`, `.log`, `node_modules/`, etc.)

If you find files that should be excluded, mention them in your summary.

### 3. Sync beads issue state

Run `bd sync` to commit beads issue changes to git. This ensures any issue updates from this session (status changes, new issues, closed issues) are captured before the final push.

If `bd` is not installed or `.beads/` doesn't exist, skip this step silently.

### 4. Commit

Create a single commit with a clear, descriptive message summarizing ALL the work done in this session. Look at the diff and recent conversation context to write a meaningful message -- not a generic "checkpoint" or "wip".

Format:
```
<concise summary of what changed>

<optional body with details if the change is non-trivial>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

### 5. Run quality gates -- MANDATORY BEFORE PUSH

**Do NOT push until these pass.** Run the following checks and report results:

```bash
# JavaScript tests
npx jest --no-coverage

# Python quality gates (ruff + mypy + pytest with 100% coverage)
./scripts/verify-python.sh
```

**If any check fails:**
1. STOP — do not push
2. Report which check failed and the error output
3. Fix the failure (edit code, fix lint errors, update tests)
4. Re-run the failing check to confirm the fix
5. Return to step 2 (stage the fix, re-commit, re-run gates)

**Do NOT push code that fails quality gates.** This is the most important step.

### 6. Push -- NON-NEGOTIABLE

Pull with rebase first, then push to the remote tracking branch:

```
git pull --rebase
git push
```

If the push fails, resolve the issue and retry. Do NOT force push. If it cannot be resolved, report the specific error.

### 7. Monitor CI -- MANDATORY

After pushing, wait for CI to complete and verify it passes:

```bash
gh run watch --exit-status
```

**If CI fails:**
1. Check which job failed: `gh run view --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'`
2. Get failure details from the logs
3. Fix the failure locally
4. Return to step 2 (stage, commit, verify, push again)
5. Repeat until CI is green

**The plane is NOT landed until CI is green.** A push with failing CI is not a landing — it's a crash.

### 8. Clean up git state

```
git stash list
```

If there are stale stashes, note them in the summary (do not drop them without being asked).

### 9. Confirm clean state

Run `git status` one final time. Report:

- The commit hash and message
- The branch and remote
- Whether the working tree is clean
- CI status (pass/fail)
- Any files that were intentionally skipped

### Output format

Report a brief summary like:

```
Landed. <commit-hash> on <branch> -> <remote>
  <one-line commit message>
  <N> files changed
  Working tree: clean
  CI: green
```

Or if there were issues:

```
Partial landing:
  Committed: <hash>
  Push: failed (behind remote -- pull needed)
  CI: failed (Python Quality Gates)
  Skipped: .env, build/output.bin
  Stale stashes: 2 (run `git stash list` to review)
```
