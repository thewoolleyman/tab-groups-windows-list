"""Pipeline error types for ADWS workflow engine."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class PipelineError:
    """Structured error for pipeline step failures."""

    step_name: str
    error_type: str
    message: str
    context: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return plain dict suitable for JSON serialization."""
        return asdict(self)

    def __str__(self) -> str:
        """Human-readable error representation for logging."""
        base = f"PipelineError[{self.step_name}] {self.error_type}: {self.message}"
        if self.context:
            base += f" | context={self.context}"
        return base
