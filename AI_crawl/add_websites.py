#!/usr/bin/env python3
"""Add sample websites to database"""
from db_manager import DatabaseManager

websites = [
    {
        'name': 'phongvu.vn',
        'base_url': 'https://phongvu.vn',
        'domain': 'phongvu.vn'
    },
    {
        'name': 'mypc.vn',
        'base_url': 'https://mypc.vn',
        'domain': 'mypc.vn'
    },
    {
        'name': 'tiki.vn',
        'base_url': 'https://tiki.vn',
        'domain': 'tiki.vn'
    }
]

if __name__ == '__main__':
    db = DatabaseManager()
    db.connect()
    try:
        print("📝 Adding websites to database...\n")
        for site in websites:
            result = db.add_website(site['name'], site['base_url'], site['domain'])
            if result:
                print(f"✓ Added: {site['name']}")
            else:
                print(f"⚠ Already exists or error: {site['name']}")
        print("\n✅ Done!")
    finally:
        db.close()
