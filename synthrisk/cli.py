"""Command-line interface for synthrisk."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import glob
import os

from .lint_runner import LinterExecutionError, run_linter
from .report import format_critical_count, render_report
from .triage import TriageError, TriageResult, triage_file


_SEVERITIES = ("critical", "warning", "style")


def _expand_file_arguments(file_arguments: Sequence[str]) -> list[str]:
    """Expand wildcard arguments for shells that do not expand globs themselves."""

    files: list[str] = []
    for file_argument in file_arguments:
        if "*" not in file_argument and "?" not in file_argument:
            files.append(file_argument)
            continue
        matches = glob.glob(file_argument)
        # Keep unmatched patterns so they produce a visible per-file error.
        files.extend(matches if matches else [file_argument])
    return files


def _print_file_header(source_path: str) -> None:
    print("==============================")
    print(f" {source_path}")
    print("==============================")


def _raw_violation_output(source_path: str) -> tuple[int, int, int]:
    """Print raw violations and return zero triage counts for --no-ai mode."""

    result = run_linter(source_path)
    for violation in result.violations:
        print(
            f"{violation.file}:{violation.line}:{violation.col_start}-{violation.col_end}: "
            f"{violation.message} [{violation.category}] [{violation.rule}]"
        )
    return (0, 0, 0)


def _triage_counts(result: TriageResult) -> tuple[int, int, int]:
    counts = {severity: 0 for severity in _SEVERITIES}
    for finding in result.findings:
        if finding.severity in counts:
            counts[finding.severity] += 1
    return tuple(counts[severity] for severity in _SEVERITIES)


def _right_aligned_critical(count: int, width: int, use_color: bool) -> str:
    """Right-align a possibly ANSI-colored number by its visible width."""

    return " " * (width - len(str(count))) + format_critical_count(
        count, use_color=use_color
    )


def _print_summary(
    rows: list[tuple[str, tuple[int, int, int]]], use_color: bool
) -> None:
    """Render the aggregate finding-count table."""

    file_width = max(len("File"), *(len(source_path) for source_path, _ in rows))
    critical_width = len("Critical")
    warning_width = len("Warning")
    style_width = len("Style")

    print(
        f"{'File':<{file_width}}  {'Critical':>{critical_width}}  "
        f"{'Warning':>{warning_width}}  {'Style':>{style_width}}"
    )
    totals = [0, 0, 0]
    for source_path, counts in rows:
        critical, warning, style = counts
        totals[0] += critical
        totals[1] += warning
        totals[2] += style
        print(
            f"{source_path:<{file_width}}  "
            f"{_right_aligned_critical(critical, critical_width, use_color)}  "
            f"{warning:>{warning_width}}  {style:>{style_width}}"
        )

    print("-" * (file_width + critical_width + warning_width + style_width + 6))
    print(
        f"{'TOTAL':<{file_width}}  "
        f"{_right_aligned_critical(totals[0], critical_width, use_color)}  "
        f"{totals[1]:>{warning_width}}  {totals[2]:>{style_width}}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Lint, triage, and report on one or more SystemVerilog files."""

    parser = argparse.ArgumentParser(description="Lint Verilog/SystemVerilog files.")
    parser.add_argument(
        "files",
        nargs="+",
        help="Verilog or SystemVerilog source files to lint (glob patterns supported)",
    )
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

    if args.mock:
        os.environ["SYNTHRISK_MOCK"] = "1"

    use_color = not args.no_color
    summary_rows: list[tuple[str, tuple[int, int, int]]] = []
    had_error = False
    had_critical = False

    for source_path in _expand_file_arguments(args.files):
        _print_file_header(source_path)
        try:
            if args.no_ai:
                counts = _raw_violation_output(source_path)
            else:
                lint_result = run_linter(source_path)
                with open(source_path, encoding="utf-8") as source_file:
                    source_code = source_file.read()
                triage_result = triage_file(
                    source_path, source_code, lint_result.violations
                )
                render_report(triage_result, use_color=use_color)
                counts = _triage_counts(triage_result)
        except (LinterExecutionError, OSError, UnicodeError, TriageError) as exc:
            print(f"Error processing {source_path}: {exc}")
            had_error = True
            continue
        except Exception as exc:
            # API client errors are surfaced per file without stopping the batch.
            print(f"Error processing {source_path}: {exc}")
            had_error = True
            continue

        summary_rows.append((source_path, counts))
        had_critical = had_critical or counts[0] > 0

    _print_summary(summary_rows, use_color)
    return 1 if had_error or had_critical else 0
