# 📋 CHECKLIST ĐẦY ĐỦ ĐỂ EXPORT DỰ ÁN

## 🎯 Mục tiêu
Export dự án NaviTech ChatBot để có thể chạy trên bất kỳ server nào chỉ với Docker.

---

## ✅ BƯỚC 1: Chuẩn bị files trên máy hiện tại

### 1.1. Kiểm tra các files BẮT BUỘC phải có

```bash
# Chạy lệnh này để check
cd /home/dev/NaviTech-ChatBot

echo "Checking required files..."
for file in docker-compose.yml Dockerfile requirements.txt .env.example README.md alembic.ini; do
    [ -f "$file" ] && echo "✅ $file" || echo "❌ MISSING: $file"
done

for dir in agent alembic/versions controllers embedding models repositories services utils; do
    [ -d "$dir" ] && echo "✅ $dir/" || echo "❌ MISSING: $dir/"
done

[ -f "AI_crawl/init.sql" ] && echo "✅ AI_crawl/init.sql" || echo "❌ MISSING: AI_crawl/init.sql"
```

**Danh sách files/folders BẮT BUỘC:**
- ✅ `docker-compose.yml` - Orchestration file
- ✅ `Dockerfile` - Build image cho app
- ✅ `requirements.txt` - Python dependencies
- ✅ `.env.example` - Template cho environment variables
- ✅ `alembic.ini` - Alembic config
- ✅ `app.py` - FastAPI entry point
- ✅ `db.py` - Database connection
- ✅ `env.py` - Environment loader
- ✅ `app_environment.py` - App config
- ✅ `README.md` - Documentation
- ✅ `AI_crawl/init.sql` - Database init script
- ✅ `agent/` - Tất cả agents
- ✅ `alembic/versions/` - Migration files
- ✅ `controllers/` - API endpoints
- ✅ `embedding/` - Embedding & search
- ✅ `models/` - Database models
- ✅ `repositories/` - Data access layer
- ✅ `services/` - Business logic
- ✅ `utils/` - Utilities
- ✅ `tool_call/` - Tool functions

### 1.2. Kiểm tra .env có đủ thông tin chưa

```bash
# Check các biến môi trường cần thiết
cat .env | grep -E "POSTGRES_|FASTAPI_|QDRANT_|OPENAI_"
```

**Các biến BẮT BUỘC trong .env:**
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your-password>
POSTGRES_DB=chatbot
POSTGRES_PORT=5432

FASTAPI_PORT=8000
DEBUG=true

QDRANT_HOST=chatbot-qdrant  # Để dùng Qdrant trong Docker
QDRANT_PORT=6333

OPENAI_API_KEY=<your-openai-key>
OPENAI_API_MODEL=gpt-4o-mini

DATABASE_URL=postgresql://postgres:<password>@db:5432/chatbot
```

⚠️ **LƯU Ý:** `.env` chứa secrets, KHÔNG export file này. Dùng `.env.example` thay thế.

---

## ✅ BƯỚC 2: Tạo package để export

### 2.1. Tự động tạo archive (KHUYẾN NGHỊ)

```bash
cd /home/dev/NaviTech-ChatBot

# Tạo archive loại trừ các file không cần thiết
tar -czf navitech-chatbot-$(date +%Y%m%d).tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='uploads/*' \
  --exclude='*.log' \
  --exclude='*.tmp' \
  --exclude='.vscode' \
  --exclude='.idea' \
  --exclude='test.ipynb' \
  --exclude='test.py' \
  --exclude='test_*.py' \
  --exclude='scripts/' \
  --exclude='docs/' \
  .

echo "✅ Archive created: navitech-chatbot-$(date +%Y%m%d).tar.gz"
ls -lh navitech-chatbot-*.tar.gz
```

### 2.2. Hoặc dùng rsync (nếu copy trực tiếp sang server)

```bash
# Copy sang server khác, tự động loại trừ files không cần
rsync -avz --progress \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='.git/' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='uploads/' \
  --exclude='*.log' \
  /home/dev/NaviTech-ChatBot/ \
  user@server:/path/to/destination/
```

---

## ✅ BƯỚC 3: Transfer sang server mới

### 3.1. Copy file

```bash
# Nếu dùng tar.gz
scp navitech-chatbot-20260115.tar.gz user@server-ip:/home/user/

# SSH vào server
ssh user@server-ip
```

### 3.2. Extract trên server mới

```bash
# Trên server mới
cd /home/user/
mkdir -p navitech-chatbot
tar -xzf navitech-chatbot-20260115.tar.gz -C navitech-chatbot/
cd navitech-chatbot/

