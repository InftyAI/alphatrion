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

.PHONY: format
format:
	ruff format .
	ruff check --fix .

.PHONY: test
test: format
	$(POETRY) run pytest tests/unit

.PHONY: test-integration
test-integration: format
	$(POETRY) run pytest tests/integration