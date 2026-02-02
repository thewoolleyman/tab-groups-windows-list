"""Format accumulated feedback as context for retry agents."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from adws.adw_modules.types import WorkflowContext

_PREFIX = "VERIFY_FEEDBACK|"
_NO_FAILURES = "No previous verify failures recorded."
_RAW_DELIM = "|raw="


def _unescape_field(value: str) -> str:
    """Reverse escaping applied by _escape_field."""
    return value.replace("\\x3B\\x3B", ";;").replace(
        "\\x7C", "|"
    )


def _parse_feedback_entry(
    entry: str,
) -> dict[str, str] | None:
    """Parse a serialized VerifyFeedback string.

    Returns a dict of fields or None if not a feedback
    entry.  The ``raw`` field is always last and may
    contain unescaped ``|`` characters, so it is
    extracted first via a single split.
    """
    if not entry.startswith(_PREFIX):
        return None

    body = entry[len(_PREFIX):]

    # Split off 'raw' (last field, may contain '|')
    raw_idx = body.find(_RAW_DELIM)
    if raw_idx >= 0:
        head = body[:raw_idx]
        raw_value = body[raw_idx + len(_RAW_DELIM):]
    else:
        head = body
        raw_value = ""

    fields: dict[str, str] = {}
    for part in head.split("|"):
        if "=" in part:
            key, _, value = part.partition("=")
            # 'errors' is unescaped per-item after split
            if key != "errors":
                fields[key] = _unescape_field(value)
            else:
                fields[key] = value
    fields["raw"] = raw_value
    return fields


def _parse_errors(errors_raw: str) -> list[str]:
    """Split and unescape individual error strings."""
    if not errors_raw:
        return []
    parts = errors_raw.split(";;")
    return [
        _unescape_field(e).strip()
        for e in parts
        if _unescape_field(e).strip()
    ]


def _format_entry(fields: dict[str, str]) -> str:
    """Format a parsed feedback entry as markdown."""
    tool = fields.get("tool", "unknown")
    step = fields.get("step", "unknown")
    errors_raw = fields.get("errors", "")
    errors = _parse_errors(errors_raw)
    error_count = len(errors)
    lines = [
        f"- **{tool}** (step: {step})"
        f" -- {error_count} error(s):",
    ]
    lines.extend(f"  - {err}" for err in errors)
    return "\n".join(lines)


def build_feedback_context(ctx: WorkflowContext) -> str:
    """Format accumulated feedback for implementation retry.

    Reads ctx.feedback entries, parses VerifyFeedback entries,
    and produces a human-readable + agent-consumable summary.
    Non-VerifyFeedback entries are included as-is.
    """
    if not ctx.feedback:
        return _NO_FAILURES

    sections: list[str] = ["## Previous Verify Failures"]
    current_attempt: str | None = None

    for entry in ctx.feedback:
        parsed = _parse_feedback_entry(entry)
        if parsed is not None:
            attempt = parsed.get("attempt", "?")
            attempt_header = f"### Attempt {attempt}"
            if attempt_header != current_attempt:
                current_attempt = attempt_header
                sections.append("")
                sections.append(attempt_header)
            sections.append(_format_entry(parsed))
        else:
            sections.append(f"\n{entry}")

    return "\n".join(sections)
