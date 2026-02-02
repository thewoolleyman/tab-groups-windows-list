"""Shared type definitions for ADWS pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field, replace


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
        """Merge outputs into inputs and clear outputs for the next step."""
        return replace(
            self,
            inputs={**self.inputs, **self.outputs},
            outputs={},
        )

    def merge_outputs(self, new_outputs: dict[str, object]) -> WorkflowContext:
        """Return new context with new_outputs merged into existing outputs."""
        return replace(self, outputs={**self.outputs, **new_outputs})
