"""Command-line interface for synthrisk."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import os

from .lint_runner import LinterExecutionError, run_linter
from .report import render_report
from .triage import TriageError, triage_file


def main(argv: Sequence[str] | None = None) -> int:
    """Run the linter for one SystemVerilog file."""

    parser = argparse.ArgumentParser(description="Lint a Verilog/SystemVerilog file.")
    parser.add_argument("file", help="Verilog or SystemVerilog source file to lint")
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip AI triage and print raw parsed lint violations.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use representative triage data without calling the API.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored report output.",
    )
    args = parser.parse_args(argv)

    try:
        result = run_linter(args.file)
    except LinterExecutionError as exc:
        parser.error(str(exc))

    if args.no_ai:
        for violation in result.violations:
            print(
                f"{violation.file}:{violation.line}:{violation.col_start}-{violation.col_end}: "
                f"{violation.message} [{violation.category}] [{violation.rule}]"
            )
        return 0

    if args.mock:
        os.environ["SYNTHRISK_MOCK"] = "1"

    try:
        with open(args.file, encoding="utf-8") as source_file:
            source_code = source_file.read()
        triage_result = triage_file(args.file, source_code, result.violations)
    except (OSError, UnicodeError, TriageError) as exc:
        parser.error(str(exc))

    render_report(triage_result, use_color=not args.no_color)

    return 0
