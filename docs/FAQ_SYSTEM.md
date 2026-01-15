# 🎯 FAQ SYSTEM - Hệ Thống Câu Hỏi Thường Gặp

## 📋 Tổng Quan

Hệ thống FAQ được thiết kế để chatbot có thể trả lời trực tiếp các câu hỏi thường gặp với độ chính xác cao, giảm tải cho các agents khác.

### ✨ Tính Năng Chính

- **Threshold-based Matching**: Chỉ trả lời khi similarity score >= 0.85 (configurable)
- **Smart Fallback**: Tự động fallback về normal flow nếu không match FAQ
- **Multi-user Support**: Mỗi user/company có FAQs riêng
- **Real-time Sync**: Tự động sync FAQ vào Qdrant khi tạo/update
- **Priority System**: FAQs có độ ưu tiên cao được ưu tiên hiển thị
- **Category Management**: Phân loại FAQs theo categories (chính sách, bảo hành, etc.)

---

## 🏗️ Kiến Trúc

```
┌─────────────────────────────────────────────────────────┐
│                    USER QUERY                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
    ┌────────────────────────────────────────┐
    │     CHAT PIPELINE (chat_pipeline.py)   │
    │                                         │
    │  [1] Save user message                 │
    │  [2] Get history                       │
    │  [2.5] 🆕 FAQ PRE-CHECK ◄──────────┐  │
    │       │                              │  │
    │       ├─ Score >= 0.85?             │  │
    │       │   YES → Return FAQ answer   │  │
    │       │   NO  → Continue ↓           │  │
    │       │                              │  │
    │  [3] Manager routing                │  │
    │  [4] Execute agent                  │  │
    └───────────────┬────────────────────────┘
                    │                         
                    ▼                         
         ┌─────────────────────┐             
         │    FAQ AGENT        │◄────────────┤
         │  (faq_agent.py)     │             │
         │                     │             │
         │  - search_faq()     │             │
         │  - check threshold  │             │
         │  - return result    │             │
         └──────────┬──────────┘             
                    │                         
                    ▼                         
         ┌─────────────────────┐             
         │  QDRANT SEARCH      │             
         │  (search.py)        │             
         │                     │             
         │  Collection: "faqs" │             
         │  Filter: user_id    │             
         │  Threshold: 0.85    │             
         └─────────────────────┘             
```

---

## 📁 Cấu Trúc Files

### **Models & Database**
```
models/faq.py                    # SQLAlchemy models
├── FAQTable                     # Database table
├── FAQModel                     # Pydantic response model
├── FAQCreateModel               # Create payload
├── FAQUpdateModel               # Update payload
└── FAQSearchResult              # Search result với score

alembic/versions/create_faqs_table.py   # Migration script
```

### **Repository & Service Layers**
```
repositories/faq.py              # Data access layer
└── FAQRepository                # CRUD operations

services/faq.py                  # Business logic
└── FAQService                   # FAQ management
    ├── create_faq()
    ├── list_faqs()
    ├── update_faq()
    ├── delete_faq()
    └── get_statistics()
```

### **Embedding & Search**
```
embedding/faq_embedding.py       # Qdrant integration
└── FAQEmbedding
    ├── sync_faq_to_qdrant()    # Sync single FAQ
    ├── bulk_sync_faqs()        # Bulk sync
    ├── delete_faq_from_qdrant()
    └── ensure_collection_exists()

embedding/search.py
└── faq_semantic_search()        # Search với threshold
```

### **Agent & Controllers**
```
agent/faq_agent.py               # FAQ matching logic
└── FAQAgent
    ├── search_faq()            # Find best match
    ├── process_with_fallback() # With fallback logic
    └── get_all_matches()       # Multiple matches

controllers/faq.py               # REST API endpoints
├── POST   /api/faqs            # Create FAQ
├── GET    /api/faqs            # List FAQs
├── GET    /api/faqs/{id}       # Get FAQ
├── PUT    /api/faqs/{id}       # Update FAQ
├── DELETE /api/faqs/{id}       # Delete FAQ
├── POST   /api/faqs/bulk       # Bulk create
├── POST   /api/faqs/{id}/sync  # Sync to Qdrant
└── POST   /api/faqs/test-match # Test matching
```

---

## 🚀 Hướng Dẫn Sử Dụng

### **1. Khởi Tạo Database**

