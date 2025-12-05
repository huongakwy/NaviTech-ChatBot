# 🎭 AI PERSONALITY SYSTEM - IMPLEMENTATION GUIDE

## Overview
AI Personality System cho phép customize tone/style của AI responses dựa trên user preferences. Mỗi user có thể set tính cách AI riêng (vui vẻ, sáng tạo, chuyên nghiệp, v.v).

---

## 📋 Architecture

### 1. Database Schema

#### personality_types Table (Master Data)
```sql
CREATE TABLE personality_types (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIMEZONE,
    updated_at TIMESTAMP WITH TIMEZONE
);
```

**Default Personality:**
- `id: 1`
- `name: bình_thường`
- `description: Bình thường, chuyên nghiệp, cân bằng`

#### users Table (Modified)
```sql
ALTER TABLE users ADD COLUMN ai_personality_id INTEGER 
  FOREIGN KEY REFERENCES personality_types(id) ON DELETE SET NULL
  NULLABLE;
```

---

### 2. Models Layer

#### AIPersonalityTable (SQLAlchemy ORM)
- File: `models/ai_personality.py`
- Represents `personality_types` table
- Fields: `id`, `name`, `description`, `created_at`, `updated_at`

#### UserTable (Updated)
- File: `models/user.py`
- New field: `ai_personality_id` (FK to personality_types)
- New relationship: `ai_personality` (lazy joined)

#### Pydantic Models
- `AIPersonalityModel`: For API responses
- `AIPersonalityCreateModel`: For POST requests
- `AIPersonalityUpdateModel`: For PATCH requests

---

### 3. Repository Layer

#### AIPersonalityRepository
- File: `repositories/ai_personality.py`
- Methods:
  - `get_all()`: Get all personalities
  - `get_by_id(id)`: Get personality by ID
  - `get_by_name(name)`: Get personality by name
  - `create(name, description)`: Create new personality
  - `update(id, name, description)`: Update personality
  - `delete(id)`: Delete personality

---

### 4. Service Layer

#### AIPersonalityService
- File: `services/ai_personality.py`
- Methods:
  - `get_all_personalities()`: Get all personalities
  - `get_personality(id)`: Get personality by ID
  - `get_personality_by_name(name)`: Get personality by name
  - `create_personality(data)`: Create new personality
  - `update_personality(id, data)`: Update personality
  - `delete_personality(id)`: Delete personality
  - `get_default_personality_id()`: Get default personality ID

#### UserService (Extended)
- File: `services/user.py`
- New methods:
  - `set_user_personality(session, user_id, personality_name)`: Set user's personality
  - `get_user_personality(user_id)`: Get user's current personality

---

### 5. Controller Layer

#### Personality Controller
- File: `controllers/personality.py`
- Routes:
  - `POST /api/personality/set-ai-personality`: Set user personality
  - `GET /api/personality/user/{user_id}`: Get user personality
  - `GET /api/personality/list`: List all personalities
  - `POST /api/personality/create`: Create new personality

---

### 6. Agent Integration

#### ProductAgent (Modified)
- File: `agent/product_agent.py`
- New attributes:
  - `user_personality`: Stores current user's personality
- New methods:
  - `set_personality(personality)`: Set personality
  - `get_personality()`: Get personality
  - `_apply_personality_style(explanation, personality)`: Apply styling to response
- Modified methods:
  - `_generate_explanation()`: Now accepts personality parameter
  - `process_query()`: Uses personality for response styling

**Personality Styling:**
```python
personality_suffixes = {
    "bình_thường": "",  # No change
    "vui_vẻ": "\n\n😄 Haha, mong bạn thích những sản phẩm này!",
    "sáng_tạo": "\n\n✨ Những lựa chọn sáng tạo cho bạn!",
    "nghịch_ngợm": "\n\n😜 Wink wink, bạn có thích không nè?",
    "chuyên_nghiệp": "\n\n📊 Đây là các tùy chọn hàng đầu phù hợp với tiêu chí.",
    "tử_tế": "\n\n💚 Tôi hy vọng những gợi ý này sẽ giúp bạn!",
}
```

