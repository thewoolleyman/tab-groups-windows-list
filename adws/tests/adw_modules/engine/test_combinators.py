"""Tests for engine combinators (with_verification, sequence)."""
from __future__ import annotations

from adws.adw_modules import engine as engine_pkg
from adws.adw_modules.engine import combinators as combo_mod
from adws.adw_modules.engine.combinators import (
    sequence,
    with_verification,
)
from adws.adw_modules.engine.types import Step, Workflow
from adws.adw_modules.types import WorkflowContext

# --- Task 1: with_verification tests ---


class TestWithVerification:
    """Tests for with_verification combinator."""

    def test_with_verification_returns_workflow(self) -> None:
        """Returns Workflow with 2 steps, correct name, not disp."""
        main = Step(name="impl", function="fn1")
        verify = Step(name="verify", function="fn2")
        result = with_verification(main, verify)
        assert isinstance(result, Workflow)
        assert len(result.steps) == 2
        assert result.name == "impl_with_verification"
        assert result.dispatchable is False

    def test_with_verification_step_order(self) -> None:
        """Main step is first, verify step is second."""
        main = Step(name="impl", function="fn1")
        verify = Step(name="verify", function="fn2")
        result = with_verification(main, verify)
        assert result.steps[0].name == "impl"
        assert result.steps[1].name == "verify"

    def test_with_verification_custom_name(self) -> None:
        """output_name parameter overrides default name."""
        main = Step(name="impl", function="fn1")
        verify = Step(name="verify", function="fn2")
        result = with_verification(
            main, verify, output_name="custom_wf",
        )
        assert result.name == "custom_wf"

    def test_with_verification_verify_max_attempts(self) -> None:
        """verify_step gets configured max_attempts."""
        main = Step(name="impl", function="fn1")
        verify = Step(
            name="verify", function="fn2", max_attempts=1,
        )
        result = with_verification(
            main, verify, verify_max_attempts=3,
        )
        assert result.steps[1].max_attempts == 3

    def test_with_verification_preserves_main_step(self) -> None:
        """Main step properties preserved unchanged."""
        main = Step(
            name="impl",
            function="fn1",
            always_run=True,
            max_attempts=5,
            retry_delay_seconds=1.5,
            output="my_output",
        )
        verify = Step(name="verify", function="fn2")
        result = with_verification(main, verify)
        assert result.steps[0] is main

    def test_with_verification_preserves_verify_defaults(
        self,
    ) -> None:
        """Verify step properties (other than max_attempts) kept."""

        def cond(ctx: WorkflowContext) -> bool:
            return True

        verify = Step(  # noqa: S604
            name="verify",
            function="fn2",
            always_run=True,
            retry_delay_seconds=2.0,
            shell=True,
            command="echo test",
            output="v_out",
            input_from={"src": "dest"},
            condition=cond,
        )
        main = Step(name="impl", function="fn1")
        result = with_verification(main, verify)
        v = result.steps[1]
        assert v.name == "verify"
        assert v.function == "fn2"
        assert v.always_run is True
        assert v.retry_delay_seconds == 2.0
        assert v.shell is True
        assert v.command == "echo test"
        assert v.output == "v_out"
        assert v.input_from == {"src": "dest"}
        assert v.condition is cond
        # Verify condition callable works
        assert cond(WorkflowContext()) is True

    def test_with_verification_description(self) -> None:
        """Workflow description references main step name."""
        main = Step(name="impl", function="fn1")
        verify = Step(name="verify", function="fn2")
        result = with_verification(main, verify)
        assert "impl" in result.description


# --- Task 2: sequence tests ---


