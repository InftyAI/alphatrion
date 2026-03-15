#!/usr/bin/env python
"""ClickHouse migration management CLI.

Usage:
    python -m migrations.clickhouse.cli list       # List all migrations
    python -m migrations.clickhouse.cli status     # Show migration status
    python -m migrations.clickhouse.cli migrate    # Run pending migrations
    python -m migrations.clickhouse.cli rollback   # Rollback last migration (not implemented)
"""
import os
import sys
from pathlib import Path

import clickhouse_connect
from dotenv import load_dotenv

from migrations.clickhouse.runner import ClickHouseMigrationRunner

# Load environment variables
load_dotenv()


def get_client() -> clickhouse_connect.driver.Client:
    """Get ClickHouse client from environment variables."""
    host = os.getenv("ALPHATRION_CLICKHOUSE_URL", "localhost:8123")
    username = os.getenv("ALPHATRION_CLICKHOUSE_USERNAME", "alphatrion")
    password = os.getenv("ALPHATRION_CLICKHOUSE_PASSWORD", "alphatr1on")

    # Parse host and port
    clean_host = host
    if "://" in clean_host:
        clean_host = clean_host.split("://", 1)[1]

    host_parts = clean_host.split(":")
    ch_host = host_parts[0]
    ch_port = int(host_parts[1]) if len(host_parts) > 1 else 8123

    return clickhouse_connect.get_client(
        host=ch_host, port=ch_port, username=username, password=password
    )


def list_migrations(migrations_dir: Path):
    """List all available migrations."""
    print("Available migrations:")
    print()

    for migration_file in sorted(migrations_dir.glob("*.py")):
        if migration_file.name.startswith("__"):
            continue

        # Read first few lines to get description
        with open(migration_file) as f:
            lines = f.readlines()
            description = lines[0].strip('"""').strip() if lines else "No description"

        version = migration_file.stem.split("_")[0]
        print(f"  {version}: {migration_file.name}")
        print(f"         {description}")
        print()


def show_status(runner: ClickHouseMigrationRunner, migrations_dir: Path):
    """Show migration status."""
    # Get applied migrations
    runner.init_migrations_table()
    applied = runner.get_applied_migrations()

    # Get all migrations
    all_migrations = []
    for migration_file in sorted(migrations_dir.glob("*.py")):
        if migration_file.name.startswith("__"):
            continue
        version = migration_file.stem.split("_")[0]
        all_migrations.append((version, migration_file.name))

    print("Migration Status:")
    print()
    print(f"Database: {runner.database}")
    print()

    if not all_migrations:
        print("No migrations found")
        return

    print("Version  Status      Name")
    print("-" * 60)
    for version, name in all_migrations:
        status = "✓ Applied" if version in applied else "  Pending"
        print(f"{version:<8} {status:<11} {name}")

    print()
    print(f"Total: {len(all_migrations)} migrations")
    print(f"Applied: {len(applied)}")
    print(f"Pending: {len(all_migrations) - len(applied)}")


def run_migrate(runner: ClickHouseMigrationRunner, migrations_dir: Path):
    """Run pending migrations."""
    print(f"Running migrations for database: {runner.database}")
    print()

    runner.run_pending_migrations(migrations_dir)

    print()
    print("Migration complete!")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    # Get database name
    database = os.getenv("ALPHATRION_CLICKHOUSE_DATABASE", "alphatrion_traces")

    # Get migrations directory
    migrations_dir = Path(__file__).parent / "versions"

    if not migrations_dir.exists():
        print(f"Error: Migrations directory not found: {migrations_dir}")
        sys.exit(1)

    if command == "list":
        list_migrations(migrations_dir)

    elif command == "status":
        client = get_client()
        runner = ClickHouseMigrationRunner(client, database)
        show_status(runner, migrations_dir)

    elif command == "migrate":
        client = get_client()
        runner = ClickHouseMigrationRunner(client, database)
        run_migrate(runner, migrations_dir)

    elif command == "rollback":
        print("Rollback not implemented yet")
        print("To manually rollback, run the downgrade() method from the migration file")
        sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
