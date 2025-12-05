from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict
import sys
import os
import threading
from datetime import datetime
import asyncio

# Add AI crawl to path để import pipeline
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'AI crawl'))

router = APIRouter(
    prefix="/crawler",
    tags=["crawler"]
)


class CrawlRequest(BaseModel):
    """Request model for crawler"""
    user_id: str  # User ID (UUID)
    url: str  # Website URL to crawl
    website_name: Optional[str] = None  # Tên website (optional)
    max_products: Optional[int] = 10000  # Max products to extract (default: 10000)


class CrawlResponse(BaseModel):
    """Response model for crawler"""
    status: str
    message: str
    url: str
    task_id: str
    timestamp: str
    sitemap_found: Optional[bool] = None
    sitemap_urls_count: Optional[int] = None


class CrawlStatusResponse(BaseModel):
    """Response for task status check"""
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    url: str
    products_count: Optional[int] = None
    error: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None


# Global task tracking
crawl_tasks: Dict[str, Dict] = {}


def run_crawl_background(task_id: str, user_id: str, url: str, website_name: str, max_products: int):
    """Background function to run crawl task"""
    try:
        # Update task status to running
        crawl_tasks[task_id]["status"] = "running"
        
        # Import pipeline
        from pipeline import main as pipeline_main
        
        # Prepare argv for pipeline
        # Format: python3 pipeline.py <url> <user_id> [max_products] [website_name]
        original_argv = sys.argv.copy()
        sys.argv = [
            sys.argv[0],
            url,
            user_id,
            str(max_products),
            website_name or ""
        ]
        
        try:
            # Run pipeline
            products_count = pipeline_main()
            
            # Update task status to completed
            crawl_tasks[task_id].update({
                "status": "completed",
                "products_count": products_count or 0,
                "completed_at": datetime.now().isoformat()
            })
            
        except Exception as e:
            # Update task status to failed
            crawl_tasks[task_id].update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            })
        finally:
            sys.argv[:] = original_argv
            
    except Exception as e:
        crawl_tasks[task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })


@router.post("/start", response_model=CrawlResponse)
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks) -> CrawlResponse:
    """
    🚀 Start crawling a website (ASYNC - returns immediately after finding sitemap)
    
    - **user_id**: User ID (UUID) - dùng để phân biệt data của từng user
    - **url**: Website URL to crawl (e.g., https://mypc.vn)
    - **website_name**: Tên website (optional, dùng URL nếu không có)
    - **max_products**: Max products to crawl (default: 10000)
    
    ⚡ Response NGAY SAU KHI tìm thấy sitemap
    📦 Crawl chạy background, check status bằng GET /crawler/status/{task_id}
    """
    try:
        # Validate URL
        if not request.url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
        
        # Generate task ID
        task_id = f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Check sitemap quickly
        try:
            from pipeline import find_sitemap
            
            print(f"🔍 Checking sitemap for {request.url}...")
            sitemap_urls = find_sitemap(request.url)
            sitemap_found = len(sitemap_urls) > 0
            sitemap_count = len(sitemap_urls)
            
            print(f"✅ Found {sitemap_count} sitemap URLs")
            
        except Exception as e:
            print(f"⚠️ Sitemap check error: {e}")
            sitemap_found = False
            sitemap_count = 0
        
        # Create task record
        crawl_tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "url": request.url,
            "user_id": request.user_id,
            "website_name": request.website_name or request.url,
            "products_count": None,
            "error": None,
            "started_at": datetime.now().isoformat(),
            "completed_at": None
        }
        
        # Start background crawl
        background_tasks.add_task(
            run_crawl_background,
            task_id=task_id,
            user_id=request.user_id,
            url=request.url,
            website_name=request.website_name or request.url,
            max_products=request.max_products
        )
        
        # Return immediately after sitemap check
        return CrawlResponse(
            status="accepted",
            message=f"Crawl task started. Sitemap {'found' if sitemap_found else 'not found'}. Check /crawler/status/{task_id} for progress.",
            url=request.url,
            task_id=task_id,
            timestamp=datetime.now().isoformat(),
            sitemap_found=sitemap_found,
            sitemap_urls_count=sitemap_count if sitemap_found else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}", response_model=CrawlStatusResponse)
async def get_crawl_status(task_id: str) -> CrawlStatusResponse:
    """
    📊 Check crawl task status
    
    - **task_id**: Task ID returned from /crawler/start
    
    Returns current status: pending, running, completed, or failed
    """
    if task_id not in crawl_tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task = crawl_tasks[task_id]
    
    return CrawlStatusResponse(**task)
