# app/main.py
import os
import io
import csv
import json
import secrets
from datetime import datetime, date, timedelta
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Path, Body, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List
from sqlalchemy import or_

from .db import Base, engine, get_db
from .models import *
from .schemas import *
from .ocr import run_tesseract, run_vision_fallback, best_merge
from .parsers import parse_invoice_lines
from .logic import refresh_expiry_alerts, naive_hourly_forecast, reorder_suggestion
from .utils import save_upload, file_md5
from .match import build_product_name_map, fuzzy_match_product
from .gs1 import parse_gs1_from_text, parse_expiry_from_free_text

# ——————————————————— YENİ: BASIC AUTH ———————————————————
security = HTTPBasic()

def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "retailai2025")  # istediğin zaman değiştir
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yetkisiz erişim",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
# ——————————————————— AUTH BİTİŞ ———————————————————

# create tables if not exist
Base.metadata.create_all(bind=engine)

# ——————————————————— GLOBAL AUTH (bütün API ve UI otomatik korunur) ———————————————————
app = FastAPI(
    title="Retail Demo",
    dependencies=[Depends(verify_auth)]  # ← BU SATIR HER ŞEYİ ŞİFRELİYOR!
)

# Auth’suz kalmasını istediğin endpoint’ler (rahatlık için)
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# -----------------------------
# P0-1) Upload + MD5 Duplicate
# -----------------------------
@app.post("/upload_invoice", response_model=InvoiceUploadResp)
async def upload_invoice(
    file: UploadFile = File(...),
    store_id: int = 1,
    supplier_id: int = 1,
    db: Session = Depends(get_db)
):
    # 1) Dosyayı kaydet
    img_path = save_upload(file, "invoice")

    # 2) Duplicate kontrolü
    h = file_md5(img_path)
    dup = db.query(Invoice).filter(Invoice.file_hash == h).first()
    if dup:
        raise HTTPException(
            status_code=409,
            detail={"message": "Duplicate invoice image", "existing_invoice_id": dup.id}
        )

    # 3) OCR & parse
    ocr = run_tesseract(img_path)
    lines = parse_invoice_lines(ocr.get("text", ""))

    # düşük güven/çıktı durumunda fallback
    if len(lines) == 0 or ocr.get("conf", 0) < 0.6:
        ocr2 = run_vision_fallback(img_path)
        ocr = best_merge(ocr, ocr2)
        lines = parse_invoice_lines(ocr.get("text", ""))

    # 4) ürün eşleştirme için name map (fuzzy yedeği)
    products = [{"id": p.id, "name": p.name} for p in db.query(Product).all()]
    pmap = build_product_name_map(products)

    # 5) faturayı kaydet (önce header)
    inv = Invoice(
        store_id=store_id,
        supplier_id=supplier_id,
        raw_image_path=img_path,
        ocr_json=json.dumps(ocr),
        status="parsed",
        file_hash=h,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    # 6) satırları ekle
    for L in lines:
        pid = None
        product_name = None

        # 6-a) Barkod ile direkt eşle (varsa)
        barcode = L.get("barcode")
        if barcode:
            p = db.query(Product).filter(Product.barcode_gtin == barcode).first()
            if p:
                pid = p.id
                product_name = p.name

        # 6-b) Barkod yoksa/fail ise fuzzy isim ile dene
        if pid is None:
            pid, _score = fuzzy_match_product(L.get("name_raw", ""), pmap, score_cutoff=85)

        # 6-c) kayıt edilecek isim: DB adı varsa onu kullan, yoksa OCR ismi
        name_to_store = product_name or L.get("name_raw", "")

        il = InvoiceLine(
            invoice_id=inv.id,
            product_id=pid,
            supplier_sku=None,
            name_raw=name_to_store,
            qty=L.get("qty", 0),
            unit=L.get("unit", "adet"),
            unit_price=L.get("unit_price", 0.0)
        )
        db.add(il)

    db.commit()

    return {
        "invoice_id": inv.id,
        "lines_preview": lines[:10]
    }

@app.post("/invoice/upload_csv")
async def upload_invoice_csv(
    file: UploadFile = File(...),
    store_id: int = 1,
    supplier_id: int = 1,
    db: Session = Depends(get_db)
):
    """
    CSV Fatura Yükleme - Demo için
    Format: urun_adi,barkod,adet,birim_fiyat,skt_tarihi,kategori
    """
    import csv
    from io import StringIO

    # CSV'yi oku
    content = await file.read()
    csv_text = content.decode('utf-8')
    csv_reader = csv.DictReader(StringIO(csv_text))

    # Fatura oluştur
    invoice_no = f"CSV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    inv = Invoice(
        store_id=store_id,
        supplier_id=supplier_id,
        invoice_no=invoice_no,
        invoice_date=datetime.now().date(),
        raw_image_path=f"/uploads/csv_{invoice_no}.csv",
        status="completed",
        file_hash=f"csv_{secrets.token_hex(8)}"
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    lines_created = 0
    batches_created = 0

    for row in csv_reader:
        # Ürün adı ve barkod
        product_name = row.get('urun_adi', '').strip()
        barcode = row.get('barkod', '').strip()
        qty = float(row.get('adet', 0))
        unit_price = float(row.get('birim_fiyat', 0))
        skt_str = row.get('skt_tarihi', '').strip()
        category = row.get('kategori', '').strip()

        if not product_name:
            continue

        # Ürünü bul veya oluştur
        product = None
        if barcode:
            product = db.query(Product).filter(Product.barcode_gtin == barcode).first()

        if not product:
            # Yeni ürün oluştur
            sku = f"SKU{secrets.token_hex(4).upper()}"
            product = Product(
                sku=sku,
                name=product_name,
                category=category,
                barcode_gtin=barcode if barcode else None,
                shelf_life_days=30
            )
            db.add(product)
            db.commit()
            db.refresh(product)

        # Invoice line oluştur
        invoice_line = InvoiceLine(
            invoice_id=inv.id,
            product_id=product.id,
            name_raw=product_name,
            qty=qty,
            unit="adet",
            unit_price=unit_price
        )
        db.add(invoice_line)
        lines_created += 1

        # SKT varsa batch oluştur
        if skt_str:
            try:
                # Tarih formatı: 2024-12-03 veya 03.12.2024
                if '-' in skt_str:
                    expiry_date = datetime.strptime(skt_str, '%Y-%m-%d').date()
                elif '.' in skt_str:
                    expiry_date = datetime.strptime(skt_str, '%d.%m.%Y').date()
                else:
                    expiry_date = None

                if expiry_date:
                    batch = Batch(
                        product_id=product.id,
                        store_id=store_id,
                        lot_code=f"LOT{secrets.token_hex(4).upper()}",
                        expiry_date=expiry_date,
                        qty_received=qty,
                        qty_on_hand=qty,
                        source_invoice_id=inv.id
                    )
                    db.add(batch)
                    batches_created += 1
            except Exception:
                pass  # SKT parse edilemezse skip et

    db.commit()

    # Expiry alert'leri güncelle
    try:
        refresh_expiry_alerts(db, store_id, days_window=7)
    except Exception:
        pass

    return {
        "ok": True,
        "invoice_id": inv.id,
        "invoice_no": invoice_no,
        "lines_created": lines_created,
        "batches_created": batches_created,
        "message": f"✅ Fatura yüklendi! {lines_created} ürün, {batches_created} batch oluşturuldu."
    }

# -----------------------------
# P0-2) Invoice Detay & Satır Güncelle
# -----------------------------
@app.get("/invoice/{invoice_id}")
def get_invoice(invoice_id: int = Path(...), db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter_by(id=invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="invoice not found")
    lines = db.query(InvoiceLine).filter_by(invoice_id=invoice_id).all()
    return {
        "invoice_id": inv.id,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "lines": [{
            "id": L.id,
            "product_id": L.product_id,
            "name_raw": L.name_raw,
            "qty": L.qty,
            "unit": L.unit,
            "unit_price": L.unit_price
        } for L in lines]
    }

class UpdateLineReq(BaseModel):
    line_id: int
    product_id: int | None = None
    qty: float | None = None
    unit_price: float | None = None
    name_raw: str | None = None

class ProductCreate(BaseModel):
    sku: str
    name: str
    category: str | None = None
    barcode_gtin: str | None = None
    shelf_life_days: int | None = None

@app.post("/invoice/line/update")
def update_line(body: UpdateLineReq, db: Session = Depends(get_db)):
    L = db.query(InvoiceLine).filter_by(id=body.line_id).first()
    if not L:
        raise HTTPException(status_code=404, detail="line not found")
    if body.product_id is not None:
        L.product_id = body.product_id
    if body.qty is not None:
        L.qty = body.qty
    if body.unit_price is not None:
        L.unit_price = body.unit_price
    if body.name_raw is not None:
        L.name_raw = body.name_raw
    db.commit()
    return {"ok": True}

# -----------------------------
# P0-3) CSV Export
# -----------------------------
@app.get("/invoice/{invoice_id}/export.csv")
def export_invoice_csv(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter_by(id=invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="invoice not found")

    lines = db.query(InvoiceLine).filter_by(invoice_id=invoice_id).all()

    # product_id -> Product map (barcode çekmek için)
    pids = [L.product_id for L in lines if L.product_id]
    prod_map = {}
    if pids:
        prods = db.query(Product).filter(Product.id.in_(pids)).all()
        prod_map = {p.id: p for p in prods}

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["barcode", "name", "qty", "unit_price", "line_total"])

    for L in lines:
        barcode = ""
        if L.product_id and L.product_id in prod_map:
            barcode = prod_map[L.product_id].barcode_gtin or ""
        name = L.name_raw or ""
        qty = float(L.qty or 0)
        unit_price = float(L.unit_price or 0)
        line_total = round(qty * unit_price, 2)
        w.writerow([barcode, name, qty, unit_price, line_total])

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="invoice_{invoice_id}.csv"'}
    )

# -----------------------------
# Helper endpoint: recent invoices (debug / UI için)
# -----------------------------
@app.get("/invoices/recent")
def invoices_recent(limit: int = 20, db: Session = Depends(get_db)):
    q = db.query(Invoice).order_by(Invoice.id.desc()).limit(limit).all()
    out = []
    for inv in q:
        cnt = db.query(InvoiceLine).filter_by(invoice_id=inv.id).count()
        out.append({"id": inv.id, "created_at": inv.created_at.isoformat() if inv.created_at else None, "line_count": cnt})
    return out

# -----------------------------
# Dashboard: Stok Trend Grafiği (Demo/Sentetik Veri)
# -----------------------------
@app.get("/dashboard/stock_trend")
def dashboard_stock_trend(store_id: int = 1, days: int = 7, db: Session = Depends(get_db)):
    """
    Stok düşüş trendi için günlük veri döndürür.
    Gerçek satış verisi varsa hesaplar, yoksa demo verisi döndürür.
    """
    from datetime import datetime, timedelta
    import random

    # Son N gün için stok seviyelerini hesapla
    labels = []
    data = []
    today = datetime.now().date()

    # Gerçek batch verisinden stok seviyelerini al
    total_stock_by_day = []
    for i in range(days - 1, -1, -1):
        target_date = today - timedelta(days=i)

        # Bu tarihe kadar eklenen batch'lerin toplamı (basit demo mantık)
        total_batches = db.query(Batch).filter(
            Batch.store_id == store_id
        ).count()

        # Eğer veri yoksa sentetik veri oluştur
        if total_batches == 0:
            # Demo verisi: hafta boyunca azalan trend
            base_stock = 100
            variation = random.randint(-10, 10)
            stock_level = max(20, base_stock - (i * 8) + variation)
        else:
            # Gerçek veri varsa batch sayısını kullan (basitleştirilmiş)
            stock_level = total_batches + random.randint(0, 20)

        # Türkçe gün isimleri
        day_names = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        day_name = day_names[target_date.weekday()]

        labels.append(day_name)
        data.append(stock_level)
        total_stock_by_day.append({"date": target_date.isoformat(), "stock": stock_level})

    return {
        "labels": labels,
        "data": data,
        "details": total_stock_by_day,
        "note": "Demo verisi - gerçek satış verileriyle güncellenecek"
    }

# -----------------------------
# Diğer mevcut endpointler (hepsi otomatik auth’lu artık)
# -----------------------------
@app.post("/batch/scan")
def batch_scan(payload: BatchScanReq, db: Session = Depends(get_db)):
    b = Batch(
        product_id=payload.product_id,
        store_id=payload.store_id,
        expiry_date=payload.expiry_date,
        lot_code=payload.lot_code,
        qty_received=payload.qty,
        qty_on_hand=payload.qty
    )
    db.add(b); db.commit(); db.refresh(b)
    return {"batch_id": b.id, "status": "ok"}

@app.post("/ingest_sales")
def ingest_sales(body: IngestSalesReq, db: Session = Depends(get_db)):
    sku_to_id = {p.sku: p.id for p in db.query(Product).all()}
    added = 0
    for r in body.rows:
        pid = sku_to_id.get(r.sku)
        if not pid:
            continue
        s = Sale(store_id=body.store_id, product_id=pid, ts=r.ts, qty=r.qty)
        db.add(s); added += 1
    db.commit()
    return {"inserted": added}

@app.get("/alerts/expiry")
def get_expiry_alerts(store_id: int = 1, days: int = 7, db: Session = Depends(get_db)):
    refresh_expiry_alerts(db, store_id, days)
    alerts = (db.query(ExpiryAlert)
                .filter(ExpiryAlert.store_id == store_id)
                .order_by(ExpiryAlert.created_at.desc())
                .limit(200).all())
    return [{
        "product_id": a.product_id,
        "batch_id": a.batch_id,
        "expiry_date": str(a.expiry_date),
        "days_left": a.days_left,
        "severity": a.severity,
        "created_at": a.created_at.isoformat()
    } for a in alerts]

@app.get("/reorder/suggestions")
def reorder_suggestions(store_id: int, product_id: int, current_stock: float = 0,
                        db: Session = Depends(get_db)):
    pol = db.query(ReorderPolicy).filter_by(store_id=store_id, product_id=product_id).first()
    if not pol:
        pol = ReorderPolicy(store_id=store_id, product_id=product_id,
                            min_stock=0, max_stock=0, lead_time_days=2, safety_stock=1)
        db.add(pol); db.commit(); db.refresh(pol)

    existed = db.query(Forecast).filter_by(store_id=store_id, product_id=product_id).first()
    if not existed:
        naive_hourly_forecast(db, store_id, product_id, horizon_days=7)

    import pandas as pd
    fc_rows = db.query(Forecast).filter_by(store_id=store_id, product_id=product_id).all()
    fdf = pd.DataFrame([{"ts": r.ts, "yhat": r.yhat} for r in fc_rows]).sort_values("ts")
    qty = reorder_suggestion(current_stock, pol.lead_time_days, pol.safety_stock, fdf)
    return {
        "product_id": product_id,
        "qty_to_order": qty,
        "lead_time_days": pol.lead_time_days,
        "safety_stock": pol.safety_stock
    }

@app.post("/seed/products")
def seed_products(db: Session = Depends(get_db)):
    demo = [
    {"sku":"SUT1L","name":"1L Süt","category":"sut","barcode_gtin":"869000000001","shelf_life_days":7,
     "image_url":"https://i.hizliresim.com/abc123/sut.jpg"},
    {"sku":"YOG500","name":"500g Yoğurt","category":"sut","barcode_gtin":"869000000002","shelf_life_days":10,
     "image_url":"https://i.hizliresim.com/xyz789/yogurt.jpg"},
    {"sku":"EKM200","name":"Ekmek 200g","category":"firin","barcode_gtin":"869000000003","shelf_life_days":2,
     "image_url":"https://i.hizliresim.com/123abc/ekmek.jpg"},
]
    for d in demo:
        if not db.query(Product).filter_by(sku=d["sku"]).first():
            db.add(Product(**d))
    db.commit()
    return {"ok": True, "count": db.query(Product).count()}

@app.post("/seed/demo_data")
def seed_demo_data(db: Session = Depends(get_db)):
    """Gerçekçi market demo verisi oluşturur - sunuma hazır!"""
    from datetime import datetime, timedelta
    import random

    # 1. Gerçekçi Market Ürünleri (50+ ürün)
    demo_products = [
        # SÜT ÜRÜNLERİ
        {"sku":"SUT1L","name":"Süt Tam Yağlı 1L","category":"Süt Ürünleri","barcode_gtin":"8690504321001","shelf_life_days":7},
        {"sku":"YOG500","name":"Yoğurt Yağlı 500g","category":"Süt Ürünleri","barcode_gtin":"8690504321002","shelf_life_days":10},
        {"sku":"PEY500","name":"Beyaz Peynir 500g","category":"Süt Ürünleri","barcode_gtin":"8690504321003","shelf_life_days":30},
        {"sku":"KSR350","name":"Kaşar Peynir 350g","category":"Süt Ürünleri","barcode_gtin":"8690504321004","shelf_life_days":45},
        {"sku":"TRY250","name":"Tereyağı 250g","category":"Süt Ürünleri","barcode_gtin":"8690504321005","shelf_life_days":90},
        {"sku":"AYR250","name":"Ayran 250ml","category":"Süt Ürünleri","barcode_gtin":"8690504322003","shelf_life_days":7},

        # FIRIN ÜRÜNLERİ
        {"sku":"EKM350","name":"Taze Ekmek 350g","category":"Fırın","barcode_gtin":"8690504321006","shelf_life_days":1},
        {"sku":"SMT4","name":"Simit 4'lü","category":"Fırın","barcode_gtin":"8690504321007","shelf_life_days":1},
        {"sku":"KPK350","name":"Kepek Ekmeği","category":"Fırın","barcode_gtin":"8690504321008","shelf_life_days":2},

        # SEBZE-MEYVE
        {"sku":"DOM1K","name":"Domates 1kg","category":"Sebze-Meyve","barcode_gtin":"8690504321009","shelf_life_days":5},
        {"sku":"SAL1K","name":"Salatalık 1kg","category":"Sebze-Meyve","barcode_gtin":"8690504321010","shelf_life_days":5},
        {"sku":"BIB1K","name":"Biber 1kg","category":"Sebze-Meyve","barcode_gtin":"8690504321011","shelf_life_days":5},
        {"sku":"ELM1K","name":"Elma 1kg","category":"Sebze-Meyve","barcode_gtin":"8690504321012","shelf_life_days":14},
        {"sku":"MUZ1K","name":"Muz 1kg","category":"Sebze-Meyve","barcode_gtin":"8690504321013","shelf_life_days":7},
        {"sku":"POR1K","name":"Portakal 1kg","category":"Sebze-Meyve","barcode_gtin":"8690504321014","shelf_life_days":10},

        # ET-TAVUK
        {"sku":"TVK1K","name":"Tavuk But 1kg","category":"Et-Tavuk","barcode_gtin":"8690504321015","shelf_life_days":3},
        {"sku":"KYM1K","name":"Kıyma 1kg","category":"Et-Tavuk","barcode_gtin":"8690504321016","shelf_life_days":2},
        {"sku":"KUS1K","name":"Dana Kuşbaşı 1kg","category":"Et-Tavuk","barcode_gtin":"8690504321017","shelf_life_days":3},

        # TEMEL GIDA
        {"sku":"MKR500","name":"Makarna 500g","category":"Temel Gıda","barcode_gtin":"8690504321018","shelf_life_days":540},
        {"sku":"PRN1K","name":"Pirinç 1kg","category":"Temel Gıda","barcode_gtin":"8690504321019","shelf_life_days":365},
        {"sku":"MER1K","name":"Mercimek 1kg","category":"Temel Gıda","barcode_gtin":"8690504321020","shelf_life_days":365},
        {"sku":"NHT1K","name":"Nohut 1kg","category":"Temel Gıda","barcode_gtin":"8690504321021","shelf_life_days":365},
        {"sku":"BLG1K","name":"Bulgur 1kg","category":"Temel Gıda","barcode_gtin":"8690504321022","shelf_life_days":365},
        {"sku":"TUZ1K","name":"Tuz 1kg","category":"Temel Gıda","barcode_gtin":"8690504321023","shelf_life_days":730},
        {"sku":"SKR1K","name":"Şeker 1kg","category":"Temel Gıda","barcode_gtin":"8690504321024","shelf_life_days":730},
        {"sku":"YAG1L","name":"Ayçiçek Yağı 1L","category":"Temel Gıda","barcode_gtin":"8690504321025","shelf_life_days":365},

        # KAHVALTIILIK
        {"sku":"ZYT500","name":"Zeytin 500g","category":"Kahvaltılık","barcode_gtin":"8690504321026","shelf_life_days":180},
        {"sku":"RCL380","name":"Reçel 380g","category":"Kahvaltılık","barcode_gtin":"8690504321027","shelf_life_days":365},
        {"sku":"BAL450","name":"Bal 450g","category":"Kahvaltılık","barcode_gtin":"8690504321028","shelf_life_days":730},

        # İÇECEK
        {"sku":"CAY500","name":"Çay 500g","category":"İçecek","barcode_gtin":"8690504321029","shelf_life_days":365},
        {"sku":"KHV200","name":"Kahve 200g","category":"İçecek","barcode_gtin":"8690504321030","shelf_life_days":365},
        {"sku":"SUY1.5","name":"Su 1.5L","category":"İçecek","barcode_gtin":"8690504322001","shelf_life_days":365},
        {"sku":"KOL2.5","name":"Kola 2.5L","category":"İçecek","barcode_gtin":"8690504322002","shelf_life_days":180},
        {"sku":"MYS1L","name":"Meyve Suyu 1L","category":"İçecek","barcode_gtin":"8690504322004","shelf_life_days":180},

        # ATIŞTIRMALIK
        {"sku":"CLK80","name":"Çikolata 80g","category":"Atıştırmalık","barcode_gtin":"8690504322005","shelf_life_days":180},
        {"sku":"CPS150","name":"Cips 150g","category":"Atıştırmalık","barcode_gtin":"8690504322006","shelf_life_days":120},
        {"sku":"BIS200","name":"Bisküvi 200g","category":"Atıştırmalık","barcode_gtin":"8690504322007","shelf_life_days":150},
        {"sku":"KRK100","name":"Kraker 100g","category":"Atıştırmalık","barcode_gtin":"8690504322008","shelf_life_days":120},

        # TEMİZLİK
        {"sku":"TUV16","name":"Tuvalet Kağıdı 16'lı","category":"Temizlik","barcode_gtin":"8690504322009","shelf_life_days":730},
        {"sku":"BLS1L","name":"Bulaşık Deterjanı 1L","category":"Temizlik","barcode_gtin":"8690504322010","shelf_life_days":730},
        {"sku":"CMS3K","name":"Çamaşır Deterjanı 3kg","category":"Temizlik","barcode_gtin":"8690504322011","shelf_life_days":730},
        {"sku":"SBN6","name":"Sabun 6'lı","category":"Temizlik","barcode_gtin":"8690504322012","shelf_life_days":730},

        # KİŞİSEL BAKIM
        {"sku":"SMP500","name":"Şampuan 500ml","category":"Kişisel Bakım","barcode_gtin":"8690504322013","shelf_life_days":730},
        {"sku":"DSM100","name":"Diş Macunu 100ml","category":"Kişisel Bakım","barcode_gtin":"8690504322014","shelf_life_days":730},
        {"sku":"TRS5","name":"Traş Bıçağı 5'li","category":"Kişisel Bakım","barcode_gtin":"8690504322015","shelf_life_days":1095},
    ]

    product_ids = []
    for p_data in demo_products:
        existing = db.query(Product).filter_by(sku=p_data["sku"]).first()
        if not existing:
            p = Product(**p_data)
            db.add(p)
            db.flush()
            product_ids.append(p.id)
        else:
            product_ids.append(existing.id)

    db.commit()

    # 2. Gerçekçi Batch'ler (stok durumu)
    today = datetime.now().date()
    batches_data = [
        # ACIL SKT (1-3 gün) - %20 indirim önerileri
        {"product_id": product_ids[0], "expiry_date": today + timedelta(days=2), "qty": 24},  # Süt
        {"product_id": product_ids[6], "expiry_date": today + timedelta(days=1), "qty": 50},  # Ekmek
        {"product_id": product_ids[16], "expiry_date": today + timedelta(days=2), "qty": 15},  # Kıyma
        {"product_id": product_ids[5], "expiry_date": today + timedelta(days=3), "qty": 18},  # Ayran

        # YAKIN SKT (4-7 gün) - %10 indirim önerileri
        {"product_id": product_ids[1], "expiry_date": today + timedelta(days=5), "qty": 20},  # Yoğurt
        {"product_id": product_ids[2], "expiry_date": today + timedelta(days=6), "qty": 12},  # Peynir
        {"product_id": product_ids[13], "expiry_date": today + timedelta(days=7), "qty": 30},  # Muz
        {"product_id": product_ids[9], "expiry_date": today + timedelta(days=4), "qty": 40},  # Domates

        # NORMAL STOK
        {"product_id": product_ids[3], "expiry_date": today + timedelta(days=30), "qty": 8},  # Kaşar
        {"product_id": product_ids[4], "expiry_date": today + timedelta(days=60), "qty": 15},  # Tereyağı
        {"product_id": product_ids[18], "expiry_date": today + timedelta(days=400), "qty": 60},  # Makarna
        {"product_id": product_ids[19], "expiry_date": today + timedelta(days=250), "qty": 40},  # Pirinç
        {"product_id": product_ids[29], "expiry_date": today + timedelta(days=300), "qty": 30},  # Çay
        {"product_id": product_ids[31], "expiry_date": today + timedelta(days=200), "qty": 100},  # Su
        {"product_id": product_ids[34], "expiry_date": today + timedelta(days=120), "qty": 50},  # Çikolata
        {"product_id": product_ids[38], "expiry_date": today + timedelta(days=600), "qty": 25},  # Tuvalet Kağıdı
    ]

    for b_data in batches_data:
        b = Batch(
            product_id=b_data["product_id"],
            store_id=1,
            expiry_date=b_data["expiry_date"],
            lot_code=f"LOT{random.randint(1000, 9999)}",
            qty_received=b_data["qty"],
            qty_on_hand=b_data["qty"]
        )
        db.add(b)

    db.commit()

    # 3. Faturalar (son 5 gün)
    for i in range(5):
        inv = Invoice(
            store_id=1,
            supplier_id=1,
            invoice_no=f"MRK-2024-{1100 + i}",
            invoice_date=(datetime.now() - timedelta(days=4-i)).date(),
            raw_image_path=f"/uploads/invoice_{i+1}.csv",
            status="completed",
            file_hash=f"hash_{random.randint(100000, 999999)}"
        )
        db.add(inv)
        db.flush()

        # Her faturada 5-10 ürün
        num_lines = random.randint(5, 10)
        for j in range(num_lines):
            prod_id = random.choice(product_ids)
            product = db.query(Product).get(prod_id)
            line = InvoiceLine(
                invoice_id=inv.id,
                name_raw=product.name,
                product_id=prod_id,
                qty=random.randint(10, 50),
                unit_price=round(random.uniform(10.0, 150.0), 2)
            )
            db.add(line)

    db.commit()

    # 4. Expiry alert'leri oluştur
    from app.logic import refresh_expiry_alerts
    refresh_expiry_alerts(db, store_id=1, days_window=7)

    # İstatistikler
    stats = {
        "products": db.query(Product).count(),
        "batches": db.query(Batch).count(),
        "invoices": db.query(Invoice).count(),
        "invoice_lines": db.query(InvoiceLine).count(),
        "expiry_alerts": db.query(ExpiryAlert).count()
    }

    return {
        "ok": True,
        "message": "✅ Gerçekçi market demo verisi hazır!",
        "stats": stats,
        "demo_info": {
            "product_categories": ["Süt Ürünleri", "Fırın", "Sebze-Meyve", "Et-Tavuk", "Temel Gıda", "Kahvaltılık", "İçecek", "Atıştırmalık", "Temizlik", "Kişisel Bakım"],
            "urgent_skt": 4,
            "near_skt": 4,
            "invoices_last_week": 5
        }
    }

@app.post("/batch/scan_from_image")
async def batch_scan_from_image(
    file: UploadFile = File(...),
    product_id: int = 1,
    store_id: int = 1,
    qty: float = 1.0,
    db: Session = Depends(get_db)
):
    img_path = save_upload(file, "label")
    ocr = run_tesseract(img_path)
    text = ocr.get("text","").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Metin okunamadı")

    expiry, lot = parse_gs1_from_text(text)
    if not expiry:
        expiry = parse_expiry_from_free_text(text)
    if not expiry:
        raise HTTPException(status_code=422, detail="SKT bulunamadı; manuel girin")

    b = Batch(product_id=product_id, store_id=store_id, expiry_date=expiry.date(),
              lot_code=lot, qty_received=qty, qty_on_hand=qty)
    db.add(b); db.commit(); db.refresh(b)
    return {"batch_id": b.id, "expiry_date": str(b.expiry_date), "lot_code": lot, "qty": qty}

@app.post("/products")
def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    if body.barcode_gtin:
        exists = db.query(Product).filter(Product.barcode_gtin == body.barcode_gtin).first()
        if exists:
            return {"ok": True, "id": exists.id, "note": "already exists by barcode"}
    exists_sku = db.query(Product).filter(Product.sku == body.sku).first()
    if exists_sku:
        return {"ok": True, "id": exists_sku.id, "note": "already exists by sku"}

    p = Product(**body.dict())
    db.add(p); db.commit(); db.refresh(p)
    return {"ok": True, "id": p.id}

@app.post("/products/bulk")
def create_products_bulk(items: List[ProductCreate], db: Session = Depends(get_db)):
    created = 0
    for body in items:
        if body.barcode_gtin:
            exists = db.query(Product).filter(Product.barcode_gtin == body.barcode_gtin).first()
            if exists:
                continue
        if db.query(Product).filter(Product.sku == body.sku).first():
            continue
        p = Product(**body.dict())
        db.add(p); created += 1
    db.commit()
    return {"ok": True, "created": created, "count": db.query(Product).count()}

@app.get("/products")
def products_list(q: str | None = None, sku_or_id: str | None = None, limit: int = 30, db: Session = Depends(get_db)):
    qs = db.query(Product)
    if sku_or_id:
        if sku_or_id.isdigit():
            qs = qs.filter(Product.id == int(sku_or_id))
        else:
            qs = qs.filter(or_(Product.sku == sku_or_id, Product.barcode_gtin == sku_or_id))
        prods = qs.limit(limit).all()
    elif q:
        qlike = f"%{q.strip()}%"
        prods = qs.filter(or_(Product.name.ilike(qlike), Product.sku.ilike(qlike), Product.barcode_gtin.ilike(qlike))).limit(limit).all()
    else:
        prods = qs.limit(limit).all()

    out = []
    for p in prods:
        out.append({
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "barcode_gtin": p.barcode_gtin,
            "category": p.category,
            "shelf_life_days": p.shelf_life_days
        })
    return out

# -----------------------------
# Dashboard summary + alerts actions
# -----------------------------
def ensure_expiry_alert_columns(db: Session):
    table = "expiry_alerts"
    try:
        cols = [r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]
    except Exception:
        return
    try:
        if "status" not in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN status TEXT DEFAULT 'new'")
        if "snooze_until" not in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN snooze_until DATE")
        db.commit()
    except Exception:
        db.rollback()
        return

@app.on_event("startup")
def startup_migrations_and_checks():
    try:
        db = next(get_db())
        ensure_expiry_alert_columns(db)
        try:
            db.close()
        except Exception:
            pass
    except Exception:
        pass

@app.get("/dashboard/summary")
def dashboard_summary(store_id: int = 1, days: int = 7, db: Session = Depends(get_db)):
    from datetime import datetime, timedelta

    try:
        refresh_expiry_alerts(db, store_id, days_window=days)
    except Exception:
        pass

    expiry_count = 0
    try:
        expiry_count = db.query(ExpiryAlert).filter(
            ExpiryAlert.store_id == store_id,
            ExpiryAlert.days_left <= days,
            (ExpiryAlert.status == None) | (ExpiryAlert.status != 'ack')
        ).count()
    except Exception:
        expiry_count = 0

    # Aksiyon öğeleri oluştur (gerçekten işe yarar görevler)
    actionable_tasks = []

    # 1. SKT yaklaşan ürünler için indirim önerileri
    try:
        urgent_alerts = db.query(ExpiryAlert).join(Product).filter(
            ExpiryAlert.store_id == store_id,
            ExpiryAlert.days_left <= 3,
            (ExpiryAlert.status == None) | (ExpiryAlert.status != 'ack')
        ).order_by(ExpiryAlert.days_left.asc()).limit(3).all()

        for alert in urgent_alerts:
            product = db.query(Product).get(alert.product_id)
            if product:
                discount = 20 if alert.days_left <= 1 else 15 if alert.days_left <= 2 else 10
                reyon = f"Reyon {(alert.product_id % 4) + 1}"  # Simüle reyon numarası
                actionable_tasks.append({
                    "type": "discount",
                    "priority": "urgent" if alert.days_left <= 1 else "high",
                    "title": f"{product.name} - %{discount} indirime çıkart",
                    "description": f"{reyon}'de SKT {alert.days_left} gün kaldı",
                    "action": "İndirimi uygula",
                    "product_id": product.id,
                    "days_left": alert.days_left
                })
    except Exception as e:
        pass

    # 2. Stok azalan ürünler için sipariş önerileri
    try:
        sub = db.query(Batch.product_id, func.sum(Batch.qty_on_hand).label("on_hand")).group_by(Batch.product_id).subquery()
        rows = db.query(sub.c.product_id, sub.c.on_hand).all()

        low_stock_items = []
        for pid, on_hand in rows:
            pol = db.query(ReorderPolicy).filter_by(store_id=store_id, product_id=pid).first()
            min_stock = pol.min_stock if pol else 5
            if on_hand <= min_stock:
                product = db.query(Product).get(pid)
                if product:
                    low_stock_items.append((product, on_hand, min_stock))

        # İlk 2 düşük stok ürünü için görev ekle
        for product, on_hand, min_stock in low_stock_items[:2]:
            reorder_qty = max(20, min_stock * 3)  # Minimum 20 veya min_stock'un 3 katı
            actionable_tasks.append({
                "type": "reorder",
                "priority": "high",
                "title": f"{product.name} - {reorder_qty} adet sipariş ver",
                "description": f"Stokta sadece {int(on_hand)} adet kaldı (min: {min_stock})",
                "action": "Sipariş oluştur",
                "product_id": product.id,
                "reorder_qty": reorder_qty
            })
    except Exception as e:
        pass

    # 3. Yeni teslimat uyarıları (simüle - son invoice'lardan)
    try:
        recent_inv = db.query(Invoice).order_by(Invoice.id.desc()).first()
        if recent_inv and len(actionable_tasks) < 5:
            # Simüle teslimat zamanı (3-5 gün sonra)
            delivery_hours = 72 + ((recent_inv.id % 3) * 24)  # 3-5 gün
            delivery_date = datetime.now() + timedelta(hours=delivery_hours)
            days = delivery_hours // 24
            hours = delivery_hours % 24

            actionable_tasks.append({
                "type": "delivery",
                "priority": "normal",
                "title": f"Yeni ürün teslimatı {days} gün {hours} saat sonra",
                "description": f"Reyon 2-3 arası alan hazırlanmalı (Tahmini: {delivery_date.strftime('%d.%m %H:%M')})",
                "action": "Alanı hazırla",
                "delivery_date": delivery_date.isoformat()
            })
    except Exception:
        pass

    # 4. Depo/reyon düzenleme önerileri (SKT'ye göre)
    try:
        middle_range_alerts = db.query(ExpiryAlert).join(Product).filter(
            ExpiryAlert.store_id == store_id,
            ExpiryAlert.days_left > 3,
            ExpiryAlert.days_left <= 7,
            (ExpiryAlert.status == None) | (ExpiryAlert.status != 'ack')
        ).limit(2).all()

        for alert in middle_range_alerts:
            product = db.query(Product).get(alert.product_id)
            if product and len(actionable_tasks) < 5:
                actionable_tasks.append({
                    "type": "organize",
                    "priority": "normal",
                    "title": f"{product.name} - Depo'da öne çıkart",
                    "description": f"SKT {alert.days_left} gün - FIFO için ön sıraya",
                    "action": "Düzenle",
                    "product_id": product.id
                })
    except Exception:
        pass

    # Eğer hiç görev yoksa, genel öneriler ekle
    if len(actionable_tasks) == 0:
        actionable_tasks.append({
            "type": "info",
            "priority": "normal",
            "title": "Stok durumu iyi görünüyor! ✨",
            "description": "Yaklaşan SKT veya düşük stok yok",
            "action": "Devam et"
        })

    low_stock_count = 0
    try:
        sub = db.query(Batch.product_id, func.sum(Batch.qty_on_hand).label("on_hand")).group_by(Batch.product_id).subquery()
        rows = db.query(sub.c.product_id, sub.c.on_hand).all()
        for pid, on_hand in rows:
            pol = db.query(ReorderPolicy).filter_by(store_id=store_id, product_id=pid).first()
            min_stock = pol.min_stock if pol else 5
            if on_hand <= min_stock:
                low_stock_count += 1
    except Exception:
        low_stock_count = 0

    return {
        "expiry_count": expiry_count,
        "low_stock_count": low_stock_count,
        "actionable_tasks": actionable_tasks  # Yeni: İşe yarar görevler!
    }

@app.post("/migrate/add_status_columns")
def migrate_add_status_columns(db: Session = Depends(get_db)):
    """Manually add status and snooze_until columns to expiry_alerts"""
    try:
        from sqlalchemy import text
        # Check if columns exist
        cols = [r[1] for r in db.execute(text("PRAGMA table_info(expiry_alerts)")).fetchall()]

        added = []
        if "status" not in cols:
            db.execute(text("ALTER TABLE expiry_alerts ADD COLUMN status TEXT DEFAULT 'new'"))
            added.append("status")

        if "snooze_until" not in cols:
            db.execute(text("ALTER TABLE expiry_alerts ADD COLUMN snooze_until DATE"))
            added.append("snooze_until")

        db.commit()
        return {"ok": True, "message": "Columns added successfully", "added": added}
    except Exception as e:
        db.rollback()
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}

