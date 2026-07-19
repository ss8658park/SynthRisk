"""Terminal rendering for AI triage results."""

from __future__ import annotations

from .triage import Finding, TriageResult


try:
    from colorama import Fore, Style, just_fix_windows_console

    just_fix_windows_console()
    _RESET = Style.RESET_ALL
    _COLORS = {
        "critical": Fore.RED,
        "warning": Fore.YELLOW,
        "style": Style.DIM + Fore.WHITE,
    }
except ImportError:
    _RESET = ""
    _COLORS: dict[str, str] = {}


_SEVERITY_ORDER = {"critical": 0, "warning": 1, "style": 2}


def _color_for(finding: Finding, text: str) -> str:
    color = _COLORS.get(finding.severity, "")
    return f"{color}{text}{_RESET}" if color else text


def render_report(result: TriageResult) -> None:
    """Print findings in priority order followed by a concise summary."""

    findings = sorted(
        result.findings,
        key=lambda finding: (_SEVERITY_ORDER.get(finding.severity, 99), finding.line),
    )

    for finding in findings:
        header = (
            f"[{finding.severity.upper()}] line {finding.line}  "
            f"({finding.rule}) {finding.message}"
        )
        print(_color_for(finding, header))
        if finding.source == "ai":
            print("    source: ★ AI-DETECTED (not reported by linter)")
        else:
            print("    source: verible")
        print(f"    why: {finding.why}")
        print(f"    fix: {finding.fix}")

    counts = {severity: 0 for severity in _SEVERITY_ORDER}
    for finding in findings:
        if finding.severity in counts:
            counts[finding.severity] += 1
    summary = (
        f"{counts['critical']} critical, {counts['warning']} warning, "
        f"{counts['style']} style — review critical items before synthesis."
    )
    try:
        print(summary)
    except UnicodeEncodeError:
        # Some legacy Windows console encodings cannot display an em dash.
        print(summary.replace("—", "-"))
