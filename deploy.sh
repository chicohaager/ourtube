#!/bin/bash
# OurTube Production Deployment Script

set -e

echo "🚀 Starting OurTube production deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from project root
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Please run this script from the OurTube project root directory${NC}"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "🔍 Checking dependencies..."

if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    echo "Install from: https://docs.docker.com/engine/install/"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    echo "Install from: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Dependencies check passed${NC}"

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Build and start
echo "🏗️  Building and starting containers..."
docker-compose up -d --build

# Wait for health check
echo "⏳ Waiting for application to be ready..."
sleep 10

# Check if application is running
if curl -f http://localhost:8000/docs >/dev/null 2>&1; then
    echo -e "${GREEN}✅ OurTube is running successfully!${NC}"
    echo ""
    echo "🌐 Access your application at:"
    echo "   • Main app: http://localhost:8000"
    echo "   • API docs: http://localhost:8000/docs"
    echo ""
    echo "📁 Downloads will be saved to: ./downloads"
    echo ""
    echo "📋 Useful commands:"
    echo "   • View logs: docker-compose logs -f"
    echo "   • Stop app: docker-compose down"
    echo "   • Restart: docker-compose restart"
else
    echo -e "${YELLOW}⚠️  Application started but health check failed${NC}"
    echo "Check logs with: docker-compose logs"
fi

echo ""
echo -e "${GREEN}🎉 Deployment complete!${NC}"