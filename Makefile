.PHONY: install lint test fmt run migrate verify openapi openapi-check simulate contract-check

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
PYTEST ?= .venv/bin/pytest
RUFF ?= .venv/bin/ruff
UVICORN ?= .venv/bin/uvicorn
ALEMBIC ?= .venv/bin/alembic
BASE_URL ?= http://localhost:8080

install:
	test -d .venv || python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

lint:
	$(RUFF) check src tests tools

test:
	$(PYTEST)

fmt:
	$(RUFF) format src tests tools

run:
	$(UVICORN) withdrawal_soles.main:app --reload

migrate:
	$(ALEMBIC) upgrade head

verify: lint test

openapi:
	$(PYTHON) scripts/export_openapi.py

# Regenerate the contract, fail if the committed file is stale, then validate it
# against the OpenAPI 3 schema. CI runs this on every push and pull request.
openapi-check: openapi
	@git diff --exit-code -- api/openapi.yaml || { \
		echo "api/openapi.yaml is out of date: run 'make openapi' and commit the result." >&2; \
		exit 1; }
	$(PYTHON) -m openapi_spec_validator api/openapi.yaml

simulate:
	$(PYTHON) scripts/simulate_wallet_integration.py --mode simulate

contract-check:
	$(PYTHON) scripts/wallet_contract_check.py --base-url $(BASE_URL)
