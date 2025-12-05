#!/usr/bin/env python3
"""
🔄 UNIFIED CRAWLER PIPELINE - All in One
Input: Website URL + User ID (UUID)
Process: Crawl → Extract (Multi-threaded) → PostgreSQL → Embeddings (Qdrant)
Output: Data inserted into database + embeddings in Qdrant
"""

import sys
import os
import time
import json
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import signal
from datetime import datetime, timedelta
import uuid
from typing import List

# ==================== CONFIG ====================
class Config:
    """All hardcoded configuration values"""
    AI_PROVIDER = 'openai'  # 'openai', 'gemini', 'grok'
    MAX_PRODUCTS = 10000
    NUM_THREADS = 40              # Giảm từ 60 → 40 (balance: nhanh + không bị block)
    BATCH_SIZE = 100
    TIMEOUT_SECONDS = 3600  # 1 hour

# Easy access to config values
AI_PROVIDER = Config.AI_PROVIDER
MAX_PRODUCTS = Config.MAX_PRODUCTS
NUM_THREADS = Config.NUM_THREADS
BATCH_SIZE = Config.BATCH_SIZE
TIMEOUT_SECONDS = Config.TIMEOUT_SECONDS
# ================================================


def find_sitemap(url: str, timeout: int = 10) -> List[str]:
    """
    🔍 Quick sitemap finder - trả về list sitemap URLs
    Dùng để check nhanh trước khi crawl
    """
    try:
        from crawl import SimpleSitemapCrawler
        
        crawler = SimpleSitemapCrawler(url, ai_provider='gemini')
        sitemap_urls = crawler.get_sitemap_urls()
        
        return sitemap_urls if sitemap_urls else []
        
    except Exception as e:
        print(f"⚠️ Sitemap check error: {e}")
        return []


def extract_products_threaded(crawler, urls, max_products=10000, num_threads=5):
    """Extract products using multiple threads"""
    products = []
    products_lock = threading.Lock()
    
    def extract_worker(url):
        try:
            product = crawler.extract_product(url)
            with products_lock:
                products.append(product)
            return url, True
        except Exception as e:
            return url, False
    
    # Extract sản phẩm với multi-threading
    print(f"  ⏳ Extracting {min(len(urls), max_products)} products ({num_threads} threads)...\n")
    
    extracted = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {
            executor.submit(extract_worker, url): url 
            for url in urls[:max_products]
        }
        
        for i, future in enumerate(as_completed(futures), 1):
            url, success = future.result()
            if success:
                extracted += 1
                # Chỉ print mỗi 10 items để tránh i/o chậm
                if i % 10 == 0:
                    print(f"  [{i}/{min(len(urls), max_products)}] {extracted} success")
            else:
                failed += 1
    
    print(f"  ✅ Extracted {extracted} products ({failed} failed)\n")
    return products

def timeout_handler(signum, frame):
    """Handle timeout - force exit"""
    print("\n\n" + "="*70)
    print("⏱️  TIMEOUT! Pipeline vượt quá thời gian cho phép")
    print("="*70)
    sys.exit(130)  # Exit code for timeout

def cleanup_user_old_data(user_id, db):
    """
    Xóa toàn bộ data + embeddings cũ của user
    1 user chỉ được lưu 1 website tại 1 thời điểm
    """
    print("📍 BƯỚC 0: Cleanup old data\n")
    
    try:
        # Xóa products cũ trong PostgreSQL
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products WHERE user_id = %s", (user_id,))
        old_count = cursor.fetchone()[0]
        
        if old_count > 0:
            print(f"  🗑️  Xóa {old_count} products cũ từ database...")
            cursor.execute("DELETE FROM products WHERE user_id = %s", (user_id,))
            db.conn.commit()
            print(f"  ✅ Đã xóa {old_count} products\n")
        else:
            print(f"  ℹ️  Không có data cũ trong database\n")
        
        cursor.close()
        
        # Xóa embeddings cũ trong Qdrant
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            qdrant = QdrantClient(url="http://localhost:6334")
            collection_name = "products"
            
            # Check collection exists
            collections = qdrant.get_collections().collections
            if any(c.name == collection_name for c in collections):
                # Count old vectors
                count_result = qdrant.count(
                    collection_name=collection_name,
                    count_filter=Filter(
                        must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                    )
                )
                old_vectors = count_result.count
                
                if old_vectors > 0:
                    print(f"  🗑️  Xóa {old_vectors} embeddings cũ từ Qdrant...")
                    # Delete vectors by user_id filter
                    qdrant.delete(
                        collection_name=collection_name,
                        points_selector=Filter(
                            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                        )
                    )
                    print(f"  ✅ Đã xóa {old_vectors} embeddings\n")
                else:
                    print(f"  ℹ️  Không có embeddings cũ trong Qdrant\n")
            else:
                print(f"  ℹ️  Collection '{collection_name}' chưa tồn tại\n")
                
        except Exception as e:
            print(f"  ⚠️  Lỗi khi xóa embeddings: {e}")
            print(f"  ℹ️  Tiếp tục với crawl mới...\n")
    
    except Exception as e:
        print(f"  ⚠️  Lỗi cleanup: {e}")
        print(f"  ℹ️  Tiếp tục với crawl mới...\n")


