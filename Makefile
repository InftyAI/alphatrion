POETRY := poetry

.PHONY: build
build:
	$(POETRY) build

.PHONY: publish
publish: build
	$(POETRY) publish

.PHONY: launch
launch:
	docker-compose -f ./docker-compose.yaml up -d

.PHONY: lint
lint:
	$(POETRY) run ruff check .

.PHONY: format
format:
	$(POETRY) run ruff format .
	$(POETRY) run ruff check --fix .

.PHONY: test
test: lint
	$(POETRY) run pytest tests/unit --timeout=15

.PHONY: test-integration
test-integration: lint
	@bash -c '\
	set -e; \
	docker-compose -f ./docker-compose.yaml up -d; \
	trap "docker-compose -f ./docker-compose.yaml down" EXIT; \
	until docker exec postgres pg_isready -U alphatr1on; do sleep 1; done; \
	until curl -sf http://localhost:11434/api/tags | grep "smollm:135m" > /dev/null; do sleep 1; done; \
	$(POETRY) run pytest tests/integration --timeout=30; \
	'
.PHONY: test-all
test-all: test test-integration
