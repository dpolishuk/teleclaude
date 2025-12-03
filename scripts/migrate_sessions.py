#!/usr/bin/env python3
"""Migrate sessions table to unified schema.

This script:
1. Renames claude_session_id to id for rows that have it
2. Deletes rows without claude_session_id (orphaned)
3. Drops removed columns
"""
import sqlite3
import sys
from pathlib import Path


def migrate(db_path: str) -> None:
    """Run migration on database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Migrating {db_path}...")

    # Check current schema
    cursor.execute("PRAGMA table_info(sessions)")
    columns = {row[1] for row in cursor.fetchall()}

    if "claude_session_id" not in columns:
        print("Already migrated (no claude_session_id column)")
        return

    # Count rows to migrate
    cursor.execute("SELECT COUNT(*) FROM sessions WHERE claude_session_id IS NOT NULL")
    total_with_id = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT claude_session_id) FROM sessions WHERE claude_session_id IS NOT NULL")
    distinct_ids = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM sessions WHERE claude_session_id IS NULL")
    to_delete = cursor.fetchone()[0]

    duplicates = total_with_id - distinct_ids

    print(f"Sessions to migrate: {distinct_ids}")
    if duplicates > 0:
        print(f"Duplicate sessions to merge: {duplicates}")
    print(f"Orphaned sessions to delete: {to_delete}")

    # Create new table with simplified schema
    cursor.execute("""
        CREATE TABLE sessions_new (
            id TEXT PRIMARY KEY,
            telegram_user_id INTEGER NOT NULL,
            project_path TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            last_active TIMESTAMP NOT NULL,
            total_cost_usd REAL NOT NULL DEFAULT 0.0
        )
    """)

    # Migrate valid rows - for duplicates, keep the most recently active one
    cursor.execute("""
        INSERT INTO sessions_new (id, telegram_user_id, project_path, created_at, last_active, total_cost_usd)
        SELECT
            claude_session_id,
            telegram_user_id,
            project_path,
            MIN(created_at) as created_at,
            MAX(COALESCE(last_active, created_at)) as last_active,
            SUM(COALESCE(total_cost_usd, 0.0)) as total_cost_usd
        FROM sessions
        WHERE claude_session_id IS NOT NULL
        GROUP BY claude_session_id
    """)

    # Drop old table and rename
    cursor.execute("DROP TABLE sessions")
    cursor.execute("ALTER TABLE sessions_new RENAME TO sessions")

    # Create index
    cursor.execute("CREATE INDEX ix_sessions_telegram_user_id ON sessions(telegram_user_id)")

    conn.commit()
    print(f"Migration complete! {distinct_ids} sessions migrated, {to_delete} orphaned deleted.")
    if duplicates > 0:
        print(f"Merged {duplicates} duplicate sessions.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default path
        db_path = Path.home() / ".teleclaude" / "teleclaude.db"
    else:
        db_path = Path(sys.argv[1])

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    migrate(str(db_path))
