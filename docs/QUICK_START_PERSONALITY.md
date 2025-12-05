# 🚀 AI PERSONALITY SYSTEM - QUICK START

## What It Does
This system allows you to customize how the AI responds to users by setting personality types (fun, creative, professional, etc.).

---

## 5-Minute Setup

### Step 1: Verify Database Migrations
```bash
# The migrations should already be applied when you run the app
# Check migration status:
alembic current
```

**Expected output:**
```
14582c6d86e7 (personality_001) (add_ai_personality_001)
```

### Step 2: List Available Personalities
```bash
curl http://localhost:8000/api/personality/list
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "bình_thường",
    "description": "Bình thường, chuyên nghiệp, cân bằng"
  }
]
```

---

## Common Workflows

### Workflow 1: Set User Personality

```bash
# Step 1: Set personality for user
USER_ID="550e8400-e29b-41d4-a716-446655440000"

curl -X POST http://localhost:8000/api/personality/set-ai-personality \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"personality\": \"bình_thường\"
  }"

# Response:
# {
#   "user_id": "550e8400-e29b-41d4-a716-446655440000",
#   "personality_id": 1,
#   "personality_name": "bình_thường",
#   "personality_description": "Bình thường, chuyên nghiệp, cân bằng"
# }
```

### Workflow 2: Search Products with Personality

```bash
USER_ID="550e8400-e29b-41d4-a716-446655440000"

# Search with user's personality
curl "http://localhost:8000/api/sqlchatbot/chatbot?question=sữa rửa mặt cho da dầu&user_id=$USER_ID"

# Response will include personality-based suffix in the response
```

### Workflow 3: Add New Personality

```bash
curl -X POST "http://localhost:8000/api/personality/create?name=vui_vẻ&description=Vui vẻ, hài hước"

# Response:
# {
#   "id": 2,
#   "name": "vui_vẻ",
#   "description": "Vui vẻ, hài hước"
# }
```

---

## API Endpoints Overview

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/personality/list` | List all personalities |
| POST | `/api/personality/create` | Create new personality |
| POST | `/api/personality/set-ai-personality` | Set user's personality |
| GET | `/api/personality/user/{user_id}` | Get user's personality |

---

## Available Personality Types

| Name | Effect on Response |
|------|-------------------|
| `bình_thường` | No special styling (default) |
| `vui_vẻ` | Adds: 😄 Haha, mong bạn thích những sản phẩm này! |
| `sáng_tạo` | Adds: ✨ Những lựa chọn sáng tạo cho bạn! |
| `nghịch_ngợm` | Adds: 😜 Wink wink, bạn có thích không nè? |
| `chuyên_nghiệp` | Adds: 📊 Đây là các tùy chọn hàng đầu phù hợp với tiêu chí. |
| `tử_tế` | Adds: 💚 Tôi hy vọng những gợi ý này sẽ giúp bạn! |

---

## Python Usage Examples

### Example 1: Set Personality via Service
```python
from services.user import UserService
from sqlalchemy.orm import Session
import uuid

user_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

result = UserService.set_user_personality(
    session=db_session,
    user_id=user_id,
    personality_name="vui_vẻ"
)

print(f"Set personality: {result['personality_name']}")
```

### Example 2: Get User Personality
```python
from services.user import UserService
import uuid

user_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
personality = UserService.get_user_personality(user_id)

if personality:
    print(f"User's personality: {personality['personality_name']}")
else:
    print("User has no personality set")
```

### Example 3: List All Personalities
```python
from services.ai_personality import AIPersonalityService
from sqlalchemy.orm import Session

personalities = AIPersonalityService.get_all_personalities(db_session)

for p in personalities:
    print(f"{p.name}: {p.description}")
```

---

## Testing

### Run Full Test Suite
```bash
python test_personality_system.py
```

### Manual Test with cURL
```bash
# Create a test user
TEST_USER="550e8400-e29b-41d4-a716-446655440000"

# 1. List personalities
curl http://localhost:8000/api/personality/list

# 2. Set personality for user
curl -X POST http://localhost:8000/api/personality/set-ai-personality \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"$TEST_USER\",\"personality\":\"bình_thường\"}"

# 3. Verify it was set
curl http://localhost:8000/api/personality/user/$TEST_USER

# 4. Search products with personality
curl "http://localhost:8000/api/sqlchatbot/chatbot?question=sữa rửa mặt&user_id=$TEST_USER"
```

---

## File Structure

```
d:\AIHUB\
├── models\
│   ├── ai_personality.py          (NEW: AIPersonality model)
│   └── user.py                    (MODIFIED: Added ai_personality_id)
├── repositories\
│   └── ai_personality.py          (NEW: Database CRUD)
├── services\
│   ├── ai_personality.py          (NEW: Business logic)
│   └── user.py                    (MODIFIED: Added personality methods)
├── controllers\
│   ├── personality.py             (NEW: API endpoints)
│   └── __init__.py                (MODIFIED: Added personality import)
├── agent\
│   └── product_agent.py           (MODIFIED: Added personality styling)
├── alembic\
│   └── versions\
│       ├── personality_types_table.py     (NEW: Migration 1)
│       └── add_ai_personality_to_users.py (NEW: Migration 2)
├── docs\
│   ├── AI_PERSONALITY_SYSTEM.md   (NEW: Full documentation)
│   └── QUICK_START.md             (NEW: This file)
├── test_personality_system.py     (NEW: Test script)
└── app.py                         (MODIFIED: Registered personality router)
```

---

## Troubleshooting

### Q: "Personality not found" error
**A:** Create the personality first:
```bash
curl -X POST "http://localhost:8000/api/personality/create?name=vui_vẻ&description=Vui vẻ"
```

### Q: ProductAgent response doesn't have personality suffix
**A:** Verify user personality is set:
```bash
curl http://localhost:8000/api/personality/user/$USER_ID
```

### Q: Database migration fails
**A:** Check migration chain:
```bash
alembic history
alembic current
alembic upgrade head  # Re-run migrations
```

---

## Next Steps

1. ✅ Create users and set their personalities
2. ✅ Test product search with different personalities
3. ✅ Monitor response styling changes
4. ✅ Add more custom personalities as needed
5. ✅ Integrate with frontend to show personality selection UI

---

**For detailed documentation, see: `docs/AI_PERSONALITY_SYSTEM.md`**
