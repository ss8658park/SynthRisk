# SynthRisk

**Triage RTL lint warnings by synthesis risk, not rule severity.**

SynthRisk uses GPT-5.6 to re-rank Verible RTL lint warnings by their real hardware
consequence — separating cosmetic style nits from issues that actually turn into
unintended hardware (inferred latches, unintended sequential logic) before a design
is cast in silicon. It also inspects the source directly and reports synthesis risks
the linter never flagged.

> Built for the OpenAI Build Week hackathon.
> Developed with **Codex (GPT-5.6 Terra)**; the triage engine runs on **GPT-5.6 Terra** via the OpenAI API.

---

## The problem

RTL (the code that describes a chip) can compile cleanly and pass simulation while
still describing broken hardware. A missing `else`, a `case` without `default`, or a
plain `always` block where `always_ff` / `always_comb` was intended can all synthesize
into **inferred latches** or unintended logic — bugs that only surface at the netlist
or timing stage, where fixing them is enormously expensive. In silicon, there is no
runtime patch.

Linters like [Verible](https://github.com/chipsalliance/verible) catch many of these.
The trouble is *how* they report them: a real design produces hundreds of warnings,
and a missing-newline nit is printed with the same weight as a latch-inferring
`case` statement. Worse, some real risks (a combinational `if` without `else`,
blocking assignments in sequential logic) are not reported at all. The signal that
matters drowns in noise — or never appears.

## What SynthRisk does

SynthRisk adds the one thing a linter doesn't have: **judgment about consequence.**

1. Runs `verible-verilog-lint --ruleset=all` on one or more SystemVerilog files.
2. Sends the warnings **plus the full source** to **GPT-5.6**, which:
   - classifies each linter warning by *synthesis risk* — critical / warning / style;
   - independently inspects the source and reports latch-inference risks the linter
     stayed silent on, marked with an `[!] AI-DETECTED` badge.
3. Prints a risk-sorted report per file — each finding with a plain-language *why*
   and a suggested *fix* — plus a cross-file risk summary table.

The linter knows the rules. SynthRisk knows the consequences.

> **Note:** SynthRisk *shows* suggested fixes; it never rewrites your RTL. In hardware,
> automatic edits are too dangerous — the designer decides.

## Architecture

```
.sv files ──▶ verible-verilog-lint (--ruleset=all) ──▶ raw warnings
                                                           │
                                      full source ─────────┤
                                                           ▼
                                     GPT-5.6 Terra triage (one API call per file)
                                      · risk classification of linter warnings
                                      · independent latch-risk detection
                                                           │
                                                           ▼
                        risk-sorted report per file + summary table
```

- **Detection:** Verible (deterministic rule checking)
- **Judgment:** GPT-5.6 Terra (context-aware risk classification + gap detection)
- **Built with:** Codex (GPT-5.6 Terra)

## Setup

Requirements: Python 3.8+, a [Verible](https://github.com/chipsalliance/verible/releases)
binary, and an OpenAI API key.

```bash
git clone https://github.com/ss8658park/SynthRisk.git
cd SynthRisk
pip install -r requirements.txt
```

1. Install Verible: download a binary release for your platform and either put
   `verible-verilog-lint` on your `PATH`, or point the env var `VERIBLE_LINT_PATH`
   at the executable.
2. Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=sk-...
   ```

## Usage

```bash
# Full run: lint + GPT-5.6 triage
python -m synthrisk examples/latch_if.sv

# Multiple files (glob patterns work on Windows too)
python -m synthrisk examples/*.sv

# Linter output only, no AI call
python -m synthrisk examples/latch_if.sv --no-ai

# Development mode: render the report with canned findings, no API call
python -m synthrisk examples/latch_if.sv --mock

# Plain text (no ANSI colors); colors also auto-disable when piping to a file
python -m synthrisk examples/latch_if.sv --no-color
```

## Example

`examples/latch_if.sv` contains a combinational `if` with no `else` — a classic
latch-inference bug. Verible (even with `--ruleset=all`) reports only a style
suggestion and a missing newline. SynthRisk's output:

```
[CRITICAL] line 8  (incomplete-combinational-assignment) `data_o` is assigned only when `en_i` is true.
    source: [!] AI-DETECTED (not reported by linter)
    why: When `en_i` is low, `data_o` must retain its previous value, causing
         synthesis to infer a level-sensitive latch.
    fix: Add a default or `else` assignment, e.g. `data_o = '0; if (en_i) data_o = data_i;`.
         If storage is intended, use an explicit `always_latch` block.
[WARNING] line 7  (always-comb) Use 'always_comb' instead of 'always @*'.
    source: verible
    why: `always @*` is synthesizable, but `always_comb` declares combinational
         intent and enables additional tool checks.
    fix: Replace `always @* begin` with `always_comb begin`.
[STYLE] line 12  (posix-eof) File must end with a newline.
    source: verible
    why: No effect on simulation or synthesized hardware.
    fix: Add a newline after the final `endmodule`.
1 critical, 1 warning, 1 style - review critical items before synthesis.
```

The item the linter never reported is the one that would have become real,
incorrect hardware.

Running all four examples at once produces a per-file risk summary:

```
File                        Critical  Warning  Style
examples/latch_if.sv           1        1       1
examples/latch_case.sv         2        1       1
examples/legacy_always.sv      0        3       1
examples/clean.sv              0        0       8
------------------------------------------------
TOTAL                          3        5      11
```

Note the clean reference file: the linter still emits 8 style warnings on it,
but SynthRisk correctly reports **zero synthesis risks** — no false alarms.

Full logs for the example cases are in [`logs/`](logs/).

## Built with Codex

The entire tool was developed with **Codex (GPT-5.6 Terra, medium reasoning)** inside
VS Code, following a spec-driven workflow: each module (lint-output parser, triage
engine, report renderer, multi-file runner) was generated from a detailed prompt in
a single Codex session, verified against the real Verible output, and committed
immediately.

- The commit history documents each Codex-generated change (commit messages are tagged
  `generated with Codex, GPT-5.6 Terra`).
- Screenshots of the Codex sessions are in [`docs/codex-evidence/`](docs/codex-evidence/).
- The runtime triage engine calls **`gpt-5.6-terra`** via the OpenAI API — one request
  per analyzed file.

## Roadmap (out of scope for the hackathon MVP)

- Support for additional RTL linters (Slang, Spyglass) behind the same triage layer
- CI / git-hook integration
- Timing-risk hints alongside latch-risk detection

## License

MIT
