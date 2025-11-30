#!/bin/bash

# BuildTrace Overlay - Local Development Starter
# This script helps you run the application locally

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 BuildTrace Overlay - Local Development${NC}"
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if config.env exists
if [ ! -f "config.env" ]; then
    echo -e "${YELLOW}⚠️  config.env not found. Creating a template...${NC}"
    cat > config.env << 'EOF'
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# OpenAI Model Configuration
OPENAI_MODEL=gpt-4o

# Analysis Configuration
DEFAULT_DPI=300
DEBUG_MODE=false
EOF
    echo "Please edit config.env with your OpenAI API key before running again."
    exit 1
fi

# Function to stop and remove existing container
cleanup() {
    if docker ps -a --format 'table {{.Names}}' | grep -q buildtrace-overlay; then
        echo "Stopping existing container..."
        docker stop buildtrace-overlay >/dev/null 2>&1 || true
        docker rm buildtrace-overlay >/dev/null 2>&1 || true
    fi
}

# Check command line arguments
case "${1:-dev}" in
    "dev")
        echo -e "${GREEN}Starting in development mode with hot reload...${NC}"
        echo "✨ Code changes will be automatically reflected without rebuilding!"
        cleanup
        docker-compose --profile dev up --build buildtrace-dev
        ;;
    "quick")
        echo -e "${GREEN}Starting in quick development mode (mounts entire directory)...${NC}"
        echo "⚡ Fastest startup, but may have permission issues on some systems"
        cleanup
        docker-compose --profile quick up --build buildtrace-dev-quick
        ;;
    "prod")
        echo -e "${GREEN}Starting in production mode...${NC}"
        cleanup
        docker-compose up --build buildtrace
        ;;
    "stop")
        echo -e "${GREEN}Stopping BuildTrace Overlay...${NC}"
        cleanup
        docker-compose down
        ;;
    "rebuild")
        echo -e "${GREEN}Rebuilding and starting...${NC}"
        cleanup
        docker-compose down
        docker-compose build --no-cache
        docker-compose up buildtrace
        ;;
    "logs")
        echo -e "${GREEN}Showing application logs...${NC}"
        docker-compose logs -f
        ;;
    *)
        echo "Usage: $0 [dev|quick|prod|stop|rebuild|logs]"
        echo ""
        echo "Commands:"
        echo "  dev     - Start in development mode with hot reload (default)"
        echo "  quick   - Quick dev mode (mounts entire directory)"
        echo "  prod    - Start in production mode with Gunicorn"
        echo "  stop    - Stop the application"
        echo "  rebuild - Rebuild the Docker image and start"
        echo "  logs    - Show application logs"
        echo ""
        echo "🔥 Development Features:"
        echo "  • Hot reload - changes are automatically detected"
        echo "  • Debug mode - detailed error messages"
        echo "  • No rebuild needed for code changes"
        echo ""
        echo "The application will be available at: http://localhost:8080"
        exit 1
        ;;
esac