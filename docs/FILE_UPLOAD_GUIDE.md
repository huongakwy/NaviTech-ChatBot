# 📤 File Upload API - User Guide

## Tổng quan

API upload file hỗ trợ import products từ nhiều định dạng file khác nhau vào database.

## 🎯 Supported File Formats

- ✅ **Excel**: `.xlsx`, `.xls`
- ✅ **CSV**: `.csv`
- ✅ **JSON**: `.json`
- ✅ **Word**: `.docx` (chứa bảng/tables)
- ✅ **PDF**: `.pdf` (chứa bảng/tables)

## 📋 Column Mapping

File phải chứa các cột với tên (không phân biệt hoa thường):

| English | Tiếng Việt | Field |
|---------|-----------|-------|
| `title`, `name`, `product_name` | `tên sản phẩm`, `tên` | Title |
| `price` | `giá`, `gia`, `giá bán` | Price |
| `original_price` | `giá gốc`, `gia goc` | Original Price |
| `sku` | `mã sản phẩm`, `ma san pham` | SKU |
| `brand` | `thương hiệu`, `thuong hieu` | Brand |
| `category` | `danh mục`, `danh muc` | Category |
| `description` | `mô tả`, `mo ta` | Description |
| `images` | `hình ảnh`, `hinh anh` | Images (comma-separated URLs) |
| `url` | `link` | Product URL |

**Lưu ý:**
- Cột `title` hoặc `tên sản phẩm` là **BẮT BUỘC**
- Các cột khác là optional
- Column names không phân biệt hoa thường, khoảng trắng

## 📊 Example File Formats

### Excel/CSV Example

| title | price | giá gốc | brand | category | images |
|-------|-------|---------|-------|----------|--------|
| iPhone 15 Pro | 25990000 | 29990000 | Apple | Điện thoại | https://example.com/img1.jpg |
| Samsung Galaxy S24 | 22990000 | 24990000 | Samsung | Điện thoại | https://example.com/img2.jpg,https://example.com/img3.jpg |

### JSON Example

```json
[
  {
    "title": "iPhone 15 Pro",
    "price": 25990000,
    "original_price": 29990000,
    "brand": "Apple",
    "category": "Điện thoại",
    "images": ["https://example.com/img1.jpg"]
  },
  {
    "title": "Samsung Galaxy S24",
    "price": 22990000,
    "brand": "Samsung"
  }
]
```

Hoặc:

```json
{
  "products": [
    {...},
    {...}
  ]
}
```

### Word (.docx) Format

File Word phải chứa **bảng** (table) với:
- Dòng đầu tiên: Header (tên cột)
- Các dòng tiếp theo: Dữ liệu sản phẩm

Example:

```
| Tên sản phẩm       | Giá      | Thương hiệu |
|--------------------|----------|-------------|
| iPhone 15 Pro      | 25990000 | Apple       |
| Samsung Galaxy S24 | 22990000 | Samsung     |
```

### PDF Format

Tương tự Word, PDF phải chứa **bảng** với header và data rows.

## 🚀 API Usage

### Endpoint

```
POST /api/upload/file
```

### Request

**Form Data:**
- `file`: File upload (required)
- `user_id`: User UUID (optional, default: hardcoded)
- `website_name`: Website name (optional, use filename if not provided)

### cURL Example

```bash
# Upload Excel
curl -X POST "http://localhost:8000/api/upload/file" \
  -F "file=@products.xlsx" \
  -F "user_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "website_name=My Products Store"

# Upload CSV (auto website name from filename)
curl -X POST "http://localhost:8000/api/upload/file" \
  -F "file=@products.csv"

# Upload Word
curl -X POST "http://localhost:8000/api/upload/file" \
  -F "file=@products.docx"

# Upload PDF
curl -X POST "http://localhost:8000/api/upload/file" \
  -F "file=@products.pdf"

# Upload JSON
curl -X POST "http://localhost:8000/api/upload/file" \
  -F "file=@products.json"
```

### Python Example

```python
import requests

url = "http://localhost:8000/api/upload/file"

files = {
    'file': open('products.xlsx', 'rb')
}

data = {
    'user_id': '550e8400-e29b-41d4-a716-446655440000',
    'website_name': 'My Products Store'
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

### Response

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

## 📝 Notes

### File Size Limit
- Max: **50MB**

### Price Format
Parser tự động xử lý các format:
- `25990000` → 25990000
- `25,990,000` → 25990000
- `25.990.000đ` → 25990000
- `25.990.000 VND` → 25990000

### Images
Nhiều images trong 1 cell, phân cách bằng:
- Comma: `img1.jpg, img2.jpg`
- Semicolon: `img1.jpg; img2.jpg`
- Pipe: `img1.jpg | img2.jpg`

### URL Generation
Nếu file không có cột `url`, hệ thống tự động generate:
```
file://{website-name}/{title-slug}
```

## 🔍 Testing

Test parser locally:

```bash
cd d:\AIHUB
python utils/file_parser.py products.xlsx
```

Output:
```
✅ Parsed 150 products from products.xlsx

First product:
{
  "title": "iPhone 15 Pro",
  "price": 25990000,
  "original_price": 29990000,
  ...
}
```

## ⚠️ Error Handling

### Common Errors

**1. Unsupported file type**
```json
{
  "detail": "Unsupported file type: .txt. Allowed: .xlsx, .xls, .csv, .json, .docx, .pdf"
}
```

**2. File too large**
```json
{
  "detail": "File too large: 75.3MB. Max: 50MB"
}
```

**3. No valid tables (Word/PDF)**
```json
{
  "detail": "Error processing file: No valid tables found in Word document"
}
```

**4. Missing title column**
```json
{
  "detail": "Error processing file: No products found in file"
}
```

## 📦 Installation

Install required packages:

```bash
pip install pandas openpyxl python-docx pdfplumber python-multipart
```

## 🎓 Example Files

Tạo file Excel mẫu:

```python
import pandas as pd

data = {
    'title': ['iPhone 15 Pro', 'Samsung Galaxy S24', 'MacBook Pro M3'],
    'price': [25990000, 22990000, 45990000],
    'giá gốc': [29990000, 24990000, 49990000],
    'brand': ['Apple', 'Samsung', 'Apple'],
    'category': ['Điện thoại', 'Điện thoại', 'Laptop']
}

df = pd.DataFrame(data)
df.to_excel('products.xlsx', index=False)
print("✅ Created products.xlsx")
```

---

## 🚀 Ready to use!

Upload files và import products ngay lập tức! 🎉
