#!/bin/bash

# ========================================
# Quick Deploy Script for New Server
# ========================================
# Run this script on the NEW server after extracting the archive

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  NaviTech ChatBot - Quick Deploy${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Step 1: Check Docker
echo -e "${YELLOW}Step 1: Checking Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✅ Docker is installed${NC}"
    docker --version
else
    echo -e "${RED}❌ Docker not found!${NC}"
    echo -e "${YELLOW}Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo -e "${GREEN}✅ Docker installed. Please logout and login again, then re-run this script.${NC}"
    exit 0
fi

if command -v docker compose &> /dev/null; then
    echo -e "${GREEN}✅ Docker Compose is available${NC}"
    docker compose version
else
    echo -e "${RED}❌ Docker Compose not found!${NC}"
    exit 1
fi
echo ""

# Step 2: Check .env
echo -e "${YELLOW}Step 2: Checking .env file...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}⚠️  .env not found, copying from .env.example${NC}"
        cp .env.example .env
        echo -e "${GREEN}✅ .env created${NC}"
        echo ""
        echo -e "${RED}⚠️  IMPORTANT: You MUST edit .env before continuing!${NC}"
        echo -e "${YELLOW}Required changes:${NC}"
        echo "  1. POSTGRES_PASSWORD=<strong-password>"
        echo "  2. OPENAI_API_KEY=<your-openai-key>"
        echo "  3. QDRANT_HOST=chatbot-qdrant"
        echo ""
        echo -e "${BLUE}Press any key to open .env in editor...${NC}"
        read -n 1 -s
        ${EDITOR:-nano} .env
    else
        echo -e "${RED}❌ Neither .env nor .env.example found!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ .env exists${NC}"
    
    # Validate critical variables
    echo -e "${YELLOW}Validating .env...${NC}"
    source .env
    
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your-openai-key-here" ]; then
        echo -e "${RED}⚠️  OPENAI_API_KEY not set or still default!${NC}"
        echo "Please edit .env and set a valid OPENAI_API_KEY"
        exit 1
    fi
    
    if [ "$QDRANT_HOST" != "chatbot-qdrant" ] && [ "$QDRANT_HOST" != "localhost" ]; then
        echo -e "${YELLOW}⚠️  QDRANT_HOST is set to: $QDRANT_HOST${NC}"
        echo "For Docker deployment, it should be 'chatbot-qdrant'"
        echo "Do you want to continue anyway? (y/n)"
        read -n 1 answer
        echo ""
        if [ "$answer" != "y" ]; then
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✅ .env validated${NC}"
fi
echo ""

# Step 3: Create required directories
echo -e "${YELLOW}Step 3: Creating required directories...${NC}"
mkdir -p uploads
chmod 755 uploads
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Step 4: Build Docker images
echo -e "${YELLOW}Step 4: Building Docker images...${NC}"
docker compose build
echo -e "${GREEN}✅ Images built${NC}"
echo ""

# Step 5: Start containers
echo -e "${YELLOW}Step 5: Starting containers...${NC}"
docker compose up -d
echo ""

# Wait for containers to be ready
echo -e "${YELLOW}Waiting for containers to be healthy...${NC}"
sleep 10

# Check container status
docker compose ps
echo ""

# Step 6: Run migrations
echo -e "${YELLOW}Step 6: Running database migrations...${NC}"
sleep 5  # Wait a bit more for database
docker compose exec chatbot-app alembic upgrade head
echo -e "${GREEN}✅ Migrations completed${NC}"
echo ""

# Step 7: Verify deployment
echo -e "${YELLOW}Step 7: Verifying deployment...${NC}"
echo ""

echo -e "${BLUE}Checking PostgreSQL...${NC}"
if docker compose exec db psql -U postgres -d chatbot -c "SELECT version();" &> /dev/null; then
    echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
else
    echo -e "${RED}❌ PostgreSQL connection failed${NC}"
fi

echo -e "${BLUE}Checking Qdrant...${NC}"
source .env
if curl -s http://localhost:${QDRANT_PORT:-6333}/collections &> /dev/null; then
    echo -e "${GREEN}✅ Qdrant is ready${NC}"
else
    echo -e "${YELLOW}⚠️  Qdrant might not be accessible (check firewall)${NC}"
fi

echo -e "${BLUE}Checking FastAPI...${NC}"
sleep 5
if curl -s http://localhost:${FASTAPI_PORT:-8000}/ &> /dev/null; then
    echo -e "${GREEN}✅ FastAPI is ready${NC}"
else
    echo -e "${YELLOW}⚠️  FastAPI might not be ready yet (still starting up)${NC}"
fi
echo ""

# Summary
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  ✅ DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "${YELLOW}🔗 Access Points:${NC}"
echo "   • API Docs: http://localhost:${FASTAPI_PORT:-8000}/docs"
echo "   • Qdrant Dashboard: http://localhost:${QDRANT_PORT:-6333}/dashboard"
echo "   • PostgreSQL: localhost:${POSTGRES_PORT:-5432}"
echo ""
echo -e "${YELLOW}📝 Useful Commands:${NC}"
echo "   • View logs:       docker compose logs -f chatbot-app"
echo "   • Restart:         docker compose restart"
echo "   • Stop:            docker compose down"
echo "   • Database shell:  docker compose exec db psql -U postgres -d chatbot"
echo ""
echo -e "${YELLOW}🧪 Test the API:${NC}"
echo "   curl http://localhost:${FASTAPI_PORT:-8000}/docs"
echo ""
echo -e "${BLUE}To view application logs now:${NC}"
echo "   docker compose logs -f chatbot-app"
echo ""
