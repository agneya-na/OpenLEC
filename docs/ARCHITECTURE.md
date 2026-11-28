# OpenLEC Architecture

OpenLEC is a Python-first, AI-native EDA verification infrastructure for
**low-power Logic Equivalence Checking (LEC)** and **IEEE 1801 UPF power-aware
verification**, backed by the open-source Yosys synthesis engine.

## High-level view

```text
                     ┌───────────────────────────┐
                     │            CLI            │   openlec/cli.py
                     └────────────┬──────────────┘
                                  │ OpenLECConfig → VerificationContext
                     ┌────────────▼──────────────┐
                     │        Orchestrator       │   agents/orchestrator.py
                     └──────────────────────────┘
   ┌────────┬─────────┬───────────┼───────────┬───────────┬───────────┐
   ▼        ▼         ▼           ▼           ▼           ▼           ▼
Parsing  PowerIntent Equivalence Timing     Power     Optimization Reporting
   │        │         │           │           │           │           │
   ▼        ▼         ▼           ▼           ▼           ▼           ▼
UPFParser UPFChecker LECEngine TimingEst  PowerEst   Optimizer   (report)
   │        │         │           │           │           │
   │        │         └─────┬─────┘           │           │
   │        │         ┌─────▼──────┐          │           │
   │        │         │ YosysRunner│──yosys (external, open source)
   │        │         └────────────┘          │           │
   └────────┴─────────┴───────────┬───────────┴───────────┘
                     ┌─────────────▼─────────────┐
                     │  openlec/models (typed    │   single shared contract
                     │  contract: contexts,      │
                     │  verdicts, UPF intent)    │
                     └───────────────────────────┘
```

## Layer responsibilities

| Layer | Modules | Responsibility |
|---|---|---|
| CLI | `cli.py`, `config.py` | Argument parsing, YAML config merge, exit codes (0 pass / 1 fail / 2 usage) |
| Orchestration | `agents/orchestrator.py` | Fixed agent pipeline, halt semantics, always-on reporting |
| Agents | `agents/*_agent.py` | One verification concern per agent; mutates shared `VerificationContext` |
| Engine | `engine/*.py` | Yosys subprocess, SAT LEC, UPF parse/check, estimators, passes |
| Models | `models/*.py` | Pydantic/dataclass contract shared by every layer |

## Data flow and halt semantics

1. `ParsingAgent` validates inputs and loads the UPF intent
   (Conformal analogue: `READ DESIGN` / `READ POWER INTENT`). The golden design
   is `rtl_file`; the revised design is `revised_file` (CLI `--revised`), or the
   golden file itself when none is given. Multi-file inputs (file lists, include
   directories, defines, SystemVerilog) arrive as `golden_source` /
   `revised_source` (`engine/design_source.py`); every engine reads a
   `DesignSource` or a plain path, and each side's macros are reset before it is
   read (`design -reset-vlog`) so they cannot leak between golden and revised.
2. `PowerIntentAgent` runs structural UPF checks; a failed isolation check
   **halts** the pipeline (an un-isolated switched domain is a hard error).
3. `EquivalenceAgent` runs `LECEngine` (Conformal: `COMPARE` / `ANALYZE ABORT`).
   Each design is loaded into its own Yosys design (`design -stash`) and
   flattened, then the `equiv_make/simple/induct/status` flow tries to prove
   every compare point. If points stay unproven, a miter of the two designs is
   bounded-model-checked (`sat -seq N`, all-zero initial state) to look for a
   concrete counterexample. `NONEQUIVALENT` (counterexample found) halts;
   `ABORT` (setup error, timeout, or unproven without a counterexample) and
   `INCONCLUSIVE` (no compare points) are recorded but do not halt — the final
   verdict still fails.
4. `TimingAgent` / `PowerAgent` fill `DesignMetrics` from the Yosys
   `stat -json` cell/register counts (heuristic estimators until
   OpenSTA/Liberty integration lands).
5. `OptimizationAgent` proposes synthesis passes; a pass is accepted only if the
   LEC gate passes **and** metrics stay within budget; otherwise the step is
   rejected and the previous netlist is kept.
6. `ReportingAgent` always runs (also on halt) and emits
   `VerificationReport.to_text()`. The run passes only if LEC is `EQUIVALENT`,
   every UPF family passes, and the final delay/power are within budget.

`VerificationContext` is the single mutable state object; agents never talk to
each other directly, only through it. This keeps agents independently testable
with stubs (see `tests/test_agents.py`).

## Conformal → OpenLEC mapping

| Cadence Conformal | OpenLEC |
|---|---|
| `READ DESIGN -golden` / `-revised` | `rtl_file` / `--revised` (or `-f`/`-F` and `--revised-f`/`--revised-F` file lists) → `ParsingAgent` + Yosys `read_verilog [-sv] -I -D` |
| `READ POWER INTENT` | `UPFParser.parse()` |
| `COMPARE` / `ANALYZE SETUP` | `LECEngine.run_equivalence_check()` (`equiv_make/simple/induct/status`) |
| `ANALYZE ABORT` | miter + `sat` BMC counterexample search; `LECVerdict.ABORT` + `abort_points` |
| `CHECK LOWPOWER CELLS` / `COMPARE POWER CONSISTENCY` | `UPFChecker` rule families |
| `REPORT LOWPOWER VERIFICATION` | `ReportingAgent` / `VerificationReport` |
| dofile scripting | `AgenticOrchestrator` pipeline |

## Verdict semantics

| Symbol | Meaning |
|---|---|
| `LECVerdict.EQUIVALENT` | SAT proof completed, all compare points proven |
| `LECVerdict.NONEQUIVALENT` | concrete counterexample found (`LECResult.counterexample`) → hard halt |
| `LECVerdict.ABORT` | setup error, timeout, or points unproven with no counterexample within the BMC bound → fail-soft, no halt |
| `LECVerdict.INCONCLUSIVE` | no compare points matched → fail-soft, no halt |
| `StepVerdict.ACCEPT` | optimization pass kept (LEC + budgets held) |
| `StepVerdict.REJECT` | pass reverted, previous netlist retained |

## Extension guide

* **New agent**: subclass `BaseAgent`, implement `execute(ctx) -> ctx`,
  register it in `AgenticOrchestrator.__init__` in pipeline order.
* **New UPF command**: add model in `models/upf_models.py`, one `_parse_*`
  method in `UPFParser`, optional rule method in `UPFChecker`,
  document it in `docs/UPF_SUPPORT.md`.
* **New synthesis pass**: append to `Optimizer` pass list; the LEC gate and
  metric gates are applied automatically by `OptimizationAgent`.

## Testing strategy

* Unit tests are **Yosys-free**: engines are replaced with stubs at the agent
  boundary (`tests/test_agents.py`), parser/checker tests are pure Python, and
  the LEC verdict logic and `stat -json` parsing are tested against recorded
  Yosys log excerpts (`tests/test_lec_engine.py`, `tests/test_engine_passes.py`).
* Integration tests (`requires_yosys`) run real Yosys and skip themselves when
  `yosys` is not on `PATH`. Set `OPENLEC_REQUIRE_YOSYS=1` to make a missing
  Yosys an error instead of a skip.
* CI (`.github/workflows/ci.yml`) runs ruff + mypy, then the full suite, the
  demo and a CLI RTL-vs-synthesized-netlist check on Python 3.10/3.12/3.13 with
  Ubuntu's Yosys 0.33, plus one job on the latest OSS CAD Suite Yosys to catch
  Yosys output-format changes early. `OPENLEC_REQUIRE_YOSYS` is set there.