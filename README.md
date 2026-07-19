# SynthRisk

**Triage RTL lint warnings by synthesis risk, not rule severity.**

SynthRisk uses GPT-5.6 to re-rank Verible RTL lint warnings by their real hardware
consequence — separating cosmetic style nits from issues that actually turn into
unintended hardware (inferred latches, unintended sequential logic) before a design
is cast in silicon.

> Built for the OpenAI Build Week hackathon.
> Developed with **Codex**; the triage engine runs on **GPT-5.6**.

---

## The problem

RTL (the code that describes a chip) can compile cleanly and pass simulation while
still describing broken hardware. A missing `else`, a `case` without `default`, or a
plain `always` block where `always_ff` / `always_comb` was intended can all synthesize
into **inferred latches** or unintended logic — bugs that only surface at the netlist
or timing stage, where fixing them is enormously expensive. In silicon, there is no
runtime patch.

Linters like [Verible](https://github.com/chipsalliance/verible) do catch these. The
trouble is *how* they report them: a real design produces hundreds of warnings, and a
naming-convention nit is printed with the same weight as a latch-inferring `else`. The
signal that matters drowns in noise.

## What SynthRisk does

SynthRisk adds the one thing a linter doesn't have: **judgment about consequence.**

1. Runs `verible-verilog-lint` on a SystemVerilog file.
2. Sends the warnings plus the source to **GPT-5.6**, which classifies each warning by
   *synthesis risk* — does this actually become bad hardware, or is it just style?
3. Prints the warnings re-ordered by risk, each with a plain-language reason and a
   suggested fix.

The linter knows the rules. SynthRisk knows the consequences.

> **Note:** SynthRisk *shows* suggested fixes; it never rewrites your RTL. In hardware,
> automatic edits are too dangerous — the designer decides.

## Architecture

```
.sv file ──▶ verible-verilog-lint ──▶ raw warnings
                                          │
                                          ▼
                          GPT-5.6 triage (risk classification)
                                          │
                                          ▼
                     risk-sorted report (reason + suggested fix)
```

- **Detection:** Verible (deterministic rule checking)
- **Judgment:** GPT-5.6 (context-aware risk classification)
- **Built with:** Codex

## Usage

> _TODO: fill in once the CLI is finalized._

```bash
# planned interface
synthrisk path/to/design.sv
```

## Example

> _TODO: add real terminal output once the pipeline runs end-to-end._

## Built with Codex

This project was developed using Codex inside VS Code. Development history is visible
in the commit log. _TODO: add a short note / screenshots of Codex sessions before
submission._

## Roadmap (out of scope for the hackathon MVP)

- Support for additional RTL linters (Slang, Spyglass) behind the same triage layer
- CI / git-hook integration
- Multi-file / project-level analysis

## License

MIT
