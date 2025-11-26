# 🎯 Demo Hazırlık Kontrol Listesi

Yarınki demo için son kontroller:

## ✅ Kurulum Kontrolleri

- [ ] Git repo güncel (`git pull origin claude/retailai-fix-issues-01EAcYjcbEaP3p45cys1Gdjm`)
- [ ] Virtual environment aktif (`venv\Scripts\activate`)
- [ ] Dependencies kurulu (`pip install -r requirements.txt`)
- [ ] Server çalışıyor (`python -m uvicorn app.main:app --reload`)

## ✅ Demo Veri Kontrolleri

- [ ] Demo verisi yüklendi (`curl -X POST http://localhost:8000/seed/demo_data -u admin:retailai2025`)
- [ ] Migration çalıştırıldı (`curl -X POST http://localhost:8000/migrate/add_status_columns -u admin:retailai2025`)
- [ ] Dashboard açılıyor (`http://localhost:8000/ui/`)
- [ ] Login çalışıyor (`admin` / `retailai2025`)

## ✅ Özellik Kontrolleri

### Dashboard
- [ ] "Bugün yapılacaklar" görevleri gösteriyor (indirim önerileri, teslimat, FIFO)
- [ ] Stok trend grafiği yükleniyor
- [ ] SKT uyarı sayısı gösteriliyor

### CSV Fatura Yükleme
- [ ] Invoice sayfası açılıyor (`http://localhost:8000/ui/invoice.html`)
- [ ] Yeşil "CSV Fatura Yükle" kutusu var
- [ ] `demo_market_fatura.csv` yüklenebiliyor
- [ ] Başarılı mesaj geliyor (30 ürün, 30 batch)
- [ ] Fatura otomatik açılıyor

### Ürün Yönetimi
- [ ] Ürünler sayfası açılıyor (`http://localhost:8000/ui/products.html`)
- [ ] `sample_products_bulk_import.csv` yüklenebiliyor
- [ ] Önizleme çalışıyor
- [ ] Toplu yükleme başarılı

## 🎤 Demo Senaryosu

### 1. Giriş (30 saniye)
```
"RetailAI - modern marketler için akıllı stok yönetim sistemi.
Tamamen offline çalışır, verileriniz sizde kalır."
```

### 2. Dashboard Gösterisi (1 dakika)
- Ana dashboard'u aç
- "Bugün yapılacaklar" görevlerini göster:
  - 🏷️ SKT yaklaşan ürünler için indirim önerileri
  - 📦 Düşük stok için sipariş uyarıları
  - 🚚 Teslimat planlaması
  - 📍 FIFO depo organizasyonu
- Stok trend grafiğini göster

### 3. CSV Fatura Yükleme (2 dakika)
- Invoice sayfasını aç
- `demo_market_fatura.csv` yükle
- "30 ürün, 30 batch oluşturuldu" mesajını göster
- Fatura detaylarını göster
- Dashboard'a dön → yeni SKT uyarılarını göster

### 4. Soru-Cevap (1 dakika)
- "Sistem tamamen offline çalışır"
- "CSV ile kolay entegrasyon"
- "Otomatik SKT takibi ve indirim önerileri"

## 📋 Demo Sonrası

- [ ] CSV dosyalarını market sahibine ver
- [ ] GitHub repo linkini paylaş
- [ ] README'deki kurulum adımlarını göster

## 🚨 Olası Sorunlar & Çözümler

### Problem: Dashboard boş görünüyor
**Çözüm:** Demo verisini yükle ve migration'ı çalıştır
```bash
curl -X POST http://localhost:8000/seed/demo_data -u admin:retailai2025
curl -X POST http://localhost:8000/migrate/add_status_columns -u admin:retailai2025
```

### Problem: CSV yüklenmiyor
**Çözüm:**
- Invoice sayfasından yükle (products sayfasından değil!)
- Format kontrol et: `urun_adi,barkod,adet,birim_fiyat,skt_tarihi,kategori`

### Problem: Login çalışmıyor
**Çözüm:**
- Username: `admin`
- Password: `retailai2025`
- Büyük/küçük harf duyarlı!

---

**Son Kontrol:** Tüm checkboxları işaretle, demo senaryosunu 1 kez prova et! 🎯
