"""
Database migration system.

This module provides a simple, idempotent migration runner that executes
on application startup to safely migrate the database schema.
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def run_migrations(db_path: Path) -> None:
    """
    Run all migrations in order.
    
    This function is idempotent - it can be run multiple times safely.
    Each migration checks if it needs to run before making changes.
    
    Args:
        db_path: Path to the SQLite database file
    """
    logger.info(f"Running migrations on database: {db_path}")
    
    if not db_path.exists():
        logger.info("Database does not exist yet - will be created with latest schema")
        return
    
    conn = sqlite3.connect(db_path)
    try:
        # Run migrations in order
        _migrate_001_add_containers(conn)
        
        conn.commit()
        logger.info("All migrations completed successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Check if a table exists."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    return cursor.fetchone() is not None


def _migrate_001_add_containers(conn: sqlite3.Connection) -> None:
    """
    Migration 001: Add containers table and migrate existing data.
    
    This migration:
    1. Creates the containers table
    2. Adds container_id and purchase_url columns to dolls table
    3. Creates system containers (Home, Wishlist)
    4. Creates bag containers based on existing data
    5. Backfills dolls.container_id from location/bag_number
    """
    logger.info("Running migration 001: Add containers")
    cursor = conn.cursor()
    
    # Step 1: Create containers table if it doesn't exist
    if not _table_exists(conn, "containers"):
        logger.info("Creating containers table...")
        cursor.execute("""
            CREATE TABLE containers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                sort_order INTEGER NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                is_system BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX idx_containers_sort_order ON containers(sort_order)")
        cursor.execute("CREATE INDEX idx_containers_is_active ON containers(is_active)")
        logger.info("✓ Created containers table")
    else:
        logger.info("✓ Containers table already exists")
    
    # Step 2: Add columns to dolls table if they don't exist
    if not _column_exists(conn, "dolls", "container_id"):
        logger.info("Adding container_id column to dolls table...")
        cursor.execute("ALTER TABLE dolls ADD COLUMN container_id INTEGER")
        cursor.execute("CREATE INDEX idx_dolls_container_id ON dolls(container_id)")
        logger.info("✓ Added container_id column")
    else:
        logger.info("✓ container_id column already exists")
    
    if not _column_exists(conn, "dolls", "purchase_url"):
        logger.info("Adding purchase_url column to dolls table...")
        cursor.execute("ALTER TABLE dolls ADD COLUMN purchase_url TEXT")
        logger.info("✓ Added purchase_url column")
    else:
        logger.info("✓ purchase_url column already exists")

    # Step 2.5: Make location column nullable (SQLite doesn't support ALTER COLUMN, so we check if we need to recreate)
    # Check if location column allows NULL
    cursor.execute("PRAGMA table_info(dolls)")
    columns = cursor.fetchall()
    location_col = next((col for col in columns if col[1] == 'location'), None)

    if location_col and location_col[3] == 1:  # notnull == 1 means NOT NULL
        logger.info("Making location column nullable...")
        # SQLite requires table recreation to change column constraints
        # Get all existing data
        cursor.execute("SELECT * FROM dolls")
        existing_dolls = cursor.fetchall()

        # Get column names
        col_names = [col[1] for col in columns]

        # Rename old table
        cursor.execute("ALTER TABLE dolls RENAME TO dolls_old")

        # Create new table with nullable location
        cursor.execute("""
            CREATE TABLE dolls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                container_id INTEGER,
                purchase_url TEXT,
                location VARCHAR(10),
                bag_number INTEGER,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                deleted_at DATETIME,
                deleted_by VARCHAR(255)
            )
        """)

        # Recreate indexes (with IF NOT EXISTS to avoid errors)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dolls_container_id ON dolls(container_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dolls_location ON dolls(location)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dolls_bag_number ON dolls(bag_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dolls_deleted_at ON dolls(deleted_at)")

        # Copy data back
        if existing_dolls:
            placeholders = ','.join(['?' for _ in col_names])
            cursor.executemany(
                f"INSERT INTO dolls ({','.join(col_names)}) VALUES ({placeholders})",
                existing_dolls
            )

        # Drop old table
        cursor.execute("DROP TABLE dolls_old")
        logger.info("✓ Made location column nullable")
    else:
        logger.info("✓ Location column is already nullable")

    # Step 3: Create system containers if they don't exist
    # Check if Home container exists
    cursor.execute("SELECT id FROM containers WHERE name = 'Home' AND is_system = 1")
    home_container = cursor.fetchone()

    if not home_container:
        logger.info("Creating Home container...")
        cursor.execute("""
            INSERT INTO containers (name, sort_order, is_active, is_system, created_at, updated_at)
            VALUES ('Home', 0, 1, 1, datetime('now'), datetime('now'))
        """)
        home_container_id = cursor.lastrowid
        logger.info(f"✓ Created Home container (id={home_container_id})")
    else:
        home_container_id = home_container[0]
        logger.info(f"✓ Home container already exists (id={home_container_id})")
    
    # Step 4: Create bag containers based on existing data
    # Find all unique bag numbers from existing dolls
    cursor.execute("""
        SELECT DISTINCT bag_number 
        FROM dolls 
        WHERE location = 'BAG' AND bag_number IS NOT NULL
        ORDER BY bag_number
    """)
    existing_bags = [row[0] for row in cursor.fetchall()]
    
    if existing_bags:
        max_bag = max(existing_bags)
        logger.info(f"Found existing bags: {existing_bags}, max bag number: {max_bag}")
        
        # Create containers for all bags from 1 to max_bag
        for bag_num in range(1, max_bag + 1):
            bag_name = f"Bag {bag_num}"
            cursor.execute("SELECT id FROM containers WHERE name = ?", (bag_name,))
            existing = cursor.fetchone()
            
            if not existing:
                sort_order = bag_num * 10
                cursor.execute("""
                    INSERT INTO containers (name, sort_order, is_active, is_system, created_at, updated_at)
                    VALUES (?, ?, 1, 0, datetime('now'), datetime('now'))
                """, (bag_name, sort_order))
                logger.info(f"✓ Created {bag_name} container (sort_order={sort_order})")
    else:
        logger.info("No existing bags found in dolls table")
    
    # Step 5: Create Wishlist container
    # Calculate sort_order for wishlist (after all bags)
    cursor.execute("SELECT MAX(sort_order) FROM containers")
    max_sort_order = cursor.fetchone()[0] or 0
    wishlist_sort_order = max_sort_order + 10
    
    cursor.execute("SELECT id FROM containers WHERE name = 'Wishlist' AND is_system = 1")
    wishlist_container = cursor.fetchone()
    
    if not wishlist_container:
        logger.info(f"Creating Wishlist container (sort_order={wishlist_sort_order})...")
        cursor.execute("""
            INSERT INTO containers (name, sort_order, is_active, is_system, created_at, updated_at)
            VALUES ('Wishlist', ?, 1, 1, datetime('now'), datetime('now'))
        """, (wishlist_sort_order,))
        logger.info("✓ Created Wishlist container")
    else:
        logger.info("✓ Wishlist container already exists")
    
    # Step 6: Backfill dolls.container_id
    # Only backfill where container_id is NULL
    cursor.execute("SELECT COUNT(*) FROM dolls WHERE container_id IS NULL")
    dolls_to_migrate = cursor.fetchone()[0]
    
    if dolls_to_migrate > 0:
        logger.info(f"Backfilling container_id for {dolls_to_migrate} dolls...")
        
        # Migrate HOME dolls
        cursor.execute("""
            UPDATE dolls 
            SET container_id = (SELECT id FROM containers WHERE name = 'Home' AND is_system = 1)
            WHERE location = 'HOME' AND container_id IS NULL
        """)
        home_count = cursor.rowcount
        logger.info(f"✓ Migrated {home_count} dolls to Home container")
        
        # Migrate BAG dolls
        cursor.execute("""
            SELECT DISTINCT bag_number 
            FROM dolls 
            WHERE location = 'BAG' AND bag_number IS NOT NULL AND container_id IS NULL
        """)
        bag_numbers = [row[0] for row in cursor.fetchall()]
        
        for bag_num in bag_numbers:
            bag_name = f"Bag {bag_num}"
            cursor.execute("""
                UPDATE dolls 
                SET container_id = (SELECT id FROM containers WHERE name = ?)
                WHERE location = 'BAG' AND bag_number = ? AND container_id IS NULL
            """, (bag_name, bag_num))
            bag_count = cursor.rowcount
            logger.info(f"✓ Migrated {bag_count} dolls to {bag_name} container")
        
        # Handle any remaining dolls with unexpected values (default to Home)
        cursor.execute("""
            UPDATE dolls 
            SET container_id = (SELECT id FROM containers WHERE name = 'Home' AND is_system = 1)
            WHERE container_id IS NULL
        """)
        remaining_count = cursor.rowcount
        if remaining_count > 0:
            logger.warning(f"⚠ Migrated {remaining_count} dolls with unexpected location to Home container")
    else:
        logger.info("✓ All dolls already have container_id assigned")
    
    logger.info("Migration 001 completed successfully")

