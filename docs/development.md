# Development

## Prerequisites

- Python 3.12 or higher
- Poetry for dependency management

## How to Develop

We welcome contributions! Please follow these steps:

1. Fork the repository.
2. Run `eval $(poetry env activate)` to activate the virtual environment.
3. Install dependencies with `poetry install`.
4. Make your changes.

## How to Build and Publish

> NOTE: You need to have the PyPI token set in your environment variables to publish the package.

To build the project, run:

```cmd
make build
```

To publish the project, run:

```cmd
make publish
```
