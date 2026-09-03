<p align="center">
  <img src="https://raw.githubusercontent.com/agneya-na/OpenLEC/main/docs/openlec_logo.png" alt="OpenLEC Logo" width="150" />
</p>

<h1 align="center">OpenLEC</h1>

<p align="center">
  <b>Open-source Agentic AI Infrastructure for Low-Power LEC and UPF Verification</b><br>
  <i>An open-source, Python-native alternative verification stack with UPF (IEEE 1801) checks, SAT-based equivalence flow integration, and multi-agent optimization orchestration.</i>
</p>

<p align="center">
  <a href="https://github.com/agneya-na/OpenLEC/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://github.com/python/mypy"><img src="https://img.shields.io/badge/mypy-checked-green" alt="MyPy"></a>
  <a href="https://github.com/agneya-na/OpenLEC/issues"><img src="https://img.shields.io/github/issues/agneya-na/OpenLEC" alt="Issues"></a>
  <a href="https://github.com/agneya-na/OpenLEC/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
  <br>
  <a href="https://github.com/agneya-na/OpenLEC/stargazers"><img src="https://img.shields.io/github/stars/agneya-na/OpenLEC?style=social" alt="Stars"></a>
  <a href="https://github.com/agneya-na/OpenLEC/network/members"><img src="https://img.shields.io/github/forks/agneya-na/OpenLEC?style=social" alt="Forks"></a>
</p>

<p align="center"><i>"Open-source EDA is not just about replacing commercial tools, but building transparent, AI-native verification flows."</i></p>

---

## 🌟 Overview

**OpenLEC** is an open-source EDA infrastructure and verification toolchain focused on **Low-Power Logic Equivalence Checking (LEC)** and **UPF (IEEE 1801) power-aware verification**.

Unlike traditional monolithic flows, OpenLEC adopts a **Python-first, AI-native architecture** for rapid iteration, transparent data flow, and agentic automation.

### ✨ Key Features
- **SAT-Based LEC Flow Integration:** Yosys `equiv_*` style flow integration for equivalence checking.
- **IEEE 1801 UPF Support:** Structural parsing and power-domain/isolation intent checks.
- **Agentic AI Orchestration:** Multi-agent loop with acceptance gates (LEC/UPF/timing/power).
- **Python-Native SDK:** Fast prototyping for EDA algorithms and AI-driven verification.
- **Tapeout-Oriented Design:** Built to evolve toward real low-power signoff-style flows.

### 🎉 News
- **[2026-08]** 🚀 Released **OpenLEC v0.1.0** with Python agentic orchestrator and SAT-based LEC flow integration.
- **[2026-07]** 🛡️ Added initial UPF (IEEE 1801) structural parser and isolation checks.

---

## 🧭 Navigation
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [User Guide](#-user-guide)
- [Running OpenLEC](#-running-openlec)
- [Roadmap](#-roadmap)
- [Contribution Guide](#-contribution-guide)

---

## 🏗 Architecture

OpenLEC is designed as an SDK-like infrastructure for AI-integrated EDA verification development:

- **Infrastructure Layer:** Data models, configuration manager, and external tool interfaces.
- **Agent Layer:** Parsing, equivalence, power-intent, timing, power, optimization, and reporting agents.
- **Engine Layer:** LEC flow, UPF parser/checker, and estimation/optimization components.

> **Why Python-first?** It enables rapid prototyping, LLM integration, and transparent experimentation compared to legacy-heavy toolchains.

---

## 📂 Project Structure

```text
OpenLEC/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── Makefile
├── config/
├── docs/
├── openlec/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── models/
│   ├── engine/
│   └── agents/
├── examples/
│   ├── designs/
│   ├── upf/
│   └── run_demo.py
└── tests/
    ├── test_cli.py
    ├── test_agents.py
    ├── test_lec_engine.py
    └── test_upf_parser.py
```

---

## 📖 User Guide

Before running OpenLEC, set up the runtime environment using one of the methods below.

### Method 1: Docker (Recommended)

```bash
docker run -it --rm openlec/base:latest bash

# Inside the container
git clone https://github.com/agneya-na/OpenLEC.git && cd OpenLEC
pip install -e .
openlec --help
```

### Method 2: Local Installation

Requires Python 3.10+ and Yosys available on your host.

```bash
# Ubuntu/Debian example
sudo apt-get update && sudo apt-get install -y yosys

# Clone repo
git clone https://github.com/agneya-na/OpenLEC.git && cd OpenLEC

# Virtual environment
python3 -m venv .venv && source .venv/bin/activate

# Install
pip install -r requirements.txt
pip install -e .

# Verify
openlec --help
```

---

## 🚀 Running OpenLEC

### Method 1: Run Demo

```bash
python examples/run_demo.py
```

Expected output: PASS/FAIL-style report with delay/power/area estimates, UPF status, and accepted optimization steps.

### Method 2: Run CLI on Custom Designs

```bash
openlec <rtl_file> \
  --upf <file.upf> \
  --top <top_module> \
  --iterations 5 \
  --delay-budget 10.0 \
  --power-budget 1000 \
  -v
```

---

## 🗺 Roadmap

- Expand UPF command coverage beyond structural subset.
- Integrate richer timing/power estimation flows.
- Add multi-file netlist partitioning and distributed checks.
- Improve reporting outputs (HTML/PDF).
- Add CI workflows for Python + Yosys + sample designs.
- Integrate local open-source LLM workflows for failure diagnosis.

---

## 🤝 Contribution Guide

OpenLEC is maintained by the project owner and sole maintainer: `agneya-na`.

If you would like to propose a change, please open an issue first describing the intended change and link any relevant designs or testcases. The maintainer must approve any non-trivial changes before a pull request is created.

Preferred workflow for small fixes:
1. Fork the repository.
2. Create a branch named `fix/your-short-description`.
3. Run tests and linters (see coding style below).
4. Open a Pull Request against `main` with a clear description and any test results.

For larger changes or new features, open an issue first and wait for the maintainer's guidance.

Coding style and quality checks:
- Formatting and linting: `ruff` (project style).
- Type checks: `mypy`.
- Tests: pytest (see `tests/`).

---

## 📖 Future contributions

This repository is primarily maintained by `agneya-na`. Contributions are welcome as described above but will be reviewed and merged at the maintainer's discretion. If you require that your contribution be merged under a different authoring policy, mention it in the issue and discuss it with the maintainer prior to submission.

---

## 📚 Citation

If you use OpenLEC in research or tapeout flows, please cite:

```bibtex
@software{openlec2026,
  title={OpenLEC: An Open-source Agentic AI Infrastructure for Low-Power LEC and UPF Verification},
  author={OpenLEC Contributors},
  year={2026},
  publisher={GitHub},
  url={https://github.com/agneya-na/OpenLEC}
}
```

---

## 💬 Discussion

- Open an issue in this repository.
- Community channels can be linked here when published.

---

## 📜 License

MIT License

---

## 🙏 Acknowledgement

OpenLEC builds on the open-source EDA and Python ecosystems. Reuse is encouraged under the MIT license.
