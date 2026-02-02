"""Tests for WorkflowContext and shared types."""
import dataclasses

import pytest
from pydantic import BaseModel

from adws.adw_modules.types import (
    AdwsRequest,
    AdwsResponse,
    SecurityLogEntry,
    ShellResult,
    VerifyFeedback,
    VerifyResult,
    WorkflowContext,
)


def test_workflow_context_construction() -> None:
    """Test WorkflowContext stores all fields correctly."""
    ctx = WorkflowContext(
        inputs={"key": "value"},
        outputs={"result": 42},
        feedback=["some feedback"],
    )
    assert ctx.inputs == {"key": "value"}
    assert ctx.outputs == {"result": 42}
    assert ctx.feedback == ["some feedback"]


def test_workflow_context_defaults() -> None:
    """Test WorkflowContext defaults to empty collections."""
    ctx = WorkflowContext()
    assert ctx.inputs == {}
    assert ctx.outputs == {}
    assert ctx.feedback == []


def test_workflow_context_is_frozen() -> None:
    """Test WorkflowContext is an immutable frozen dataclass."""
    ctx = WorkflowContext()
    assert dataclasses.is_dataclass(ctx)
    assert type(ctx).__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_workflow_context_with_updates() -> None:
    """Test with_updates returns new context with changed fields."""
    ctx = WorkflowContext(inputs={"a": 1})
    updated = ctx.with_updates(outputs={"b": 2})
    assert updated.inputs == {"a": 1}
    assert updated.outputs == {"b": 2}
    assert updated is not ctx


def test_workflow_context_with_updates_preserves_unchanged() -> None:
    """Test with_updates preserves fields not being updated."""
    ctx = WorkflowContext(
        inputs={"a": 1},
        outputs={"b": 2},
        feedback=["f1"],
    )
    updated = ctx.with_updates(feedback=["f1", "f2"])
    assert updated.inputs == {"a": 1}
    assert updated.outputs == {"b": 2}
    assert updated.feedback == ["f1", "f2"]


def test_workflow_context_with_updates_inputs() -> None:
    """Test with_updates can replace inputs field."""
    ctx = WorkflowContext(inputs={"old": 1})
    updated = ctx.with_updates(inputs={"new": 2})
    assert updated.inputs == {"new": 2}
    assert updated.outputs == {}
    assert updated.feedback == []


def test_workflow_context_add_feedback_appends_entry() -> None:
    """RED: Will fail with AttributeError because add_feedback does not exist yet."""
    ctx = WorkflowContext(feedback=["first"])
    updated = ctx.add_feedback("second")
    assert updated.feedback == ["first", "second"]
    assert updated is not ctx


def test_workflow_context_add_feedback_preserves_other_fields() -> None:
    """RED: Will fail with AttributeError because add_feedback does not exist yet."""
    ctx = WorkflowContext(
        inputs={"a": 1},
        outputs={"b": 2},
        feedback=["f1"],
    )
    updated = ctx.add_feedback("f2")
    assert updated.inputs == {"a": 1}
    assert updated.outputs == {"b": 2}
    assert updated.feedback == ["f1", "f2"]


def test_workflow_context_add_feedback_on_empty() -> None:
    """RED: Will fail with AttributeError because add_feedback does not exist yet."""
    ctx = WorkflowContext()
    updated = ctx.add_feedback("first")
    assert updated.feedback == ["first"]


def test_workflow_context_promote_outputs_to_inputs() -> None:
    """RED: promote_outputs_to_inputs does not exist yet."""
    ctx = WorkflowContext(
        inputs={"existing": 1},
        outputs={"result": 42, "data": "hello"},
    )
    updated = ctx.promote_outputs_to_inputs()
    assert updated.inputs == {"existing": 1, "result": 42, "data": "hello"}
    assert updated.outputs == {}
    assert updated is not ctx


def test_workflow_context_promote_outputs_raises_on_conflicting_inputs() -> None:
    """Test promote_outputs_to_inputs raises ValueError on key collision."""
    ctx = WorkflowContext(
        inputs={"key": "old"},
        outputs={"key": "new"},
    )
    with pytest.raises(ValueError, match="Collision detected"):
        ctx.promote_outputs_to_inputs()


