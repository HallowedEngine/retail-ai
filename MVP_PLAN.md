# 🚀 Retail AI SaaS MVP - Teknik Mimari ve Geliştirme Planı

## 📌 Proje Özeti
Kurumsal kalitede, bulut tabanlı, ölçeklenebilir fiş tarama ve stok yönetim SaaS platformu.

---

## 🏗️ Teknoloji Stack

### Backend
- **Framework**: FastAPI 0.104+ (async, high-performance)
- **Database**: PostgreSQL 15+ (kurumsal, ACID compliance)
- **ORM**: SQLAlchemy 2.0 (async support)
- **Migration**: Alembic
- **Cache**: Redis (session, real-time data)
- **Task Queue**: Celery + Redis (async processing)
- **OCR Engine**: Tesseract + OpenCV + Custom AI models

### Frontend
- **Framework**: Next.js 14+ (React 18, App Router)
- **UI Library**: Tailwind CSS + shadcn/ui
- **State Management**: Zustand / React Query
- **Real-time**: WebSocket (Socket.io) / Server-Sent Events
- **Charts**: Chart.js / Recharts
- **Forms**: React Hook Form + Zod validation

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Orchestration**: Kubernetes (production)
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Error Tracking**: Sentry

### Cloud & Deployment
- **Hosting**: AWS / Google Cloud / Azure
- **Storage**: S3-compatible object storage
- **CDN**: CloudFlare
- **Email**: SendGrid / AWS SES
- **Database**: Managed PostgreSQL (RDS/Cloud SQL)

---

## 📊 Database Schema

### Core Tables

```sql
-- Users & Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    company_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products (Enhanced)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    sku VARCHAR(100) NOT NULL,
    name VARCHAR(500) NOT NULL,
    category VARCHAR(255),
    barcode_gtin VARCHAR(50),
    current_stock INTEGER DEFAULT 0,
    critical_stock_level INTEGER DEFAULT 10,
    unit VARCHAR(50) DEFAULT 'adet',
    unit_price DECIMAL(10,2),
    image_url TEXT,
    shelf_life_days INTEGER,
    metadata JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, sku)
);

-- Receipts (Fişler)
CREATE TABLE receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    receipt_number VARCHAR(100),
    store_name VARCHAR(255),
    receipt_date DATE,
    total_amount DECIMAL(10,2),
    image_url TEXT NOT NULL,
    image_hash VARCHAR(64) UNIQUE,
    ocr_raw_text TEXT,
    ocr_confidence DECIMAL(5,4),
    processing_status VARCHAR(50) DEFAULT 'pending',
    processed_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Receipt Items
CREATE TABLE receipt_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_id UUID REFERENCES receipts(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    name_raw VARCHAR(500),
    quantity DECIMAL(10,3),
    unit VARCHAR(50),
    unit_price DECIMAL(10,2),
    total_price DECIMAL(10,2),
    confidence_score DECIMAL(5,4),
    matched_automatically BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Stock Transactions
CREATE TABLE stock_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    transaction_type VARCHAR(50) NOT NULL, -- 'in', 'out', 'adjustment'
    quantity INTEGER NOT NULL,
    reference_type VARCHAR(50), -- 'receipt', 'manual', 'sale'
    reference_id UUID,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

-- Alerts & Notifications
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL, -- 'low_stock', 'expiry_warning'
    severity VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    title VARCHAR(255) NOT NULL,
    message TEXT,
    is_read BOOLEAN DEFAULT false,
    is_sent_email BOOLEAN DEFAULT false,
    sent_email_at TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Email Queue
CREATE TABLE email_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    recipient_email VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body_html TEXT NOT NULL,
    body_text TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error_message TEXT,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit Log
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    changes JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_products_user_id ON products(user_id);
CREATE INDEX idx_products_barcode ON products(barcode_gtin);
CREATE INDEX idx_products_low_stock ON products(user_id, current_stock) WHERE current_stock <= critical_stock_level;
CREATE INDEX idx_receipts_user_id ON receipts(user_id);
CREATE INDEX idx_receipts_status ON receipts(processing_status);
CREATE INDEX idx_receipt_items_product ON receipt_items(product_id);
CREATE INDEX idx_stock_transactions_product ON stock_transactions(product_id);
CREATE INDEX idx_alerts_user_unread ON alerts(user_id, is_read) WHERE is_read = false;
CREATE INDEX idx_email_queue_status ON email_queue(status) WHERE status = 'pending';
```

