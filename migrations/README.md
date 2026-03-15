# AlphaTrion Database Migrations

This directory contains database schema migrations for AlphaTrion.

## Structure

```
migrations/
├── README.md                      # This file
├── env.py                         # Alembic environment configuration
├── script.py.mako                 # Alembic migration template
├── versions/                      # PostgreSQL migrations (Alembic)
│   ├── 344adc5da83a_init_schema.py
│   ├── 0f417c7cf4d3_add_duration_for_run.py
│   └── ...
└── clickhouse/                    # ClickHouse migrations
    ├── __init__.py
    ├── runner.py                  # Migration runner
    ├── cli.py                     # CLI tool
    ├── README.md                  # ClickHouse migration docs
    └── versions/                  # ClickHouse migration files
        ├── 001_init_otel_spans_table.py
        └── 002_add_session_id_column.py
```

## PostgreSQL Migrations (Alembic)

AlphaTrion uses [Alembic](https://alembic.sqlalchemy.org/) for PostgreSQL schema migrations.

### Create a new migration

```bash
alembic revision -m "description of changes"
```

### Apply pending migrations

```bash
alembic upgrade head
```

### View migration history

```bash
alembic history
```

### Rollback one migration

```bash
alembic downgrade -1
```

## ClickHouse Migrations

ClickHouse uses a custom migration system (see `clickhouse/README.md` for details).

### View migration status

```bash
python -m migrations.clickhouse.cli status
```

### Apply pending migrations

```bash
python -m migrations.clickhouse.cli migrate
```

### List all migrations

```bash
python -m migrations.clickhouse.cli list
```

## Automatic Migrations

### PostgreSQL
- Run automatically in production via Kubernetes migration job
- In development, run manually: `alembic upgrade head`

### ClickHouse
- Run manually via CLI: `python -m migrations.clickhouse.cli migrate`
- In production, run via Kubernetes init container or job

## Best Practices

### PostgreSQL (Alembic)
- Always review auto-generated migrations
- Test both upgrade and downgrade
- Use batch operations for large tables
- Add indexes in separate migrations

### ClickHouse
- Always use `IF NOT EXISTS` / `IF EXISTS` clauses
- Add indexes separately from columns
- Use appropriate compression codecs
- Test migrations on production-like data volumes

## Migration Naming

### PostgreSQL
Alembic auto-generates names: `{revision}_{slug}.py`
- Example: `344adc5da83a_init_schema.py`

### ClickHouse
Use sequential versions: `{version}_{description}.py`
- Version: 3-digit number (001, 002, 003...)
- Example: `001_init_otel_spans_table.py`

## Troubleshooting

### PostgreSQL migration fails
1. Check error message
2. Fix migration file
3. Reset to known good state: `alembic downgrade {revision}`
4. Apply fixed migration: `alembic upgrade head`

### ClickHouse migration fails
1. Check error message in logs
2. Manually revert partial changes (ClickHouse DDL is not transactional)
3. Delete migration record: `DELETE FROM schema_migrations WHERE version = '{version}'`
4. Fix migration and re-run

### Check applied migrations

**PostgreSQL:**
```sql
SELECT * FROM alembic_version;
```

**ClickHouse:**
```sql
SELECT * FROM alphatrion_traces.schema_migrations ORDER BY version;
```
