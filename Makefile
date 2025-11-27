POETRY := poetry
RUFF := .venv/bin/ruff
PYTEST := .venv/bin/pytest

.PHONY: build
build: lint
	$(POETRY) build

.PHONY: publish
publish: build
	$(POETRY) publish --username=__token__ --password=$(INFTYAI_PYPI_TOKEN)

.PHONY: up
up:
	docker-compose -f ./docker-compose.yaml up -d
	alembic upgrade head

.PHONY: down
down:
	docker-compose -f ./docker-compose.yaml down

.PHONY: lint
lint:
	$(RUFF) check .

.PHONY: format
format:
	$(RUFF) format .
	$(RUFF) check --fix .

.PHONY: test
test: lint
	$(PYTEST) tests/unit --timeout=15

.PHONY: test-integration
test-integration: lint
	@bash -c '\
	set -e; \
	docker-compose -f ./docker-compose.yaml up -d; \
	trap "docker-compose -f ./docker-compose.yaml down" EXIT; \
	until docker exec postgres pg_isready -U alphatr1on; do sleep 1; done; \
	until curl -sf http://localhost:11434/api/tags | grep "smollm:135m" > /dev/null; do sleep 1; done; \
	$(PYTEST) tests/integration --timeout=30; \
	'
.PHONY: test-all
test-all: test test-integration

.PHONY: seed
seed:
	python hack/seed.py seed

.PHONY: seed-cleanup
seed-cleanup:
	python hack/seed.py cleanup
