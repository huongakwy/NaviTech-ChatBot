"""Get first user ID from database"""
import sys
sys.path.append('.')

from sqlalchemy import create_engine, text
from env import env

try:
    # Connect to database
    engine = create_engine(env.DATABASE_URL)
    
    with engine.connect() as conn:
        # Get first user
        result = conn.execute(text("SELECT id, full_name, email FROM users LIMIT 1"))
        user = result.fetchone()
        
        if user:
            print(f"✅ Found user:")
            print(f"   ID: {user[0]}")
            print(f"   Name: {user[1]}")
            print(f"   Email: {user[2]}")
            print(f"\nUse this ID for sample FAQs: {user[0]}")
        else:
            print("❌ No users found in database")
            print("   Please create a user first")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
