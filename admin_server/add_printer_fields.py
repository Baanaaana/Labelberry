#!/usr/bin/env python3
"""Add device_name and location columns to pis table"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def add_columns():
    """Add missing columns to pis table"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("No DATABASE_URL found")
        return
    
    print(f"Connecting to database...")
    conn = await asyncpg.connect(database_url)
    
    try:
        # Check if device_name column exists
        has_device_name = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name='pis' 
                AND column_name='device_name'
            )
        """)
        
        if not has_device_name:
            print("Adding device_name column to pis table...")
            await conn.execute("""
                ALTER TABLE pis 
                ADD COLUMN device_name VARCHAR(255)
            """)
            print("✓ Added device_name column")
        else:
            print("✓ device_name column already exists")
        
        # Check if location column exists
        has_location = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name='pis' 
                AND column_name='location'
            )
        """)
        
        if not has_location:
            print("Adding location column to pis table...")
            await conn.execute("""
                ALTER TABLE pis 
                ADD COLUMN location VARCHAR(255)
            """)
            print("✓ Added location column")
        else:
            print("✓ location column already exists")
        
        # Check if label_size column exists
        has_label_size = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name='pis' 
                AND column_name='label_size'
            )
        """)
        
        if not has_label_size:
            print("Adding label_size column to pis table...")
            await conn.execute("""
                ALTER TABLE pis 
                ADD COLUMN label_size VARCHAR(50) DEFAULT 'standard'
            """)
            print("✓ Added label_size column")
        else:
            print("✓ label_size column already exists")
        
        print("\n✓ Database schema updated successfully")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(add_columns())