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
   (Conformal analogue: `READ DESIGN` / `READ POWER INTENT`).
2. `PowerIntentAgent` runs structural UPF checks; a failed isolation check
   **halts** the pipeline (an un-isolated switched domain is a hard error).
3. `EquivalenceAgent` runs the Yosys `equiv_*` SAT flow (Conformal: `COMPARE`).
   `NONEQUIVALENT` halts; `ABORT` (SAT timeout/inconclusive) is recorded but does
   not halt — the final verdict still fails because `lec_ok` is false.
4. `TimingAgent` / `PowerAgent` fill `DesignMetrics` (heuristic estimators until
   OpenSTA/Liberty integration lands).
5. `OptimizationAgent` proposes synthesis passes; a pass is accepted only if the
   LEC gate passes **and** metrics stay within budget; otherwise the step is
   rejected and the previous netlist is kept.
6. `ReportingAgent` always runs (also on halt) and emits
   `VerificationReport.to_text()`.

`VerificationContext` is the single mutable state object; agents never talk to
each other directly, only through it. This keeps agents independently testable
with stubs (see `tests/test_agents.py`).

## Conformal → OpenLEC mapping

| Cadence Conformal | OpenLEC |
|---|---|
| `READ DESIGN` | `ParsingAgent` + Yosys `read_verilog` |
| `READ POWER INTENT` | `UPFParser.parse()` |
| `COMPARE` / `ANALYZE SETUP` | `LECEngine.run_equivalence_check()` (`equiv_make/simple/induct/status`) |
| `ANALYZE ABORT` | `LECVerdict.ABORT` + `abort_points` |
| `CHECK LOWPOWER CELLS` / `COMPARE POWER CONSISTENCY` | `UPFChecker` rule families |
| `REPORT LOWPOWER VERIFICATION` | `ReportingAgent` / `VerificationReport` |
| dofile scripting | `AgenticOrchestrator` pipeline |

## Verdict semantics

| Symbol | Meaning |
|---|---|
| `LECVerdict.EQUIVALENT` | SAT proof completed, all compare points proven |
| `LECVerdict.NONEQUIVALENT` | counter-example exists → hard halt |
| `LECVerdict.ABORT` | SAT inconclusive/timeout → fail-soft, no halt |
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
  boundary (`tests/test_agents.py`), parser/checker tests are pure Python.
* `tests/test_lec_engine.py` is an integration test and skips itself when
  `yosys` is not on `PATH`.
* CI installs Yosys so the integration test runs on every push/PR.