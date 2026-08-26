.PHONY: install build test lint clean demo

install:
	pip install -r requirements.txt
	pip install -e .

build:
	python -m build

test:
	pytest tests/ -v

lint:
	flake8 openlec/ tests/
	mypy openlec/

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache
	find . -name "__pycache__" -exec rm -rf {} +

demo:
	python examples/run_demo.py
