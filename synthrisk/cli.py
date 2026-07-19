"""Command-line interface for synthrisk."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from .lint_runner import LinterExecutionError, run_linter


def main(argv: Sequence[str] | None = None) -> int:
    """Run the linter for one SystemVerilog file."""

    parser = argparse.ArgumentParser(description="Lint a Verilog/SystemVerilog file.")
    parser.add_argument("file", help="Verilog or SystemVerilog source file to lint")
    args = parser.parse_args(argv)

    try:
        result = run_linter(args.file)
    except LinterExecutionError as exc:
        parser.error(str(exc))

    for violation in result.violations:
        print(
            f"{violation.file}:{violation.line}:{violation.col_start}-{violation.col_end}: "
            f"{violation.message} [{violation.category}] [{violation.rule}]"
        )

    return 0
