"""
Migration: Add user_id column to products table
"""
import sys
sys.path.insert(0, 'D:\\AIHUB\\AI_crawl')
from db_manager import DatabaseManager

db = DatabaseManager()
if not db.connect():
    print("❌ Không kết nối được database")
    sys.exit(1)

print("="*70)
print("MIGRATION: Add user_id to products table")
print("="*70)

cursor = db.conn.cursor()

# Check if user_id column exists
cursor.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name='products' AND column_name='user_id'
""")

if cursor.fetchone():
    print("\n✅ Column 'user_id' đã tồn tại")
else:
    print("\n➕ Thêm column 'user_id'...")
    try:
        cursor.execute("""
            ALTER TABLE products 
            ADD COLUMN user_id UUID
        """)
        db.conn.commit()
        print("✅ Đã thêm column 'user_id'")
        
        # Create index
        print("➕ Tạo index cho user_id...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id)
        """)
        db.conn.commit()
        print("✅ Đã tạo index")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        db.conn.rollback()

cursor.close()
db.close()

print("\n" + "="*70)
print("MIGRATION HOÀN TẤT")
print("="*70)
