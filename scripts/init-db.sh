#!/bin/bash
# Database initialization script for MVP SaaS

set -e

echo "🚀 Retail AI MVP - Database Initialization"
echo "=========================================="

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until pg_isready -h localhost -p 5432 -U retail_user; do
  echo "   Waiting for database connection..."
  sleep 2
done

echo "✓ PostgreSQL is ready!"

# Run Alembic migrations
echo ""
echo "📊 Running database migrations..."
alembic upgrade head

echo ""
echo "✅ Database initialization complete!"
echo ""
echo "You can now start the application with:"
echo "  uvicorn app.main_mvp:app --reload"
