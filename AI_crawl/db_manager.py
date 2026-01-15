#!/usr/bin/env python3
"""
Database Manager - Quản lý PostgreSQL database cho crawler
Mỗi website có bảng riêng
"""
import sys
import psycopg2
from psycopg2.extras import execute_values
import json
import os
from datetime import datetime
import zlib
import uuid as uuid_lib

# Add parent directory to path to import env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from env import env

class DatabaseManager:
    # ⚙️ Configuration - Set cứng mặc định
    DB_HOST = 'localhost'
    DB_PORT = env.POSTGRES_PORT
    DB_USER = 'postgres'
    DB_PASSWORD = 'mypassword'
    DB_NAME = 'chatbot'
    CONNECT_TIMEOUT = 10
    BATCH_PAGE_SIZE = 100
    
    # Website ID mapping - simple 1, 2, 3...
    WEBSITE_MAPPING = {
        'mypc.vn': 1,
        'phongvu.vn': 2,
        'tiki.vn': 3,
        'nguyencongpc.vn': 4,
    }
    NEXT_WEBSITE_ID = 5  # For new websites
    
    def __init__(self, host=None, port=None, user=None, password=None, dbname=None):
        self.host = host or self.DB_HOST
        self.port = port or self.DB_PORT
        self.user = user or self.DB_USER
        self.password = password or self.DB_PASSWORD
        self.dbname = dbname or self.DB_NAME
        self.conn = None
    
    def connect(self):
        """Kết nối tới database"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname=self.dbname,
                connect_timeout=self.CONNECT_TIMEOUT
            )
            print(f"✅ PostgreSQL connected: {self.user}@{self.host}:{self.port}/{self.dbname}")
            return self.conn
        except psycopg2.Error as e:
            print(f"❌ Connection failed: {e}")
            return None
    
    def reset_schema(self):
        """DROP và recreate bảng products từ init.sql"""
        if not self.conn:
            print("❌ Không có kết nối database")
            return False
        
        try:
            with self.conn.cursor() as cur:
                # DROP TABLE if exists
                print("🗑️  Đang xóa bảng products...")
                cur.execute('DROP TABLE IF EXISTS public.products CASCADE;')
                self.conn.commit()
                print("✅ Bảng products đã xóa")
                
                # Recreate từ init.sql
                if os.path.exists('init.sql'):
                    print("📝 Recreate bảng từ init.sql...")
                    with open('init.sql', 'r', encoding='utf-8') as f:
                        cur.execute(f.read())
                    self.conn.commit()
                    print('✅ Bảng products đã được tạo lại từ init.sql')
                    return True
                else:
                    print('❌ Không tìm thấy init.sql')
                    return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def init_schema(self):
        """Khởi tạo schema (nếu chưa tạo)"""
        if not self.conn:
            print("❌ Không có kết nối database")
            return False
        
        try:
            with self.conn.cursor() as cur:
                # Check if products table exists
                cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'products')")
                if cur.fetchone()[0]:
                    print("ℹ️  Table 'public.products' đã tồn tại")

                    # Verify required columns exist; if some are missing, try to ALTER TABLE to add them
                    required_columns = {
                        'id': 'UUID PRIMARY KEY DEFAULT gen_random_uuid()',
                        'website_id': 'INTEGER DEFAULT 0',
                        'website_name': "VARCHAR(255)",
                        'url': "VARCHAR(1000)",
                        'title': "VARCHAR(500)",
                        'price': 'FLOAT DEFAULT 0',
                        'original_price': 'FLOAT DEFAULT 0',
                        'currency': "VARCHAR(10) DEFAULT 'VND'",
                        'sku': "VARCHAR(255)",
                        'brand': "VARCHAR(255)",
                        'category': "VARCHAR(255)",
                        'description': 'TEXT',
                        'availability': "VARCHAR(100)",
                        'images': 'TEXT[]',
                        'user_id': 'UUID',
                        'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                        'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                    }

                    # Get existing columns
                    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='products'")
                    existing = {r[0] for r in cur.fetchall()}

                    missing = [col for col in required_columns.keys() if col not in existing]
                    if missing:
                        print(f"⚠️  Trang bị thiếu cột trong products: {missing}. Sẽ cố gắng sửa bằng ALTER TABLE...")
                        for col in missing:
                            try:
                                # Note: don't re-add primary key if exists; if id missing, recreate table below
                                if col == 'id':
                                    raise Exception('id column missing - recreate required')
                                alter_sql = f"ALTER TABLE public.products ADD COLUMN {col} {required_columns[col]};"
                                cur.execute(alter_sql)
                                print(f"   ✓ Đã thêm cột {col}")
                            except Exception as e:
                                print(f"   ❌ Không thêm được cột {col}: {e}")

                        # If id missing (primary key) or critical mismatch, try recreating from init.sql
                        if 'id' not in existing:
                            print("⚠️  Cột 'id' bị thiếu. Thực hiện DROP TABLE và tạo lại từ init.sql (nếu có)...")
                            if os.path.exists('init.sql'):
                                cur.execute('DROP TABLE IF EXISTS public.products CASCADE;')
                                with open('init.sql', 'r', encoding='utf-8') as f:
                                    cur.execute(f.read())
                                self.conn.commit()
                                print('✅ Đã recreate bảng products từ init.sql')
                                return True
                            else:
                                print('❌ Không tìm thấy init.sql để recreate bảng')
                                return False

                    # Commit any ALTERs
                    self.conn.commit()

                    # Ensure there is a unique constraint/index on url to support ON CONFLICT (url)
                    try:
                        cur.execute("SELECT conname FROM pg_constraint WHERE conrelid = 'public.products'::regclass AND contype = 'u'")
                        unique_constraints = [r[0] for r in cur.fetchall()]
                        # Also check indexes
                        cur.execute("SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename='products'")
                        indexes = [r[0] for r in cur.fetchall()]

                        has_unique_url = False
                        # Check if any unique constraint/index mentions 'url'
                        for uc in unique_constraints:
                            if 'url' in uc:
                                has_unique_url = True
                        for idx in indexes:
                            if 'url' in idx:
                                # Need to check index definition
                                cur.execute("SELECT indexdef FROM pg_indexes WHERE indexname = %s", (idx,))
                                idxdef = cur.fetchone()[0]
                                if 'unique' in idxdef.lower() and 'url' in idxdef.lower():
                                    has_unique_url = True

                        if not has_unique_url:
                            print("ℹ️  Tạo UNIQUE INDEX trên products(url) để hỗ trợ ON CONFLICT...")
                            cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_products_url_unique ON public.products ((url));')
                            self.conn.commit()
                    except Exception as e:
                        print(f"⚠️ Không thể đảm bảo unique index trên url: {e}")
                    return True
                
                # Try to create table from init.sql
                if os.path.exists('init.sql'):
                    print("📝 Tạo bảng products...")
                    with open('init.sql', 'r', encoding='utf-8') as f:
                        sql_content = f.read()
                        cur.execute(sql_content)
                        self.conn.commit()
                        print("✅ Bảng products khởi tạo thành công")
                        return True
                else:
                    print("ℹ️  init.sql không tìm thấy - giả định bảng đã tồn tại trên remote DB")
                    return True
        
        except Exception as e:
            print(f"❌ Schema init error: {e}")
            self.conn.rollback()
            return False
    
    def add_website(self, name, base_url, ai_provider='openai'):
        """Thêm website mới hoặc lấy ID của website đã tồn tại"""
        if not self.conn:
            print("❌ Không có kết nối database")
            return None
        
        try:
            from urllib.parse import urlparse
            
            domain = urlparse(base_url).netloc
            
            # Normalize domain: remove www prefix
            if domain.startswith('www.'):
                domain_normalized = domain[4:]
            else:
                domain_normalized = domain
            
            # Use website_name as unique key (better for file uploads)
            # Check if this website_name already exists in database
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT website_id FROM products WHERE website_name = %s LIMIT 1",
                    (name,)
                )
                result = cur.fetchone()
                
                if result:
                    # Website exists, use existing ID
                    website_id = result[0]
                    print(f"✅ Website exists: {name} (ID: {website_id})")
                else:
                    # New website, assign new ID
                    # Try domain mapping first (for known websites)
                    if domain_normalized in self.WEBSITE_MAPPING:
                        website_id = self.WEBSITE_MAPPING[domain_normalized]
                    else:
                        # Query max website_id from database
                        cur.execute("SELECT COALESCE(MAX(website_id), 0) FROM products")
                        max_id = cur.fetchone()[0]
                        website_id = max_id + 1
                    
                    print(f"✅ New website: {name}")
            
            print(f"   Domain: {domain_normalized}")
            print(f"   Website ID: {website_id}")
            print(f"   Tất cả products sẽ lưu vào: public.products")
            return website_id
        except Exception as e:
            print(f"❌ Error adding website: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def import_products_from_json(self, json_file, website_id=None, website_name=None, user_id=None):
        """Import sản phẩm từ JSON file vào bảng riêng của website"""
        if not self.conn:
            print("❌ Không có kết nối database")
            return False
        
        if not os.path.exists(json_file):
            print(f"❌ File không tìm thấy: {json_file}")
            return False
        
        # VALIDATE USER_ID - BẮT BUỘC PHẢI CÓ VÀ TỒN TẠI TRONG DATABASE
        if not user_id:
            print("❌ Thiếu user_id! Phải đăng nhập mới được crawl.")
            return False
        
        # Verify user exists in database
        try:
            user_uuid = uuid_lib.UUID(user_id) if isinstance(user_id, str) else user_id
        except (ValueError, AttributeError):
            print(f"❌ user_id không hợp lệ: {user_id}")
            return False
        
        # Check if user exists
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import Session
            
            # Tạo connection string
            conn_str = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"
            engine = create_engine(conn_str)
            
            # Import models
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from models.user import UserTable
            from models.ai_personality import AIPersonalityTable
            
            with Session(engine) as session:
                user = session.query(UserTable).filter(UserTable.id == user_uuid).first()
                
                if not user:
                    print(f"❌ User {user_id} không tồn tại trong database!")
                    print("   Vui lòng đăng nhập trước khi crawl.")
                    return False
                
                print(f"✅ User verified: {user.full_name} ({user.email})")
        except Exception as e:
            print(f"❌ Lỗi xác thực user: {e}")
            return False
        
        try:
            # Nếu chưa có website_id, thêm website mới
            if not website_id:
                if not website_name:
                    # Extract từ tên file
                    website_name = json_file.split('_')[0]
                
                # Lấy domain từ filename
                base_url = f"https://{website_name.replace('_', '.')}"
                website_id = self.add_website(website_name, base_url)
                if not website_id:
                    print(f"❌ Không thể tạo website")
                    return False
            
            # Lấy website info (simplified - just use website_name directly)
            if not website_name:
                website_name = "unknown"
            
            # Load JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
            
            print(f"📥 Đang import {len(products)} sản phẩm vào products...")
            
            # Check existing products for this website
            with self.conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM products WHERE website_id = %s", (website_id,))
                existing_count = cur.fetchone()[0]
            
            print(f"   ℹ️  Website hiện có {existing_count} sản phẩm")
            
            # Prepare data for batch insert
            products_data = []
            skipped_invalid = 0
            duplicates_in_batch = 0
            
            seen_urls = set()
            
            for product in products:
                # Validate URL
                url = product.get('url', '').strip()
                if not url:
                    skipped_invalid += 1
                    continue
                
                # Validate Title (bắt buộc)
                title = product.get('title', '').strip()
                if not title:
                    skipped_invalid += 1
                    continue
                
                # Check duplicate in current batch
                if url in seen_urls:
                    duplicates_in_batch += 1
                    continue
                seen_urls.add(url)
                
                # Convert images list to PostgreSQL array format
                images = product.get('images', [])
                if not isinstance(images, list):
                    images = []
                # Convert to PostgreSQL array format if not empty
                if images:
                    images = images  # psycopg2 handles list to array conversion automatically
                else:
                    images = None
                
                # Clean price - nếu price > 1e15 hoặc không hợp lệ, set to 0
                price = product.get('price') or 0
                try:
                    price = float(price)
                    if price > 1e15 or price < 0:
                        price = 0
                except:
                    price = 0
                
                original_price = product.get('original_price') or 0
                try:
                    original_price = float(original_price)
                    if original_price > 1e15 or original_price < 0:
                        original_price = 0
                except:
                    original_price = 0
                
                products_data.append((
                    str(uuid_lib.uuid4()),  # Generate new UUID for id as string
                    website_id,
                    website_name,
                    url,
                    title,  # Đã validate ở trên, chắc chắn có giá trị
                    price,
                    original_price,
                    product.get('currency', 'VND'),
                    product.get('sku', ''),
                    product.get('brand', ''),
                    product.get('category', ''),
                    product.get('description', ''),
                    product.get('availability', ''),
                    images,
                    str(user_uuid)  # user_uuid đã được validate ở trên
                ))
            
            # Batch insert vào bảng products chung
            if products_data:
                with self.conn.cursor() as cur:
                    execute_values(cur, """
                        INSERT INTO products
                        (id, website_id, website_name, url, title, price, original_price, currency, sku, brand, category, description, availability, images, user_id)
                        VALUES %s
                        ON CONFLICT (url) DO UPDATE SET
                            title = EXCLUDED.title,
                            price = EXCLUDED.price,
                            original_price = EXCLUDED.original_price,
                            currency = EXCLUDED.currency,
                            sku = EXCLUDED.sku,
                            brand = EXCLUDED.brand,
                            category = EXCLUDED.category,
                            description = EXCLUDED.description,
                            availability = EXCLUDED.availability,
                            images = EXCLUDED.images,
                            user_id = EXCLUDED.user_id,
                            updated_at = CURRENT_TIMESTAMP;
                    """, products_data, page_size=self.BATCH_PAGE_SIZE)
                    
                    self.conn.commit()
            
            # Check final count
            with self.conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM products WHERE website_id = %s", (website_id,))
                final_count = cur.fetchone()[0]
            
            new_products = final_count - existing_count
            print(f"  ✅ Thêm {new_products} sản phẩm mới (tổng: {final_count})")
            if skipped_invalid > 0:
                print(f"  ⚠️  Bỏ qua {skipped_invalid} sản phẩm không hợp lệ (không có URL)")
            if duplicates_in_batch > 0:
                print(f"  ⚠️  Bỏ qua {duplicates_in_batch} duplicate URLs trong batch")
            
            return True
        
        except Exception as e:
            print(f"❌ Import error: {e}")
            self.conn.rollback()
            return False
    
    def log_crawl(self, website_id, total_urls, products_found, products_with_price, products_with_images, status="success", error_msg=None, duration_seconds=0):
        """Ghi log crawl vào database (disabled - simplified schema)"""
        # Simplified schema doesn't have crawl_logs table, so just skip logging
        print(f"\n  📋 LOG: {products_found} products ({products_with_price} with price, {products_with_images} with images) in {duration_seconds}s")
        return True
    
    def get_stats(self, website_id=None):
        """Lấy thống kê cho website (simplified - queries public.products only)"""
        if not self.conn:
            return {}
        
        try:
            with self.conn.cursor() as cur:
                if website_id:
                    # Lấy stats từ bảng products chung cho specific website
                    cur.execute("""
                        SELECT
                            COUNT(*) as total_products,
                            COUNT(CASE WHEN price > 0 THEN 1 END) as products_with_price,
                            COUNT(CASE WHEN images IS NOT NULL AND array_length(images, 1) > 0 THEN 1 END) as products_with_images,
                            COUNT(CASE WHEN sku IS NOT NULL AND sku != '' THEN 1 END) as products_with_sku,
                            AVG(price) as avg_price,
                            MIN(price) as min_price,
                            MAX(price) as max_price,
                            MAX(website_name) as website_name
                        FROM products
                        WHERE website_id = %s
                    """, (website_id,))
                    
                    stats = cur.fetchone()
                    if stats and stats[0] > 0:
                        return {
                            'id': website_id,
                            'name': stats[7] or 'Unknown',
                            'total_products': stats[0],
                            'products_with_price': stats[1],
                            'products_with_images': stats[2],
                            'products_with_sku': stats[3],
                            'avg_price': stats[4],
                            'min_price': stats[5],
                            'max_price': stats[6]
                        }
                else:
                    # Lấy tất cả stats từ products table
                    cur.execute("""
                        SELECT
                            website_id,
                            website_name,
                            COUNT(*) as total_products,
                            COUNT(CASE WHEN price > 0 THEN 1 END) as products_with_price,
                            COUNT(CASE WHEN images IS NOT NULL AND array_length(images, 1) > 0 THEN 1 END) as products_with_images,
                            COUNT(CASE WHEN sku IS NOT NULL AND sku != '' THEN 1 END) as products_with_sku,
                            AVG(price) as avg_price,
                            MIN(price) as min_price,
                            MAX(price) as max_price
                        FROM products
                        GROUP BY website_id, website_name
                        ORDER BY total_products DESC
                    """)
                    
                    results = []
                    for row in cur.fetchall():
                        if row[2] > 0:  # Chỉ thêm nếu có products
                            results.append({
                                'id': row[0],
                                'name': row[1] or 'Unknown',
                                'total_products': row[2],
                                'products_with_price': row[3],
                                'products_with_images': row[4],
                                'products_with_sku': row[5],
                                'avg_price': row[6],
                                'min_price': row[7],
                                'max_price': row[8]
                            })
                    return results
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {} if website_id else []
    
    def query_products(self, website_id=None, brand=None, min_price=None, max_price=None, limit=50, offset=0):
        """Truy vấn sản phẩm từ bảng products chung"""
        if not self.conn:
            return []
        
        try:
            with self.conn.cursor() as cur:
                # Build query
                where_conditions = ["1=1"]
                params = []
                
                if website_id:
                    where_conditions.append("website_id = %s")
                    params.append(website_id)
                
                if brand:
                    where_conditions.append("brand = %s")
                    params.append(brand)
                
                if min_price:
                    where_conditions.append("price >= %s")
                    params.append(min_price)
                
                if max_price:
                    where_conditions.append("price <= %s")
                    params.append(max_price)
                
                where_clause = " AND ".join(where_conditions)
                
                query = f"""
                    SELECT id, website_name, url, title, price, sku, brand, images
                    FROM products
                    WHERE {where_clause}
                    ORDER BY price DESC
                    LIMIT %s OFFSET %s
                """
                
                params.extend([limit, offset])
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                return [{
                    'id': r[0],
                    'url': r[1],
                    'title': r[2],
                    'price': r[3],
                    'sku': r[4],
                    'brand': r[5],
                    'images': r[6]
                } for r in results]
        
        except Exception as e:
            print(f"❌ Query error: {e}")
            return []
    
    def get_crawl_history(self, website_id=None, limit=10):
        """Lấy lịch sử crawl (disabled - simplified schema doesn't have crawl_logs)"""
        return []
    
    def get_crawl_stats_summary(self):
        """Lấy tóm tắt thống kê crawl (disabled - simplified schema doesn't have crawl_logs)"""
        return {
            'total_crawls': 0,
            'total_products': 0,
            'avg_duration': 0,
            'total_duration': 0,
            'success_rate': 0
        }
    
    def update_user_website_name(self, user_id, website_name):
        """Update website_name của user sử dụng SQLAlchemy ORM"""
        try:
            # Import SQLAlchemy + models
            from sqlalchemy import create_engine
            from sqlalchemy.orm import Session
            import uuid as uuid_lib
            
            # Tạo connection string từ db config
            db_url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"
            engine = create_engine(db_url, echo=False)
            
            # Import UserTable model
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from models.user import UserTable
            from models.ai_personality import AIPersonalityTable  # Import để fix relationship error
            
            # Parse user_id thành UUID
            try:
                user_uuid = uuid_lib.UUID(user_id)
            except (ValueError, AttributeError):
                print(f"  ❌ Invalid user_id format: {user_id}")
                return False
            
            # Update user
            with Session(engine) as session:
                user = session.query(UserTable).filter(UserTable.id == user_uuid).first()
                
                if user:
                    user.website_name = website_name
                    session.commit()
                    print(f"  ✅ Updated user {user_id} with website_name: '{website_name}'")
                    return True
                else:
                    print(f"  ⚠️  User {user_id} not found in database")
                    return False
        
        except Exception as e:
            print(f"  ❌ Error updating user: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def close(self):
        """Đóng kết nối"""
        if self.conn:
            self.conn.close()
            print("✅ Database connection closed")


if __name__ == "__main__":
    # Test
    db = DatabaseManager()
    
    if db.connect():
        db.init_schema()
        
        # Test: List all websites
        stats = db.get_stats()
        if stats:
            print("\n📊 WEBSITES:")
            for stat in stats:
                print(f"  - {stat['name']}: {stat['total_products']} products")
        
        db.close()
