# Development

## Prerequisites

- Python 3.12 or higher
- Poetry for dependency management

## How to Set Up

1. Fork the repository.
2. Run `source start.sh` to activate the virtual environment.
3. Install dependencies with `poetry install`.
4. Make your changes.


## How to Test

To run tests, use:

```bash
make test
```

To run integration tests, use:

```bash
make test-integration
```

## How to migrate the Database

To create a new migration, use:

```bash
alembic revision --autogenerate -m "your message here"
```

To apply migrations, use:

```bash
alembic upgrade head
```

## How to Publish to PyPI

> Note: You need to have the PyPI token set in your environment variables to publish the package.

To build the project, run:

```bash
make build
```

To publish the project, run:

```bash
make publish
```
