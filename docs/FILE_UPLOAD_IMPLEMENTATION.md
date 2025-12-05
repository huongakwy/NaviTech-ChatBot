# 📦 File Upload Implementation Summary

## ✅ Implemented Files

### 1. **Utils Package**
- `d:\AIHUB\utils\file_parser.py` - File parser cho Excel, CSV, JSON, Word, PDF
- `d:\AIHUB\utils\generate_test_files.py` - Generate test files
- `d:\AIHUB\utils\__init__.py` - Package init

### 2. **Controller**
- `d:\AIHUB\controllers\file_upload.py` - Upload endpoint theo frame như `pipeline_endpoint.py`

### 3. **Pipeline Integration**
- `d:\AIHUB\AI crawl\pipeline.py` - Added `import_from_file()` function

### 4. **App Registration**
- `d:\AIHUB\app.py` - Registered file_upload router

### 5. **Dependencies**
- `d:\AIHUB\requirements.txt` - Added `pdfplumber`, `python-multipart`

### 6. **Documentation**
- `d:\AIHUB\docs\FILE_UPLOAD_GUIDE.md` - Complete usage guide

---

## 🎯 Features

### Supported Formats
- ✅ **Excel**: `.xlsx`, `.xls`
- ✅ **CSV**: `.csv` (auto-detect encoding)
- ✅ **JSON**: `.json` (array or object with 'products' key)
- ✅ **Word**: `.docx` (tables)
- ✅ **PDF**: `.pdf` (tables)

### Smart Column Mapping
- Auto-map Vietnamese và English column names
- Case-insensitive matching
- Support nhiều variants (giá/gia, tên/ten, etc.)

### Auto Price Parsing
- Remove currency symbols (đ, ₫, VND)
- Handle comma separators (25,990,000 → 25990000)
- Round to integer

### Auto URL Generation
- Generate `file://{website-name}/{title-slug}` nếu missing

---

## 📋 API Endpoints

### Upload File
```
POST /api/upload/file
```

**Request:**
- `file`: File upload (multipart/form-data)
- `user_id`: User UUID (optional, default: hardcoded)
- `website_name`: Website name (optional)

**Response:**
```json
{
  "status": "success",
  "message": "File uploaded and processed successfully",
  "filename": "products.xlsx",
  "products_count": 150,
  "timestamp": "2025-10-23T10:30:45.123456",
  "task_id": "upload_20251023_103045"
}
```

---

## 🚀 Usage Examples

### cURL
```bash
curl -X POST "http://localhost:8000/api/upload/file" \
  -F "file=@products.xlsx" \
  -F "user_id=550e8400-e29b-41d4-a716-446655440000"
```

### Python
```python
import requests

files = {'file': open('products.xlsx', 'rb')}
data = {'user_id': '550e8400-e29b-41d4-a716-446655440000'}

response = requests.post('http://localhost:8000/api/upload/file', 
                        files=files, data=data)
print(response.json())
```

### JavaScript/Fetch
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('user_id', '550e8400-e29b-41d4-a716-446655440000');

fetch('http://localhost:8000/api/upload/file', {
  method: 'POST',
  body: formData
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## 🧪 Testing

### Generate Test Files
```bash
cd d:\AIHUB
python utils/generate_test_files.py
```

Output:
```
📄 Generating Excel file...
  ✅ Created: d:\AIHUB\test_files\products_sample.xlsx
📄 Generating CSV file...
  ✅ Created: d:\AIHUB\test_files\products_sample.csv
📄 Generating JSON file...
  ✅ Created: d:\AIHUB\test_files\products_sample.json
📄 Generating Vietnamese columns Excel...
  ✅ Created: d:\AIHUB\test_files\products_vietnamese.xlsx
📄 Generating Word file...
  ✅ Created: d:\AIHUB\test_files\products_sample.docx
```

### Test Parser
```bash
python utils/file_parser.py test_files/products_sample.xlsx
```

### Test Upload Endpoint
```bash
curl -X POST "http://localhost:8000/api/upload/file" \
  -F "file=@test_files/products_sample.xlsx"
```

---

## 📊 Pipeline Flow

```
1. Upload File
   ↓
2. Save to uploads/ directory
   ↓
3. Parse File (FileParser)
   ↓
4. Import to PostgreSQL
   ↓
5. Update User website_name
   ↓
6. Generate Embeddings
   ↓
7. Insert to Qdrant
   ↓
8. Return products_count
```

---

## 🔧 Code Structure

### File Parser (`utils/file_parser.py`)
```python
class FileParser:
    COLUMN_MAPPING = {...}  # Vietnamese + English mapping
    
    @staticmethod
    def parse_excel(file_path) -> List[Dict]
    
    @staticmethod
    def parse_csv(file_path) -> List[Dict]
    
    @staticmethod
    def parse_json(file_path) -> List[Dict]
    
    @staticmethod
    def parse_word(file_path) -> List[Dict]
    
    @staticmethod
    def parse_pdf(file_path) -> List[Dict]
    
    @staticmethod
    def parse_file(file_path) -> List[Dict]  # Auto-detect
```

### Controller (`controllers/file_upload.py`)
```python
router = APIRouter(prefix="/upload", tags=["File Upload"])

@router.post("/file", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    website_name: Optional[str] = Form(None)
) -> FileUploadResponse
```

### Pipeline (`AI crawl/pipeline.py`)
```python
def import_from_file(
    file_path: str, 
    user_id: str, 
    website_name: str = None
) -> int:
    """Import products from file"""
    # 1. Parse file
    # 2. Import to PostgreSQL
    # 3. Generate embeddings
    # 4. Return count
```

---

## ⚙️ Configuration

### File Size Limit
```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
```

### Upload Directory
```python
UPLOAD_DIR = "d:\AIHUB\uploads"
```

### Batch Size
```python
BATCH_SIZE = 100  # Products per batch
```

---

## 🎓 Column Mapping Reference

| Field | English | Tiếng Việt |
|-------|---------|-----------|
| Title | title, name, product_name | tên sản phẩm, tên |
| Price | price | giá, gia, giá bán |
| Original Price | original_price | giá gốc, gia goc |
| SKU | sku | mã sản phẩm, ma san pham |
| Brand | brand | thương hiệu, thuong hieu |
| Category | category | danh mục, danh muc |
| Description | description | mô tả, mo ta |
| Images | images, image | hình ảnh, hinh anh |
| URL | url, link | - |

---

## 🚨 Error Handling

### Validation Errors
- Unsupported file type → 400
- File too large (>50MB) → 400
- Missing title column → 500

### Parse Errors
- Invalid Excel format → 500
- Malformed JSON → 500
- No tables in Word/PDF → 500

### Database Errors
- Connection failed → 500
- Insert failed → Rollback + continue

---

## ✅ Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import pandas, openpyxl, docx, pdfplumber; print('✅ All packages installed')"

# Generate test files
python utils/generate_test_files.py

# Start server
uvicorn app:app --reload
```

---

## 📖 Documentation

Full guide: `docs/FILE_UPLOAD_GUIDE.md`

---

**🎉 Implementation Complete!**

File upload endpoint ready to use với đầy đủ features:
- ✅ Multi-format support
- ✅ Smart parsing
- ✅ Database integration  
- ✅ Embedding generation
- ✅ Error handling
- ✅ Documentation
