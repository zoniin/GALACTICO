.PHONY: install test lint licence check profiles prepare serve e2e release-check

install:
	uv venv && uv pip install -e ".[dev,api,viz]"
	git config core.hooksPath .githooks
	npm install && npx playwright install chromium

test:
	uv run pytest -q

lint:
	uv run ruff check galactico tests

licence:
	uv run python scripts/check_licensing.py

profiles:
	uv run python scripts/build_profiles.py

prepare:
	uv run python scripts/fetch_pappalardo.py --only Spain
	uv run python scripts/prepare_lab.py

serve: profiles
	uv run uvicorn galactico.api.player_lab:app --host 127.0.0.1 --port 8090 --reload

e2e:
	npx playwright test e2e/smoke.spec.js e2e/labs.spec.js

check: licence lint test

release-check: licence lint test e2e
	@echo ""
	@echo "AUTOMATED CHECKS PASSED. This does not certify external human acceptance."
	@echo "  [ ] external football analyst acceptance"
	@echo "  [ ] external statistical acceptance"
	@echo ""
	@echo "Agent review and screenshot inspection are documented in VALIDATION.md."