---

## 🔧 API Endpoints

### Authentication
```
POST   /api/v1/auth/register          - Kullanıcı kaydı
POST   /api/v1/auth/login             - Giriş (JWT token)
POST   /api/v1/auth/logout            - Çıkış
POST   /api/v1/auth/refresh           - Token yenileme
GET    /api/v1/auth/me                - Kullanıcı bilgileri
PUT    /api/v1/auth/profile           - Profil güncelleme
POST   /api/v1/auth/change-password   - Şifre değiştirme
```

### Receipts (Fişler)
```
POST   /api/v1/receipts/upload        - Fiş yükleme + OCR
GET    /api/v1/receipts               - Fiş listesi (pagination)
GET    /api/v1/receipts/{id}          - Fiş detayı
PUT    /api/v1/receipts/{id}          - Fiş güncelleme
DELETE /api/v1/receipts/{id}          - Fiş silme
POST   /api/v1/receipts/{id}/reprocess - Yeniden işleme
GET    /api/v1/receipts/{id}/items    - Fiş kalemleri
PUT    /api/v1/receipts/items/{id}    - Kalem güncelleme
```

### Products
```
GET    /api/v1/products               - Ürün listesi
POST   /api/v1/products               - Ürün oluşturma
GET    /api/v1/products/{id}          - Ürün detayı
PUT    /api/v1/products/{id}          - Ürün güncelleme
DELETE /api/v1/products/{id}          - Ürün silme
POST   /api/v1/products/bulk          - Toplu ürün ekleme
GET    /api/v1/products/low-stock     - Düşük stoklu ürünler
GET    /api/v1/products/{id}/history  - Stok geçmişi
```

### Stock Management
```
POST   /api/v1/stock/adjust           - Stok ayarlama
GET    /api/v1/stock/transactions     - İşlem geçmişi
GET    /api/v1/stock/summary          - Stok özeti
GET    /api/v1/stock/stats            - İstatistikler
```

### Alerts & Notifications
```
GET    /api/v1/alerts                 - Uyarı listesi
GET    /api/v1/alerts/{id}            - Uyarı detayı
PUT    /api/v1/alerts/{id}/read       - Okundu işaretle
DELETE /api/v1/alerts/{id}            - Uyarı sil
GET    /api/v1/alerts/unread-count    - Okunmamış sayısı
```

### Dashboard
```
GET    /api/v1/dashboard/summary      - Genel özet
GET    /api/v1/dashboard/charts       - Grafik verileri
GET    /api/v1/dashboard/recent       - Son aktiviteler
```

### Settings
```
GET    /api/v1/settings               - Kullanıcı ayarları
PUT    /api/v1/settings               - Ayar güncelleme
GET    /api/v1/settings/notifications - Bildirim tercihleri
PUT    /api/v1/settings/notifications - Bildirim güncelleme
```

---

## 🎯 MVP Geliştirme Fazları

### Faz 1: Temel Altyapı (1-2 gün)
- [x] Proje yapısı kurulumu
- [ ] PostgreSQL database setup
- [ ] Backend API skeleton (FastAPI)
- [ ] Authentication sistemi (JWT)
- [ ] Database migrations (Alembic)
- [ ] Docker containerization
- [ ] Basic logging

### Faz 2: OCR ve Fiş İşleme (2-3 gün)
- [ ] Tesseract OCR entegrasyonu
- [ ] Image preprocessing (OpenCV)
- [ ] Receipt parsing logic
- [ ] Product matching algoritması
- [ ] Async task processing (Celery)
- [ ] File upload ve storage