# Verify files
ls -la
```

---

## ✅ BƯỚC 4: Cài đặt trên server mới

### 4.1. Kiểm tra yêu cầu hệ thống

```bash
# Check Docker installed
docker --version
docker compose version

# Nếu chưa có Docker, cài:
# Ubuntu/Debian:
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

### 4.2. Tạo file .env

```bash
# Copy từ template
cp .env.example .env

# Edit với editor bạn thích
nano .env
# Hoặc
vi .env
```

**Cập nhật các giá trị trong .env:**
```env
# PostgreSQL - ĐỔI PASSWORD MẠNH
POSTGRES_USER=postgres
POSTGRES_PASSWORD=YourStrongPassword123!
POSTGRES_DB=chatbot
POSTGRES_PORT=5432

# Database URL - Nhớ update password
DATABASE_URL=postgresql://postgres:YourStrongPassword123!@db:5432/chatbot

# FastAPI
FASTAPI_PORT=8000
DEBUG=false  # Production nên để false

# Qdrant - QUAN TRỌNG: Dùng tên service trong Docker
QDRANT_HOST=chatbot-qdrant
QDRANT_PORT=6333

# OpenAI - ĐẶT API KEY THẬT
OPENAI_API_KEY=sk-proj-your-real-key-here
OPENAI_API_MODEL=gpt-4o-mini

# Embedding
LEN_EMBEDDING=1536
```

### 4.3. Tạo thư mục cần thiết

```bash
# Tạo uploads folder nếu chưa có
mkdir -p uploads
chmod 755 uploads
```

---

## ✅ BƯỚC 5: Build và Start Docker

### 5.1. Build images

```bash
# Build chatbot app image
docker compose build

# Hoặc build với no-cache nếu có vấn đề
docker compose build --no-cache
```

### 5.2. Start tất cả services

```bash
# Start trong background
docker compose up -d

# Xem logs để check
docker compose logs -f
```

**Expected output:**
```
✅ Container postgres-container           Started
✅ Container chatbot-qdrant-container     Started
✅ Container chatbot-app-container        Started
```

### 5.3. Verify containers đang chạy

```bash
docker compose ps

# Kết quả mong đợi:
# NAME                        STATUS         PORTS
# postgres-container          Up (healthy)   0.0.0.0:5432->5432/tcp
# chatbot-qdrant-container    Up             0.0.0.0:6333->6333/tcp
# chatbot-app-container       Up             0.0.0.0:8000->8000/tcp
```

---

## ✅ BƯỚC 6: Run Database Migrations

### 6.1. Check database connection

```bash
# Test kết nối database
docker compose exec db psql -U postgres -d chatbot -c "SELECT version();"
```

### 6.2. Run Alembic migrations

```bash
# Run migrations trong container
docker compose exec chatbot-app alembic upgrade head

# Verify tables được tạo
docker compose exec db psql -U postgres -d chatbot -c "\dt"
```

**Expected tables:**
- users
- chats
- messages
- products
- faqs
- ai_personality
- personality_types
- (và các tables từ AI_crawl: websites, documents, logs)

---

## ✅ BƯỚC 7: Verify Deployment

### 7.1. Test API

```bash
# Test health check
curl http://localhost:8000/

# Check API docs
curl http://localhost:8000/docs

# Hoặc mở browser
firefox http://localhost:8000/docs
```

### 7.2. Test Qdrant

```bash
# Check Qdrant dashboard
curl http://localhost:6333/dashboard

# List collections
curl http://localhost:6333/collections

# Hoặc mở browser
firefox http://localhost:6333/dashboard
```

### 7.3. Test Database

```bash
# Check user count
docker compose exec db psql -U postgres -d chatbot -c "SELECT COUNT(*) FROM users;"

# Check FAQs
docker compose exec db psql -U postgres -d chatbot -c "SELECT COUNT(*) FROM faqs;"
```

### 7.4. Test full chat pipeline

```bash
# Create a test request
curl -X POST http://localhost:8000/chatbots/full_pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "query": "chính sách đổi trả như thế nào",
    "user_id": "your-user-id-here",
    "chat_id": "your-chat-id-here"
  }'
```

---

## ✅ BƯỚC 8: Setup Production (Optional nhưng khuyến nghị)

### 8.1. Setup Nginx reverse proxy

```bash
# Install nginx
sudo apt install nginx -y

# Create nginx config
sudo nano /etc/nginx/sites-available/chatbot
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 8.2. Setup SSL với Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d your-domain.com
```

### 8.3. Setup auto-restart

