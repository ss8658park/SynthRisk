"""AI-assisted triage of Verible lint findings."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from .lint_runner import Violation


MODEL = "gpt-5.6-terra"

SYSTEM_PROMPT = """You are a senior digital design engineer reviewing RTL lint results.
You will receive: (1) the full SystemVerilog source of one file, (2) a list of lint violations from verible-verilog-lint.

Your job:
1. TRIAGE: For each violation, classify its synthesis risk:
   - "critical": can produce incorrect hardware (inferred latches, sim/synth mismatch, unintended sequential logic)
   - "warning": intent/robustness issue (e.g. legacy always blocks, missing begin/end that invites future bugs)
   - "style": cosmetic only, no hardware consequence (naming, whitespace, file endings)
2. DETECT: Independently inspect the source for latch-inference or synthesis risks the linter did NOT report (e.g. combinational if without else, incomplete assignments). Report each as an additional finding.

For every item provide:
- "why": 1-2 sentences explaining the hardware consequence in plain language
- "fix": a short suggested code change (as text; do not assume it will be auto-applied)

Respond ONLY with valid JSON matching this schema:
{
  "findings": [
    {
      "source": "verible" | "ai",
      "rule": string,
      "line": number,
      "severity": "critical" | "warning" | "style",
      "message": string,
      "why": string,
      "fix": string
    }
  ]
}
Do not include markdown fences or any text outside the JSON.
"""


@dataclass(frozen=True)
class Finding:
    """A triaged lint finding or an AI-detected synthesis risk."""

    source: str
    rule: str
    line: int
    severity: str
    message: str
    why: str
    fix: str


@dataclass(frozen=True)
class TriageResult:
    """All findings produced while reviewing one source file."""

    findings: list[Finding]


class TriageError(RuntimeError):
    """Raised when the model response cannot be parsed as the required JSON."""

    def __init__(self, message: str, raw_response: str) -> None:
        super().__init__(f"{message}\nRaw response:\n{raw_response}")
        self.raw_response = raw_response


def _strip_markdown_fences(response: str) -> str:
    """Remove a single accidental fenced-JSON wrapper from a response."""

    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?[ \t]*\r?\n?", "", cleaned, count=1, flags=re.I)
        cleaned = re.sub(r"\r?\n?```$", "", cleaned, count=1).strip()
    return cleaned


def _result_from_response(response: str) -> TriageResult:
    """Convert a model response into validated dataclass instances."""

    try:
        payload: Any = json.loads(_strip_markdown_fences(response))
        raw_findings = payload["findings"]
        if not isinstance(raw_findings, list):
            raise TypeError("'findings' must be a list")
        findings = [
            Finding(
                source=str(item["source"]),
                rule=str(item["rule"]),
                line=int(item["line"]),
                severity=str(item["severity"]),
                message=str(item["message"]),
                why=str(item["why"]),
                fix=str(item["fix"]),
            )
            for item in raw_findings
        ]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise TriageError("Could not parse triage response as valid findings JSON.", response) from exc

    return TriageResult(findings=findings)


def _mock_result() -> TriageResult:
    """Provide representative data for report development without API usage."""

    return TriageResult(
        findings=[
            Finding(
                source="verible",
                rule="always-comb",
                line=7,
                severity="critical",
                message="Combinational logic uses a legacy always block.",
                why="A plain always block can hide incomplete assignments and infer storage. "
                "always_comb makes the combinational intent explicit.",
                fix="Replace 'always @*' with 'always_comb' and assign every output on all paths.",
            ),
            Finding(
                source="verible",
                rule="posix-eof",
                line=12,
                severity="style",
                message="File must end with a newline.",
                why="This does not affect synthesized hardware.",
                fix="Add a trailing newline at the end of the file.",
            ),
            Finding(
                source="ai",
                rule="incomplete-assignment",
                line=7,
                severity="critical",
                message="A combinational branch leaves an output unassigned.",
                why="When the condition is false, the output retains its prior value, "
                "which infers a latch.",
                fix="Give the output a default assignment before the conditional or add an else branch.",
            ),
        ]
    )


def triage_file(
    source_path: str, source_code: str, violations: list[Violation]
) -> TriageResult:
    """Send one file and all of its lint violations in a single model request."""

    if os.environ.get("SYNTHRISK_MOCK") == "1":
        return _mock_result()

    load_dotenv()
    violation_lines = "\n".join(
        f"line {violation.line}: {violation.message} [{violation.rule}]"
        for violation in violations
    )
    user_prompt = (
        f"Source path: {source_path}\n\n"
        f"SystemVerilog source:\n{source_code}\n\n"
        f"Verible violations:\n{violation_lines}"
    )

    client = OpenAI()
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    response = completion.choices[0].message.content or ""
    return _result_from_response(response)
