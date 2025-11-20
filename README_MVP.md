# 🚀 Retail AI MVP SaaS

Enterprise-grade SaaS platform for retail inventory management with receipt OCR, real-time stock tracking, and intelligent alerts.

## 📋 Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Development](#development)
- [Deployment](#deployment)

## ✨ Features

### Phase 1 (Current) - Core Infrastructure ✅

- **🔐 Authentication & Authorization**
  - JWT token-based authentication
  - User registration and login
  - Profile management
  - Password change functionality

- **📦 Product Management**
  - Full CRUD operations
  - Bulk import support
  - Low stock filtering
  - Category management
  - Stock value tracking

- **📄 Receipt Processing**
  - Image upload (JPG, PNG, PDF)
  - OCR processing (ready for integration)
  - Receipt item management
  - Duplicate detection
  - Manual correction support

- **📊 Stock Management**
  - Real-time stock tracking
  - Transaction history
  - Stock adjustments
  - In/Out/Adjustment operations
  - Audit trail

- **🔔 Alert System**
  - Multi-severity alerts (low, medium, high, critical)
  - Multiple alert types (low_stock, out_of_stock, expiry_warning, system)
  - Read/unread tracking
  - Email notification support (ready)
  - Alert statistics

- **📈 Dashboard**
  - Comprehensive metrics
  - Stock trends
  - Category distribution
  - Recent activity feed
  - Health monitoring

## 🛠 Technology Stack

### Backend
- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 15+ with asyncpg
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Authentication**: JWT (python-jose) + bcrypt
- **Validation**: Pydantic v2

### Infrastructure
- **Cache/Queue**: Redis
- **Task Queue**: Celery (ready for OCR integration)
- **Containerization**: Docker + Docker Compose
- **OCR**: Tesseract (ready)

### Development
- **Python**: 3.11+
- **Type Hints**: Full typing support
- **Code Quality**: Black, Ruff, MyPy (configured)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional but recommended)

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd retail-ai

# Start all services
docker-compose -f docker-compose-mvp.yml up -d

# Check logs
docker-compose -f docker-compose-mvp.yml logs -f app

# Run database migrations
docker-compose -f docker-compose-mvp.yml exec app alembic upgrade head
```

The application will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:5050 (admin@retailai.com / admin)

### Option 2: Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements-mvp.txt

# 3. Set up environment
cp .env.mvp .env
# Edit .env with your configuration

# 4. Start PostgreSQL and Redis
# (Use Docker or install locally)

# 5. Run database migrations
alembic upgrade head

# 6. Start the application
uvicorn app.main_mvp:app --reload --host 0.0.0.0 --port 8000
```

### First Steps

1. **Register a user**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe",
    "company_name": "My Store"
  }'
