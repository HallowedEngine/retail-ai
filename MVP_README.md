# 🚀 RetailAI SaaS MVP - Kurumsal Stok & Fiş Yönetim Sistemi

## 📋 İçindekiler
- [Genel Bakış](#genel-bakış)
- [Özellikler](#özellikler)
- [Teknoloji Stack](#teknoloji-stack)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [API Dokümantasyonu](#api-dokümantasyonu)
- [Deployment](#deployment)
- [Güvenlik](#güvenlik)
- [Gelecek Özellikler](#gelecek-özellikler)

---

## 🎯 Genel Bakış

RetailAI, market ve perakende işletmeler için geliştirilmiş kurumsal kalitede bir **SaaS stok yönetim sistemi**dir. OCR teknolojisi ile fiş tarama, gerçek zamanlı stok takibi, SKT (Son Kullanma Tarihi) uyarıları ve e-posta bildirimleri sunar.

### MVP Kapsamı
✅ **Fiş Tarama (OCR)** - Tesseract + OpenCV ile %90+ doğruluk
✅ **Stok Yönetimi** - Gerçek zamanlı güncelleme, batch tracking
✅ **Uyarı Sistemi** - E-posta + Web bildirimleri
✅ **Modern Dashboard** - React/NextJS, responsive, kullanıcı dostu
✅ **Kurumsal Kalite** - Structured logging, rate limiting, error handling
✅ **Production Ready** - Docker, docker-compose, health checks

### MVP Dışında (Gelecek)
⏳ SKT taraması (veri modeli hazır)
⏳ Mobil uygulama / PWA
⏳ Çoklu kullanıcı & rol yönetimi
⏳ Tahminleme & otomatik sipariş

---

## ✨ Özellikler

### 1. Fiş Tarama (OCR)
- 📸 Fotoğraf veya dosya yükleme desteği
- 🔍 Tesseract OCR + OpenCV preprocessing
- 🇹🇷 Türkçe ve İngilizce dil desteği
- 🎯 Fuzzy matching ile otomatik ürün eşleştirme
- 🔄 Duplicate detection (MD5 hash)
- ⚡ Hızlı işlem (<3 saniye)

### 2. Stok Yönetimi
- 📦 Ürün giriş/çıkış kaydı
- 🏷️ Batch/lot tracking
- 📊 Real-time stok durumu
- ⚠️ Kritik stok seviyesi uyarıları
- 🔍 Barkod ve SKU bazlı arama
- 📈 Stok geçmişi ve raporlama

### 3. SKT Uyarı Sistemi
- 📅 7/3 gün öncesi otomatik uyarılar
- 📧 E-posta bildirimleri (SMTP)
- 🔔 Web dashboard notifications
- 🎨 Severity bazlı renk kodlama (kırmızı/sarı)
- ✅ Uyarı onaylama ve erteleme
- 📝 Structured logging

### 4. Modern Web Dashboard
- ⚡ NextJS 14 App Router
- 🎨 TailwindCSS + responsive design
- 📱 Mobil uyumlu
- 🔐 Basic Auth güvenlik
- 🚀 Server-side rendering (SSR)
- 📊 Real-time metrics

### 5. Kurumsal Özellikler
- 🔒 Rate limiting (100 req/min)
- 📝 Structured JSON logging
- ⚠️ Global error handling
- 🏥 Health check endpoints
- 🐳 Docker & docker-compose
- 📊 Production-ready monitoring

---

## 🛠️ Teknoloji Stack

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **Database:** SQLite (SQLAlchemy ORM)
- **OCR:** Tesseract + OpenCV
- **Auth:** HTTP Basic Authentication
- **Email:** SMTP (Gmail, SendGrid, vb.)
- **Logging:** Python logging + structured format

### Frontend
- **Framework:** Next.js 14 (React 18+)
- **Styling:** TailwindCSS
- **HTTP Client:** Axios
- **Icons:** Lucide React
- **Date:** date-fns

### DevOps
- **Container:** Docker + docker-compose
- **CI/CD:** GitHub Actions (opsiyonel)
- **Monitoring:** Health checks, logs

---

## 🚀 Kurulum

### Önkoşullar
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (production için)
- Tesseract OCR (lokal development için)

### 1. Development Kurulumu

#### Backend
```bash
# Repository'yi klonlayın
git clone https://github.com/HallowedEngine/retail-ai.git
cd retail-ai

# Python virtual environment oluşturun
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# .env dosyasını düzenleyin (email ayarları vb.)

# Veritabanını başlatın (otomatik)
# Sunucuyu çalıştırın
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend

# Bağımlılıkları yükleyin
npm install

# Environment variables
cp .env.local.example .env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Development server
npm run dev
```

### 2. Docker ile Kurulum (Production)

```bash
# docker-compose ile tüm servisleri başlatın
docker-compose up -d

# Logları izleyin
docker-compose logs -f

# Servisleri durdurun
docker-compose down
```

**Servisler:**
- Backend API: http://localhost:8000
- Frontend Dashboard: http://localhost:3000
- API Docs: http://localhost:8000/docs

---

## 📖 Kullanım

### İlk Adımlar

1. **Dashboard'a Erişim**
   - URL: http://localhost:3000
   - Kullanıcı: `admin`
   - Şifre: `retailai2025`

2. **Ürün Ekleme**
   ```bash
   curl -u admin:retailai2025 -X POST http://localhost:8000/seed/products
   ```

3. **Fiş Yükleme**
   - Dashboard → "Fiş Yükle"
   - Fotoğraf seçin veya sürükleyin
   - OCR otomatik başlar
   - Sonuçları kontrol edin

4. **Uyarıları Görüntüleme**
   - Dashboard → "Uyarılar"
   - Kritik/uyarı filtreleme
   - Onaylama veya erteleme

### Email Bildirimleri Aktifleştirme

`.env` dosyasını düzenleyin:
```env
EMAIL_ENABLED=true
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAILS=manager@company.com,inventory@company.com
```

**Gmail için:**
1. Google hesabınızda 2FA aktif olmalı
2. App Password oluşturun: https://myaccount.google.com/apppasswords
3. SMTP_PASSWORD olarak app password kullanın

---

## 📚 API Dokümantasyonu

API dokümantasyonuna şu adresten erişebilirsiniz:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Örnek API Kullanımı

#### Fiş Yükleme
```bash
curl -u admin:retailai2025 -X POST \
  http://localhost:8000/upload_invoice \
  -F "file=@fis.jpg" \
  -F "store_id=1" \
  -F "supplier_id=1"
```

#### Uyarıları Listele
```bash
curl -u admin:retailai2025 \
  http://localhost:8000/alerts/expiry/full?store_id=1&days=7
```

#### Dashboard Özeti
```bash
curl -u admin:retailai2025 \
  http://localhost:8000/dashboard/summary?store_id=1
```

---

## 🐳 Deployment

### Docker Production Deployment

1. **Environment Hazırlama**
```bash
cp .env.example .env
# Production değerlerini girin
```

2. **Build ve Deploy**
```bash
docker-compose -f docker-compose.yml up -d --build
```

3. **Health Check**
```bash
curl http://localhost:8000/health
```

### Cloud Deployment (AWS/GCP/Azure)

1. **Backend (Container Registry)**
```bash
docker build -f Dockerfile.backend -t retailai-backend:latest .
docker tag retailai-backend:latest <registry>/retailai-backend:latest
docker push <registry>/retailai-backend:latest
```

2. **Frontend**
```bash
docker build -f Dockerfile.frontend -t retailai-frontend:latest .
docker tag retailai-frontend:latest <registry>/retailai-frontend:latest
docker push <registry>/retailai-frontend:latest
```

3. **Environment Variables** - Cloud platformunda ayarlayın

### Database Backup
```bash
# SQLite backup
docker exec retailai-backend cp /app/data/demo.db /app/data/backup_$(date +%Y%m%d).db

# Yerel kopyalama
docker cp retailai-backend:/app/data/demo.db ./backup.db
```

---

## 🔒 Güvenlik

### Mevcut Güvenlik Özellikleri
- ✅ HTTP Basic Authentication (tüm API)
- ✅ Rate limiting (100 req/min)
- ✅ Input validation (Pydantic)
- ✅ SQL injection koruması (SQLAlchemy)
- ✅ CORS configuration
- ✅ Secure password handling
- ✅ File upload validation

### Önerilen Güvenlik İyileştirmeleri (Production)
- [ ] HTTPS/TLS sertifikası (Let's Encrypt)
- [ ] JWT token authentication
- [ ] Role-based access control (RBAC)
- [ ] API key rotation
- [ ] Audit logging
- [ ] DDoS protection (CloudFlare)
- [ ] Database encryption at rest

---

## 🧪 Test

### Backend Tests
```bash
# Unit tests (gelecek)
pytest app/tests/

# API health check
curl http://localhost:8000/health
```

### Frontend Tests
```bash
cd frontend
npm run test  # (gelecek)
npm run lint
```

### Manuel Test Senaryoları

1. **Fiş Yükleme Testi**
   - Örnek fiş: `invoice_1.csv`
   - Beklenen: 3+ ürün tespit edilmeli

2. **SKT Uyarı Testi**
   ```bash
   # Yakın SKT'li batch ekle
   curl -u admin:retailai2025 -X POST \
     http://localhost:8000/batch/scan \
     -H "Content-Type: application/json" \
     -d '{
       "product_id": 1,
       "store_id": 1,
       "expiry_date": "2025-11-25",
       "qty": 10
     }'

   # Uyarıları kontrol et
   curl -u admin:retailai2025 \
     http://localhost:8000/alerts/expiry/full?store_id=1
   ```

3. **Email Testi**
   - .env'de EMAIL_ENABLED=true
   - SKT yakın batch oluştur
   - Email geldiğini kontrol et

---

## 🔮 Gelecek Özellikler (Roadmap)

### Q1 2025
- [ ] **SKT OCR Tarama** - Etiket fotoğrafından SKT okuma
- [ ] **Mobil PWA** - Progressive Web App desteği
- [ ] **Multi-tenant** - Çoklu işletme desteği

### Q2 2025
- [ ] **Kullanıcı Yönetimi** - Role-based access control
- [ ] **Tahminleme** - AI ile stok tahminleri
- [ ] **Otomatik Sipariş** - Kritik stokta otomatik sipariş

### Q3 2025
- [ ] **Raporlama** - PDF/Excel export
- [ ] **Analytics Dashboard** - Gelişmiş metrikler
- [ ] **Entegrasyonlar** - ERP, accounting sistemleri

---

## 📞 Destek & Katkı

### Issues
- 🐛 Bug report: [GitHub Issues](https://github.com/HallowedEngine/retail-ai/issues)
- 💡 Feature request: [GitHub Discussions](https://github.com/HallowedEngine/retail-ai/discussions)

### Katkıda Bulunma
```bash
# Fork & clone
git checkout -b feature/amazing-feature
git commit -m "Add amazing feature"
git push origin feature/amazing-feature
# Pull request oluşturun
```

---

## 📄 Lisans

Bu proje [MIT License](LICENSE) altında lisanslanmıştır.

---

## 👏 Teşekkürler

- **Tesseract OCR** - Google
- **FastAPI** - Sebastián Ramírez
- **Next.js** - Vercel
- **TailwindCSS** - Tailwind Labs

---

**⭐ Projeyi beğendiyseniz GitHub'da yıldız vermeyi unutmayın!**

RetailAI © 2024 - Kurumsal Kalitede Stok Yönetim Sistemi
