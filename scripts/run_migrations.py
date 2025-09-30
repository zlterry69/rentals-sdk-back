#!/usr/bin/env python3
"""
Script to run database migrations
"""
import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings
import structlog

logger = structlog.get_logger()


async def run_migrations():
    """Run all database migrations"""
    try:
        # Connect to database
        conn = await asyncpg.connect(settings.SUPABASE_DB_URL)
        logger.info("Connected to database")
        
        # Get migrations directory
        migrations_dir = Path(__file__).parent.parent / "database" / "migrations"
        
        # Get all SQL migration files
        migration_files = sorted(migrations_dir.glob("*.sql"))
        
        if not migration_files:
            logger.warning("No migration files found")
            return
        
        # Create migrations tracking table if it doesn't exist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                filename TEXT UNIQUE NOT NULL,
                executed_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Get already executed migrations
        executed = await conn.fetch("SELECT filename FROM migrations")
        executed_files = {row['filename'] for row in executed}
        
        # Run pending migrations
        for migration_file in migration_files:
            filename = migration_file.name
            
            if filename in executed_files:
                logger.info("Migration already executed", filename=filename)
                continue
            
            logger.info("Running migration", filename=filename)
            
            # Read and execute migration
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            
            try:
                await conn.execute(migration_sql)
                
                # Record migration as executed
                await conn.execute(
                    "INSERT INTO migrations (filename) VALUES ($1)",
                    filename
                )
                
                logger.info("Migration completed successfully", filename=filename)
                
            except Exception as e:
                logger.error("Migration failed", filename=filename, error=str(e))
                raise
        
        logger.info("All migrations completed successfully")
        
    except Exception as e:
        logger.error("Migration process failed", error=str(e))
        raise
    finally:
        if 'conn' in locals():
            await conn.close()


async def check_database_connection():
    """Check if database connection is working"""
    try:
        conn = await asyncpg.connect(settings.SUPABASE_DB_URL)
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        
        if result == 1:
            logger.info("Database connection successful")
            return True
        else:
            logger.error("Database connection test failed")
            return False
            
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument("--check", action="store_true", help="Only check database connection")
    args = parser.parse_args()
    
    # Setup basic logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    if args.check:
        # Just check connection
        success = asyncio.run(check_database_connection())
        sys.exit(0 if success else 1)
    else:
        # Run migrations
        asyncio.run(run_migrations())
