# 🎭 AI PERSONALITY SYSTEM - REVISED ARCHITECTURE

## Overview

**The PersonalityAgent is a SEPARATE agent** that applies personality styling to responses from ANY other agent (ProductAgent, RecommendationAgent, DocumentRetrievalAgent, etc.).

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              User Query                                 │
└────────────────────┬────────────────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │  ProductAgent       │ (SQL Query → Products)
          │  OR                 │
          │  RecommendationAgent│ (Recommendations)
          │  OR                 │
          │  Other Agents...    │ (Any response)
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │  Agent Response     │
          │  (Plain text)       │
          └──────────┬──────────┘
                     │
                     ▼
          ┌──────────────────────────────────────┐
          │  PersonalityAgent                    │
          │  - Load user's personality           │
          │  - Apply personality suffix          │
          │  - Return styled response            │
          └──────────┬──────────────────────────┘
                     │
                     ▼
          ┌──────────────────────────────────┐
          │  Styled Response (To User)       │
          │  "... product info ... 😄"       │
          └──────────────────────────────────┘
```

---

## 🎯 PersonalityAgent Features

### **1. Pure Response Styling**
- Takes ANY text response from any agent
- Applies personality suffix based on user preference
- Returns original + styled response

### **2. Database Integration**
- Loads user personality from `users.ai_personality_id`
- Looks up personality name in `personality_types` table
- Automatically applies correct suffix

### **3. API Endpoints**

#### Endpoint 1: Apply Personality to User's Response
```http
POST /api/personality/apply
Content-Type: application/json

{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "response_text": "✅ Tôi tìm thấy 5 sản phẩm phù hợp..."
}

Response:
{
    "original_response": "✅ Tôi tìm thấy 5 sản phẩm phù hợp...",
    "styled_response": "✅ Tôi tìm thấy 5 sản phẩm phù hợp...\n\n😄 Haha, mong bạn thích những sản phẩm này!",
    "personality_name": "vui_vẻ",
    "personality_applied": true
}
```

#### Endpoint 2: Apply Personality Directly (without user lookup)
```http
POST /api/personality/apply-direct?response_text=Hello&personality=vui_vẻ

Response:
{
    "original_response": "Hello",
    "styled_response": "Hello\n\n😄 Haha, mong bạn thích những sản phẩm này!",
    "personality_name": "vui_vẻ",
    "personality_applied": true
}
```

#### Endpoint 3: Get Available Personality Suffixes
```http
GET /api/personality/available-suffixes

Response:
{
    "bình_thường": "",
    "vui_vẻ": "\n\n😄 Haha, mong bạn thích những sản phẩm này!",
    "sáng_tạo": "\n\n✨ Những lựa chọn sáng tạo cho bạn!",
    "nghịch_ngợm": "\n\n😜 Wink wink, bạn có thích không nè?",
    "chuyên_nghiệp": "\n\n📊 Đây là các tùy chọn hàng đầu phù hợp với tiêu chí.",
    "tử_tế": "\n\n💚 Tôi hy vọng những gợi ý này sẽ giúp bạn!"
}
```

---

## 📊 Domain Agents (Unchanged)

### ProductAgent
- **Responsibility:** SQL query generation & product search
- **Input:** User search query
- **Output:** Plain list of products with description
- **NO personality logic** ✅

### RecommendationAgent
- **Responsibility:** Generate product recommendations
- **Input:** User profile, preferences
- **Output:** Recommendation list
- **NO personality logic** ✅

### DocumentRetrievalAgent
- **Responsibility:** Search documents & retrieve content
- **Input:** Search query
- **Output:** Document results
- **NO personality logic** ✅

### Other Agents
- Same pattern - each handles their domain
- NO personality styling

---

## 🔄 Complete Flow

### **Step 1: User Sets Personality**
```bash
POST /api/personality/set-ai-personality
{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "personality": "vui_vẻ"
}
```

Stored in `users.ai_personality_id`

### **Step 2: User Makes Query**
```bash
POST /api/sqlchatbot/chatbot?question=sữa rửa mặt cho da dầu
```

ProductAgent processes:
- Generates SQL
- Fetches products
- Returns plain response: "✅ Tôi tìm thấy 5 sản phẩm..."

### **Step 3: Personality Agent Applies Styling**
```bash
POST /api/personality/apply
{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "response_text": "✅ Tôi tìm thấy 5 sản phẩm..."
}
```

Returns:
```json
{
    "styled_response": "✅ Tôi tìm thấy 5 sản phẩm...\n\n😄 Haha, mong bạn thích những sản phẩm này!"
}
```

### **Step 4: Return Styled Response to User**

---

## 💻 Usage Examples

### Python - Using PersonalityAgent
```python
from agent.personality_agent import PersonalityAgent

