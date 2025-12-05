from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
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
    user_id: str = Form("b95c2881-387f-4093-b80d-ac83b1dea7a9"),
    website_name: Optional[str] = Form(None)
) -> ProductUploadResponse:
    """
    Upload file sản phẩm và import vào database + embeddings
    
    Supported formats:
    - **Excel**: .xlsx, .xls
    - **CSV**: .csv
    - **JSON**: .json
    - **Word**: .docx (tables)
    - **PDF**: .pdf (tables)
    
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


if __name__ == "__main__":
    print("File upload endpoints ready!")
    print(f"Upload directory: {UPLOAD_DIR}")
    print(f"\n📦 Product Endpoint: POST /api/upload/product")
    print(f"   Formats: Excel, CSV, JSON, Word (tables), PDF (tables)")
    print(f"\n📄 Document Endpoint: POST /api/upload/document")
    print(f"   Formats: TXT, Word (text), PDF (text)")