def test_workflow_context_promote_outputs_empty() -> None:
    """RED: promote_outputs_to_inputs does not exist yet."""
    ctx = WorkflowContext(inputs={"a": 1})
    updated = ctx.promote_outputs_to_inputs()
    assert updated.inputs == {"a": 1}
    assert updated.outputs == {}


def test_workflow_context_merge_outputs_adds_new() -> None:
    """RED: Will fail with AttributeError because merge_outputs does not exist."""
    ctx = WorkflowContext(outputs={"a": 1})
    updated = ctx.merge_outputs({"b": 2})
    assert updated.outputs == {"a": 1, "b": 2}
    assert updated is not ctx


def test_workflow_context_merge_outputs_overwrites_existing() -> None:
    """RED: Will fail with AttributeError because merge_outputs does not exist."""
    ctx = WorkflowContext(outputs={"key": "old"})
    updated = ctx.merge_outputs({"key": "new"})
    assert updated.outputs == {"key": "new"}


def test_workflow_context_merge_outputs_preserves_other_fields() -> None:
    """RED: Will fail with AttributeError because merge_outputs does not exist."""
    ctx = WorkflowContext(
        inputs={"i": 1},
        outputs={"o": 2},
        feedback=["f"],
    )
    updated = ctx.merge_outputs({"o2": 3})
    assert updated.inputs == {"i": 1}
    assert updated.outputs == {"o": 2, "o2": 3}
    assert updated.feedback == ["f"]


def test_workflow_context_merge_outputs_empty() -> None:
    """RED: Will fail with AttributeError because merge_outputs does not exist."""
    ctx = WorkflowContext(outputs={"a": 1})
    updated = ctx.merge_outputs({})
    assert updated.outputs == {"a": 1}


# --- AdwsRequest Tests ---


def test_adws_request_construction_all_fields() -> None:
    """RED: AdwsRequest does not exist yet."""
    req = AdwsRequest(
        model="claude-sonnet-4-20250514",
        system_prompt="You are helpful.",
        prompt="Hello",
        allowed_tools=["bash"],
        disallowed_tools=["web"],
        max_turns=5,
        permission_mode="acceptEdits",
    )
    assert req.model == "claude-sonnet-4-20250514"
    assert req.system_prompt == "You are helpful."
    assert req.prompt == "Hello"
    assert req.allowed_tools == ["bash"]
    assert req.disallowed_tools == ["web"]
    assert req.max_turns == 5
    assert req.permission_mode == "acceptEdits"


def test_adws_request_defaults() -> None:
    """RED: AdwsRequest does not exist yet."""
    req = AdwsRequest(system_prompt="sys", prompt="hello")
    assert req.model == "claude-sonnet-4-20250514"
    assert req.allowed_tools is None
    assert req.disallowed_tools is None
    assert req.max_turns is None
    assert req.permission_mode is None


def test_adws_request_is_frozen() -> None:
    """RED: AdwsRequest does not exist yet."""
    req = AdwsRequest(system_prompt="sys", prompt="hello")
    with pytest.raises(Exception):  # noqa: B017, PT011
        req.model = "other"


def test_adws_request_validation_missing_required() -> None:
    """RED: AdwsRequest does not exist yet."""
    with pytest.raises(Exception):  # noqa: B017, PT011
        AdwsRequest()  # type: ignore[call-arg]


def test_adws_request_is_pydantic_model() -> None:
    """RED: AdwsRequest does not exist yet."""
    assert issubclass(AdwsRequest, BaseModel)


# --- AdwsResponse Tests ---


def test_adws_response_construction_all_fields() -> None:
    """RED: AdwsResponse does not exist yet."""
    resp = AdwsResponse(
        result="Hello!",
        cost_usd=0.003,
        duration_ms=1500,
        session_id="sess-123",
        is_error=False,
        error_message=None,
        num_turns=2,
    )
    assert resp.result == "Hello!"
    assert resp.cost_usd == 0.003
    assert resp.duration_ms == 1500
    assert resp.session_id == "sess-123"
    assert resp.is_error is False
    assert resp.error_message is None
    assert resp.num_turns == 2


