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
        """Return plain dict suitable for JSON serialization.

        Non-serializable context values are converted to string representations.
        """
        data = asdict(self)

        def make_safe(obj: object) -> object:
            if isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            if isinstance(obj, (list, tuple)):
                return [make_safe(x) for x in obj]
            if isinstance(obj, dict):
                return {str(k): make_safe(v) for k, v in obj.items()}
            return str(obj)

        data["context"] = make_safe(self.context)
        return data

    def __str__(self) -> str:
        """Human-readable error representation for logging."""
        max_len = 500
        base = f"PipelineError[{self.step_name}] {self.error_type}: {self.message}"
        if self.context:
            ctx_str = str(self.context)
            if len(ctx_str) > max_len:
                ctx_str = ctx_str[: max_len - 3] + "..."
            base += f" | context={ctx_str}"
        return base