### Faz 3: Stok Yönetimi (1-2 gün)
- [ ] Product CRUD işlemleri
- [ ] Stock transaction sistemi
- [ ] Real-time stock update
- [ ] Concurrent transaction handling
- [ ] Stock history tracking

### Faz 4: Uyarı Sistemi (1-2 gün)
- [ ] Alert generation engine
- [ ] Email notification (SendGrid/SMTP)
- [ ] Web notification (WebSocket/SSE)
- [ ] Alert management API
- [ ] Notification preferences

### Faz 5: Frontend Dashboard (2-3 gün)
- [ ] Next.js proje kurulumu
- [ ] Authentication UI
- [ ] Dashboard ana sayfa
- [ ] Receipt upload ve görüntüleme
- [ ] Product management UI
- [ ] Alert/notification UI
- [ ] Charts ve istatistikler

### Faz 6: Test ve Optimizasyon (1-2 gün)
- [ ] Unit testler
- [ ] Integration testler
- [ ] Performance testing
- [ ] Security audit
- [ ] Bug fixes

### Faz 7: Deployment (1 gün)
- [ ] Production Docker images
- [ ] CI/CD pipeline
- [ ] Cloud deployment
- [ ] Monitoring setup
- [ ] Documentation

---

## 🔐 Güvenlik Özellikleri

1. **Authentication & Authorization**
   - JWT tokens (access + refresh)
   - Secure password hashing (bcrypt)
   - Rate limiting
   - CORS configuration

2. **Data Security**
   - SQL injection prevention
   - XSS protection
   - CSRF tokens
   - Encrypted sensitive data
   - Secure file uploads

3. **Infrastructure Security**
   - HTTPS only
   - Environment variables
   - Secret management
   - Database connection pooling
   - Regular security updates

---

## 📈 Ölçeklenebilirlik Stratejisi

1. **Database**
   - Connection pooling
   - Read replicas
   - Indexing optimization
   - Partitioning (future)

2. **Application**
   - Horizontal scaling
   - Load balancing
   - Caching (Redis)
   - CDN for static files

3. **File Storage**
   - Object storage (S3)
   - Image optimization
   - CDN integration

4. **Monitoring**
   - Application metrics
   - Database performance
   - Error tracking
   - User analytics

---

## 🚀 Deployment Stratejisi

### Development
```bash
docker-compose up -d
```

### Staging
```bash
docker build -t retail-ai-backend:staging .
docker push registry/retail-ai-backend:staging
kubectl apply -f k8s/staging/
```

### Production
```bash
docker build -t retail-ai-backend:v1.0.0 .
docker push registry/retail-ai-backend:v1.0.0
kubectl apply -f k8s/production/
```

---

## 📊 Başarı Kriterleri

### MVP Acceptance Criteria

1. ✅ Kullanıcı fiş fotoğrafı yükleyebilir
2. ✅ OCR %85+ doğrulukla ürünleri tanır
3. ✅ Stok otomatik güncellenir
4. ✅ Düşük stok uyarısı email gönderir
5. ✅ Dashboard gerçek zamanlı verileri gösterir
6. ✅ Response time < 2s (çoğu endpoint)
7. ✅ 100+ concurrent user desteği
8. ✅ %99.5 uptime

### Performance Targets

- OCR Processing: < 5 saniye
- API Response: < 500ms (p95)
- Page Load: < 2 saniye
- Database Queries: < 100ms (p95)

---

## 📝 Notlar

- SKT taraması MVP dışında ama veri modeli hazır
- Mobil app MVP dışında ama API hazır
- Multi-tenant MVP dışında ama user isolation var
- Advanced analytics MVP dışında
- Automated ordering MVP dışında

---

**Proje Sahibi**: Retail AI Team
**Versiyon**: MVP 1.0
**Tarih**: 2025
**Status**: 🚧 Development
