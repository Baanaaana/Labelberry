#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv('admin_server/.env')

async def check_pi():
    database_url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(database_url)
    
    # Get all Pis
    rows = await conn.fetch("SELECT id, device_id, friendly_name, status FROM pis")
    print("All Pis in database:")
    for row in rows:
        print(f"  ID: {row['id']}")
        print(f"  Device ID: {row['device_id']}")
        print(f"  Name: {row['friendly_name']}")
        print(f"  Status: {row['status']}")
        print("  ---")
    
    # Check config for René's printer
    rows = await conn.fetch("""
        SELECT p.id, p.device_id, c.* 
        FROM pis p 
        LEFT JOIN configurations c ON p.id = c.pi_id 
        WHERE p.friendly_name LIKE '%René%'
    """)
    print("\nRené's printer config:")
    for row in rows:
        print(f"  Database ID: {row['id']}")
        print(f"  Device ID: {row['device_id']}")
        print(f"  Override Settings: {row.get('override_settings', 'N/A')}")
        print(f"  Default Darkness: {row.get('default_darkness', 'N/A')}")
        print(f"  Default Speed: {row.get('default_speed', 'N/A')}")
    
    await conn.close()

asyncio.run(check_pi())