def test_adws_response_defaults() -> None:
    """RED: AdwsResponse does not exist yet."""
    resp = AdwsResponse()
    assert resp.result is None
    assert resp.cost_usd is None
    assert resp.duration_ms is None
    assert resp.session_id is None
    assert resp.is_error is False
    assert resp.error_message is None
    assert resp.num_turns is None


def test_adws_response_error_state() -> None:
    """RED: AdwsResponse does not exist yet."""
    resp = AdwsResponse(
        is_error=True,
        error_message="Model not found",
    )
    assert resp.is_error is True
    assert resp.error_message == "Model not found"
    assert resp.result is None


def test_adws_response_is_frozen() -> None:
    """RED: AdwsResponse does not exist yet."""
    resp = AdwsResponse()
    with pytest.raises(Exception):  # noqa: B017, PT011
        resp.is_error = True


def test_adws_response_is_pydantic_model() -> None:
    """RED: AdwsResponse does not exist yet."""
    assert issubclass(AdwsResponse, BaseModel)


# --- ShellResult Tests ---


def test_shell_result_construction() -> None:
    """RED: ShellResult does not exist yet."""
    sr = ShellResult(
        return_code=0,
        stdout="hello\n",
        stderr="",
        command="echo hello",
    )
    assert sr.return_code == 0
    assert sr.stdout == "hello\n"
    assert sr.stderr == ""
    assert sr.command == "echo hello"


def test_shell_result_frozen() -> None:
    """RED: ShellResult does not exist yet."""
    sr = ShellResult(
        return_code=0, stdout="", stderr="", command="ls"
    )
    assert dataclasses.is_dataclass(sr)
    assert type(sr).__dataclass_params__.frozen  # type: ignore[attr-defined]
    with pytest.raises(dataclasses.FrozenInstanceError):
        sr.return_code = 1  # type: ignore[misc]


# --- VerifyResult Tests ---


def test_verify_result_construction_all_fields() -> None:
    """RED: VerifyResult does not exist yet."""
    vr = VerifyResult(
        tool_name="jest",
        passed=True,
        errors=["error1", "error2"],
        raw_output="some output",
    )
    assert vr.tool_name == "jest"
    assert vr.passed is True
    assert vr.errors == ["error1", "error2"]
    assert vr.raw_output == "some output"


def test_verify_result_defaults() -> None:
    """RED: VerifyResult does not exist yet."""
    vr = VerifyResult(tool_name="mypy", passed=False)
    assert vr.tool_name == "mypy"
    assert vr.passed is False
    assert vr.errors == []
    assert vr.raw_output == ""


def test_verify_result_is_frozen() -> None:
    """RED: VerifyResult does not exist yet."""
    vr = VerifyResult(tool_name="ruff", passed=True)
    assert dataclasses.is_dataclass(vr)
    assert type(vr).__dataclass_params__.frozen  # type: ignore[attr-defined]
    with pytest.raises(dataclasses.FrozenInstanceError):
        vr.passed = False  # type: ignore[misc]


def test_verify_result_errors_default_factory() -> None:
    """RED: Verify each instance gets its own errors list."""
    vr1 = VerifyResult(tool_name="jest", passed=True)
    vr2 = VerifyResult(tool_name="jest", passed=True)
    assert vr1.errors is not vr2.errors
    assert vr1.errors == []
    assert vr2.errors == []


# --- VerifyFeedback Tests (Story 3.3) ---


def test_verify_feedback_construction_all_fields() -> None:
    """RED: VerifyFeedback does not exist yet."""
    vf = VerifyFeedback(
        tool_name="jest",
        errors=["FAIL src/test.ts"],
        raw_output="FAIL src/test.ts\n1 test failed",
        attempt=2,
        step_name="run_jest_step",
    )
    assert vf.tool_name == "jest"
    assert vf.errors == ["FAIL src/test.ts"]
    assert vf.raw_output == "FAIL src/test.ts\n1 test failed"
    assert vf.attempt == 2
    assert vf.step_name == "run_jest_step"


def test_verify_feedback_defaults() -> None:
    """RED: VerifyFeedback does not exist yet."""
    vf = VerifyFeedback(tool_name="ruff")
    assert vf.tool_name == "ruff"
    assert vf.errors == []
    assert vf.raw_output == ""
    assert vf.attempt == 1
    assert vf.step_name == ""


