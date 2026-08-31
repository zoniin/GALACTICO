.PHONY: install test lint typecheck licence check reliability

install:
	uv venv && uv pip install -e ".[dev,viz]"

test:
	python -m pytest -q

lint:
	python -m ruff check galactico tests

typecheck:
	python -m mypy galactico

licence:
	python scripts/check_licensing.py

check: licence lint test

reliability:
	python -m galactico.reliability.report
