#!/usr/bin/env python3
"""
Remove override_settings, default_darkness, and default_speed from database
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv('.env')

async def remove_override_fields():
    database_url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(database_url)
    
    try:
        # Remove the columns from configurations table
        await conn.execute("""
            ALTER TABLE configurations 
            DROP COLUMN IF EXISTS override_settings,
            DROP COLUMN IF EXISTS default_darkness,
            DROP COLUMN IF EXISTS default_speed
        """)
        print("✅ Removed override_settings, default_darkness, and default_speed columns from configurations table")
        
        # Verify the columns are gone
        columns = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'configurations'
        """)
        
        print("\nRemaining columns in configurations table:")
        for col in columns:
            print(f"  - {col['column_name']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(remove_override_fields())