class TestSequence:
    """Tests for sequence combinator."""

    def test_sequence_returns_workflow(self) -> None:
        """Returns Workflow with combined steps, not disp."""
        wf_a = Workflow(
            name="a",
            description="wf a",
            steps=[Step(name="s1", function="fn1")],
        )
        wf_b = Workflow(
            name="b",
            description="wf b",
            steps=[Step(name="s2", function="fn2")],
        )
        result = sequence(wf_a, wf_b)
        assert isinstance(result, Workflow)
        assert result.name == "a_then_b"
        assert result.dispatchable is False

    def test_sequence_step_count(self) -> None:
        """Step count equals sum of both workflows' steps."""
        wf_a = Workflow(
            name="a",
            description="wf a",
            steps=[
                Step(name="s1", function="fn1"),
                Step(name="s2", function="fn2"),
            ],
        )
        wf_b = Workflow(
            name="b",
            description="wf b",
            steps=[Step(name="s3", function="fn3")],
        )
        result = sequence(wf_a, wf_b)
        assert len(result.steps) == 3

    def test_sequence_step_order(self) -> None:
        """A's steps come before B's steps."""
        wf_a = Workflow(
            name="a",
            description="wf a",
            steps=[Step(name="a1", function="fn1")],
        )
        wf_b = Workflow(
            name="b",
            description="wf b",
            steps=[Step(name="b1", function="fn2")],
        )
        result = sequence(wf_a, wf_b)
        assert result.steps[0].name == "a1"
        assert result.steps[1].name == "b1"

    def test_sequence_custom_name(self) -> None:
        """name parameter overrides default."""
        wf_a = Workflow(
            name="a", description="a",
            steps=[Step(name="s1", function="fn1")],
        )
        wf_b = Workflow(
            name="b", description="b",
            steps=[Step(name="s2", function="fn2")],
        )
        result = sequence(wf_a, wf_b, name="custom")
        assert result.name == "custom"

    def test_sequence_custom_description(self) -> None:
        """description parameter overrides default."""
        wf_a = Workflow(
            name="a", description="a",
            steps=[Step(name="s1", function="fn1")],
        )
        wf_b = Workflow(
            name="b", description="b",
            steps=[Step(name="s2", function="fn2")],
        )
        result = sequence(
            wf_a, wf_b, description="my desc",
        )
        assert result.description == "my desc"

    def test_sequence_preserves_step_properties(self) -> None:
        """All step fields preserved from source workflows."""

        def cond(ctx: WorkflowContext) -> bool:
            return True

        step_a = Step(
            name="a1",
            function="fn1",
            always_run=True,
            max_attempts=3,
            retry_delay_seconds=1.0,
            output="a1_out",
            input_from={"src": "dest"},
            condition=cond,
        )
        step_b = Step(  # noqa: S604
            name="b1",
            function="fn2",
            shell=True,
            command="echo hi",
        )
        wf_a = Workflow(
            name="a", description="a", steps=[step_a],
        )
        wf_b = Workflow(
            name="b", description="b", steps=[step_b],
        )
        result = sequence(wf_a, wf_b)
        # Step A preserved by reference
        assert result.steps[0] is step_a
        # Step B preserved by reference
        assert result.steps[1] is step_b
        # Verify condition callable works
        assert cond(WorkflowContext()) is True

    def test_sequence_three_workflows(self) -> None:
        """Chaining: sequence(A, sequence(B, C)) is correct."""
        wf_a = Workflow(
            name="a", description="a",
            steps=[Step(name="a1", function="fn1")],
        )
        wf_b = Workflow(
            name="b", description="b",
            steps=[Step(name="b1", function="fn2")],
        )
        wf_c = Workflow(
            name="c", description="c",
            steps=[Step(name="c1", function="fn3")],
        )
        result = sequence(wf_a, sequence(wf_b, wf_c))
        assert len(result.steps) == 3
        assert result.steps[0].name == "a1"
        assert result.steps[1].name == "b1"
        assert result.steps[2].name == "c1"

    def test_sequence_empty_workflow(self) -> None:
        """Sequence with empty-steps workflow works."""
        wf_a = Workflow(
            name="a", description="a", steps=[],
        )
        wf_b = Workflow(
            name="b", description="b",
            steps=[Step(name="b1", function="fn1")],
        )
        result = sequence(wf_a, wf_b)
        assert len(result.steps) == 1
        assert result.steps[0].name == "b1"

    def test_sequence_default_description(self) -> None:
        """Default description includes both workflow names."""
        wf_a = Workflow(
            name="alpha", description="a",
            steps=[Step(name="s1", function="fn1")],
        )
        wf_b = Workflow(
            name="beta", description="b",
            steps=[Step(name="s2", function="fn2")],
        )
        result = sequence(wf_a, wf_b)
        assert "alpha" in result.description
        assert "beta" in result.description


# --- Task 3: Composability tests ---


class TestComposability:
    """Tests for composing combinators together."""

    def test_with_verification_into_sequence(self) -> None:
        """sequence(with_verification(A, B), C) -> 3 steps."""
        step_a = Step(name="impl", function="fn1")
        step_b = Step(name="verify", function="fn2")
        step_c = Step(name="close", function="fn3")
        wf_ab = with_verification(step_a, step_b)
        wf_c = Workflow(
            name="close", description="close",
            steps=[step_c],
        )
        result = sequence(wf_ab, wf_c)
        assert len(result.steps) == 3
        assert result.steps[0].name == "impl"
        assert result.steps[1].name == "verify"
        assert result.steps[2].name == "close"

    def test_sequence_with_verification_both_ends(
        self,
    ) -> None:
        """sequence(with_ver(A,B), with_ver(C,D)) -> 4 steps."""
        a = Step(name="a", function="fn1")
        b = Step(name="b", function="fn2")
        c = Step(name="c", function="fn3")
        d = Step(name="d", function="fn4")
        wf_ab = with_verification(a, b)
        wf_cd = with_verification(c, d)
        result = sequence(wf_ab, wf_cd)
        assert len(result.steps) == 4
        assert result.steps[0].name == "a"
        assert result.steps[1].name == "b"
        assert result.steps[2].name == "c"
        assert result.steps[3].name == "d"


# --- Task 5: Import path tests ---


class TestCombinatorImports:
    """Tests for importing combinators from engine package."""

    def test_import_from_engine_package(self) -> None:
        """with_verification and sequence from engine pkg."""
        assert callable(engine_pkg.with_verification)
        assert callable(engine_pkg.sequence)

    def test_import_from_combinators_module(self) -> None:
        """with_verification and sequence from combinators."""
        assert callable(combo_mod.with_verification)
        assert callable(combo_mod.sequence)

    def test_engine_package_exports_match(self) -> None:
        """Engine package exports same functions as module."""
        assert engine_pkg.with_verification is (
            combo_mod.with_verification
        )
        assert engine_pkg.sequence is combo_mod.sequence
