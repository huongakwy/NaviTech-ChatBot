#!/usr/bin/env python3
"""
📊 Xem lịch sử crawl từ database
"""

import sys
from datetime import datetime
from db_manager import DatabaseManager

def format_duration(seconds):
    """Format duration thành human-readable"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds//60}m {seconds%60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def print_crawl_history():
    """In lịch sử crawl"""
    db = DatabaseManager()
    
    if not db.connect():
        print("❌ Không thể kết nối database")
        return
    
    print("\n" + "="*100)
    print("📊 LỊCH SỬ CRAWL")
    print("="*100 + "\n")
    
    # Get all history
    history = db.get_crawl_history(limit=20)
    
    if not history:
        print("❌ Không có lịch sử crawl\n")
        db.close()
        return
    
    # Print header
    print(f"{'ID':<5} {'Website':<20} {'Time':<19} {'URLs':<8} {'Products':<10} {'Price':<8} {'Images':<8} {'Duration':<12} {'Status':<10}")
    print("-" * 100)
    
    # Print each record
    for record in history:
        log_id, website_id, website_name, total_urls, products_found, products_with_price, products_with_images, duration, status, started_at, completed_at = record
        
        # Format timestamp
        if started_at:
            time_str = started_at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            time_str = "N/A"
        
        # Format duration
        if duration:
            duration_str = format_duration(duration)
        else:
            duration_str = "N/A"
        
        # Format status with emoji
        status_emoji = "✅" if status == 'success' else "❌"
        
        print(f"{log_id:<5} {website_name:<20} {time_str:<19} {total_urls:<8} {products_found:<10} {products_with_price or 0:<8} {products_with_images or 0:<8} {duration_str:<12} {status_emoji} {status:<8}")
    
    print("\n" + "="*100)
    
    # Print summary stats
    stats = db.get_crawl_stats_summary()
    if stats:
        print("📈 THỐNG KÊ TỔNG HỢP:")
        print(f"  Total Crawls: {stats['total_crawls']}")
        print(f"  Total Products: {stats['total_products']:,}")
        print(f"  Avg Duration: {format_duration(int(stats['avg_duration']))}")
        print(f"  Total Time: {format_duration(stats['total_duration'])}")
        print(f"  Success Rate: {stats['success_rate']:.1f}%")
    
    print("=" * 100 + "\n")
    
    db.close()

def print_website_history(website_name):
    """In lịch sử crawl cho một website cụ thể"""
    db = DatabaseManager()
    
    if not db.connect():
        print("❌ Không thể kết nối database")
        return
    
    # Get website ID
    try:
        with db.conn.cursor() as cur:
            cur.execute("SELECT id FROM crawler.websites WHERE name ILIKE %s", (website_name,))
            result = cur.fetchone()
            if not result:
                print(f"❌ Không tìm thấy website: {website_name}")
                db.close()
                return
            website_id = result[0]
    except Exception as e:
        print(f"❌ Error: {e}")
        db.close()
        return
    
    print("\n" + "="*100)
    print(f"📊 LỊCH SỬ CRAWL: {website_name}")
    print("="*100 + "\n")
    
    # Get history for this website
    history = db.get_crawl_history(website_id, limit=20)
    
    if not history:
        print(f"❌ Không có lịch sử crawl cho {website_name}\n")
        db.close()
        return
    
    # Print header
    print(f"{'ID':<5} {'Time':<19} {'URLs':<8} {'Products':<10} {'Price':<8} {'Images':<8} {'Duration':<12} {'Status':<10}")
    print("-" * 100)
    
    # Print each record
    for record in history:
        log_id, website_id, name, total_urls, products_found, products_with_price, products_with_images, duration, status, started_at, completed_at = record
        
        # Format timestamp
        if started_at:
            time_str = started_at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            time_str = "N/A"
        
        # Format duration
        if duration:
            duration_str = format_duration(duration)
        else:
            duration_str = "N/A"
        
        # Format status with emoji
        status_emoji = "✅" if status == 'success' else "❌"
        
        print(f"{log_id:<5} {time_str:<19} {total_urls:<8} {products_found:<10} {products_with_price or 0:<8} {products_with_images or 0:<8} {duration_str:<12} {status_emoji} {status:<8}")
    
    print("\n" + "="*100)
    print()
    
    db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # View history for specific website
        website_name = sys.argv[1]
        print_website_history(website_name)
    else:
        # View all history
        print_crawl_history()
