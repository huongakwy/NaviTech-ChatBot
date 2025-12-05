from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from pydantic import BaseModel, HttpUrl
from typing import Optional
import sys
import os
import shutil
from datetime import datetime

# Add AI_crawl to path để import pipeline
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'AI_crawl'))

router = APIRouter(
    prefix="/upload",
    tags=["File Upload"]
)

# Upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ProductUploadResponse(BaseModel):
    """Response model for product file upload"""
    status: str
    message: str
    filename: str
    products_count: int
    timestamp: str
    task_id: str


class DocumentUploadResponse(BaseModel):
    """Response model for document file upload"""
    status: str
    message: str
    filename: str
    chunks_count: int
    timestamp: str
    task_id: str


@router.post("/product", response_model=ProductUploadResponse)
async def upload_product_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),  # Required - no default
    website_name: Optional[str] = Form(None)
) -> ProductUploadResponse:
    """
    Upload file sản phẩm và import vào database + embeddings
    
    **📁 Supported formats:**
    - **Excel**: .xlsx, .xls (với tên cột khớp database)
    - **CSV**: .csv (với tên cột khớp database)
    - **JSON**: .json (với field khớp database)
    - **Word**: .docx (tables tự động parse, hoặc AI extract nếu không có table)
    - **PDF**: .pdf (tables tự động parse, hoặc AI extract nếu không có table)
    
    **📋 Cấu trúc dữ liệu (tên cột/field phải khớp):**
    
    **Bắt buộc:**
    - `url` - Link URL sản phẩm (UNIQUE)
    - `title` hoặc `name` - Tên sản phẩm
    
    **Tùy chọn (NULL nếu không có):**
    - `price`, `giá` - Giá bán
    - `original_price`, `giá gốc` - Giá gốc
    - `currency` - Đơn vị tiền tệ (default: VND)
    - `sku`, `mã sản phẩm` - Mã SKU
    - `brand`, `thương hiệu` - Thương hiệu
    - `category`, `danh mục` - Danh mục
    - `description`, `mô tả` - Mô tả
    - `availability` - Tình trạng
    - `images`, `hình ảnh` - Link ảnh (CSV: phân cách bằng dấu phẩy)
    
    **🤖 AI Extraction:**
    - Nếu file không có table/cấu trúc rõ ràng → tự động dùng Gemini AI extract
    - AI sẽ extract theo đúng schema database
    
    Args:
        - **file**: File upload
        - **user_id**: User ID (UUID) - default: hardcoded
        - **website_name**: Tên website (optional, dùng filename nếu không có)
    
    Returns:
        ProductUploadResponse với products_count sau khi hoàn thành
    """ 
    # Validate file extension
    allowed_extensions = ['.xlsx', '.xls', '.csv', '.json', '.docx', '.pdf']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size (max 50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size / (1024*1024):.1f}MB. Max: 50MB"
        )
    
    # Generate task ID
    task_id = f"product_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    file_path = os.path.join(UPLOAD_DIR, f"{task_id}{file_ext}")
    
    # Save uploaded file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Import product data
    try:
        from AI_crawl.pipeline import import_from_file
        
        products_count = import_from_file(
            file_path=file_path,
            user_id=user_id,
            website_name=website_name
        )
        
        return ProductUploadResponse(
            status="success",
            message=f"Product file uploaded and processed successfully",
            filename=file.filename,
            products_count=products_count or 0,
            timestamp=datetime.now().isoformat(),
            task_id=task_id
        )
        
    except Exception as e:
        # Clean up file on error
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    finally:
        file.file.close()


@router.post("/document", response_model=DocumentUploadResponse)
async def upload_document_file(
    file: UploadFile = File(...),
    user_id: str = Form("b95c2881-387f-4093-b80d-ac83b1dea7a9"),
    document_name: Optional[str] = Form(None)
) -> DocumentUploadResponse:
    """
    Upload văn bản text để chatbot học (policies, FAQs, guides, etc.)
    
    Supported formats:
    - **Text**: .txt
    - **Word**: .docx (text content)
    - **PDF**: .pdf (text content)
    
    Args:
        - **file**: File upload
        - **user_id**: User ID (UUID) - default: hardcoded
        - **document_name**: Tên document (optional, dùng filename nếu không có)
    
    Returns:
        DocumentUploadResponse với chunks_count sau khi hoàn thành
    """ 
    # Validate file extension
    allowed_extensions = ['.txt', '.docx', '.pdf']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size (max 50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size / (1024*1024):.1f}MB. Max: 50MB"
        )
    
    # Generate task ID
    task_id = f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    file_path = os.path.join(UPLOAD_DIR, f"{task_id}{file_ext}")
    
    # Save uploaded file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Import text document
    try:
        from AI_crawl.pipeline import import_text_document
        
        chunks_count = import_text_document(
            file_path=file_path,
            user_id=user_id,
            document_name=document_name or file.filename
        )
        
        return DocumentUploadResponse(
            status="success",
            message=f"Text document uploaded and processed successfully",
            filename=file.filename,
            chunks_count=chunks_count or 0,
            timestamp=datetime.now().isoformat(),
            task_id=task_id
        )
        
    except Exception as e:
        # Clean up file on error
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    finally:
        file.file.close()


