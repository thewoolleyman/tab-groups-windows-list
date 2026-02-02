"""Dangerous command blocker step functions (FR37-FR39, NFR4).

Provides block_dangerous_command() for core blocking logic and
block_dangerous_command_safe() for fail-open wrapper behavior.
Blocks known destructive patterns and suggests safer alternatives.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from returns.io import IOFailure, IOResult, IOSuccess
from returns.unsafe import unsafe_perform_io

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError
from adws.adw_modules.types import SecurityLogEntry, WorkflowContext


@dataclass(frozen=True)
class DangerousPattern:
    """A known destructive command pattern with metadata."""

    name: str
    pattern: re.Pattern[str]
    reason: str
    alternative: str


@dataclass(frozen=True)
class BlockResult:
    """Result of checking a command against dangerous patterns."""

    blocked: bool
    command: str
    pattern_name: str
    reason: str
    alternative: str


DANGEROUS_PATTERNS: list[DangerousPattern] = [
    DangerousPattern(
        name="rm_rf_root",
        pattern=re.compile(
            r"\brm\b.*\s+-[^\s]*r[^\s]*f[^\s]*\s+/"
            r"|\brm\b.*\s+-[^\s]*f[^\s]*r[^\s]*\s+/"
            r"|\brm\b\s.*-[^\s]*r\b.*\s+-[^\s]*f\b.*\s+/"
            r"|\brm\b\s.*-[^\s]*f\b.*\s+-[^\s]*r\b.*\s+/",
        ),
        reason="Recursive force-delete of root filesystem",
        alternative=(
            "Use 'rm -rf ./specific-directory'"
            " with an explicit, safe path"
        ),
    ),
    DangerousPattern(
        name="rm_rf_home",
        pattern=re.compile(
            r"\brm\b.*\s+-[^\s]*r[^\s]*f[^\s]*\s+(?:~|\$HOME)"
            r"|\brm\b.*\s+-[^\s]*f[^\s]*r[^\s]*\s+(?:~|\$HOME)"
            r"|\brm\b\s.*-[^\s]*r\b.*\s+-[^\s]*f\b.*\s+(?:~|\$HOME)"
            r"|\brm\b\s.*-[^\s]*f\b.*\s+-[^\s]*r\b.*\s+(?:~|\$HOME)",
        ),
        reason="Recursive force-delete of home directory",
        alternative=(
            "Use 'rm -rf ~/specific-subdirectory'"
            " instead"
        ),
    ),
    DangerousPattern(
        name="rm_rf_star",
        pattern=re.compile(
            r"\brm\b.*\s+-[^\s]*r[^\s]*f[^\s]*\s+\*"
            r"|\brm\b.*\s+-[^\s]*f[^\s]*r[^\s]*\s+\*"
            r"|\brm\b\s.*-[^\s]*r\b.*\s+-[^\s]*f\b.*\s+\*"
            r"|\brm\b\s.*-[^\s]*f\b.*\s+-[^\s]*r\b.*\s+\*",
        ),
        reason=(
            "Recursive force-delete with wildcard"
            " -- may destroy unexpected files"
        ),
        alternative=(
            "Use 'rm -rf ./specific-directory'"
            " with an explicit path"
        ),
    ),
    DangerousPattern(
        name="git_push_force_main",
        pattern=re.compile(
            r"\bgit\b\s+push\b.*(?:--force|-f)\b"
            r".*\b(?:main|master)\b"
            r"|\bgit\b\s+push\b.*\b(?:main|master)\b"
            r".*(?:--force|-f)\b",
        ),
        reason=(
            "Force-push to main/master"
            " destroys remote history"
        ),
        alternative=(
            "Use 'git push --force-with-lease'"
            " or push to a feature branch"
        ),
    ),
    DangerousPattern(
        name="git_reset_hard",
        pattern=re.compile(
            r"\bgit\b\s+reset\b.*--hard\b",
        ),
        reason=(
            "Hard reset discards all uncommitted changes"
        ),
        alternative=(
            "Use 'git stash' to save changes"
            " before resetting"
        ),
    ),
    DangerousPattern(
        name="git_clean_force",
        pattern=re.compile(
            r"\bgit\b\s+clean\b.*-[^\s]*f",
        ),
        reason=(
            "git clean -f removes untracked files"
            " permanently"
        ),
        alternative=(
            "Use 'git clean -n' (dry run) first"
            " to preview what will be deleted"
        ),
    ),
    DangerousPattern(
        name="chmod_recursive_777",
        pattern=re.compile(
            r"\bchmod\b.*-R\s+777\s+/"
            r"|\bchmod\b.*777.*-R\s+/",
        ),
        reason=(
            "Recursive chmod 777 on root makes all"
            " files world-writable"
        ),
        alternative=(
            "Use specific permissions on specific"
            " directories (e.g., chmod 755)"
        ),
    ),
    DangerousPattern(
        name="dd_dev_overwrite",
        pattern=re.compile(
            r"\bdd\b.*\bof=/dev/",
        ),
        reason=(
            "dd writing to /dev/ device can overwrite"
            " disk or partition"
        ),
        alternative=(
            "Double-check the target device;"
            " use 'of=output.img' for file output"
        ),
    ),
    DangerousPattern(
        name="mkfs",
        pattern=re.compile(
            r"\bmkfs\b",
        ),
        reason=(
            "mkfs formats a filesystem, destroying"
            " all data on the device"
        ),
        alternative=(
            "Verify the target device carefully"
            " before formatting"
        ),
    ),
    DangerousPattern(
        name="dev_overwrite",
        pattern=re.compile(
            r">\s*/dev/[hs]d[a-z]",
        ),
        reason=(
            "Redirecting output to a device"
            " overwrites it completely"
        ),
        alternative=(
            "Redirect to a regular file instead"
            " (e.g., '> output.bin')"
        ),
    ),
    DangerousPattern(
        name="fork_bomb",
        pattern=re.compile(
            r":\(\)\s*\{\s*:\|:&\s*\}\s*;:",
        ),
        reason=(
            "Fork bomb exhausts system resources"
            " and causes a denial of service"
        ),
        alternative=(
            "Do not run fork bombs;"
            " use proper process management"
        ),
    ),
    DangerousPattern(
        name="curl_pipe_sh",
        pattern=re.compile(
            r"\bcurl\b.*\|\s*(?:sudo\s+|env\s+"
            r"|(?:/\S+/)?)?(?:sh|bash|zsh)\b"
            r"|\bwget\b.*\|\s*(?:sudo\s+|env\s+"
            r"|(?:/\S+/)?)?(?:sh|bash|zsh)\b",
        ),
        reason=(
            "Piping remote content to shell"
            " executes untrusted code"
        ),
        alternative=(
            "Download file first, inspect it,"
            " then execute manually"
        ),
    ),
    DangerousPattern(
        name="git_checkout_dot",
        pattern=re.compile(
            r"\bgit\b\s+checkout\b\s+\.",
        ),
        reason=(
            "git checkout . discards all"
            " unstaged changes"
        ),
        alternative=(
            "Use 'git stash' to save changes"
            " before discarding"
        ),
    ),
]


def _check_command(
    command: str,
) -> BlockResult | None:
    """Check command against dangerous patterns.

    Pure function: no I/O. Returns BlockResult on match,
    None if command is safe.
    """
    for pattern in DANGEROUS_PATTERNS:
        if pattern.pattern.search(command):
            return BlockResult(
                blocked=True,
                command=command,
                pattern_name=pattern.name,
                reason=pattern.reason,
                alternative=pattern.alternative,
            )
    return None


def block_dangerous_command(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Block dangerous commands with audit logging (FR37-FR39).

    Validates command input, checks against dangerous patterns.
    If blocked, writes security log entry and returns IOSuccess
    with blocked=True in outputs. If safe, returns IOSuccess
    with blocked=False. Returns IOFailure only for internal
    errors (missing/invalid input).
    """
    command = ctx.inputs.get("command")
    if not isinstance(command, str) or not command:
        return IOFailure(
            PipelineError(
                step_name="block_dangerous_command",
                error_type="MissingInputError",
                message=(
                    "Required input 'command'"
                    " is missing or not a string"
                ),
                context={"available_inputs": list(
                    ctx.inputs.keys(),
                )},
            ),
        )

    result = _check_command(command)
    if result is None:
        return IOSuccess(
            ctx.with_updates(
                outputs={"blocked": False},
            ),
        )

    # Command is blocked -- write security log
    session_id = ctx.inputs.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        ts = datetime.now(tz=UTC).strftime(
            "%Y%m%d%H%M%S",
        )
        session_id = f"unknown-{ts}"

    entry = SecurityLogEntry(
        timestamp=datetime.now(tz=UTC).isoformat(),
        command=command,
        pattern_name=result.pattern_name,
        reason=result.reason,
        alternative=result.alternative,
        session_id=session_id,
        action="blocked",
    )

    write_result = io_ops.write_security_log(
        session_id, entry.to_jsonl(),
    )

    security_log_written = True
    if isinstance(write_result, IOFailure):
        security_log_written = False

    return IOSuccess(
        ctx.with_updates(
            outputs={
                "blocked": True,
                "pattern_name": result.pattern_name,
                "reason": result.reason,
                "alternative": result.alternative,
                "security_log_written": security_log_written,
            },
        ),
    )


def block_dangerous_command_safe(
    ctx: WorkflowContext,
) -> IOResult[WorkflowContext, PipelineError]:
    """Fail-open wrapper for dangerous command blocking (NFR4).

    Calls block_dangerous_command(). On failure, logs to stderr
    and returns IOSuccess with blocked=False in outputs.
    NEVER returns IOFailure -- fail-open means never blocking
    the observed operation on internal error.
    """
    try:
        result = block_dangerous_command(ctx)
        if isinstance(result, IOSuccess):
            return result

        error = unsafe_perform_io(result.failure())
        error_msg = str(error)

        io_ops.write_stderr(
            f"block_dangerous_command_safe:"
            f" {error_msg}\n",
        )
    except Exception as exc:  # noqa: BLE001
        error_msg = f"unexpected error: {exc}"
        io_ops.write_stderr(
            f"block_dangerous_command_safe:"
            f" {error_msg}\n",
        )

    return IOSuccess(
        ctx.with_updates(
            outputs={
                "blocked": False,
                "blocker_error": error_msg,
            },
        ),
    )