```bash
# Docker auto-restart đã enable trong docker-compose.yml
# Verify:
docker compose ps

# Nếu muốn Docker tự start khi server reboot:
sudo systemctl enable docker
```

---

## ✅ BƯỚC 9: Backup & Monitoring Setup

### 9.1. Setup database backup

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/user/backups"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
docker compose exec -T db pg_dump -U postgres chatbot > "$BACKUP_DIR/chatbot_$DATE.sql"
# Keep only last 7 days
find $BACKUP_DIR -name "chatbot_*.sql" -mtime +7 -delete
echo "Backup completed: chatbot_$DATE.sql"
EOF

chmod +x backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/user/navitech-chatbot/backup.sh") | crontab -
```

### 9.2. Setup log rotation

```bash
# Docker logs tự động rotate, check config:
cat /etc/docker/daemon.json

# Nếu chưa có, tạo:
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

sudo systemctl restart docker
```

### 9.3. Monitor với docker stats

```bash
# Real-time monitoring
docker stats

# Hoặc tạo monitoring script
watch -n 5 'docker compose ps && echo && docker stats --no-stream'
```

---

## 📦 SUMMARY: Những gì cần export

### **Files/Folders BẮT BUỘC:**
```
navitech-chatbot/
├── docker-compose.yml          ✅ REQUIRED
├── Dockerfile                  ✅ REQUIRED
├── requirements.txt            ✅ REQUIRED
├── .env.example                ✅ REQUIRED (template)
├── alembic.ini                 ✅ REQUIRED
├── app.py                      ✅ REQUIRED
├── db.py                       ✅ REQUIRED
├── env.py                      ✅ REQUIRED
├── app_environment.py          ✅ REQUIRED
├── README.md                   ✅ REQUIRED
├── AI_crawl/
│   └── init.sql               ✅ REQUIRED
├── agent/                      ✅ REQUIRED (all files)
├── alembic/                    ✅ REQUIRED (all migrations)
├── controllers/                ✅ REQUIRED (all files)
├── embedding/                  ✅ REQUIRED (all files)
├── models/                     ✅ REQUIRED (all files)
├── repositories/               ✅ REQUIRED (all files)
├── services/                   ✅ REQUIRED (all files)
├── tool_call/                  ✅ REQUIRED (all files)
└── utils/                      ✅ REQUIRED (all files)
```

### **Files/Folders KHÔNG CẦN:**
```
❌ .env                 (có secrets, tạo mới trên server)
❌ venv/                (sẽ build lại trong Docker)
❌ __pycache__/         (auto-generated)
❌ .git/                (optional, nếu không cần git history)
❌ uploads/*            (user data, backup riêng)
❌ *.log                (logs)
❌ test*.py             (test files)
❌ scripts/             (helper scripts, optional)
❌ docs/                (documentation, optional)
```

---

## 🚀 QUICK START (Tóm tắt cho server mới)

```bash
# 1. Extract files
tar -xzf navitech-chatbot-20260115.tar.gz
cd navitech-chatbot/

# 2. Create .env
cp .env.example .env
nano .env  # Update: POSTGRES_PASSWORD, OPENAI_API_KEY, QDRANT_HOST=chatbot-qdrant

# 3. Start Docker
docker compose up -d

# 4. Run migrations
docker compose exec chatbot-app alembic upgrade head

# 5. Verify
curl http://localhost:8000/docs
curl http://localhost:6333/dashboard

# 6. View logs
docker compose logs -f chatbot-app
```

---

## ❓ TROUBLESHOOTING

### Issue: Container không start
```bash
docker compose logs chatbot-app
docker compose ps
```

### Issue: Port đã được dùng
```bash
# Thay đổi port trong .env
FASTAPI_PORT=8001
POSTGRES_PORT=5433
QDRANT_PORT=6334

docker compose down
docker compose up -d
```

### Issue: Database connection failed
```bash
# Check database status
docker compose exec db pg_isready -U postgres

# Check .env DATABASE_URL
docker compose exec chatbot-app env | grep DATABASE_URL
```

### Issue: Migration failed
```bash
# Check alembic current version
docker compose exec chatbot-app alembic current

# Force to head
docker compose exec chatbot-app alembic stamp head
docker compose exec chatbot-app alembic upgrade head
```

---

## 📞 Support

Nếu gặp vấn đề, check:
1. Logs: `docker compose logs -f`
2. Container status: `docker compose ps`
3. Environment variables: `docker compose exec chatbot-app env`
4. Database connection: `docker compose exec db psql -U postgres -d chatbot`
