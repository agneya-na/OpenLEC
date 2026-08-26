.PHONY: all build test demo clean

all: build test

build:
	mkdir -p build && cd build && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j$$(nproc)

test:
	python -m pytest tests/ -v --tb=short

demo:
	python examples/run_demo.py

lint:
	python -m ruff check . --fix

clean:
	rm -rf build __pycache__ **/__pycache__ .pytest_cache
