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
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload