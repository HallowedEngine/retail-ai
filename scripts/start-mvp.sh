#!/bin/bash
# Quick start script for Retail AI MVP

set -e

echo "🚀 Retail AI MVP - Quick Start"
echo "=============================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✓ Docker and Docker Compose are installed"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.mvp .env
    echo "✓ .env file created. Please review and update if needed."
    echo ""
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads logs
echo "✓ Directories created"
echo ""

# Start Docker Compose services
echo "🐳 Starting Docker services..."
docker-compose -f docker-compose-mvp.yml up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Run database migrations
echo ""
echo "📊 Running database migrations..."
docker-compose -f docker-compose-mvp.yml exec -T app alembic upgrade head

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Services are running at:"
echo "  - API:      http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - pgAdmin:  http://localhost:5050 (admin@retailai.com / admin)"
echo ""
echo "📊 View logs:"
echo "  docker-compose -f docker-compose-mvp.yml logs -f app"
echo ""
echo "🛑 Stop services:"
echo "  docker-compose -f docker-compose-mvp.yml down"
echo ""
echo "Happy coding! 🎉"
