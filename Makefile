.PHONY: install lint test fmt run migrate verify openapi

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
PYTEST ?= .venv/bin/pytest
RUFF ?= .venv/bin/ruff
UVICORN ?= .venv/bin/uvicorn
ALEMBIC ?= .venv/bin/alembic

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
