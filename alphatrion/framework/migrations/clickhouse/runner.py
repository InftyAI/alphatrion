"""ClickHouse migration runner.

This module provides a migration system for ClickHouse that tracks applied
migrations and runs pending ones in order.
"""

import importlib.util
import logging
from abc import ABC, abstractmethod
from pathlib import Path

import clickhouse_connect

logger = logging.getLogger(__name__)


class Migration(ABC):
    """Base class for ClickHouse migrations.

    Each migration must:
    1. Inherit from this class
    2. Set version and name attributes
    3. Implement upgrade() and downgrade() methods
    4. Export an instance as 'migration'
    """

    version: str
    name: str

    @abstractmethod
    def upgrade(self, client: clickhouse_connect.driver.Client, database: str) -> None:
        """Apply the migration.

        Args:
            client: ClickHouse client
            database: Database name
        """
        pass

    @abstractmethod
    def downgrade(self, client: clickhouse_connect.driver.Client, database: str) -> None:
        """Revert the migration.

        Args:
            client: ClickHouse client
            database: Database name
        """
        pass


class ClickHouseMigrationRunner:
    """Runs ClickHouse migrations in version order."""

    def __init__(self, client: clickhouse_connect.driver.Client, database: str):
        """Initialize the migration runner.

        Args:
            client: ClickHouse client
            database: Database name
        """
        self.client = client
        self.database = database

    def init_migrations_table(self) -> None:
        """Create the schema_migrations table if it doesn't exist."""
        sql = f"""
        CREATE TABLE IF NOT EXISTS {self.database}.schema_migrations (
            version String,
            applied_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY version
        """
        try:
            self.client.command(sql)
            logger.info(f"Migrations table {self.database}.schema_migrations ready")
        except Exception as e:
            logger.error(f"Failed to create migrations table: {e}")
            raise

    def get_applied_migrations(self) -> set[str]:
        """Get list of already applied migration versions.

        Returns:
            Set of applied migration versions
        """
        try:
            result = self.client.query(
                f"SELECT version FROM {self.database}.schema_migrations ORDER BY version"
            )
            return {row[0] for row in result.result_rows}
        except Exception as e:
            logger.error(f"Failed to query applied migrations: {e}")
            raise

    def mark_migration_applied(self, version: str) -> None:
        """Record a migration as applied.

        Args:
            version: Migration version
        """
        try:
            self.client.command(
                f"INSERT INTO {self.database}.schema_migrations (version) VALUES ('{version}')"
            )
        except Exception as e:
            logger.error(f"Failed to mark migration {version} as applied: {e}")
            raise

    def load_migration(self, migration_file: Path) -> Migration:
        """Load a migration from a Python file.

        Args:
            migration_file: Path to migration file

        Returns:
            Migration instance
        """
        spec = importlib.util.spec_from_file_location(
            f"migration_{migration_file.stem}", migration_file
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load migration from {migration_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "migration"):
            raise AttributeError(
                f"Migration file {migration_file} must export 'migration' instance"
            )

        return module.migration

    def run_pending_migrations(self, migrations_dir: Path) -> None:
        """Run all pending migrations in version order.

        Args:
            migrations_dir: Directory containing migration files
        """
        # Ensure migrations table exists
        self.init_migrations_table()

        # Get applied migrations
        applied = self.get_applied_migrations()
        logger.info(f"Already applied migrations: {sorted(applied)}")

        # Find all migration files
        migration_files = sorted(
            [f for f in migrations_dir.glob("*.py") if not f.name.startswith("__")]
        )

        if not migration_files:
            logger.info("No migration files found")
            return

        # Load and run pending migrations
        pending_count = 0
        for migration_file in migration_files:
            # Extract version from filename (e.g., "001_init_table.py" -> "001")
            version = migration_file.stem.split("_")[0]

            if version in applied:
                logger.debug(f"Migration {version} already applied, skipping")
                continue

            # Load and run migration
            logger.info(f"Running migration {version}: {migration_file.name}")
            migration = self.load_migration(migration_file)

            try:
                migration.upgrade(self.client, self.database)
                self.mark_migration_applied(version)
                logger.info(f"✓ Migration {version} applied successfully")
                pending_count += 1
            except Exception as e:
                logger.error(f"✗ Migration {version} failed: {e}")
                raise

        if pending_count == 0:
            logger.info("No pending ClickHouse migrations")
        else:
            logger.info(f"Applied {pending_count} ClickHouse migration(s)")