**Endpoint Integration:**
```python
@router.post("/chatbot")
async def product_agent(question: str, user_id: Optional[str] = None):
    agent = SQLAgent()
    
    # Load user personality if provided
    if user_id:
        user_personality = UserService.get_user_personality(user_uuid)
        if user_personality:
            agent.set_personality(user_personality['personality_name'])
    
    response = await agent.process_query(user_query=question)
    return response
```

---

## 🔄 Flow Diagram

```
User Request
    ↓
POST /api/personality/set-ai-personality
    ↓
AIPersonalityService.get_personality_by_name()
    ↓
UserService.set_user_personality()
    ↓
Update users.ai_personality_id
    ↓
✅ Personality Set
    
---

User Chat Query
    ↓
POST /api/sqlchatbot/chatbot?question=...&user_id=...
    ↓
ProductAgent.set_personality(user_personality)
    ↓
SQLAgent.process_query()
    ↓
_generate_explanation(personality)
    ↓
_apply_personality_style()
    ↓
Add personality suffix to response
    ↓
✅ Return Response with Personality Styling
```

---

## 📡 API Endpoints

### 1. Set User Personality
```http
POST /api/personality/set-ai-personality
Content-Type: application/json

{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "personality": "vui_vẻ"
}

Response:
{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "personality_id": 2,
    "personality_name": "vui_vẻ",
    "personality_description": "Vui vẻ, hài hước, tạo cảm giác tích cực"
}
```

### 2. Get User Personality
```http
GET /api/personality/user/550e8400-e29b-41d4-a716-446655440000

Response:
{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "personality_id": 2,
    "personality_name": "vui_vẻ",
    "personality_description": "Vui vẻ, hài hước, tạo cảm giác tích cực"
}
```

### 3. List All Personalities
```http
GET /api/personality/list

Response:
[
    {
        "id": 1,
        "name": "bình_thường",
        "description": "Bình thường, chuyên nghiệp, cân bằng"
    },
    {
        "id": 2,
        "name": "vui_vẻ",
        "description": "Vui vẻ, hài hước, tạo cảm giác tích cực"
    }
]
```

### 4. Create New Personality
```http
POST /api/personality/create?name=sáng_tạo&description=Sáng tạo, có tưởng tượng

Response:
{
    "id": 3,
    "name": "sáng_tạo",
    "description": "Sáng tạo, có tưởng tượng"
}
```

### 5. Product Search with Personality
```http
POST /api/sqlchatbot/chatbot?question=sữa rửa mặt cho da dầu&user_id=550e8400-e29b-41d4-a716-446655440000

Response:
{
    "response": "✅ Tôi tìm thấy 5 sản phẩm phù hợp...\n\n😄 Haha, mong bạn thích những sản phẩm này!",
    "products": [...]
}
```

---

## 🔧 Database Migrations

### Migration 1: Create personality_types Table
- File: `alembic/versions/personality_types_table.py`
- Revision: `personality_001`
- Creates: `personality_types` table with default "bình_thường" personality

### Migration 2: Add ai_personality to users
- File: `alembic/versions/add_ai_personality_to_users.py`
- Revision: `add_ai_personality_001`
- Adds: `ai_personality_id` column to `users` table

**Run Migrations:**
```bash
alembic upgrade head
```

---

## 🧪 Testing

### Test Script
- File: `test_personality_system.py`
- Tests all endpoints and complete flow

**Run Tests:**
```bash
python test_personality_system.py
```

**Or with curl:**
```bash
# List personalities
curl http://localhost:8000/api/personality/list

# Set user personality
curl -X POST http://localhost:8000/api/personality/set-ai-personality \
  -H "Content-Type: application/json" \
  -d '{"user_id":"550e8400-e29b-41d4-a716-446655440000","personality":"vui_vẻ"}'

# Get user personality
curl http://localhost:8000/api/personality/user/550e8400-e29b-41d4-a716-446655440000

# Product search with personality
curl "http://localhost:8000/api/sqlchatbot/chatbot?question=sữa rửa mặt&user_id=550e8400-e29b-41d4-a716-446655440000"
```

---

## 📊 Available Personalities

