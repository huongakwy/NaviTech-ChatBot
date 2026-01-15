# NaviTech ChatBot - Docker Deployment Guide

## 📦 Các file cần thiết để export và chạy trong Docker

### 1. **Files bắt buộc**
- ✅ `docker-compose.yml` - Orchestration cho tất cả services
- ✅ `Dockerfile` - Build image cho chatbot app
- ✅ `requirements.txt` - Python dependencies
- ✅ `.env` - Environment variables (không commit vào git)
- ✅ `.env.example` - Template cho .env file
- ✅ `AI_crawl/init.sql` - Database initialization script
- ✅ Toàn bộ source code (app.py, models/, controllers/, agent/, etc.)

### 2. **Cấu trúc Docker**

```yaml
Services:
├── db (PostgreSQL)           - Port 5432
├── chatbot-qdrant (Qdrant)  - Port 6333
└── chatbot-app (FastAPI)    - Port 8000
```

### 3. **Hướng dẫn Deploy**

#### Bước 1: Chuẩn bị môi trường
```bash
# Copy file .env.example thành .env và cập nhật
cp .env.example .env

# Chỉnh sửa .env với các giá trị thực:
# - OPENAI_API_KEY: API key của bạn
# - POSTGRES_PASSWORD: Password mạnh
# - Các config khác nếu cần
```

#### Bước 2: Build và Start services
```bash
# Build images và start tất cả services
docker compose up -d

# Xem logs để kiểm tra
docker compose logs -f chatbot-app

# Kiểm tra status
docker compose ps
```

#### Bước 3: Run database migrations
```bash
# Chạy Alembic migrations trong container
docker compose exec chatbot-app alembic upgrade head

# Hoặc nếu cần, chạy từ host (nếu đã cài alembic)
alembic upgrade head
```

#### Bước 4: Verify deployment
```bash
# Test API endpoints
curl http://localhost:8000/docs

# Test health check
curl http://localhost:8000/

# Check PostgreSQL
docker compose exec db psql -U postgres -d chatbot -c "SELECT COUNT(*) FROM users;"

# Check Qdrant
curl http://localhost:6333/collections
```

### 4. **Export để deploy trên server khác**

#### Option 1: Export source code
```bash
# Tạo archive với tất cả files cần thiết
tar -czf navitech-chatbot.tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='.env' \
  .

# Copy sang server mới
scp navitech-chatbot.tar.gz user@server:/path/to/destination/

# Trên server mới
tar -xzf navitech-chatbot.tar.gz
cp .env.example .env
# Chỉnh sửa .env
docker compose up -d
```

#### Option 2: Export Docker images
```bash
# Build và save images
docker compose build
docker save -o chatbot-app.tar navitech-chatbot-chatbot-app:latest
docker save -o postgres.tar postgres:15
docker save -o qdrant.tar qdrant/qdrant:v1.15.1

# Copy images sang server mới
scp *.tar user@server:/path/to/destination/

# Trên server mới
docker load -i chatbot-app.tar
docker load -i postgres.tar
docker load -i qdrant.tar
docker compose up -d
```

### 5. **Quản lý Docker**

```bash
# Stop tất cả services
docker compose down

# Stop và xóa volumes (CẢNH BÁO: mất data!)
docker compose down -v

# Restart một service
docker compose restart chatbot-app

# Xem logs
docker compose logs -f

# Rebuild sau khi update code
docker compose up -d --build

# Scale service (nếu cần)
docker compose up -d --scale chatbot-app=3
```

### 6. **Backup & Restore**

#### Backup PostgreSQL
```bash
docker compose exec db pg_dump -U postgres chatbot > backup.sql
```

#### Restore PostgreSQL
```bash
docker compose exec -T db psql -U postgres chatbot < backup.sql
```

#### Backup Qdrant
```bash
docker compose exec chatbot-qdrant tar -czf /qdrant/backup.tar.gz /qdrant/storage
docker cp chatbot-qdrant-container:/qdrant/backup.tar.gz ./qdrant-backup.tar.gz
```

### 7. **Environment Variables chính**

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_USER` | PostgreSQL username | postgres |
| `POSTGRES_PASSWORD` | PostgreSQL password | mypassword |
| `POSTGRES_DB` | Database name | chatbot |
| `POSTGRES_PORT` | PostgreSQL host port | 5432 |
| `FASTAPI_PORT` | FastAPI host port | 8000 |
| `QDRANT_PORT` | Qdrant host port | 6333 |
| `OPENAI_API_KEY` | OpenAI API key | sk-... |
| `OPENAI_API_MODEL` | OpenAI model | gpt-4o-mini |

### 8. **Troubleshooting**

#### Container không start
```bash
# Check logs
docker compose logs chatbot-app

# Check container status
docker compose ps
```

#### Database connection failed
```bash
# Verify database is ready
docker compose exec db pg_isready -U postgres

# Check connection from app
docker compose exec chatbot-app env | grep DATABASE_URL
```

#### Port already in use
```bash
# Thay đổi ports trong .env
POSTGRES_PORT=5433
FASTAPI_PORT=8001
QDRANT_PORT=6334

# Restart
docker compose down
docker compose up -d
```

### 9. **Production Considerations**

- ✅ Sử dụng `.env` file với credentials mạnh
- ✅ Không commit `.env` vào git (đã có trong .gitignore)
- ✅ Setup backup tự động cho PostgreSQL và Qdrant
- ✅ Monitor logs: `docker compose logs -f`
- ✅ Setup reverse proxy (Nginx/Caddy) cho HTTPS
- ✅ Limit resource usage trong docker-compose.yml nếu cần:
  ```yaml
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
  ```

### 10. **Files cần đưa lên git**

✅ Commit:
- docker-compose.yml
- Dockerfile
- requirements.txt
- .env.example
- .gitignore

❌ Không commit:
- .env (chứa secrets)
- venv/
- __pycache__/
- *.pyc
- uploads/
- postgres-data/
- qdrant-data/

---

## 🚀 Quick Start

```bash
# 1. Clone repo
git clone <repo-url>
cd NaviTech-ChatBot

# 2. Setup environment
cp .env.example .env
# Edit .env with your values

# 3. Start everything
docker compose up -d

# 4. Run migrations
docker compose exec chatbot-app alembic upgrade head

# 5. Access
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Qdrant: http://localhost:6333/dashboard
```