```bash
# Activate venv
source venv/bin/activate

# Run migration (đã chạy tự động khi start app)
python -m alembic upgrade head
```

### **2. Khởi Động Qdrant**

```bash
# Nếu dùng Docker
docker run -p 6334:6334 qdrant/qdrant

# Collection "faqs" sẽ được tự động tạo khi add FAQ đầu tiên
```

### **3. Tạo Sample FAQs**

```bash
# Tạo FAQs mẫu cho user
python scripts/create_sample_faqs.py [user_id]

# Hoặc để script tự lấy user đầu tiên
python scripts/create_sample_faqs.py
```

### **4. Khởi Động Server**

```bash
uvicorn app:app --reload --port 8000
```

### **5. Test API**

Truy cập: `http://localhost:8000/docs`

---

## 🔧 API Endpoints

### **Tạo FAQ Mới**
```http
POST /api/faqs
Content-Type: application/json

{
  "user_id": "uuid",
  "question": "Chính sách đổi trả như thế nào?",
  "answer": "Chúng tôi hỗ trợ đổi trả trong 7 ngày...",
  "category": "chinh-sach",
  "priority": 10,
  "is_active": true
}
```

### **List FAQs**
```http
GET /api/faqs?user_id={uuid}&category=chinh-sach&is_active=true&limit=10
```

### **Update FAQ**
```http
PUT /api/faqs/{faq_id}
Content-Type: application/json

{
  "answer": "Updated answer...",
  "priority": 15
}
```

### **Test FAQ Matching**
```http
POST /api/faqs/test-match?query=đổi trả sản phẩm&user_id={uuid}&threshold=0.85

Response:
{
  "query": "đổi trả sản phẩm",
  "threshold": 0.85,
  "total_matches": 2,
  "matches": [
    {
      "faq_id": "...",
      "score": 0.92,
      "question": "Chính sách đổi trả sản phẩm...",
      "answer": "...",
      "matched": true
    }
  ]
}
```

---

## 💬 Chat Flow Với FAQ

### **Kịch Bản 1: FAQ Match (Score >= 0.85)**

```
User: "Chính sách đổi trả như thế nào?"
  ↓
FAQ Agent: Search in Qdrant
  ↓
Best Match: Score 0.92 ✅
  ↓
Return FAQ Answer TRỰC TIẾP
  ↓
(Không cần routing qua Manager Agent)
```

**Log output:**
```
🔍 CHECKING FAQ DATABASE...
✅✅✅ FAQ MATCHED! Returning direct answer
   Score: 0.920
   FAQ ID: xxx-xxx-xxx
```

### **Kịch Bản 2: No Match (Score < 0.85)**

```
User: "Laptop gaming tốt nhất là gì?"
  ↓
FAQ Agent: Search in Qdrant
  ↓
Best Match: Score 0.45 ❌ (< 0.85)
  ↓
Fallback to Normal Flow
  ↓
Manager Agent → ProductAgent/RecommendationAgent
```

**Log output:**
```
🔍 CHECKING FAQ DATABASE...
⚠️  No FAQ matched (score below 0.85)
   Fallback to normal agent routing...
🤖 Selected agent: RecommendationAgent
```

---

## ⚙️ Configuration

### **Threshold Settings**

Điều chỉnh trong `agent/chat_pipeline.py`:

```python
faq_agent = FAQAgent(threshold=0.85)  # Default: 0.85

# Hoặc config trong env.py:
# FAQ_THRESHOLD = 0.85
# FAQ_TOP_K = 3
```

### **Threshold Recommendations**

- **0.90 - 1.00**: Rất nghiêm ngặt, chỉ match câu hỏi gần giống 100%
- **0.85 - 0.90**: **Recommended** - Cân bằng giữa precision và recall
- **0.80 - 0.85**: Linh hoạt hơn, có thể match nhiều variations
- **< 0.80**: Quá lỏng, risk trả lời sai

### **Qdrant Collection Settings**

```python
# embedding/faq_embedding.py
Collection: "faqs"
Vector Size: env.LEN_EMBEDDING (default: 1536 for OpenAI)
Distance: COSINE
Indexes: user_id, category, is_active
```

---

## 📊 Database Schema

### **Table: faqs**