| Name | Description | Example Response Suffix |
|------|-------------|--------------------------|
| `bình_thường` | Bình thường, chuyên nghiệp, cân bằng | (no suffix) |
| `vui_vẻ` | Vui vẻ, hài hước, tạo cảm giác tích cực | 😄 Haha, mong bạn thích những sản phẩm này! |
| `sáng_tạo` | Sáng tạo, có tưởng tượng | ✨ Những lựa chọn sáng tạo cho bạn! |
| `nghịch_ngợm` | Nghịch ngợm, tinh nghịch | 😜 Wink wink, bạn có thích không nè? |
| `chuyên_nghiệp` | Chuyên nghiệp, trang trọng | 📊 Đây là các tùy chọn hàng đầu phù hợp với tiêu chí. |
| `tử_tế` | Tử tế, lịch sự, ấm áp | 💚 Tôi hy vọng những gợi ý này sẽ giúp bạn! |

---

## 🚀 Usage Examples

### Example 1: Setup New User with Personality
```python
from sqlalchemy.orm import Session
from services.user import UserService
from services.ai_personality import AIPersonalityService
import uuid

user_id = uuid.uuid4()

# Create user
user_data = {
    "id": user_id,
    "full_name": "John Doe",
    "email": "john@example.com"
}
# ... create user ...

# Set personality
result = UserService.set_user_personality(
    session=db_session,
    user_id=user_id,
    personality_name="vui_vẻ"
)
print(f"Personality set: {result['personality_name']}")
```

### Example 2: Query Products with User Personality
```python
import requests

response = requests.post(
    "http://localhost:8000/api/sqlchatbot/chatbot",
    params={
        "question": "sữa rửa mặt cho da dầu",
        "user_id": "550e8400-e29b-41d4-a716-446655440000"
    }
)

print(response.json()['response'])
# Output will include personality-based suffix
```

### Example 3: Add New Personality
```python
import requests

response = requests.post(
    "http://localhost:8000/api/personality/create",
    params={
        "name": "tối_giản",
        "description": "Tối giản, gọn gàng, rõ ràng"
    }
)

print(response.json())
```

---

## 🔍 Files Modified/Created

### New Files:
1. ✅ `models/ai_personality.py` - AIPersonality models
2. ✅ `repositories/ai_personality.py` - AIPersonality repository
3. ✅ `services/ai_personality.py` - AIPersonality service
4. ✅ `controllers/personality.py` - Personality API endpoints
5. ✅ `alembic/versions/personality_types_table.py` - Migration 1
6. ✅ `alembic/versions/add_ai_personality_to_users.py` - Migration 2
7. ✅ `test_personality_system.py` - Test script

### Modified Files:
1. ✅ `models/user.py` - Added ai_personality_id and relationship
2. ✅ `services/user.py` - Added set_user_personality, get_user_personality methods
3. ✅ `agent/product_agent.py` - Added personality methods and styling
4. ✅ `app.py` - Registered personality router

---

## ✅ Verification Checklist

- [x] Database migrations created and executed
- [x] Models created (AIPersonality + updated User)
- [x] Repository layer implemented
- [x] Service layer implemented
- [x] Controller endpoints created
- [x] ProductAgent integrated with personality
- [x] Personality styling applied to responses
- [x] API routes registered in app.py
- [x] Default personality set in database
- [x] Test script created
- [x] Documentation complete

---

## 🐛 Troubleshooting

### Issue: "Personality not found"
**Solution:** Ensure personality exists in database
```bash
curl http://localhost:8000/api/personality/list
```

### Issue: User personality is NULL
**Solution:** Call set-ai-personality endpoint
```bash
curl -X POST http://localhost:8000/api/personality/set-ai-personality \
  -H "Content-Type: application/json" \
  -d '{"user_id":"...","personality":"bình_thường"}'
```

### Issue: Migration conflicts
**Solution:** Check migration chain
```bash
alembic current
alembic history
```

---

## 📚 Related Documentation
- Database: See `models/ai_personality.py` for schema
- API: See `controllers/personality.py` for endpoints
- Agent: See `agent/product_agent.py` for styling logic
- Tests: See `test_personality_system.py` for examples

---

**Status:** ✅ COMPLETE AND TESTED
**Created:** 2025-10-25
**Version:** 1.0
