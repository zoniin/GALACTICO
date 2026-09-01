.PHONY: install test lint typecheck licence check reliability profiles serve e2e release-check

install:
	uv venv && uv pip install -e ".[dev,viz]"
	git config core.hooksPath .githooks
	npm install && npx playwright install chromium

test:
	PYTHONPATH=. python -m pytest -q

lint:
	python -m ruff check galactico tests

licence:
	python scripts/check_licensing.py

profiles:
	PYTHONPATH=. python scripts/build_profiles.py

serve: profiles
	PYTHONPATH=. python -m uvicorn galactico.api.player_lab:app --port 8090 --reload

e2e:
	npx playwright test e2e/smoke.spec.js

check: licence lint test

release-check: licence lint test e2e
	@echo ""
	@echo "AUTOMATED CHECKS PASSED. Stage 2 is NOT releasable until:"
	@echo "  [ ] visual review of docs/screenshots/"
	@echo "  [ ] blind interpretation review against the RUNNING app"
	@echo "  [ ] football review accepted"
	@echo "  [ ] statistician review accepted"
	@echo ""
	@echo "Human review is outstanding. This is not READY."