def main():
    """Main pipeline function"""
    # Track overall time
    start_time = time.time()
    
    # Set timeout handler - cross-platform (threading.Timer works on Windows and Unix)
    timeout_timer = threading.Timer(TIMEOUT_SECONDS, timeout_handler)
    timeout_timer.daemon = True
    timeout_timer.start()
    
    if len(sys.argv) < 2:
        print("Usage: python3 pipeline.py <url> <user_id> [max_products]")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # VALIDATE USER_ID - BẮT BUỘC PHẢI CÓ
    if len(sys.argv) <= 2:
        print("❌ Thiếu user_id! Cần phải đăng nhập mới được crawl.")
        print("Usage: python3 pipeline.py <url> <user_id> [max_products]")
        sys.exit(1)
    
    user_id = sys.argv[2]
    max_products = int(sys.argv[3]) if len(sys.argv) > 3 else MAX_PRODUCTS
    
    # Verify user_id format
    try:
        import uuid as uuid_lib
        user_uuid = uuid_lib.UUID(user_id)
    except (ValueError, AttributeError):
        print(f"❌ user_id không hợp lệ: {user_id}")
        print("   user_id phải là UUID hợp lệ (ví dụ: 1efe122f-22fd-4b54-b934-2219531e8914)")
        sys.exit(1)
    
    # Verify user exists in database
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        
        # Add parent directory to path
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from models.user import UserTable
        from models.ai_personality import AIPersonalityTable
        
        # Database config (hardcoded - same as DatabaseManager)
        DB_HOST = 'localhost'
        DB_PORT = 5431
        DB_USER = 'postgres'
        DB_PASSWORD = 'mypassword'
        DB_NAME = 'chatbot'
        
        conn_str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(conn_str)
        
        with Session(engine) as session:
            user = session.query(UserTable).filter(UserTable.id == user_uuid).first()
            
            if not user:
                print(f"❌ User {user_id} không tồn tại trong database!")
                print("   Vui lòng đăng nhập trước khi crawl.")
                sys.exit(1)
            
            print(f"✅ User verified: {user.full_name} ({user.email})\n")
    except Exception as e:
        print(f"❌ Lỗi xác thực user: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    try:
        from crawl import SimpleSitemapCrawler
    except ImportError as e:
        print(f"❌ Không tìm thấy module crawl.py: {e}")
        return
    
    print(f"  🚀 Target: {url}")
    print(f"  📦 Max Products: {max_products}")
    print(f"  👤 User ID: {user_id}")
    print(f"  ⏱️  Timeout: {TIMEOUT_SECONDS}s\n")
    
    sitemap_start = time.time()
    try:
        crawler = SimpleSitemapCrawler(url, ai_provider=AI_PROVIDER)
        
        # Get all URLs from sitemap with retry
        print("  ⏳ Lấy URLs từ sitemap...\n")
        all_urls = []
        max_retries = 2
        for attempt in range(max_retries):
            try:
                all_urls = crawler.get_sitemap_urls()
                if all_urls:
                    break
                elif attempt < max_retries - 1:
                    print(f"  ⚠️  Retry {attempt + 1}/{max_retries}...")
                    time.sleep(2)
            except Exception as e:
                print(f"  ⚠️  Error on retry {attempt + 1}: {str(e)[:50]}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2)
        
        if not all_urls:
            print("❌ Không tìm thấy URLs từ sitemap sau thử!")
            return
        
        sitemap_time = time.time() - sitemap_start
        print(f"  ✅ Tìm thấy {len(all_urls)} URLs (⏱️ {sitemap_time:.1f}s)\n")
        
        # Extract product data using multi-threading
        extract_start = time.time()
        products = extract_products_threaded(crawler, all_urls, max_products, NUM_THREADS)
        extract_time = time.time() - extract_start
        
        print(f"  ⏱️  Extract time: {extract_time:.1f}s\n")
        
    except Exception as e:
        print(f"❌ Crawling error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Import to database
    print("📍 BƯỚC 3: Import vào PostgreSQL\n")
    db_start = time.time()
    
    try:
        from db_manager import DatabaseManager
        from psycopg2.extras import execute_values
        
        print("  ✅ Connecting to database...")
        
        db = DatabaseManager()
        if not db.connect():
            print("❌ Không thể kết nối database!")
            return
        
        db.init_schema()
        print("  ✅ Database schema ready\n")
        
        # CLEANUP: Xóa data + embeddings cũ của user
        cleanup_user_old_data(user_id, db)
        
        # Add website
        domain = urlparse(url).netloc
        website_name = domain.replace('_', ' ').title()
        
        print(f"  🌐 Website: {website_name}")
        print(f"     Domain: {domain}")
        print(f"     Products: {len(products)}\n")
        
        website_id = db.add_website(website_name, url)
        
        if not website_id:
            print("❌ Không thể thêm website!")
            db.close()
            return
        
        # Update user's website_name
        if user_id:
            db.update_user_website_name(user_id, website_name)
        
        # Prepare data for batch insert
        print("  ⏳ Importing products...\n")
        
        # Remove duplicates by URL (keep first occurrence)
        seen_urls = set()
        unique_products = []
        duplicates_in_batch = 0
        
        for product in products:
            product_url = product.get('url', '').strip()
            if not product_url:
                continue
            if product_url in seen_urls:
                duplicates_in_batch += 1
                continue
            seen_urls.add(product_url)
            unique_products.append(product)
        
        if duplicates_in_batch > 0:
            print(f"  ⚠️  Bỏ qua {duplicates_in_batch} duplicate URLs\n")
        
        # Insert to database - batch by batch with progress
        total_inserted = 0
        batch_num = 0
        
        for i in range(0, len(unique_products), BATCH_SIZE):
            batch_num += 1
            batch_products = unique_products[i:i+BATCH_SIZE]
            products_data = []
            
            for product in batch_products:
                images = product.get('images', [])
                if not isinstance(images, list):
                    images = []
                # Convert to JSON string for PostgreSQL
                images_json = json.dumps(images) if images else '[]'
                
                price = product.get('price') or 0
                try:
                    price = float(price)
                    if price > 1e15 or price < 0:
                        price = 0
                    price = int(round(price))  # Làm tròn thành số nguyên
                except:
                    price = 0
                
                original_price = product.get('original_price') or 0
                try:
                    original_price = float(original_price)
                    if original_price > 1e15 or original_price < 0:
                        original_price = 0
                    original_price = int(round(original_price))  # Làm tròn thành số nguyên
                except:
                    original_price = 0
                
                products_data.append((
                    str(uuid.uuid4()),  # Generate UUID for id
                    website_id,
                    website_name,
                    product.get('url', ''),
                    product.get('title', ''),
                    price,
                    original_price,
                    product.get('currency', 'VND'),
                    product.get('sku', ''),
                    product.get('brand', ''),
                    product.get('category', ''),
                    product.get('description', ''),
                    product.get('availability', ''),
                    images_json,
                    user_id  # NEW: user_id
                ))
            
            # Insert batch to database
            try:
                with db.conn.cursor() as cur:
                    execute_values(cur, """
                        INSERT INTO products
                        (id, website_id, website_name, url, title, price, original_price, currency, sku, brand, category, description, availability, images, user_id)
                        VALUES %s
                        ON CONFLICT (url) DO UPDATE SET
                            title = EXCLUDED.title,
                            price = EXCLUDED.price,
                            brand = EXCLUDED.brand,
                            category = EXCLUDED.category,
                            description = EXCLUDED.description,
                            availability = EXCLUDED.availability,
                            images = EXCLUDED.images,
                            user_id = EXCLUDED.user_id,
                            updated_at = CURRENT_TIMESTAMP;
                    """, products_data, page_size=100)
                    
                    db.conn.commit()
                
                total_inserted += len(products_data)
                print(f"  ✓ Batch {batch_num}: {len(products_data)} products inserted (Total: {total_inserted}/{len(unique_products)})")
            except Exception as e:
                print(f"  ❌ Batch {batch_num} failed: {e}")
                db.conn.rollback()
                continue
        
        print()
        
        # Check results
        with db.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM products WHERE website_id = %s", (website_id,))
            total_in_db = cur.fetchone()[0]
        
        print(f"  ✅ Inserted/Updated {total_inserted} products (Total in DB: {total_in_db})\n")
        
        # Fetch products từ DB để lấy id cho embedding
        print("  ⏳ Fetching product IDs từ DB cho embedding...\n")
        with db.conn.cursor() as cur:
            cur.execute("""
                SELECT id, url, title, description 
                FROM products 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (user_id, len(unique_products)))
            db_products = cur.fetchall()
        
        # Map products by URL để thêm id
        products_with_id = []
        for row in db_products:
            product_id, url, title, description = row
            products_with_id.append({
                'id': str(product_id),  # Convert UUID to string
                'url': url,
                'title': title,
                'description': description
            })
        
        print(f"  ✅ Fetched {len(products_with_id)} products from DB\n")
        
        # Count products with price and images
        products_with_price = sum(1 for p in unique_products if p.get('price') and float(p.get('price', 0)) > 0)
        products_with_images = sum(1 for p in unique_products if p.get('images') and len(p.get('images', [])) > 0)
        
        # Calculate total time
        total_time = time.time() - start_time
        duration_seconds = int(total_time)
        
        # Log crawl with detailed stats (disabled - simplified schema)
        # db.log_crawl(website_id, len(all_urls), len(unique_products), duration_seconds, 'success', 
        #              products_with_price=products_with_price, products_with_images=products_with_images)
        
        # Show statistics
        print("📊 THỐNG KÊ:")
        print("-" * 70)
        stats = db.get_stats(website_id)
        
        if stats:
            print(f"  Website: {stats.get('name', 'Unknown')}")
            print(f"  Bảng: public.products")
            print(f"  Total Products: {stats.get('total_products', 0)}")
            print(f"  With Price: {stats.get('products_with_price', 0)}")
            print(f"  With Images: {stats.get('products_with_images', 0)}")
            print(f"  With SKU: {stats.get('products_with_sku', 0)}")
            if stats.get('avg_price'):
                print(f"  Avg Price: {stats['avg_price']:,.0f} VND")
            if stats.get('min_price'):
                print(f"  Min Price: {stats['min_price']:,.0f} VND")
            if stats.get('max_price'):
                print(f"  Max Price: {stats['max_price']:,.0f} VND")
        
        db.close()
        
        # Step 3: Generate embeddings for products (dùng products_with_id từ DB)
        embedding_count = generate_embeddings_for_products(products_with_id, user_id)
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return 0
    
    db_time = time.time() - db_start
    
    print("\n" + "="*70)
    print("✅ PIPELINE HOÀN THÀNH!")
    print("="*70)
    print(f"\n⏱️  THỐNG KÊ THỜI GIAN:")
    print(f"  Sitemap crawl: {sitemap_time:.1f}s")
    print(f"  Product extract: {extract_time:.1f}s ({len(products)} products)")
    print(f"  Database import: {db_time:.1f}s")
    print(f"  ───────────────────")
    print(f"  📊 TỔNG: {total_time:.1f}s ({timedelta(seconds=int(total_time))})")
    
    # Speed stats
    products_per_sec = len(products) / extract_time if extract_time > 0 else 0
    seconds_per_product = extract_time / len(products) if len(products) > 0 else 0
    print(f"\n⚡ TỐC ĐỘ:")
    print(f"  {products_per_sec:.1f} products/giây")
    print(f"  {seconds_per_product:.2f}s/product")
    print(f"  (~{int(products_per_sec * 3600)} products/giờ)\n")
    
    return embedding_count


def generate_embeddings_for_products(products, user_id):
    """Generate embeddings cho tất cả products sử dụng description - chỉ gọi hàm từ 2 file embedding"""
    print("📍 BƯỚC 4: Tạo Embeddings\n")
    print(f"  🔍 DEBUG: Received {len(products)} products")
    print(f"  🔍 DEBUG: User ID: {user_id}")
    
    try:
        # Add parent directory to path để import embedding module
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from embedding.generate_embeddings import generate_embedding
        from embedding.insert_qdrant import ensure_product_collection_exists, insert_products_to_qdrant_product
        print(f"  ✅ Import embedding modules thành công")
    except ImportError as e:
        print(f"⚠️  Import error: {str(e)[:100]}")
        print("   Bỏ qua bước embedding")
        return 0
    
    # Ensure Qdrant collection exists for this user
    collection_name = "products"  # Dùng collection chung
    print(f"  ⏳ Đảm bảo collection '{collection_name}' tồn tại trong Qdrant...\n")
    try:
        ensure_product_collection_exists(collection_name)
    except Exception as e:
        print(f"  ❌ Lỗi tạo collection: {str(e)[:100]}")
        return 0
    
    # Generate embeddings for products with description
    embedding_start = time.time()
    products_with_embedding = 0
    products_failed = 0
    
    print(f"  ⏳ Tạo embeddings cho {len(products)} products...\n")
    
    for i, product in enumerate(products, 1):
        try:
            # Only embed if description exists
            description = product.get('description', '').strip()
            
            if i <= 3:  # Debug first 3 products
                print(f"  🔍 DEBUG Product {i}:")
                print(f"     - ID: {product.get('id', 'N/A')}")
                print(f"     - Title: {product.get('title', 'N/A')[:50]}")
                print(f"     - Description length: {len(description)}")
            
            if not description:
                if i <= 3:
                    print(f"     ⚠️ SKIP: No description")
                continue
            
            # Generate embedding từ description - gọi hàm từ generate_embeddings.py
            if i <= 3:
                print(f"     ⏳ Generating embedding...")
            
            embedding = generate_embedding(description)
            
            if i <= 3:
                print(f"     ✅ Embedding generated: {len(embedding) if embedding else 0} dimensions")
            
            if embedding is not None and len(embedding) > 0:  # Check if embedding is valid
                # Prepare payload - product id là UUID string từ DB
                # insert_qdrant.py sẽ tự xử lý để convert thành Qdrant-compatible format
                payload = {
                    "id": product.get('id', ''),  # Add product UUID
                    "title": product.get('title', ''),
                    "description": description[:500]  # Limit to 500 chars for payload
                }
                
                # Insert to Qdrant - gọi hàm từ insert_qdrant.py
                if i <= 3:
                    print(f"     ⏳ Inserting to Qdrant...")
                
                insert_products_to_qdrant_product(embedding, payload, user_id, collection_name)
                products_with_embedding += 1
                
                if i <= 3:
                    print(f"     ✅ Inserted to Qdrant successfully")
            else:
                print(f"  ⚠️  Product {i}: embedding is empty or None")
            
            # Progress every 10 products
            if i % 10 == 0:
                print(f"  [{i}/{len(products)}] {products_with_embedding} embeddings created")
        
        except Exception as e:
            products_failed += 1
            print(f"  ❌ Lỗi embedding product {i}: {str(e)}")
            import traceback
            if i <= 3:  # Print full traceback for first 3 errors
                traceback.print_exc()
            continue
    
    embedding_time = time.time() - embedding_start
    
    print(f"\n  ✅ Tạo xong {products_with_embedding} embeddings (⏱️ {embedding_time:.1f}s)")
    if products_failed > 0:
        print(f"  ⚠️  {products_failed} products embedding failed")
    
    return products_with_embedding


def import_from_file(file_path: str, user_id: str, website_name: str = None) -> int:
    """Import products from uploaded file"""
    print(f"\n{'='*70}")
    print(f"📁 IMPORT FROM FILE: {os.path.basename(file_path)}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    # Parse file
    print("📍 BƯỚC 1: Parse File\n")
    parse_start = time.time()
    
    try:
        # Import FileParser từ utils
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.file_parser import FileParser
        
        products = FileParser.parse_file(file_path)
        parse_time = time.time() - parse_start
        
        print(f"  ✅ Parsed {len(products)} products from file (⏱️ {parse_time:.1f}s)\n")
    except Exception as e:
        print(f"  ❌ Parse error: {e}")
        import traceback
        traceback.print_exc()
        return 0
    
    if not products:
        print("  ❌ No products found in file")
        return 0
    
    # Import to database
    print("📍 BƯỚC 2: Import vào PostgreSQL\n")
    db_start = time.time()
    
    try:
        from db_manager import DatabaseManager
        from psycopg2.extras import execute_values
        
        print("  ✅ Connecting to database...")
        
        db = DatabaseManager()
        if not db.connect():
            print("❌ Không thể kết nối database!")
            return 0
        
        db.init_schema()
        print("  ✅ Database schema ready\n")
        
        # CLEANUP: Xóa data + embeddings cũ của user
        cleanup_user_old_data(user_id, db)
        
        # Use filename or provided website_name
        if not website_name:
            website_name = os.path.splitext(os.path.basename(file_path))[0].replace('_', ' ').title()
        
        # Add website (use file:// prefix to distinguish from web crawl)
        website_url = f"file://{os.path.basename(file_path)}"
        website_id = db.add_website(website_name, website_url)
        
        if not website_id:
            print("❌ Không thể thêm website!")
            db.close()
            return 0
        
        # Update user's website_name
        if user_id:
            db.update_user_website_name(user_id, website_name)
        
        print(f"  🌐 Website: {website_name}")
        print(f"     Source: {os.path.basename(file_path)}")
        print(f"     Products: {len(products)}\n")
        
        # Prepare data for batch insert
        print("  ⏳ Importing products...\n")
        
        # Remove duplicates by title (since file might not have URLs)
        seen_keys = set()
        unique_products = []
        
        for product in products:
            # Use URL if available, otherwise use title
            key = product.get('url', '').strip() or product.get('title', '').strip()
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            unique_products.append(product)
        
        # Insert to database - batch by batch
        total_inserted = 0
        batch_num = 0
        
        for i in range(0, len(unique_products), BATCH_SIZE):
            batch_num += 1
            batch_products = unique_products[i:i+BATCH_SIZE]
            products_data = []
            
            for product in batch_products:
                images = product.get('images', [])
                if not isinstance(images, list):
                    images = []
                images_json = json.dumps(images) if images else '[]'
                
                price = product.get('price') or 0
                try:
                    price = float(price)
                    if price > 1e15 or price < 0:
                        price = 0
                    price = int(round(price))  # Làm tròn thành số nguyên
                except:
                    price = 0
                
                original_price = product.get('original_price') or 0
                try:
                    original_price = float(original_price)
                    if original_price > 1e15 or original_price < 0:
                        original_price = 0
                    original_price = int(round(original_price))  # Làm tròn thành số nguyên
                except:
                    original_price = 0
                
                # Generate URL if missing (use file:// + title slug)
                url = product.get('url', '').strip()
                if not url:
                    import re
                    title_slug = re.sub(r'[^a-z0-9]+', '-', product.get('title', '').lower()).strip('-')
                    url = f"file://{website_name.lower().replace(' ', '-')}/{title_slug}"
                
                products_data.append((
                    website_id,
                    website_name,
                    url,
                    product.get('title', ''),
                    price,
                    original_price,
                    product.get('currency', 'VND'),
                    product.get('sku', ''),
                    product.get('brand', ''),
                    product.get('category', ''),
                    product.get('description', ''),
                    product.get('availability', ''),
                    images_json,
                    user_id  # NEW: user_id
                ))
            
            # Insert batch to database
            try:
                with db.conn.cursor() as cur:
                    execute_values(cur, """
                        INSERT INTO products
                        (website_id, website_name, url, title, price, original_price, currency, sku, brand, category, description, availability, images, user_id)
                        VALUES %s
                        ON CONFLICT (url) DO UPDATE SET
                            title = EXCLUDED.title,
                            price = EXCLUDED.price,
                            brand = EXCLUDED.brand,
                            category = EXCLUDED.category,
                            description = EXCLUDED.description,
                            availability = EXCLUDED.availability,
                            images = EXCLUDED.images,
                            user_id = EXCLUDED.user_id,
                            updated_at = CURRENT_TIMESTAMP;
                    """, products_data, page_size=100)
                    
                    db.conn.commit()
                
                total_inserted += len(products_data)
                print(f"  ✓ Batch {batch_num}: {len(products_data)} products inserted (Total: {total_inserted}/{len(unique_products)})")
            except Exception as e:
                print(f"  ❌ Batch {batch_num} failed: {e}")
                db.conn.rollback()
                continue
        
        print()
        
        # Show statistics TRƯỚC KHI fetch products
        print("📊 THỐNG KÊ:")
        print("-" * 70)
        stats = db.get_stats(website_id)
        
        if stats:
            print(f"  Website: {stats.get('name', 'Unknown')}")
            print(f"  Bảng: public.products")
            print(f"  Total Products: {stats.get('total_products', 0)}")
            print(f"  With Price: {stats.get('products_with_price', 0)}")
            print(f"  With Images: {stats.get('products_with_images', 0)}")
        
        # Fetch products từ DB để lấy id cho embedding
        print("\n  ⏳ Fetching product IDs từ DB cho embedding...\n")
        print(f"  🔍 DEBUG: user_id = {user_id}")
        print(f"  🔍 DEBUG: Expecting {len(unique_products)} products\n")
        
        with db.conn.cursor() as cur:
            cur.execute("""
                SELECT id, url, title, description 
                FROM products 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (user_id, len(unique_products)))
            db_products = cur.fetchall()
            
            print(f"  🔍 DEBUG: Query returned {len(db_products)} rows")
        
        # Map products by URL để thêm id
        products_with_id = []
        for row in db_products:
            product_id, url, title, description = row
            products_with_id.append({
                'id': str(product_id),  # Convert UUID to string
                'url': url,
                'title': title,
                'description': description
            })
        
        print(f"  ✅ Fetched {len(products_with_id)} products from DB\n")
        
        db.close()
        
        # Step 3: Generate embeddings for products (dùng products_with_id từ DB)
        print("\n" + "🔥 BẮT ĐẦU EMBEDDING PROCESS...", flush=True)
        print(f"🔥 Sẽ tạo embedding cho {len(products_with_id)} products", flush=True)
        print(f"🔥 User ID: {user_id}", flush=True)
        
        embedding_count = generate_embeddings_for_products(products_with_id, user_id)
        
        print(f"🔥 EMBEDDING HOÀN THÀNH: {embedding_count} embeddings", flush=True)
        
        total_time = time.time() - start_time
        
        print("\n" + "="*70)
        print("✅ FILE IMPORT HOÀN THÀNH!")
        print("="*70)
        print(f"  📊 Products inserted: {total_inserted}")
        print(f"  📊 Embeddings created: {embedding_count}")
        print(f"  📊 TỔNG: {total_time:.1f}s ({timedelta(seconds=int(total_time))})\n")
        
        # Return number of products inserted (not embeddings)
        return total_inserted
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def import_text_document(file_path: str, user_id: str, document_name: str = None) -> int:
    """
    Import text document for chatbot knowledge base
    Chunks text and stores in separate Qdrant collection: documents
    NOTE: 1 user chỉ lưu 1 document - data cũ sẽ bị xóa khi upload mới
    """
    print(f"\n{'='*70}")
    print(f"📄 IMPORT TEXT DOCUMENT: {os.path.basename(file_path)}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    # CLEANUP: Xóa documents cũ của user này
    print("📍 BƯỚC 0: Cleanup old documents\n")
    
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        qdrant = QdrantClient(url="http://localhost:6334")
        collection_name = "documents"
        
        # Check if collection exists
        collections = qdrant.get_collections().collections
        if any(c.name == collection_name for c in collections):
            # Delete old documents của user
            try:
                # Count existing documents
                scroll_result = qdrant.scroll(
                    collection_name=collection_name,
                    scroll_filter=Filter(
                        must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                    ),
                    limit=10000
                )
                old_count = len(scroll_result[0])
                
                if old_count > 0:
                    print(f"  🗑️  Xóa {old_count} document chunks cũ từ Qdrant...")
                    qdrant.delete(
                        collection_name=collection_name,
                        points_selector=Filter(
                            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                        )
                    )
                    print(f"  ✅ Đã xóa {old_count} chunks\n")
                else:
                    print(f"  ℹ️  Không có document chunks cũ\n")
            except Exception as e:
                print(f"  ⚠️  Warning khi cleanup: {e}\n")
        else:
            print(f"  ℹ️  Collection chưa tồn tại, sẽ tạo mới\n")
    
    except Exception as e:
        print(f"  ⚠️  Warning: {e}\n")
    
    # Parse file as text
    print("📍 BƯỚC 1: Parse Text Document\n")
    parse_start = time.time()
    
    try:
        # Import TextDocumentParser từ utils
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.file_parser import FileParser
        
        doc_data = FileParser.parse_file_as_text(file_path)
        parse_time = time.time() - parse_start
        
        chunks = doc_data.get('chunks', [])
        print(f"  ✅ Parsed document into {len(chunks)} chunks (⏱️ {parse_time:.1f}s)")
        print(f"     Filename: {doc_data.get('filename', 'N/A')}")
        print(f"     Content length: {len(doc_data.get('content', ''))} characters\n")
        
    except Exception as e:
        print(f"  ❌ Parse error: {e}")
        import traceback
        traceback.print_exc()
        return 0
    
    if not chunks:
        print("  ❌ No text chunks generated")
        return 0
    
    # Generate embeddings and store in Qdrant
    print("📍 BƯỚC 2: Generate Embeddings & Store in Qdrant\n")
    embedding_start = time.time()
    
    try:
        # Import embedding generator
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from embedding.generate_embeddings import generate_embedding
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
        import uuid
        
        # Initialize Qdrant client (port 6334)
        qdrant = QdrantClient(url="http://localhost:6334")
        collection_name = "documents"  # Collection chung cho tất cả documents
        
        # Create collection if not exists 
        # Gemini text-embedding-004 dimension = 768
        try:
            collections = qdrant.get_collections().collections
            if not any(c.name == collection_name for c in collections):
                qdrant.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
                )
                print(f"  ✅ Created Qdrant collection: {collection_name}\n")
            else:
                print(f"  ✅ Using existing collection: {collection_name}\n")
        except Exception as e:
            print(f"  ⚠️ Collection check/create warning: {e}")
        
        # Prepare chunks for embedding
        if not document_name:
            document_name = doc_data.get('filename', os.path.basename(file_path))
        
        print(f"  ⏳ Generating embeddings for {len(chunks)} chunks...")
        
        # Generate embeddings for all chunks
        texts_for_embedding = [chunk['text'] for chunk in chunks]
        
        embeddings = []
        for text in texts_for_embedding:
            emb = generate_embedding(text)
            if emb:
                embeddings.append(emb)
        
        if not embeddings or len(embeddings) != len(chunks):
            print(f"  ❌ Embedding generation failed or count mismatch")
            return 0
        
        print(f"  ✅ Generated {len(embeddings)} embeddings\n")
        
        # Insert to Qdrant
        print(f"  ⏳ Inserting to Qdrant...")
        
        points = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            
            payload = {
                'user_id': user_id,
                'document_name': document_name,
                'chunk_id': chunk['chunk_id'],
                'chunk_index': idx,
                'total_chunks': len(chunks),
                'text': chunk['text'],
                'char_count': chunk['char_count'],
                'created_at': datetime.now().isoformat()
            }
            
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            ))
        
        # Batch upload to Qdrant
        qdrant.upsert(
            collection_name=collection_name,
            points=points
        )
        
        embedding_time = time.time() - embedding_start
        print(f"  ✅ Inserted {len(points)} vectors to Qdrant (⏱️ {embedding_time:.1f}s)\n")
        
        # Show statistics
        print("📊 THỐNG KÊ:")
        print("-" * 70)
        print(f"  Document: {document_name}")
        print(f"  Collection: {collection_name}")
        print(f"  Total Chunks: {len(chunks)}")
        print(f"  Total Vectors: {len(points)}")
        print(f"  Vector Dimension: 768")
        
        total_time = time.time() - start_time
        
        print("\n" + "="*70)
        print("✅ TEXT DOCUMENT IMPORT HOÀN THÀNH!")
        print("="*70)
        print(f"  📊 TỔNG: {total_time:.1f}s ({timedelta(seconds=int(total_time))})\n")
        
        return len(points)
        
    except Exception as e:
        print(f"❌ Embedding/Qdrant error: {e}")
        import traceback
        traceback.print_exc()
        return 0
        traceback.print_exc()
        return 0


if __name__ == "__main__":
    try:
        main()
    finally:
        # If main() started a timer, try to cancel it to avoid firing after normal exit.
        try:
            timeout_timer.cancel()
        except Exception:
            # If timeout_timer isn't defined (e.g., imported elsewhere) ignore
            pass