```

2. **Login**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

3. **Access the API documentation**: http://localhost:8000/docs

## 📚 API Documentation

### Authentication (`/api/v1/auth`)
- `POST /register` - Register new user
- `POST /login` - Login and get JWT tokens
- `POST /refresh` - Refresh access token
- `GET /me` - Get current user info
- `PUT /profile` - Update profile
- `POST /change-password` - Change password
- `POST /logout` - Logout

### Products (`/api/v1/products`)
- `POST /` - Create product
- `GET /` - List products (with filters)
- `GET /low-stock` - Get low stock products
- `GET /{product_id}` - Get product details
- `PUT /{product_id}` - Update product
- `DELETE /{product_id}` - Delete product (soft delete)
- `POST /bulk` - Bulk create products

### Receipts (`/api/v1/receipts`)
- `POST /upload` - Upload receipt image
- `GET /` - List receipts
- `GET /{receipt_id}` - Get receipt with items
- `PUT /{receipt_id}` - Update receipt
- `DELETE /{receipt_id}` - Delete receipt
- `POST /{receipt_id}/reprocess` - Reprocess OCR
- `GET /{receipt_id}/status` - Get processing status
- `POST /{receipt_id}/items` - Add receipt item
- `PUT /items/{item_id}` - Update receipt item
- `DELETE /items/{item_id}` - Delete receipt item

### Stock (`/api/v1/stock`)
- `POST /transaction` - Create stock transaction
- `POST /adjust` - Adjust stock to specific quantity
- `GET /transactions` - List transactions (with filters)
- `GET /transactions/{transaction_id}` - Get transaction
- `GET /summary` - Get stock summary
- `GET /stats` - Get stock statistics

### Alerts (`/api/v1/alerts`)
- `POST /` - Create alert
- `GET /` - List alerts (with filters)
- `GET /{alert_id}` - Get alert
- `PUT /{alert_id}` - Update alert
- `POST /{alert_id}/read` - Mark as read
- `POST /mark-all-read` - Mark all as read
- `DELETE /{alert_id}` - Delete alert
- `GET /stats/summary` - Get alert statistics

### Dashboard (`/api/v1/dashboard`)
- `GET /summary` - Get comprehensive dashboard summary
- `GET /recent-activity` - Get recent activities
- `GET /stock-trend` - Get stock trend data
- `GET /category-distribution` - Get category distribution
- `GET /health` - Health check

## 📁 Project Structure

```
retail-ai/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py       # API router
│   │       ├── auth.py           # Authentication
│   │       ├── products.py       # Products management
│   │       ├── receipts.py       # Receipt processing
│   │       ├── stock.py          # Stock management
│   │       ├── alerts.py         # Alerts system
│   │       └── dashboard.py      # Dashboard metrics
│   ├── core/
│   │   ├── config.py             # Configuration
│   │   ├── database.py           # Database setup
│   │   ├── security.py           # Auth & security
│   │   └── __init__.py
│   ├── models/
│   │   ├── user.py               # User model
│   │   ├── product.py            # Product model
│   │   ├── receipt.py            # Receipt models
│   │   ├── stock.py              # Stock transaction
│   │   ├── alert.py              # Alert models
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── user.py               # User schemas
│   │   ├── product.py            # Product schemas
│   │   ├── receipt.py            # Receipt schemas
│   │   ├── stock.py              # Stock schemas
│   │   ├── alert.py              # Alert schemas
│   │   ├── dashboard.py          # Dashboard schemas
│   │   └── __init__.py
│   └── main_mvp.py               # Main application
├── migrations/
│   ├── versions/
│   │   └── 001_initial_schema.py # Initial migration
│   ├── env.py                    # Alembic environment
│   └── script.py.mako
├── scripts/
│   └── init-db.sh                # DB initialization
├── tests/                        # Test suite (to be added)
├── .env.mvp                      # Environment template
├── alembic.ini                   # Alembic config
├── docker-compose-mvp.yml        # Docker Compose
├── Dockerfile.mvp                # Docker image
├── requirements-mvp.txt          # Python dependencies
├── MVP_PLAN.md                   # Complete architecture plan
└── README_MVP.md                 # This file
```

## 🔧 Development

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### Code Quality

```bash
# Format code
black app/

# Lint code
ruff check app/

# Type checking
mypy app/
```

## 🚀 Deployment

### Environment Variables

Key environment variables to configure:

```bash
# Application
APP_NAME=Retail AI MVP
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Security
JWT_SECRET_KEY=your-super-secret-32-char-minimum-key

# Email (for alerts)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password
```

### Production Deployment

1. **Build Docker image**:
```bash
docker build -f Dockerfile.mvp -t retail-ai-mvp:latest .
```

2. **Run migrations**:
```bash
docker run --rm retail-ai-mvp:latest alembic upgrade head
```

3. **Start services**:
```bash
docker-compose -f docker-compose-mvp.yml up -d
```

### Scaling

- **Horizontal scaling**: Run multiple app instances behind a load balancer
- **Database**: Use PostgreSQL read replicas for read-heavy workloads
- **Caching**: Redis caching for frequently accessed data
- **Queue**: Celery workers for OCR processing

## 📊 Database Schema

### Tables (8 total)

1. **users** - User accounts
2. **products** - Product inventory
3. **receipts** - Receipt/invoice records
4. **receipt_items** - Line items from receipts
5. **stock_transactions** - Stock movement audit trail
6. **alerts** - Notification system
7. **email_queue** - Async email queue
8. **audit_logs** - System audit trail

All tables use UUID primary keys and include created_at/updated_at timestamps.

## 🔐 Security

- JWT token authentication with refresh tokens
- Bcrypt password hashing (12 rounds)
- CORS configuration
- SQL injection protection (SQLAlchemy ORM)
- Input validation (Pydantic)
- Rate limiting (ready to implement)

## 📝 License

Copyright © 2024 Retail AI. All rights reserved.

## 🤝 Support

For issues and questions, please open an issue on GitHub.

## 🗺 Roadmap

### Phase 2 (Next)
- [ ] OCR processing implementation (Tesseract + OpenCV)
- [ ] Email notification system
- [ ] WebSocket real-time updates
- [ ] Enhanced product matching algorithm
- [ ] Export functionality (CSV, PDF, Excel)

### Phase 3 (Future)
- [ ] Mobile app (React Native / Flutter)
- [ ] SKT (expiry date) tracking
- [ ] Advanced analytics & forecasting
- [ ] Multi-user & team management
- [ ] API rate limiting & throttling
- [ ] Automated reordering suggestions

---

**Built with ❤️ using FastAPI, PostgreSQL, and modern Python**
