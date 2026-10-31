SHELL := /bin/sh
CORE := services/core
WEB := apps/web

.PHONY: bootstrap dev-mock dev-api dev-web dev-worker test test-core test-integration test-web lint build schema db-upgrade db-bootstrap trace-check

bootstrap:
	uv sync --project $(CORE) --locked
	pnpm install --frozen-lockfile

dev-mock:
	./scripts/dev-mock.sh

dev-api:
	cd $(CORE) && uv run uvicorn medical_one_person.main:app --reload --host 127.0.0.1 --port 8000

dev-web:
	pnpm --dir $(WEB) dev

dev-worker:
	cd $(CORE) && uv run python -m medical_one_person.worker --poll-seconds 1

test: test-core test-web trace-check

test-core:
	cd $(CORE) && uv run --frozen pytest

test-integration:
	test -n "$$MEDICAL_ONE_TEST_DATABASE_URL"
	cd $(CORE) && uv run --frozen pytest tests/integration

test-web:
	pnpm --dir $(WEB) check

lint:
	cd $(CORE) && uv run --frozen ruff check . && uv run --frozen mypy src
	pnpm --dir $(WEB) lint

build:
	pnpm --dir $(WEB) build
	cd $(CORE) && uv run --frozen python -m compileall -q src

schema:
	cd $(CORE) && uv run --frozen python -m medical_one_person.export_openapi
	cd $(CORE) && uv run --frozen python -m medical_one_person.agents.export_schemas
	cd $(CORE) && uv run --frozen python -m medical_one_person.export_domain_schemas

trace-check:
	python3 tools/check_traceability.py check

db-upgrade:
	cd $(CORE) && uv run --frozen alembic upgrade head

db-bootstrap:
	cd $(CORE) && uv run --frozen python -m medical_one_person.bootstrap
