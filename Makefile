## @build

DOCKER_BUILDX_CMD ?= docker buildx
IMAGE_BUILD_CMD ?= $(DOCKER_BUILDX_CMD) build
IMAGE_BUILD_EXTRA_OPTS ?=
IMAGE_REGISTRY ?= inftyai
IMAGE_NAME ?= alphatrion
IMAGE_REPO := $(IMAGE_REGISTRY)/$(IMAGE_NAME)
GIT_TAG ?= $(shell git describe --tags --dirty --always)
IMG ?= $(IMAGE_REPO):$(GIT_TAG)
PLATFORMS ?= linux/arm64,linux/amd64

POETRY := poetry
RUFF := .venv/bin/ruff
PYTEST := .venv/bin/pytest

.PHONY: build
build: lint build-dashboard
	$(POETRY) build

.PHONY: publish
publish: build
	$(POETRY) publish --username=__token__ --password=$(INFTYAI_PYPI_TOKEN)

.PHONY: up
up:
	docker compose -f ./docker-compose.yaml up -d
	alembic upgrade head

.PHONY: down
down:
	docker compose -f ./docker-compose.yaml down

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

.PHONY: build-dashboard
build-dashboard:
	cd dashboard && npm install && npm run build

.PHONY: image-build
image-build:
	$(IMAGE_BUILD_CMD) -t $(IMG) \
		--platform=$(PLATFORMS) \
		$(IMAGE_BUILD_EXTRA_OPTS) ./
image-load: IMAGE_BUILD_EXTRA_OPTS=--load
image-load: image-build
image-push: IMAGE_BUILD_EXTRA_OPTS=--push
image-push: image-build

.PHONY: image-build-dashboard
image-build-dashboard:
	$(IMAGE_BUILD_CMD) -t $(IMG) \
		--platform=$(PLATFORMS) \
		$(IMAGE_BUILD_EXTRA_OPTS) ./dashboard
image-load-dashboard: IMAGE_BUILD_EXTRA_OPTS=--load
image-load-dashboard: image-build-dashboard
image-push-dashboard: IMAGE_BUILD_EXTRA_OPTS=--push
image-push-dashboard: image-build-dashboard
