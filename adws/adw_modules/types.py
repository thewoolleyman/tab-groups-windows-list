"""Shared type definitions for ADWS pipeline."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from typing import Literal

from pydantic import BaseModel, ConfigDict

DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"

PermissionMode = Literal["default", "acceptEdits", "plan", "bypassPermissions"]


@dataclass(frozen=True)
class HookEvent:
    """Structured hook event for JSONL logging (FR33)."""

    timestamp: str
    event_type: str
    hook_name: str
    session_id: str
    payload: dict[str, object] = field(
        default_factory=dict,
    )

    def to_jsonl(self) -> str:
        """Serialize to single-line JSON for JSONL format."""
        return json.dumps(asdict(self), separators=(",", ":"))


@dataclass(frozen=True)
class VerifyResult:
    """Structured result from a quality gate tool execution."""

    tool_name: str
    passed: bool
    errors: list[str] = field(default_factory=list)
    raw_output: str = ""


@dataclass(frozen=True)
class VerifyFeedback:
    """Structured feedback from a failed verify attempt.

    Captures which tool failed, what errors occurred, and which
    attempt this represents. Used for accumulation across
    verify-implement retry cycles (FR16, FR17).
    """

    tool_name: str
    errors: list[str] = field(default_factory=list)
    raw_output: str = ""
    attempt: int = 1
    step_name: str = ""


@dataclass(frozen=True)
class ShellResult:
    """Result of a shell command execution."""

    return_code: int
    stdout: str
    stderr: str
    command: str


@dataclass(frozen=True)
class WorkflowContext:
    """Immutable context flowing through pipeline steps.

    Frozen dataclass: attribute reassignment is blocked. Container fields
    (dicts, lists) are shallow-frozen — callers MUST NOT mutate them in
    place. Steps return a NEW context via with_updates(). Never mutate.
    """

    inputs: dict[str, object] = field(default_factory=dict)
    outputs: dict[str, object] = field(default_factory=dict)
    feedback: list[str] = field(default_factory=list)

    def with_updates(
        self,
        inputs: dict[str, object] | None = None,
        outputs: dict[str, object] | None = None,
        feedback: list[str] | None = None,
    ) -> WorkflowContext:
        """Return new context with specified fields replaced."""
        return replace(
            self,
            inputs=inputs if inputs is not None else self.inputs,
            outputs=outputs if outputs is not None else self.outputs,
            feedback=feedback if feedback is not None else self.feedback,
        )

    def add_feedback(self, entry: str) -> WorkflowContext:
        """Return new context with feedback entry appended."""
        return replace(self, feedback=[*self.feedback, entry])

    def promote_outputs_to_inputs(self) -> WorkflowContext:
        """Merge outputs into inputs and clear outputs for the next step.

        Raises:
            ValueError: If any output key already exists in inputs.
        """
        collisions = set(self.inputs.keys()) & set(self.outputs.keys())
        if collisions:
            msg = f"Collision detected: outputs {collisions} already exist in inputs"
            raise ValueError(msg)

        return replace(
            self,
            inputs={**self.inputs, **self.outputs},
            outputs={},
        )

    def merge_outputs(self, new_outputs: dict[str, object]) -> WorkflowContext:
        """Return new context with new_outputs merged into existing outputs."""
        return replace(self, outputs={**self.outputs, **new_outputs})


@dataclass(frozen=True)
class FileTrackEntry:
    """Structured file tracking entry for context bundles (FR34)."""

    timestamp: str
    file_path: str
    operation: str
    session_id: str
    hook_name: str

    def to_jsonl(self) -> str:
        """Serialize to single-line JSON for JSONL format."""
        return json.dumps(asdict(self), separators=(",", ":"))


@dataclass(frozen=True)
class SecurityLogEntry:
    """Structured security log entry for audit logging (FR38)."""

    timestamp: str
    command: str
    pattern_name: str
    reason: str
    alternative: str
    session_id: str
    action: str = "blocked"

    def to_jsonl(self) -> str:
        """Serialize to single-line JSON for JSONL format."""
        return json.dumps(asdict(self), separators=(",", ":"))


class AdwsRequest(BaseModel):
    """Request payload for SDK boundary calls."""

    model_config = ConfigDict(frozen=True)

    model: str = DEFAULT_CLAUDE_MODEL
    system_prompt: str
    prompt: str
    allowed_tools: list[str] | None = None
    disallowed_tools: list[str] | None = None
    max_turns: int | None = None
    permission_mode: PermissionMode | None = None


class AdwsResponse(BaseModel):
    """Response payload from SDK boundary calls."""

    model_config = ConfigDict(frozen=True)

    result: str | None = None
    cost_usd: float | None = None
    duration_ms: int | None = None
    session_id: str | None = None
    is_error: bool = False
    error_message: str | None = None
    num_turns: int | None = None
