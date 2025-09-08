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

.PHONY: test
test:
	$(POETRY) run pytest