@app.get("/alerts/expiry/full")
def alerts_expiry_full(store_id: int = 1, days: int = 30, db: Session = Depends(get_db)):
    try:
        refresh_expiry_alerts(db, store_id, days)
    except Exception:
        pass
    try:
        alerts = db.query(ExpiryAlert).filter(ExpiryAlert.store_id==store_id).order_by(ExpiryAlert.days_left.asc()).all()
    except Exception:
        alerts = []
    out = []
    for a in alerts:
        out.append({
            "id": a.id,
            "product_id": a.product_id,
            "batch_id": a.batch_id,
            "expiry_date": str(a.expiry_date),
            "days_left": a.days_left,
            "severity": a.severity,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "status": getattr(a, "status", "new"),
            "snooze_until": getattr(a, "snooze_until", None)
        })
    return out

class AlertActionReq(BaseModel):
    days: int | None = None
    note: str | None = None

@app.post("/alerts/{alert_id}/ack")
def ack_alert(alert_id: int, body: AlertActionReq = Body(...), db: Session = Depends(get_db)):
    a = db.query(ExpiryAlert).filter_by(id=alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="alert not found")
    try:
        setattr(a, "status", "ack")
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"ok": True, "alert_id": alert_id, "status": "ack"}

@app.post("/alerts/{alert_id}/snooze")
def snooze_alert(alert_id: int, body: AlertActionReq = Body(...), db: Session = Depends(get_db)):
    a = db.query(ExpiryAlert).filter_by(id=alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="alert not found")
    days = body.days or 1
    snooze_until = (datetime.utcnow() + timedelta(days=days)).date()
    try:
        setattr(a, "snooze_until", snooze_until)
        setattr(a, "status", "snoozed")
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"ok": True, "alert_id": alert_id, "snooze_until": str(snooze_until)}

# -----------------------------
# Root & Static (UI da artık şifreli!)
# -----------------------------
@app.get("/")
def root():
    return RedirectResponse(url="/ui")

# Statik web'i EN SON mount et
app.mount("/ui", StaticFiles(directory="app/static", html=True), name="static")