| Column      | Type         | Description                    |
|-------------|--------------|--------------------------------|
| id          | UUID         | Primary key                    |
| user_id     | UUID         | Foreign key to users (indexed)|
| question    | TEXT         | Câu hỏi FAQ                    |
| answer      | TEXT         | Câu trả lời                    |
| category    | VARCHAR(100) | Danh mục (indexed)             |
| priority    | INTEGER      | Độ ưu tiên (0-100)             |
| is_active   | BOOLEAN      | Trạng thái (indexed)           |
| created_at  | TIMESTAMP    | Thời gian tạo                  |
| updated_at  | TIMESTAMP    | Thời gian update               |

### **Qdrant Payload**

```json
{
  "faq_id": "uuid",
  "user_id": "uuid",
  "question": "...",
  "answer": "...",
  "category": "chinh-sach",
  "priority": 10,
  "is_active": true
}
```

---

## 🧪 Testing

### **Test Imports**
```bash
python test_faq_system.py
```

### **Test FAQ Creation**
```bash
python scripts/create_sample_faqs.py
```

### **Test Matching**
```python
from agent.faq_agent import FAQAgent
import uuid

agent = FAQAgent(threshold=0.85)
result = agent.search_faq(
    query="Chính sách đổi trả như thế nào?",
    user_id=uuid.UUID("your-user-id")
)

if result:
    print(f"Matched! Score: {result['score']}")
    print(f"Answer: {result['answer']}")
```

---

## 🎯 Best Practices

### **1. FAQ Content Guidelines**

✅ **DO:**
- Viết câu hỏi tự nhiên, như người dùng thường hỏi
- Câu trả lời chi tiết, đầy đủ thông tin
- Sử dụng formatting (bullet points, headers)
- Cập nhật thường xuyên

❌ **DON'T:**
- Câu hỏi quá ngắn hoặc mơ hồ
- Câu trả lời chung chung
- Duplicate FAQs

### **2. Category Organization**

```
chinh-sach  → Chính sách công ty
bao-hanh    → Bảo hành sản phẩm
thanh-toan  → Thanh toán
giao-hang   → Giao hàng
don-hang    → Đơn hàng
lien-he     → Liên hệ, cửa hàng
```

### **3. Priority System**

```
10 - Critical FAQs (chính sách quan trọng)
7-9 - High priority (thường hỏi)
4-6 - Medium priority
1-3 - Low priority
0 - Không ưu tiên
```

### **4. Maintenance**

- Review FAQs monthly
- Check matching scores và adjust threshold
- Deactivate outdated FAQs (không xóa)
- Monitor user queries không match để thêm FAQs mới

---

## 🐛 Troubleshooting

### **FAQ không match dù câu hỏi giống**

```bash
# Test xem score thực tế
POST /api/faqs/test-match?query=...&user_id=...&threshold=0.0

# Kiểm tra:
- FAQ có is_active=true không?
- user_id có đúng không?
- Qdrant có sync không?
```

### **Qdrant connection refused**

```bash
# Start Qdrant
docker run -p 6334:6334 qdrant/qdrant

# Check collection
curl http://localhost:6334/collections
```

### **FAQs không sync vào Qdrant**

```bash
# Manual sync
POST /api/faqs/{faq_id}/sync

# Re-sync all FAQs của user
python scripts/resync_all_faqs.py [user_id]
```

---

## 📈 Monitoring & Analytics

### **Metrics to Track**

- FAQ hit rate (% queries matched FAQ)
- Average match scores
- Most matched FAQs
- Queries không match (để thêm FAQ mới)
- Response time FAQ vs Normal flow

### **Get Statistics**

```http
GET /api/faqs/stats/{user_id}

Response:
{
  "total": 50,
  "active": 45,
  "inactive": 5,
  "categories": ["chinh-sach", "bao-hanh", ...],
  "category_count": 6
}
```

---

## 🔮 Future Enhancements

- [ ] Analytics dashboard cho FAQ performance
- [ ] A/B testing different thresholds
- [ ] Multi-language FAQ support
- [ ] Auto-suggest FAQs từ chat logs
- [ ] FAQ templates và bulk import từ CSV
- [ ] Reranking model để improve accuracy
- [ ] FAQ versioning và audit logs

---

## 📞 Support

Nếu có vấn đề, check:
1. Logs trong console
2. Database connection
3. Qdrant status
4. User có FAQs không

---

**Developed with ❤️ for Navitech ChatBot**
