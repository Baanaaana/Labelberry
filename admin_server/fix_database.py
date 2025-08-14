#!/usr/bin/env python3
"""Fix database schema issues"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def fix_database():
    """Add missing columns to database tables"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("No DATABASE_URL found")
        return
    
    print(f"Connecting to database...")
    conn = await asyncpg.connect(database_url)
    
    try:
        # Check if updated_at column exists in print_jobs
        has_updated_at = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name='print_jobs' 
                AND column_name='updated_at'
            )
        """)
        
        if not has_updated_at:
            print("Adding updated_at column to print_jobs table...")
            await conn.execute("""
                ALTER TABLE print_jobs 
                ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            print("✓ Added updated_at column")
        else:
            print("✓ updated_at column already exists")
        
        # Fix all pending jobs that should be completed
        # First, let's see what jobs we have
        pending_jobs = await conn.fetch("""
            SELECT id, pi_id, status, created_at 
            FROM print_jobs 
            WHERE status IN ('pending', 'processing')
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        print(f"\nFound {len(pending_jobs)} pending/processing jobs")
        
        if pending_jobs:
            print("\nPending jobs:")
            for job in pending_jobs:
                print(f"  - {job['id']}: {job['status']} (created: {job['created_at']})")
            
            # Mark old pending jobs as completed (they were test prints)
            # Jobs older than 10 minutes should be marked as completed
            result = await conn.execute("""
                UPDATE print_jobs 
                SET status = 'completed',
                    completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE status IN ('pending', 'processing')
                AND created_at < CURRENT_TIMESTAMP - INTERVAL '10 minutes'
            """)
            
            # Extract the number of rows updated from the result string
            rows_updated = int(result.split()[-1]) if result else 0
            print(f"\n✓ Marked {rows_updated} old pending jobs as completed")
        
        # Show current job statistics
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
            FROM print_jobs
        """)
        
        print("\nCurrent job statistics:")
        print(f"  Total: {stats['total']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Pending: {stats['pending']}")
        print(f"  Processing: {stats['processing']}")
        print(f"  Failed: {stats['failed']}")
        
    finally:
        await conn.close()
        print("\n✓ Database fixes completed")

if __name__ == "__main__":
    asyncio.run(fix_database())