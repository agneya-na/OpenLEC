<p align="center">
  <h1 align="center">OpenLEC</h1>
  <p align="center">
    <b>Open-source Agentic AI Infrastructure for Low-Power LEC and UPF Verification</b><br>
    <i>An open-source, Python-native alternative for Conformal LEC — featuring UPF (IEEE 1801) verification, SAT-based equivalence checking, and multi-agent optimization.</i>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/license-Apache--2.0-green.svg" alt="License">
  <img src="https://img.shields.io/github/stars/oscc-project/OpenLEC?style=social" alt="Stars">
  <img src="https://img.shields.io/github/forks/oscc-project/OpenLEC?style=social" alt="Forks">
</p>

<p align="center">
  <a href="README_CN.md">Chinese</a> | <b>English</b>
</p>

<p align="center"><i>"Open-source EDA is not just about replacing commercial tools, but building transparent, AI-native verification flows."</i></p>

---

## 🌟 OpenLEC Overview

**OpenLEC** is an open-source EDA infrastructure and verification toolchain designed specifically for **Low-Power Logic Equivalence Checking (LEC)** and **UPF (IEEE 1801) Power-Aware Verification**. 

Unlike traditional EDA tools that rely on heavy, monolithic C++ cores, OpenLEC adopts a **Python-first, AI-native architecture**. This allows for rapid integration of modern agentic AI workflows, transparent debugging, and seamless orchestration with open-source synthesis engines like Yosys.

### Core Capabilities
* **Level 1:** Open-source LEC & UPF verification supporting low-power chip design and tapeout.
* **Level 2:** Open-source Agentic Infrastructure supporting EDA algorithm research and AI-driven verification.

### 🎉 News
* **[2026-08]** Released OpenLEC v0.1.0: Pure Python agentic orchestrator with Yosys SAT-based LEC integration.
* **[2026-07]** Initial UPF (IEEE 1801) structural parsing and power-domain isolation checks merged.

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

*Why Python-first?* We intentionally avoided legacy C++ cores. Modern EDA research requires rapid prototyping, LLM integration, and transparent data flows. Python provides the ideal substrate for **Agentic EDA**.

---

## 📂 Project Structure

```text
OpenLEC/
 ├── README.md
 ├── LICENSE
 ├── pyproject.toml
 ├── requirements.txt
 ├── Makefile
 ├── Dockerfile
 │
 ├── openlec/                       # Python Core & Infrastructure
 │   ├── __init__.py
 │   ├── cli.py                     # User entrypoint
 │   ├── config.py
 │   │
 │   ├── agents/                    # Agentic AI Layer
 │   │   ├── orchestrator.py
 │   │   ├── parsing_agent.py
 │   │   ├── equivalence_agent.py
 │   │   ├── power_intent_agent.py
 │   │   ├── timing_agent.py
 │   │   ├── power_agent.py
 │   │   ├── optimization_agent.py
 │   │   └── reporting_agent.py
 │   │
 │   ├── engine/                    # Verification Engine
 │   │   ├── yosys_runner.py        # Interface to Yosys
 │   │   ├── lec_engine.py          # SAT-based equivalence
 │   │   ├── upf_parser.py          # IEEE 1801 UPF parsing
 │   │   ├── upf_checker.py         # Power-aware structural checks
 │   │   ├── timing_estimator.py
 │   │   ├── power_estimator.py
 │   │   └── optimizer.py
 │   │
 │   └── models/                    # Shared Typed Data Models
 │       ├── metrics.py
 │       ├── lec_result.py
 │       ├── upf_models.py
 │       └── optimization_step.py
 │
 ├── examples/                      # Sample Designs & UPF
 │   ├── designs/
 │   ├── upf/
 │   └── run_demo.py
 │
 ├── tests/                         # Pytest Suite
 ├── config/                        # YAML Configurations
 └── docs/                          # Documentation
