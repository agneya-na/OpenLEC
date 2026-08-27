PYTHON ?= python3
PY     ?= $(PYTHON)

.PHONY: install install-dev test lint lint-types demo docker clean

install:
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install -e .

install-dev:
	$(PY) -m pip install -r requirements-dev.txt
	$(PY) -m pip install -e .

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check openlec tests

lint-types:
	$(PY) -m mypy openlec

demo:
	$(PY) examples/run_demo.py

docker:
	docker build -t openlec/base:latest .

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache .openlec_tmp
	find . -name "__pycache__" -type d -exec rm -rf {} +
