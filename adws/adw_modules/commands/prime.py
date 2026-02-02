"""Prime command -- load codebase context into session (FR31).

Reads relevant project files (CLAUDE.md, architecture docs,
directory structure) and assembles a context bundle for use
by subsequent commands. Non-workflow command with custom logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from returns.io import IOFailure, IOResult, IOSuccess

from adws.adw_modules import io_ops
from adws.adw_modules.errors import PipelineError

if TYPE_CHECKING:
    from adws.adw_modules.types import WorkflowContext


@dataclass(frozen=True)
class PrimeContextResult:
    """User-facing output of the /prime command.

    success: True when context loaded successfully.
    files_loaded: Paths of files successfully read.
    summary: Human-readable description of what was loaded.
    context_sections: Mapping of section name to content.
    """

    success: bool
    files_loaded: list[str]
    summary: str
    context_sections: dict[str, str] = field(
        default_factory=dict,
    )


@dataclass(frozen=True)
class PrimeFileSpec:
    """Specification for a file to load during /prime.

    key: Section name in context_sections.
    path: Relative path from project root.
    description: Human-readable name for the file.
    required: True means failure is an error; False means
    skip gracefully.
    """

    key: str
    path: str
    description: str
    required: bool


PRIME_FILE_SPECS: tuple[PrimeFileSpec, ...] = (
    PrimeFileSpec(
        key="claude_md",
        path="CLAUDE.md",
        description="TDD mandate and coding conventions",
        required=True,
    ),
    PrimeFileSpec(
        key="architecture",
        path=(
            "_bmad-output/planning-artifacts"
            "/architecture.md"
        ),
        description="Architecture decision document",
        required=False,
    ),
    PrimeFileSpec(
        key="epics",
        path=(
            "_bmad-output/planning-artifacts"
            "/epics.md"
        ),
        description="Epic and story breakdown",
        required=False,
    ),
)


def _extract_io_value(
    result: IOResult[str, PipelineError],
) -> str:
    """Extract the inner value from an IOSuccess.

    Precondition: result MUST be IOSuccess. Caller MUST
    guard with isinstance(result, IOSuccess) before calling.

    Private helper for imperative loops that need to
    accumulate values from multiple IOResult calls. Uses
    returns.unsafe only in this boundary-crossing helper.
    """
    from returns.unsafe import (  # noqa: PLC0415
        unsafe_perform_io,
    )

    assert isinstance(result, IOSuccess), (  # noqa: S101
        "_extract_io_value requires IOSuccess"
    )
    return str(unsafe_perform_io(result.unwrap()))


def _load_file_context(
    file_specs: tuple[PrimeFileSpec, ...],
) -> IOResult[PrimeContextResult, PipelineError]:
    """Load context files per the given specs.

    Required file failures produce IOFailure. Optional file
    failures are skipped with a note in the summary.
    """
    files_loaded: list[str] = []
    context_sections: dict[str, str] = {}
    skipped: list[str] = []

    for spec in file_specs:
        read_result = io_ops.read_prime_file(spec.path)

        if isinstance(read_result, IOSuccess):
            content = _extract_io_value(read_result)
            files_loaded.append(spec.path)
            context_sections[spec.key] = content
        elif spec.required:
            return IOFailure(
                PipelineError(
                    step_name="commands.prime",
                    error_type="RequiredFileError",
                    message=(
                        f"Required file missing:"
                        f" {spec.path}"
                    ),
                    context={"path": spec.path},
                ),
            )
        else:
            skipped.append(spec.description)

    count = len(files_loaded)
    parts = [f"Loaded {count} file(s)"]
    if skipped:
        skipped_str = ", ".join(skipped)
        parts.append(f"skipped: {skipped_str}")
    summary = ". ".join(parts)

    return IOSuccess(
        PrimeContextResult(
            success=True,
            files_loaded=files_loaded,
            summary=summary,
            context_sections=context_sections,
        ),
    )


def _load_directory_context() -> IOResult[
    dict[str, str], PipelineError
]:
    """Load directory tree context for adws/ and project root.

    Directory tree failures are non-fatal -- returns empty
    string for the failed directory.
    """
    trees: dict[str, str] = {}

    adws_result = io_ops.get_directory_tree(
        "adws", max_depth=3,
    )
    if isinstance(adws_result, IOSuccess):
        trees["adws_tree"] = _extract_io_value(adws_result)
    else:
        trees["adws_tree"] = ""

    project_result = io_ops.get_directory_tree(
        ".", max_depth=2,
    )
    if isinstance(project_result, IOSuccess):
        trees["project_tree"] = _extract_io_value(
            project_result,
        )
    else:
        trees["project_tree"] = ""

    return IOSuccess(trees)


def run_prime_command(
    ctx: WorkflowContext,  # noqa: ARG001
) -> IOResult[PrimeContextResult, PipelineError]:
    """Execute /prime and return structured context result.

    Loads file context and directory trees, merges them into
    a single PrimeContextResult. Required file failures
    propagate as IOFailure. The ctx parameter is part of the
    command interface signature (FR28).
    """

    def _merge_with_dirs(
        pcr: PrimeContextResult,
    ) -> IOResult[PrimeContextResult, PipelineError]:
        dir_result = _load_directory_context()

        def _combine(
            dir_trees: dict[str, str],
        ) -> IOResult[PrimeContextResult, PipelineError]:
            merged = {
                **pcr.context_sections,
                **dir_trees,
            }
            return IOSuccess(
                PrimeContextResult(
                    success=pcr.success,
                    files_loaded=pcr.files_loaded,
                    summary=pcr.summary,
                    context_sections=merged,
                ),
            )

        return dir_result.bind(_combine)

    return _load_file_context(PRIME_FILE_SPECS).bind(
        _merge_with_dirs,
    )
