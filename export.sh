#!/bin/bash

# ========================================
# NaviTech ChatBot - Auto Export Script
# ========================================
# Script tự động tạo package để export dự án
# Loại bỏ tất cả files không cần thiết

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
PROJECT_DIR="/home/dev/NaviTech-ChatBot"
OUTPUT_NAME="navitech-chatbot-$(date +%Y%m%d-%H%M%S).tar.gz"
REQUIRED_FILES=(
    "docker-compose.yml"
    "Dockerfile"
    "requirements.txt"
    ".env.example"
    "alembic.ini"
    "app.py"
    "db.py"
    "env.py"
    "app_environment.py"
    "AI_crawl/init.sql"
)
REQUIRED_DIRS=(
    "agent"
    "alembic/versions"
    "controllers"
    "embedding"
    "models"
    "repositories"
    "services"
    "tool_call"
    "utils"
)

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  NaviTech ChatBot - Auto Export Tool${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Step 1: Check we're in the right directory
cd "$PROJECT_DIR"
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ Error: Not in project directory!${NC}"
    echo "Please run this script from: $PROJECT_DIR"
    exit 1
fi
echo -e "${GREEN}✅ Project directory confirmed${NC}"
echo ""

# Step 2: Check required files
echo -e "${YELLOW}Checking required files...${NC}"
MISSING=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}  ✅ $file${NC}"
    else
        echo -e "${RED}  ❌ MISSING: $file${NC}"
        MISSING=$((MISSING + 1))
    fi
done

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}  ✅ $dir/${NC}"
    else
        echo -e "${RED}  ❌ MISSING: $dir/${NC}"
        MISSING=$((MISSING + 1))
    fi
done

if [ $MISSING -gt 0 ]; then
    echo -e "${RED}❌ Missing $MISSING required files/directories!${NC}"
    exit 1
fi
echo ""

# Step 3: Check .env.example exists
if [ ! -f ".env.example" ]; then
    echo -e "${YELLOW}⚠️  .env.example not found, creating from .env...${NC}"
    if [ -f ".env" ]; then
        # Remove sensitive values
        sed -E 's/(POSTGRES_PASSWORD=).*/\1your-password-here/' .env | \
        sed -E 's/(OPENAI_API_KEY=).*/\1your-openai-key-here/' > .env.example
        echo -e "${GREEN}✅ .env.example created${NC}"
    else
        echo -e "${RED}❌ Neither .env nor .env.example found!${NC}"
        exit 1
    fi
fi
echo ""

# Step 4: Create archive
echo -e "${YELLOW}Creating export package...${NC}"
echo -e "${BLUE}Output: $OUTPUT_NAME${NC}"

tar -czf "$OUTPUT_NAME" \
    --exclude='venv' \
    --exclude='venv/' \
    --exclude='.venv' \
    --exclude='ENV' \
    --exclude='env' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='*.pyd' \
    --exclude='.Python' \
    --exclude='.git' \
    --exclude='.github' \
    --exclude='.gitignore' \
    --exclude='.env' \
    --exclude='.env.local' \
    --exclude='*.env' \
    --exclude='uploads/*' \
    --exclude='!uploads/.gitkeep' \
    --exclude='*.log' \
    --exclude='logs/*' \
    --exclude='*.tmp' \
    --exclude='*.temp' \
    --exclude='*.swp' \
    --exclude='*.swo' \
    --exclude='.vscode' \
    --exclude='.idea' \
    --exclude='*.code-workspace' \
    --exclude='.DS_Store' \
    --exclude='test.ipynb' \
    --exclude='test.py' \
    --exclude='test_*.py' \
    --exclude='scripts/' \
    --exclude='docs/' \
    --exclude='.pytest_cache' \
    --exclude='.coverage' \
    --exclude='htmlcov' \
    --exclude='.mypy_cache' \
    --exclude='*.db' \
    --exclude='*.sqlite' \
    --exclude='*.sqlite3' \
    --exclude='AI_crawl/docker-compose.yml' \
    --exclude='navitech-chatbot-*.tar.gz' \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Archive created successfully!${NC}"
    echo ""
    
    # Show file info
    SIZE=$(ls -lh "$OUTPUT_NAME" | awk '{print $5}')
    echo -e "${GREEN}📦 Package Details:${NC}"
    echo -e "   File: $OUTPUT_NAME"
    echo -e "   Size: $SIZE"
    echo ""
    
    # Show what's inside
    echo -e "${YELLOW}📋 Package Contents Preview:${NC}"
    tar -tzf "$OUTPUT_NAME" | head -20
    echo "   ..."
    TOTAL_FILES=$(tar -tzf "$OUTPUT_NAME" | wc -l)
    echo -e "   ${BLUE}Total: $TOTAL_FILES files/folders${NC}"
    echo ""
    
    # Next steps
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  ✅ EXPORT SUCCESSFUL!${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    echo -e "${YELLOW}📤 Next Steps:${NC}"
    echo ""
    echo -e "${BLUE}1. Transfer to server:${NC}"
    echo "   scp $OUTPUT_NAME user@server:/path/to/destination/"
    echo ""
    echo -e "${BLUE}2. On the new server:${NC}"
    echo "   tar -xzf $OUTPUT_NAME"
    echo "   cd navitech-chatbot/"
    echo "   cp .env.example .env"
    echo "   nano .env  # Update POSTGRES_PASSWORD, OPENAI_API_KEY, QDRANT_HOST"
    echo ""
    echo -e "${BLUE}3. Start Docker:${NC}"
    echo "   docker compose up -d"
    echo "   docker compose exec chatbot-app alembic upgrade head"
    echo ""
    echo -e "${BLUE}4. Verify:${NC}"
    echo "   curl http://localhost:8000/docs"
    echo "   docker compose logs -f chatbot-app"
    echo ""
    echo -e "${YELLOW}📖 For detailed guide, see:${NC}"
    echo "   - EXPORT_CHECKLIST.md"
    echo "   - DOCKER_DEPLOYMENT.md"
    echo ""
    
else
    echo -e "${RED}❌ Failed to create archive!${NC}"
    exit 1
fi
