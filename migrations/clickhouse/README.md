# ClickHouse Migrations

ClickHouse schema migrations for AlphaTrion trace storage.

## Quick Start

### View migration status
```bash
python -m migrations.clickhouse.cli status
```

### Run pending migrations
```bash
python -m migrations.clickhouse.cli migrate
```

### List all migrations
```bash
python -m migrations.clickhouse.cli list
```

## Creating a Migration

Create a new file in `migrations/clickhouse/versions/` with the format: `{version}_{description}.py`

**Example:** `003_add_region_column.py`

```python
"""Add region column to spans.

Revision: 003
Created: 2026-03-15
"""
import logging
import clickhouse_connect
from migrations.clickhouse.runner import Migration

logger = logging.getLogger(__name__)


class AddRegionColumn(Migration):
    version = "003"
    name = "add_region_column"

    def upgrade(self, client, database):
        logger.info("Adding Region column")

        client.command(f'''
            ALTER TABLE {database}.otel_spans
            ADD COLUMN IF NOT EXISTS Region LowCardinality(String) CODEC(ZSTD(1))
        ''')

        logger.info("Region column added")

    def downgrade(self, client, database):
        logger.info("Removing Region column")

        client.command(f'ALTER TABLE {database}.otel_spans DROP COLUMN IF EXISTS Region')

        logger.info("Region column removed")


# Export migration instance
migration = AddRegionColumn()
```

## How It Works

1. **Version Tracking** - Applied migrations are recorded in `{database}.schema_migrations` table
2. **Sequential Ordering** - Migrations are applied in version order (001, 002, 003...)
3. **Idempotent** - Uses `IF NOT EXISTS` / `IF EXISTS` clauses to safely re-run

## Best Practices

### Always use conditional statements
```sql
-- Good ✓
ALTER TABLE otel_spans ADD COLUMN IF NOT EXISTS NewColumn String

-- Bad ✗ (fails if already exists)
ALTER TABLE otel_spans ADD COLUMN NewColumn String
```

### Add indexes separately
```python
# Add column
client.command(f'ALTER TABLE {database}.otel_spans ADD COLUMN IF NOT EXISTS MyColumn String')

# Then add index
client.command(f'ALTER TABLE {database}.otel_spans ADD INDEX IF NOT EXISTS idx_my_column MyColumn TYPE bloom_filter(0.001)')
```

### Use appropriate data types
- `String` - General text
- `LowCardinality(String)` - For fields with < 10k unique values
- `DateTime64(9)` - Nanosecond timestamps
- `UInt64` - Large positive integers (durations)
- `Map(String, String)` - Key-value attributes

### Add compression codecs
- `CODEC(ZSTD(1))` - General purpose
- `CODEC(Delta, ZSTD(1))` - For timestamps/sequential IDs
- `CODEC(LZ4)` - Faster compression

## Troubleshooting

### Migration fails
1. Check error message
2. Fix migration code
3. Manually revert partial changes
4. Delete migration record: `DELETE FROM schema_migrations WHERE version = '003'`
5. Re-run

### Check applied migrations
```sql
SELECT * FROM alphatrion_traces.schema_migrations ORDER BY version;
```

### Migration not running
- Verify file is in `migrations/clickhouse/versions/`
- Check migration exports `migration` variable
- Ensure version is sequential and not already applied
- Run `python -m migrations.clickhouse.cli status` to check

## Directory Structure

```
migrations/
├── versions/              # PostgreSQL migrations (Alembic)
│   ├── 344adc5da83a_init_schema.py
│   └── ...
└── clickhouse/           # ClickHouse migrations
    ├── __init__.py
    ├── runner.py         # Migration runner
    ├── cli.py            # CLI tool
    ├── README.md         # This file
    └── versions/         # Migration files
        ├── __init__.py
        ├── 001_init_otel_spans_table.py
        └── 002_add_session_id_column.py
```

## Integration with AlphaTrion

The migration system is decoupled from the application. To run migrations:

**Development:**
```bash
python -m migrations.clickhouse.cli migrate
```

**Production (Kubernetes):**
Add a migration init container or job:
```yaml
initContainers:
- name: clickhouse-migrations
  image: alphatrion:latest
  command: ["python", "-m", "migrations.clickhouse.cli", "migrate"]
  env:
    - name: ALPHATRION_CLICKHOUSE_URL
      value: "clickhouse:8123"
```

## Migration Naming Convention

Use sequential versions: `{version}_{description}.py`
- Version: 3-digit number (001, 002, 003...)
- Description: snake_case description
- Example: `003_add_cost_tracking.py`
