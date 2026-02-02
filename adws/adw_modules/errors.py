"""Pipeline error types for ADWS workflow engine."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PipelineError:
    """Structured error for pipeline step failures."""

    step_name: str
    error_type: str
    message: str
    context: dict[str, object] = field(default_factory=dict)
