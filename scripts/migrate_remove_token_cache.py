#!/usr/bin/env python3
"""
Migration script to remove cached token data from experiment and run meta fields.

This script removes the 'total_tokens', 'input_tokens', and 'output_tokens' keys
from the meta JSON field in both experiments and runs tables since token data is
now fetched directly from ClickHouse instead of being cached.

Usage:
    python scripts/migrate_remove_token_cache.py
"""

from alphatrion.storage import runtime


def migrate():
    """Remove token cache from experiment and run meta fields."""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    # Get all experiments and clean up token cache from meta
    print("Cleaning up experiment meta...")
    # Using raw SQL for efficiency
    with metadb._engine.connect() as conn:
        # For PostgreSQL with JSONB, we can use jsonb_set or similar
        # For now, we'll fetch and update in Python
        result = conn.execute(
            "SELECT uuid, meta FROM experiments WHERE meta IS NOT NULL"
        )
        experiments = result.fetchall()

        updated_count = 0
        for exp_uuid, meta in experiments:
            if meta and any(
                key in meta for key in ["total_tokens", "input_tokens", "output_tokens"]
            ):
                # Remove token keys from meta
                new_meta = {
                    k: v
                    for k, v in meta.items()
                    if k not in ["total_tokens", "input_tokens", "output_tokens"]
                }
                # Update the experiment
                conn.execute(
                    "UPDATE experiments SET meta = %s WHERE uuid = %s",
                    (new_meta if new_meta else None, exp_uuid),
                )
                updated_count += 1

        conn.commit()
        print(f"Updated {updated_count} experiments")

    # Get all runs and clean up token cache from meta
    print("Cleaning up run meta...")
    with metadb._engine.connect() as conn:
        result = conn.execute("SELECT uuid, meta FROM runs WHERE meta IS NOT NULL")
        runs = result.fetchall()

        updated_count = 0
        for run_uuid, meta in runs:
            if meta and any(
                key in meta for key in ["total_tokens", "input_tokens", "output_tokens"]
            ):
                # Remove token keys from meta
                new_meta = {
                    k: v
                    for k, v in meta.items()
                    if k not in ["total_tokens", "input_tokens", "output_tokens"]
                }
                # Update the run
                conn.execute(
                    "UPDATE runs SET meta = %s WHERE uuid = %s",
                    (new_meta if new_meta else None, run_uuid),
                )
                updated_count += 1

        conn.commit()
        print(f"Updated {updated_count} runs")

    print("Migration complete!")


if __name__ == "__main__":
    migrate()