class GoogleSheetsUploadRequest(BaseModel):
    """Request model for Google Sheets link upload"""
    sheet_url: str
    user_id: str = "b95c2881-387f-4093-b80d-ac83b1dea7a9"
    website_name: Optional[str] = None


@router.post("/product/google-sheets", response_model=ProductUploadResponse)
async def upload_product_from_google_sheets(
    request: GoogleSheetsUploadRequest
) -> ProductUploadResponse:
    """
    Import sản phẩm từ Google Sheets link
    
    **📋 Cấu trúc bảng Google Sheets (các tên cột phải khớp với database):**
    
    **Cột bắt buộc:**
    - `url` - Link URL của sản phẩm (UNIQUE, BẮT BUỘC)
    - `title` hoặc `name` - Tên sản phẩm (BẮT BUỘC)
    
    **Cột tùy chọn (để trống = NULL):**
    - `price` hoặc `giá` - Giá bán (số, VD: 100000)
    - `original_price` hoặc `giá gốc` - Giá gốc (số)
    - `currency` hoặc `đơn vị` - Đơn vị tiền tệ (VD: VND, USD) - mặc định: VND
    - `sku` hoặc `mã sản phẩm` - Mã SKU
    - `brand` hoặc `thương hiệu` - Thương hiệu
    - `category` hoặc `danh mục` - Danh mục sản phẩm
    - `description` hoặc `mô tả` - Mô tả chi tiết
    - `availability` - Tình trạng (Còn hàng/Hết hàng)
    - `images` hoặc `hình ảnh` - Link ảnh (nhiều ảnh cách nhau bằng dấu phẩy)
    
    **Lưu ý:**
    - Tên cột không phân biệt hoa thường
    - Tên cột có thể là tiếng Anh hoặc tiếng Việt (có dấu/không dấu)
    - Hệ thống tự động map tên cột với database schema
    
    **🔗 Cách lấy link Google Sheets:**
    1. Mở Google Sheets
    2. File → Share → Get link
    3. Set quyền: "Anyone with the link can view"
    4. Copy link dạng: `https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit`
    
    Args:
        - **sheet_url**: Link Google Sheets (public)
        - **user_id**: User ID (UUID)
        - **website_name**: Tên website (optional)
    
    Returns:
        ProductUploadResponse với products_count sau khi hoàn thành
    """
    try:
        # Validate Google Sheets URL
        if "docs.google.com/spreadsheets" not in request.sheet_url:
            raise HTTPException(
                status_code=400,
                detail="Invalid Google Sheets URL. Must be from docs.google.com/spreadsheets"
            )
        
        # Extract sheet ID from URL
        import re
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', request.sheet_url)
        if not match:
            raise HTTPException(
                status_code=400,
                detail="Cannot extract Sheet ID from URL. Please check the link format."
            )
        
        sheet_id = match.group(1)
        
        # Generate task ID
        task_id = f"gsheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Convert to CSV export URL
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        
        # Download CSV to temp file
        import requests
        response = requests.get(csv_url)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot access Google Sheets. Please ensure the sheet is public (Anyone with link can view). Status: {response.status_code}"
            )
        
        # Save to temp CSV file
        file_path = os.path.join(UPLOAD_DIR, f"{task_id}.csv")
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        # Import product data using existing pipeline
        from AI_crawl.pipeline import import_from_file
        
        products_count = import_from_file(
            file_path=file_path,
            user_id=request.user_id,
            website_name=request.website_name
        )
        
        return ProductUploadResponse(
            status="success",
            message=f"Google Sheets imported successfully",
            filename=f"Google Sheets ({sheet_id})",
            products_count=products_count or 0,
            timestamp=datetime.now().isoformat(),
            task_id=task_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error processing Google Sheets: {str(e)}")


if __name__ == "__main__":
    print("File upload endpoints ready!")
    print(f"Upload directory: {UPLOAD_DIR}")
    print(f"\n📦 Product Endpoint: POST /api/upload/product")
    print(f"   Formats: Excel, CSV, JSON, Word (tables), PDF (tables)")
    print(f"\n📄 Document Endpoint: POST /api/upload/document")
    print(f"   Formats: TXT, Word (text), PDF (text)")
    print(f"\n🔗 Google Sheets Endpoint: POST /api/upload/product/google-sheets")
    print(f"   Input: Google Sheets URL (public)")

