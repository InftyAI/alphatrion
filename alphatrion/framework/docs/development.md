# Development

## Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) for dependency management

## How to Set Up

1. Fork the repository.
2. From the repo root, run `source start.sh` to create and activate the virtual environment and install all dependencies.
3. Make your changes.

Run all commands below from the repo root.

## How to Migrate the Database

To create a new migration, use:

```bash
alembic -c alphatrion/framework/alembic.ini revision --autogenerate -m "your message here"
```

To apply migrations, use:

```bash
make migrate
```

## How to Seed the Database

To seed the database with sample data, run:

```bash
make seed
```

To cleanup, run:

```bash
make seed-cleanup
```

## How to Test

To run tests, use:

```bash
make test
```

To run integration tests, use:

```bash
make test-integration
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
