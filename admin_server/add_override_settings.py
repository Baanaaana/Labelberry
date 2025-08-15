#!/usr/bin/env python3
"""
Add override_settings column to configurations table
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def add_override_settings_column():
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    try:
        # Connect to the database
        conn = await asyncpg.connect(database_url)
        
        # Check if column already exists
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'configurations' 
                AND column_name = 'override_settings'
            )
        """)
        
        if not column_exists:
            # Add the override_settings column with default value of false
            await conn.execute("""
                ALTER TABLE configurations 
                ADD COLUMN override_settings BOOLEAN DEFAULT FALSE
            """)
            print("✅ Added override_settings column to configurations table")
        else:
            print("ℹ️  override_settings column already exists")
        
        # Show current table structure
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'configurations'
            ORDER BY ordinal_position
        """)
        
        print("\nCurrent configurations table structure:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']}, default: {col['column_default']})")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error adding override_settings column: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(add_override_settings_column())