<p align="center">
  <!-- Replace this URL with your actual logo if you have one, or remove the img tag -->
  <img src="https://raw.githubusercontent.com/agneya-na/OpenLEC/main/docs/assets/logo.png" alt="OpenLEC Logo" width="150" />
  <h1 align="center">OpenLEC</h1>
  <p align="center">
    <b>Open-source Agentic AI Infrastructure for Low-Power LEC and UPF Verification</b><br>
    <i>An open-source, Python-native alternative to Conformal LEC — featuring UPF (IEEE 1801) verification, SAT-based equivalence checking, and multi-agent optimization.</i>
  </p>
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

<p align="center">
  <a href="README_CN.md">🇨🇳 Chinese</a> | <b>🇬🇧 English</b>
</p>

<p align="center"><i>"Open-source EDA is not just about replacing commercial tools, but building transparent, AI-native verification flows."</i></p>

---

## 🌟 Overview

**OpenLEC** is an open-source EDA infrastructure and verification toolchain designed specifically for **Low-Power Logic Equivalence Checking (LEC)** and **UPF (IEEE 1801) Power-Aware Verification**. 

Unlike traditional EDA tools that rely on heavy, monolithic C++ cores, OpenLEC adopts a **Python-first, AI-native architecture**. This allows for rapid integration of modern agentic AI workflows, transparent debugging, and seamless orchestration with open-source synthesis engines like [Yosys](https://github.com/YosysHQ/yosys).

### ✨ Key Features
* **SAT-Based LEC:** Yosys `equiv_*` flow integration for robust equivalence checking.
* **IEEE 1801 UPF Support:** Structural parsing and power-domain isolation checks.
* **Agentic AI Orchestration:** Multi-agent optimization loop with acceptance gates (LEC/UPF/timing/power).
* **Python-Native SDK:** Rapid prototyping for EDA algorithm research and AI-driven verification.
* **Tapeout Ready:** Designed to support real low-power chip design and tapeout flows.

### 🎉 News
* **[2026-08]** 🚀 Released **OpenLEC v0.1.0**: Pure Python agentic orchestrator with Yosys SAT-based LEC integration.
* **[2026-07]** 🛡️ Initial UPF (IEEE 1801) structural parsing and power-domain isolation checks merged.

---

## 🧭 Interactive Navigation
* [Architecture](#-architecture)
* [Project Structure](#-project-structure)
* [User Guide](#-user-guide)
* [Running OpenLEC](#-running-openlec)
* [Roadmap](#-roadmap)
* [Contribution](#-contribution-guide)

---

## 🏗 Architecture

To fast develop high-quality, AI-integrated EDA verification flows, we need a flexible Software Development Kit (SDK). OpenLEC is designed as an infrastructure to support developing verification algorithms and agentic workflows.

* **Infrastructure:** Python Data Models, Configuration Manager, Yosys Operator, Tool Interfaces.
* **Agent Layer:** Multi-agent orchestration (Parsing, Equivalence, Power-Intent, Timing, Power, Optimization, Reporting).
* **Engine Layer:** SAT-based LEC flow, UPF parser/checker, metric estimators.

> **Why Python-first?** We intentionally avoided legacy C++ cores. Modern EDA research requires rapid prototyping, LLM integration, and transparent data flows. Python provides the ideal substrate for **Agentic EDA**.

---

## 📂 Project Structure

```text
OpenLEC/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── openlec/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── metrics.py
│   │   ├── lec_result.py
│   │   ├── upf_models.py
│   │   └── optimization_step.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── yosys_runner.py
│   │   ├── lec_engine.py
│   │   ├── upf_parser.py
│   │   ├── upf_checker.py
│   │   ├── timing_estimator.py
│   │   ├── power_estimator.py
│   │   └── optimizer.py
│   └── agents/
│       ├── __init__.py
│       ├── orchestrator.py
│       ├── parsing_agent.py
│       ├── equivalence_agent.py
│       ├── power_intent_agent.py
│       ├── timing_agent.py
│       ├── power_agent.py
│       ├── optimization_agent.py
│       └── reporting_agent.py
├── examples/
│   ├── designs/
│   ├── upf/
│   └── run_demo.py
└── tests/
    ├── test_cli.py
    ├── test_agents.py
    ├── test_lec_engine.py
    └── test_upf_parser.py

📖 User Guide
Before running verification flows with OpenLEC, you need to obtain the execution environment. We provide Docker images for quick setup, or you can build from source.

1. Build OpenLEC from source
Method 1: Use the OpenLEC Docker Mirror (Recommended)
Download the latest openlec/base mirror from Dockerhub, which includes the Python environment, dependencies, and Yosys.

# Pull the docker image and start a container
docker run -it --rm openlec/base:latest bash 

# Inside the container, clone and install
git clone https://github.com/agneya-na/OpenLEC.git && cd OpenLEC
pip install -e .

# Verify installation
openlec --help

Method 2: Install dependencies and compile (Local)
Requires Python 3.10+ and Yosys installed on your host system.

# Install Yosys (Ubuntu/Debian)
sudo apt-get update && sudo apt-get install -y yosys

# Clone OpenLEC repo
git clone https://github.com/agneya-na/OpenLEC.git && cd OpenLEC

# Create and activate virtual environment
python3 -m venv .venv && source .venv/bin/activate

# Install OpenLEC
pip install -r requirements.txt
pip install -e .

# Verify installation
openlec --help

🚀 Running OpenLEC
Here are two methods to run the verification flow.

Method 1: Run the Demo
We provide a sample counter design with UPF power intent to demonstrate the agentic loop.

python examples/run_demo.py
Expected output: A final PASS/FAIL style report with delay/power/area estimates, UPF conformity status, and accepted optimization steps.

Method 2: Run via CLI on Custom Designs
Refer to the examples/ directory for config structures. You can run OpenLEC directly from the command line.

openlec <rtl_file> \
  --upf <file.upf> \
  --top <top_module> \
  --iterations 5 \
  --delay-budget 10.0 \
  --power-budget 1000 \
  -v

🗺 Roadmap
Full UPF command coverage (beyond structural subset, adding state machines and supply networks)
Real timing/power estimator integration (OpenSTA + Liberty + activity/VCD parsing)
Multi-file netlist partitioning + distributed equivalence checks
Rich HTML/PDF reporting with waveform highlighting
CI workflows for Python + Yosys + sample tapeout designs
Integration with local open-source LLMs (Ollama) for automated failure diagnosis

🤝 Contribution Guide
Fork this OpenLEC repository, and after adding and committing code, please submit a Pull Request.
Please note the Coding Style of OpenLEC (enforced via ruff and mypy).

📚 Citation
If you use OpenLEC in your research or tapeout flows, please cite our project:

@software{openlec2026,
  title={OpenLEC: An Open-source Agentic AI Infrastructure for Low-Power LEC and UPF Verification},
  author={OpenLEC Contributors},
  year={2026},
  publisher={GitHub},
  url={https://github.com/oscc-project/OpenLEC}
}

💬 Discussion
Create an Issue in the repo.
Join our Discord/WeChat community for EDA research discussions.

📜 License
MIT License

🙏 Acknowledgement
In the development of OpenLEC, we heavily rely on the open-source EDA and Python communities. We encourage other open-source projects to reuse our code within the scope of the MIT license.

