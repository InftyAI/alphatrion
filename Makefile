
.PHONY build:
build:
	poetry build

publish: build
	poetry publish