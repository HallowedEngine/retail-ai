# RetailAI - Akıllı Fatura & Stok Yönetim Sistemi

Türkçe market fişlerini OCR ile okur, ürünleri otomatik tanır, stok günceller, SKT uyarısı verir, yeniden sipariş önerir.  
Tamamen offline çalışır, SaaS hazır!

## Özellikler
- Fatura fotoğrafı/CSV yükle → otomatik parse (%90+ doğruluk)
- Ürün görselleri ile toplu CSV import (`image_url` destekli)
- Fatura detay sayfası + tek tıkla PDF export
- SKT yaklaşan ürünler uyarısı (30/7/3 gün kala renkli)
- Dashboard + mağaza bazlı özet
- Ürün eşleştirme (typeahead arama + fuzzy matching)
- Duplicate kontrol (aynı SKU/barkod engellenir)

## Ekran Görüntüleri
![Fatura Detay + PDF](https://i.ibb.co.com/0jZxY7K/invoice.png)  
![Ürün Toplu Yükleme_csv](https://i.ibb.co.com/5Y7pQ2m/products.png)  
![SKT Uyarıları](https://i.ibb.co.com/9bY3kLm/alerts.png)

## Kurulum (30 saniye)
```bash
git clone https://github.com/HallowedEngine/retail-ai.git
cd retail-ai
python -m venv venv
venv\Scripts\activate  # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 🚀 Hızlı Demo Verisi Yükleme

Dashboard'ı sentetik verilerle doldurmak için:

```bash
# 1. Kapsamlı demo verisi yükle (15 ürün + batch'ler + invoice'lar + alert'ler)
curl -X POST http://localhost:8000/seed/demo_data -u admin:retailai2025

# Demo verisi içeriği:
# ✅ 15 ürün (süt, fırın, konserve, içecek, atıştırmalık)
# ✅ 14 batch (6 yaklaşan SKT'li, 8 normal stok)
# ✅ 3 invoice (her biri 4-6 satır)
# ✅ Otomatik expiry alert'leri
```

### 📋 Bulk Import için CSV Kullanımı

Örnek CSV dosyası: `sample_products_bulk_import.csv`

```bash
# Web arayüzünden:
1. http://localhost:8000/ui/
2. "Bulk Import" menüsüne tıkla
3. "sample_products_bulk_import.csv" dosyasını seç
4. "Önizle" → "Toplu Yükle"
```

**CSV Format:**
```csv
sku,name,category,barcode_gtin,shelf_life_days,image_url
AYR100,Ayran 200ml,süt,8690000016,7,https://via.placeholder.com/150
KRP250,Tereyağı 250g,süt,8690000017,60,https://via.placeholder.com/150
```

## 🔐 Giriş Bilgileri

```
Username: admin
Password: retailai2025