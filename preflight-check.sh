#!/bin/bash

# ========================================
# Pre-flight Check Script
# ========================================
# Kiểm tra tất cả yêu cầu trước khi export

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Pre-flight Check${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

ERRORS=0
WARNINGS=0

# Required files
echo -e "${YELLOW}Checking required files...${NC}"
REQUIRED_FILES=(
    "docker-compose.yml:Docker orchestration file"
    "Dockerfile:Docker build file"
    "requirements.txt:Python dependencies"
    ".env.example:Environment template"
    "alembic.ini:Alembic config"
    "app.py:FastAPI entry point"
    "db.py:Database connection"
    "env.py:Environment loader"
    "AI_crawl/init.sql:Database init"
)

for item in "${REQUIRED_FILES[@]}"; do
    file="${item%%:*}"
    desc="${item##*:}"
    if [ -f "$file" ]; then
        echo -e "${GREEN}  ✅ $file${NC}"
    else
        echo -e "${RED}  ❌ MISSING: $file ($desc)${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# Required directories
echo -e "${YELLOW}Checking required directories...${NC}"
REQUIRED_DIRS=(
    "agent:AI agents"
    "alembic/versions:Database migrations"
    "controllers:API endpoints"
    "embedding:Embedding & search"
    "models:Database models"
    "repositories:Data access"
    "services:Business logic"
    "tool_call:Tool functions"
    "utils:Utilities"
)

for item in "${REQUIRED_DIRS[@]}"; do
    dir="${item%%:*}"
    desc="${item##*:}"
    if [ -d "$dir" ]; then
        file_count=$(find "$dir" -type f -name "*.py" | wc -l)
        echo -e "${GREEN}  ✅ $dir/ ($file_count Python files)${NC}"
    else
        echo -e "${RED}  ❌ MISSING: $dir/ ($desc)${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# Check Python files syntax
echo -e "${YELLOW}Checking Python syntax...${NC}"
PYTHON_ERRORS=0
while IFS= read -r pyfile; do
    if ! python3 -m py_compile "$pyfile" 2>/dev/null; then
        echo -e "${RED}  ❌ Syntax error: $pyfile${NC}"
        PYTHON_ERRORS=$((PYTHON_ERRORS + 1))
    fi
done < <(find . -name "*.py" -not -path "./venv/*" -not -path "./__pycache__/*")

if [ $PYTHON_ERRORS -eq 0 ]; then
    echo -e "${GREEN}  ✅ All Python files have valid syntax${NC}"
else
    echo -e "${RED}  ❌ Found $PYTHON_ERRORS files with syntax errors${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check requirements.txt
echo -e "${YELLOW}Checking requirements.txt...${NC}"
if [ -f "requirements.txt" ]; then
    PACKAGE_COUNT=$(grep -v '^#' requirements.txt | grep -v '^$' | wc -l)
    echo -e "${GREEN}  ✅ $PACKAGE_COUNT packages listed${NC}"
    
    # Check for common required packages
    for pkg in "fastapi" "sqlalchemy" "alembic" "qdrant_client" "openai"; do
        if grep -qi "^$pkg" requirements.txt; then
            echo -e "${GREEN}    ✓ $pkg${NC}"
        else
            echo -e "${YELLOW}    ⚠️  $pkg not found${NC}"
            WARNINGS=$((WARNINGS + 1))
        fi
    done
else
    echo -e "${RED}  ❌ requirements.txt not found${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check .env.example
echo -e "${YELLOW}Checking .env.example...${NC}"
if [ -f ".env.example" ]; then
    echo -e "${GREEN}  ✅ .env.example exists${NC}"
    
    # Check required variables
    REQUIRED_VARS=(
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "POSTGRES_DB"
        "DATABASE_URL"
        "OPENAI_API_KEY"
        "QDRANT_HOST"
        "FASTAPI_PORT"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^$var=" .env.example; then
            echo -e "${GREEN}    ✓ $var${NC}"
        else
            echo -e "${YELLOW}    ⚠️  $var not found${NC}"
            WARNINGS=$((WARNINGS + 1))
        fi
    done
else
    echo -e "${RED}  ❌ .env.example not found${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check Docker files
echo -e "${YELLOW}Checking Docker configuration...${NC}"
if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}  ✅ docker-compose.yml exists${NC}"
    
    # Check for required services
    for service in "db" "chatbot-qdrant" "chatbot-app"; do
        if grep -q "^\s*$service:" docker-compose.yml; then
            echo -e "${GREEN}    ✓ Service: $service${NC}"
        else
            echo -e "${RED}    ✗ Service missing: $service${NC}"
            ERRORS=$((ERRORS + 1))
        fi
    done
fi

if [ -f "Dockerfile" ]; then
    echo -e "${GREEN}  ✅ Dockerfile exists${NC}"
    if grep -q "FROM python" Dockerfile; then
        echo -e "${GREEN}    ✓ Python base image${NC}"
    fi
    if grep -q "COPY requirements.txt" Dockerfile; then
        echo -e "${GREEN}    ✓ Copies requirements.txt${NC}"
    fi
    if grep -q "CMD.*uvicorn" Dockerfile; then
        echo -e "${GREEN}    ✓ Runs uvicorn${NC}"
    fi
fi
echo ""

# Check migrations
echo -e "${YELLOW}Checking database migrations...${NC}"
if [ -d "alembic/versions" ]; then
    MIGRATION_COUNT=$(find alembic/versions -name "*.py" ! -name "__init__.py" | wc -l)
    echo -e "${GREEN}  ✅ Found $MIGRATION_COUNT migrations${NC}"
    
    # List recent migrations
    echo -e "${BLUE}  Recent migrations:${NC}"
    find alembic/versions -name "*.py" ! -name "__init__.py" | sort | tail -5 | while read f; do
        echo "    - $(basename $f)"
    done
else
    echo -e "${RED}  ❌ alembic/versions not found${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check uploads directory
echo -e "${YELLOW}Checking uploads directory...${NC}"
if [ -d "uploads" ]; then
    echo -e "${GREEN}  ✅ uploads/ exists${NC}"
else
    echo -e "${YELLOW}  ⚠️  uploads/ not found (will be created)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# Estimate size
echo -e "${YELLOW}Estimating export size...${NC}"
SIZE=$(du -sh --exclude='venv' --exclude='__pycache__' --exclude='.git' --exclude='uploads' . | cut -f1)
echo -e "${BLUE}  Estimated size: $SIZE${NC}"
echo ""

# Summary
echo -e "${BLUE}================================================${NC}"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}  ✅ ALL CHECKS PASSED!${NC}"
    echo -e "${GREEN}  Ready to export${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo ""
    echo -e "${YELLOW}Next step:${NC}"
    echo "  ./export.sh"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}  ⚠️  PASSED WITH $WARNINGS WARNINGS${NC}"
    echo -e "${YELLOW}  You can proceed but review warnings${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo ""
    echo -e "${YELLOW}Next step:${NC}"
    echo "  ./export.sh"
    exit 0
else
    echo -e "${RED}  ❌ FAILED: $ERRORS errors, $WARNINGS warnings${NC}"
    echo -e "${RED}  Please fix errors before exporting${NC}"
    echo -e "${BLUE}================================================${NC}"
    exit 1
fi
