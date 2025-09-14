POETRY := poetry

.PHONY: build
build:
	$(POETRY) build

.PHONY: publish
publish: build
	$(POETRY) publish

.PHONY: launch
launch:
	docker-compose up -d

.PHONY: lint
lint:
	$(POETRY) run ruff check .

.PHONY: format
format:
	$(POETRY) run ruff format .
	$(POETRY) run ruff check --fix .

.PHONY: test
test: lint
	$(POETRY) run pytest tests/unit

.PHONY: test-integration
test-integration: lint
	@bash -c '\
	set -e; \
	docker-compose up -d; \
	trap "docker-compose down" EXIT; \
	until docker exec postgres pg_isready -U at_user; do sleep 1; done; \
	$(POETRY) run pytest tests/integration; \
	'
.PHONY: test-all
test-all: test test-integration