# Apply personality directly
result = PersonalityAgent.apply_personality(
    response_text="✅ Tôi tìm thấy 5 sản phẩm",
    personality_name="vui_vẻ"
)

print(result['styled_response'])
# ✅ Tôi tìm thấy 5 sản phẩm
# 
# 😄 Haha, mong bạn thích những sản phẩm này!
```

### cURL - Using API
```bash
# Get user's personality and apply it
curl -X POST http://localhost:8000/api/personality/apply \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "response_text": "✅ Tôi tìm thấy 5 sản phẩm"
  }'
```

---

## 🎭 Personality Types

| Type | Suffix |
|------|--------|
| `bình_thường` | (none) |
| `vui_vẻ` | 😄 Haha, mong bạn thích những sản phẩm này! |
| `sáng_tạo` | ✨ Những lựa chọn sáng tạo cho bạn! |
| `nghịch_ngợm` | 😜 Wink wink, bạn có thích không nè? |
| `chuyên_nghiệp` | 📊 Đây là các tùy chọn hàng đầu phù hợp với tiêu chí. |
| `tử_tế` | 💚 Tôi hy vọng những gợi ý này sẽ giúp bạn! |

---

## ✅ Benefits of This Architecture

1. **Separation of Concerns**
   - Domain agents focus on their logic (ProductAgent = SQL)
   - PersonalityAgent = styling only

2. **Reusability**
   - PersonalityAgent works with ANY response from ANY agent
   - No need to modify each agent separately

3. **Scalability**
   - Add new agents without changing personality logic
   - Easy to add new personality types

4. **Maintainability**
   - Personality logic in ONE place
   - Changes don't affect domain agents

5. **Clean Architecture**
   - Domain agents are pure (no UI concerns)
   - Presentation layer is separate (PersonalityAgent)

---

## 📁 File Structure

```
agent/
├── product_agent.py           ✅ SQL queries only (reverted)
├── recomendation_agent.py     ✅ Unchanged
├── personality_agent.py       ✨ NEW - Styling only
├── document_retrieval_agent.py ✅ Unchanged
└── ... (other agents)          ✅ Unchanged

controllers/
├── personality.py             ✅ User personality management

services/
└── ai_personality.py          ✅ Personality business logic
```

---

## 🔗 Integration Points

### When Using ProductAgent
```python
# 1. Get response from ProductAgent
response = await product_agent.process_query("sữa rửa mặt")
# Returns: {"response": "...", "products": [...]}

# 2. Apply personality styling
styled = await personality_agent.apply_personality_endpoint(
    user_id=user_id,
    response_text=response['response']
)
# Returns: {"styled_response": "... with emoji"}

# 3. Return to user
return {"response": styled['styled_response'], "products": response['products']}
```

### When Using Any Other Agent
Same pattern applies:
1. Get response from domain agent
2. Pass to PersonalityAgent
3. Return styled response

---

## 🧪 Testing

### Test Direct Styling
```bash
curl -X POST "http://localhost:8000/api/personality/apply-direct?response_text=Hello&personality=vui_vẻ"
```

### Test with User Personality
```bash
# First set user personality
curl -X POST http://localhost:8000/api/personality/set-ai-personality \
  -H "Content-Type: application/json" \
  -d '{"user_id":"550e8400-e29b-41d4-a716-446655440000","personality":"vui_vẻ"}'

# Then apply to response
curl -X POST http://localhost:8000/api/personality/apply \
  -H "Content-Type: application/json" \
  -d '{"user_id":"550e8400-e29b-41d4-a716-446655440000","response_text":"Test response"}'
```

---

## 📞 API Reference

### PersonalityAgent Endpoints
- `POST /api/personality/apply` - Apply personality based on user
- `POST /api/personality/apply-direct` - Apply personality directly
- `GET /api/personality/available-suffixes` - List all suffixes

### User Personality Endpoints (from controllers/personality.py)
- `POST /api/personality/set-ai-personality` - Set user personality
- `GET /api/personality/user/{user_id}` - Get user personality
- `GET /api/personality/list` - List personalities
- `POST /api/personality/create` - Create personality

---

## ✨ Summary

**Old (Wrong) Architecture:**
- ProductAgent had personality logic ❌
- Would need to add to RecommendationAgent, DocumentRetrievalAgent, etc. ❌
- Code duplication ❌

**New (Correct) Architecture:**
- ProductAgent = pure SQL logic ✅
- PersonalityAgent = separate styling agent ✅
- Works with ANY agent response ✅
- Single source of personality logic ✅
- Clean separation of concerns ✅

---

**Status:** ✅ COMPLETE
**Date:** October 25, 2025
**Version:** 2.0 (Revised Architecture)