def test_verify_feedback_is_frozen() -> None:
    """RED: VerifyFeedback does not exist yet."""
    vf = VerifyFeedback(tool_name="mypy")
    assert dataclasses.is_dataclass(vf)
    assert type(vf).__dataclass_params__.frozen  # type: ignore[attr-defined]
    with pytest.raises(dataclasses.FrozenInstanceError):
        vf.tool_name = "other"  # type: ignore[misc]


def test_verify_feedback_errors_default_factory() -> None:
    """RED: Each instance gets its own errors list."""
    vf1 = VerifyFeedback(tool_name="jest")
    vf2 = VerifyFeedback(tool_name="jest")
    assert vf1.errors is not vf2.errors
    assert vf1.errors == []
    assert vf2.errors == []


def test_verify_feedback_field_access() -> None:
    """RED: Verify all fields are accessible."""
    vf = VerifyFeedback(
        tool_name="playwright",
        errors=["err1", "err2"],
        raw_output="raw",
        attempt=3,
        step_name="run_playwright_step",
    )
    assert vf.tool_name == "playwright"
    assert len(vf.errors) == 2
    assert vf.raw_output == "raw"
    assert vf.attempt == 3
    assert vf.step_name == "run_playwright_step"


# --- SecurityLogEntry Tests (Story 5.4) ---


def test_security_log_entry_construction() -> None:
    """SecurityLogEntry stores all fields correctly."""
    entry = SecurityLogEntry(
        timestamp="2026-02-02T10:30:00+00:00",
        command="rm -rf /",
        pattern_name="rm_rf_root",
        reason="Recursive force-delete of root filesystem",
        alternative="Use 'rm -rf ./specific-directory'",
        session_id="session-abc123",
        action="blocked",
    )
    assert entry.timestamp == "2026-02-02T10:30:00+00:00"
    assert entry.command == "rm -rf /"
    assert entry.pattern_name == "rm_rf_root"
    assert entry.reason == "Recursive force-delete of root filesystem"
    assert entry.alternative == "Use 'rm -rf ./specific-directory'"
    assert entry.session_id == "session-abc123"
    assert entry.action == "blocked"


def test_security_log_entry_default_action() -> None:
    """SecurityLogEntry defaults action to 'blocked'."""
    entry = SecurityLogEntry(
        timestamp="2026-02-02T10:30:00+00:00",
        command="rm -rf /",
        pattern_name="rm_rf_root",
        reason="Dangerous",
        alternative="Safer approach",
        session_id="sess-1",
    )
    assert entry.action == "blocked"


def test_security_log_entry_is_frozen() -> None:
    """SecurityLogEntry is a frozen dataclass."""
    entry = SecurityLogEntry(
        timestamp="2026-02-02T10:30:00+00:00",
        command="rm -rf /",
        pattern_name="rm_rf_root",
        reason="Dangerous",
        alternative="Safer approach",
        session_id="sess-1",
    )
    assert dataclasses.is_dataclass(entry)
    assert type(entry).__dataclass_params__.frozen  # type: ignore[attr-defined]
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.command = "other"  # type: ignore[misc]


def test_security_log_entry_to_jsonl() -> None:
    """SecurityLogEntry.to_jsonl serializes to compact JSON."""
    entry = SecurityLogEntry(
        timestamp="2026-02-02T10:30:00+00:00",
        command="rm -rf /",
        pattern_name="rm_rf_root",
        reason="Recursive force-delete",
        alternative="Use explicit path",
        session_id="sess-1",
        action="blocked",
    )
    jsonl = entry.to_jsonl()
    assert '"timestamp":"2026-02-02T10:30:00+00:00"' in jsonl
    assert '"command":"rm -rf /"' in jsonl
    assert '"pattern_name":"rm_rf_root"' in jsonl
    assert '"reason":"Recursive force-delete"' in jsonl
    assert '"alternative":"Use explicit path"' in jsonl
    assert '"session_id":"sess-1"' in jsonl
    assert '"action":"blocked"' in jsonl
    # Single line, no extra spaces
    assert "\n" not in jsonl
    assert ": " not in jsonl
