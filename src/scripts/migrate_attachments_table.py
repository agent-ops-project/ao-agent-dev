#!/usr/bin/env python3
"""
Migration script to update the attachments table with new columns for taint tracking.
"""

import sqlite3
import os
from pathlib import Path

def migrate_attachments_table():
    # Get the database path
    db_dir = Path.home() / ".cache" / "agent-copilot" / "db"
    db_path = db_dir / "experiments.sqlite"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    print(f"Migrating database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # Check if the new columns already exist
        c.execute("PRAGMA table_info(attachments)")
        columns = [col[1] for col in c.fetchall()]
        
        if "session_id" in columns:
            print("Database already migrated!")
            return
        
        # Backup existing data
        print("Backing up existing attachments data...")
        c.execute("SELECT * FROM attachments")
        existing_data = c.fetchall()
        
        # Drop the old table
        print("Dropping old attachments table...")
        c.execute("DROP TABLE IF EXISTS attachments")
        
        # Create new table with updated schema
        print("Creating new attachments table with taint tracking columns...")
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS attachments (
                file_id TEXT PRIMARY KEY,
                session_id TEXT,
                line_no INTEGER,
                content_hash TEXT,
                file_path TEXT,
                taint TEXT,
                FOREIGN KEY (session_id) REFERENCES experiments (session_id)
            )
            """
        )
        
        # Create index
        c.execute(
            """
            CREATE INDEX IF NOT EXISTS attachments_content_hash_idx ON attachments(content_hash)
            """
        )
        
        # Restore old data (if any)
        if existing_data:
            print(f"Restoring {len(existing_data)} existing records...")
            for row in existing_data:
                # Old schema: file_id, content_hash, file_path
                # New schema: file_id, session_id, line_no, content_hash, file_path, taint
                c.execute(
                    """
                    INSERT INTO attachments (file_id, session_id, line_no, content_hash, file_path, taint)
                    VALUES (?, NULL, NULL, ?, ?, '[]')
                    """,
                    (row[0], row[1], row[2])
                )
        
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_attachments_table()