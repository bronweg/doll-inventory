#!/usr/bin/env python3
"""
Migration script to add soft delete columns to dolls table.

This script adds:
- deleted_at (DateTime, nullable)
- deleted_by (String, nullable)

Run this script once to migrate existing databases.
"""
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings


def migrate():
    """Add soft delete columns to dolls table."""
    db_path = settings.DB_PATH
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        print("No migration needed - tables will be created with new schema on first run")
        return
    
    print(f"Migrating database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(dolls)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'deleted_at' in columns and 'deleted_by' in columns:
            print("✓ Columns already exist - no migration needed")
            return
        
        # Add deleted_at column if it doesn't exist
        if 'deleted_at' not in columns:
            print("Adding deleted_at column...")
            cursor.execute("ALTER TABLE dolls ADD COLUMN deleted_at DATETIME")
            print("✓ Added deleted_at column")
        
        # Add deleted_by column if it doesn't exist
        if 'deleted_by' not in columns:
            print("Adding deleted_by column...")
            cursor.execute("ALTER TABLE dolls ADD COLUMN deleted_by VARCHAR(255)")
            print("✓ Added deleted_by column")
        
        # Create index on deleted_at for better query performance
        print("Creating index on deleted_at...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dolls_deleted_at ON dolls(deleted_at)")
        print("✓ Created index")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()

