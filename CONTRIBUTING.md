# Contributing to OpenLEC

Thank you for your interest in contributing to OpenLEC. This project is maintained and governed by the sole maintainer: `agneya-na`. Contributions are welcome but will be reviewed and merged at the maintainer's discretion.

## Reporting bugs / requesting features

1. Prefer opening an issue first with a clear description, steps to reproduce (for bugs), and any relevant files or testcases.
2. For feature requests, explain the use case and expected behavior and link any relevant designs or example inputs.

## Quick patch workflow (small fixes)

1. Fork the repository.
2. Create a branch: `git checkout -b fix/your-short-description`.
3. Run linters and tests locally (see below).
4. Commit changes with a clear message.
5. Push and open a Pull Request against `main`, referencing the issue if applicable.

## Larger changes / new features

- Open an issue first and discuss the proposed approach with the maintainer before implementing large changes.
- For architectural or cross-cutting changes, include a design summary, alternatives considered, and a testing plan.

## Code style and checks

- Formatting & linting: ruff
- Type checking: mypy
- Tests: pytest

Suggested commands:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ruff check .
mypy openlec
pytest -q
```

## Tests & CI

- Include unit tests for new behavior and add example designs in `examples/` where applicable.
- The maintainer may add CI workflows; until then run tests locally before submitting.

## Author / Maintainer

Maintainer: `agneya-na` (sole maintainer and final arbiter for merges).

## License

By contributing you agree your contributions are licensed under the project MIT License.
