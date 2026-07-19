"""Run Verible lint and convert its output into structured violations."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Violation:
    """One lint violation reported by Verible."""

    file: str
    line: int
    col_start: int
    col_end: int
    message: str
    category: str
    rule: str


@dataclass(frozen=True)
class LintResult:
    """Structured and unstructured output from one Verible invocation."""

    violations: list[Violation]
    unparsed: list[str]


class LinterExecutionError(RuntimeError):
    """Raised when the Verible executable cannot be started."""


_VIOLATION_PATTERN = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<col_start>\d+)"
    r"(?:-(?P<col_end>\d+))?: "
    r"(?P<message>.*?) \[(?P<category>[^\]]+)\] \[(?P<rule>[^\]]+)\]$"
)


def parse_output(output: str) -> LintResult:
    """Parse Verible output, retaining non-violation lines in ``unparsed``."""

    violations: list[Violation] = []
    unparsed: list[str] = []

    for output_line in output.splitlines():
        match = _VIOLATION_PATTERN.match(output_line)
        if match is None:
            unparsed.append(output_line)
            continue

        col_start = int(match["col_start"])
        col_end_text = match["col_end"]
        violations.append(
            Violation(
                file=match["file"],
                line=int(match["line"]),
                col_start=col_start,
                col_end=int(col_end_text) if col_end_text is not None else col_start,
                message=match["message"],
                category=match["category"],
                rule=match["rule"],
            )
        )

    return LintResult(violations=violations, unparsed=unparsed)


def run_linter(file: str | Path) -> LintResult:
    """Run Verible for ``file`` and return parsed results.

    Lint violations intentionally produce a nonzero Verible exit status, so the
    subprocess result is parsed regardless of its return code.
    """

    linter_path = os.environ.get("VERIBLE_LINT_PATH", "verible-verilog-lint")
    command = [linter_path, "--ruleset=all", str(file)]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise LinterExecutionError(
            f"Could not execute Verible linter at {linter_path!r}: {exc}"
        ) from exc

    return parse_output(completed.stdout + completed.stderr)
