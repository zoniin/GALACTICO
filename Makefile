.PHONY: install test lint typecheck licence check reliability

install:
	uv venv && uv pip install -e ".[dev,viz]"
	git config core.hooksPath .githooks

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

profiles:
	PYTHONPATH=. python scripts/build_profiles.py

serve: profiles
	PYTHONPATH=. python -m uvicorn galactico.api.player_lab:app --port 8090 --reload
