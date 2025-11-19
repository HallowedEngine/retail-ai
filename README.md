# 🛒 Retail AI - Advanced Invoice & Inventory Management System

[![Tests](https://img.shields.io/badge/tests-173%20passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-78%25-green)](htmlcov/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Enterprise-grade retail management system** with OCR-powered invoice processing, intelligent inventory tracking, demand forecasting, and real-time analytics.

---

## ✨ Key Features

### 📸 Intelligent OCR Processing
- **Automatic invoice digitization** using Tesseract OCR
- **Turkish language support** with specialized character recognition
- **Fuzzy product matching** for automatic product identification
- **GS1 barcode parsing** for expiry dates and lot codes
- **Fallback mechanisms** for low-confidence OCR results

### 📦 Inventory Management
- **Real-time stock tracking** with batch-level granularity
- **Expiry alert system** with red/yellow severity levels
- **Demand forecasting** using historical sales data
- **Smart reorder suggestions** based on lead time and safety stock
- **Multi-store support** with centralized management

### 🔐 Security & Authentication
- **HTTP Basic Authentication** with configurable credentials
- **Environment-based configuration** for secure deployments
- **Input validation** and sanitization on all endpoints
- **SQL injection prevention** with parameterized queries
- **File upload restrictions** with content-type validation

### 🚀 Production-Ready
- **Comprehensive error handling** with custom exception handlers
- **Structured logging** with rotation and multiple outputs
- **78% test coverage** with 173 passing tests
- **Docker support** with multi-stage builds
- **CI/CD pipeline** with GitHub Actions
- **Health check endpoints** for monitoring

---

## 🚀 Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access the application
# Web UI: http://localhost:8000/ui
# API Docs: http://localhost:8000/docs
# Login: admin / retailai2025
```

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# Access
# App: http://localhost:8000
# pgAdmin: http://localhost:5050
```

---

## 📖 API Documentation

**Authentication**: All endpoints require HTTP Basic Auth (`admin` / `retailai2025`)

**Key Endpoints:**
- `POST /upload_invoice` - Upload & process invoice
- `GET /invoice/{id}` - Get invoice details
- `GET /products` - List products
- `POST /products/bulk` - Bulk create products
- `GET /alerts/expiry` - Get expiry alerts
- `GET /dashboard/summary` - Dashboard metrics

**Full docs**: `/docs` (Swagger) or `/redoc`

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Current stats: 173 passing, 8 skipped, 78% coverage
```

---

## ⚙️ Configuration

Create `.env` file:
```env
DB_URL=sqlite:///./data/demo.db
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-password
LOG_LEVEL=INFO
```

See `.env.example` for all options.

---

## 🐳 Docker Services

- **app**: FastAPI application
- **db**: PostgreSQL 15
- **redis**: Redis 7
- **pgadmin**: DB management
- **redis-commander**: Cache management

---

## 📊 Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **Database**: SQLAlchemy, PostgreSQL/SQLite
- **OCR**: Tesseract, OpenCV
- **Testing**: pytest (173 tests, 78% coverage)
- **Deployment**: Docker, Docker Compose
- **CI/CD**: GitHub Actions

---

## 🛡️ Security

✅ Authentication on all endpoints
✅ Environment-based secrets
✅ Input validation (Pydantic)
✅ SQL injection prevention
✅ File upload restrictions
✅ Structured logging
✅ Error tracking

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/name`)
3. Make changes and run tests
4. Commit and push
5. Open Pull Request

---

## 📝 License

MIT License - see [LICENSE](LICENSE)

---

**Built with ❤️ using FastAPI**

*Transform your retail operations with AI-powered automation!*
