# RetailAI - Akıllı Fatura & Stok Yönetim Sistemi 🏪✨

Modern market/marketler için akıllı stok yönetimi ve fatura işleme sistemi.
**Tamamen offline çalışır, demo hazır!**

## ✨ Özellikler
- 📄 **CSV Fatura Yükleme** - Toplu fatura import (otomatik ürün ve batch oluşturma)
- 🎯 **Akıllı Dashboard** - İşe yarar görevler (indirim önerileri, sipariş uyarıları, FIFO organizasyon)
- 📊 **Stok Trend Grafiği** - Son 7 günlük stok seviyesi takibi
- ⚠️ **SKT Uyarıları** - Yaklaşan son kullanma tarihi takibi (1-7 gün)
- 🔍 **Ürün Eşleştirme** - Typeahead arama + fuzzy matching
- 📦 **Batch Tracking** - LOT kodu ve SKT takibi
- 🖼️ **Görsel Ürün Yönetimi** - Image URL ile toplu CSV import
- 📑 **PDF Export** - Fatura detaylarını PDF olarak indir

## 🚀 Hızlı Başlangıç (2 dakika)

### 1. Kurulum
```bash
git clone https://github.com/HallowedEngine/retail-ai.git
cd retail-ai
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Serveri Başlat
```bash
python -m uvicorn app.main:app --reload
```

### 3. Demo Verisini Yükle
```bash
# Kapsamlı demo verisi (47 ürün + batch'ler + faturalar + uyarılar)
curl -X POST http://localhost:8000/seed/demo_data -u admin:retailai2025

# Database migration (status kolonları ekle)
curl -X POST http://localhost:8000/migrate/add_status_columns -u admin:retailai2025
```

### 4. Tarayıcıda Aç
```
http://localhost:8000/ui/
```

**Giriş:** `admin` / `retailai2025`

---

## 📋 Demo Verisi İçeriği

`/seed/demo_data` endpoint'i şunları oluşturur:

✅ **47 ürün** - 10 kategori:
- Süt Ürünleri (Süt, Yoğurt, Peynir, Kaşar, Tereyağı)
- Fırın (Ekmek, Simit, Kepek Ekmeği)
- Sebze-Meyve (Domates, Salatalık, Muz, Elma, Portakal)
- Et-Tavuk (Tavuk, Kıyma, Dana Kuşbaşı)
- Temel Gıda (Makarna, Pirinç, Bulgur, Şeker, Tuz)
- Kahvaltılık (Zeytin, Reçel, Bal)
- İçecek (Çay, Kahve, Su, Kola, Ayran)
- Atıştırmalık (Çikolata, Cips, Bisküvi)
- Temizlik (Deterjan, Sabun, Çamaşır Suyu)
- Kişisel Bakım (Diş Macunu, Şampuan, Traş Kremi)

✅ **16 batch** kayıt:
- 4 acil SKT (1-3 gün) → %15-20 indirim önerileri
- 4 yakın SKT (4-7 gün) → %10 indirim önerileri
- 8 normal stok

✅ **6 fatura** (son 5 gün içinde)

✅ **8 SKT uyarısı** (otomatik)

---

## 📄 CSV Fatura Yükleme

### Web Arayüzünden:
1. `http://localhost:8000/ui/invoice.html` sayfasını aç
2. Yeşil kutuda **"CSV Fatura Yükle"** bölümünü bul
3. `demo_market_fatura.csv` veya `demo_market_fatura_2.csv` dosyasını seç
4. **"Yükle & İşle"** butonuna tıkla
5. Fatura otomatik açılacak! 🎯

### CSV Format:
```csv
urun_adi,barkod,adet,birim_fiyat,skt_tarihi,kategori
Süt Tam Yağlı 1L,8690504321001,24,28.50,2024-12-03,Süt Ürünleri
Ekmek 350g,8690504321002,50,8.50,2024-11-27,Fırın
```

**Otomatik:**
- Ürün yoksa oluşturulur (SKU otomatik)
- Batch ve LOT kodu otomatik oluşturulur
- SKT takibi başlar
- Expiry alert'leri güncellenir

---

## 🎨 Ürün Toplu İçe Aktarma

### Web Arayüzünden:
1. `http://localhost:8000/ui/products.html` sayfasını aç
2. `sample_products_bulk_import.csv` dosyasını seç
3. **"Önizle"** → **"Toplu Yükle"**

### CSV Format:
```csv
sku,name,category,barcode_gtin,shelf_life_days,image_url
AYR100,Ayran 200ml,süt,8690000016,7,https://via.placeholder.com/150
KRP250,Tereyağı 250g,süt,8690000017,60,https://via.placeholder.com/150
```

---

## 🔐 Giriş Bilgileri

```
Username: admin
Password: retailai2025