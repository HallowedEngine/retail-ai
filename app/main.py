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
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
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
from .logging_config import get_logger, setup_logging
from .error_handlers import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    generic_exception_handler
)

# Initialize logging
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger("main")

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
    title="Retail AI - Invoice & Inventory Management",
    description="Advanced retail management system with OCR, inventory tracking, and analytics",
    version="2.0.0",
    dependencies=[Depends(verify_auth)]  # ← BU SATIR HER ŞEYİ ŞİFRELİYOR!
)

# Register error handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

logger.info("Retail AI application starting up...")

# Auth'suz kalmasını istediğin endpoint'ler (rahatlık için)
@app.get("/health")
async def health():
    """Health check endpoint."""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

logger.info("CORS middleware configured")

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
    # 1) Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail="Only image files are supported (JPEG, PNG, etc.)"
        )

    # 2) Dosyayı kaydet
    try:
        img_path = save_upload(file, "invoice")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to save uploaded file: {str(e)}"
        )

    # 3) Duplicate kontrolü
    h = file_md5(img_path)
    dup = db.query(Invoice).filter(Invoice.file_hash == h).first()
    if dup:
        raise HTTPException(
            status_code=409,
            detail={"message": "Duplicate invoice image", "existing_invoice_id": dup.id}
        )

    # 4) OCR & parse with error handling
    try:
        ocr = run_tesseract(img_path)
        lines = parse_invoice_lines(ocr.get("text", ""))

        # düşük güven/çıktı durumunda fallback
        if len(lines) == 0 or ocr.get("conf", 0) < 0.6:
            try:
                ocr2 = run_vision_fallback(img_path)
                ocr = best_merge(ocr, ocr2)
                lines = parse_invoice_lines(ocr.get("text", ""))
            except Exception:
                # Fallback failed, continue with original OCR
                pass
    except Exception as e:
        # If OCR fails completely, create invoice with empty OCR
        ocr = {"text": "", "conf": 0, "error": str(e)}
        lines = []

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
    image_url: str | None = None

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
    db.refresh(L)
    return {
        "ok": True,
        "id": L.id,
        "product_id": L.product_id,
        "qty": L.qty,
        "unit_price": L.unit_price,
        "name_raw": L.name_raw
    }

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
    created = 0
    for d in demo:
        if not db.query(Product).filter_by(sku=d["sku"]).first():
            db.add(Product(**d))
            created += 1
    db.commit()
    return {"ok": True, "created": created, "count": db.query(Product).count()}

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
            return {
                "id": exists.id,
                "sku": exists.sku,
                "name": exists.name,
                "category": exists.category,
                "barcode_gtin": exists.barcode_gtin,
                "shelf_life_days": exists.shelf_life_days,
                "image_url": exists.image_url,
                "note": "already exists by barcode"
            }
    exists_sku = db.query(Product).filter(Product.sku == body.sku).first()
    if exists_sku:
        return {
            "id": exists_sku.id,
            "sku": exists_sku.sku,
            "name": exists_sku.name,
            "category": exists_sku.category,
            "barcode_gtin": exists_sku.barcode_gtin,
            "shelf_life_days": exists_sku.shelf_life_days,
            "image_url": exists_sku.image_url,
            "note": "already exists by sku"
        }

    p = Product(**body.model_dump())  # Use model_dump instead of deprecated dict()
    db.add(p); db.commit(); db.refresh(p)
    return {
        "id": p.id,
        "sku": p.sku,
        "name": p.name,
        "category": p.category,
        "barcode_gtin": p.barcode_gtin,
        "shelf_life_days": p.shelf_life_days,
        "image_url": p.image_url
    }

@app.post("/products/bulk")
def create_products_bulk(items: List[ProductCreate], db: Session = Depends(get_db)):
    created = 0
    skipped = 0
    seen_skus = set()  # Track SKUs in current batch
    seen_barcodes = set()  # Track barcodes in current batch

    for body in items:
        # Check for duplicates in database
        if body.barcode_gtin:
            if body.barcode_gtin in seen_barcodes:
                skipped += 1
                continue
            exists = db.query(Product).filter(Product.barcode_gtin == body.barcode_gtin).first()
            if exists:
                skipped += 1
                continue
            seen_barcodes.add(body.barcode_gtin)

        # Check for duplicate SKU in batch or database
        if body.sku in seen_skus:
            skipped += 1
            continue
        if db.query(Product).filter(Product.sku == body.sku).first():
            skipped += 1
            continue

        seen_skus.add(body.sku)
        p = Product(**body.model_dump())
        db.add(p)
        created += 1

    db.commit()
    message = f"Successfully created {created} product(s)"
    if skipped > 0:
        message += f", skipped {skipped} duplicate(s)"
    return {"ok": True, "created": created, "skipped": skipped, "count": db.query(Product).count(), "message": message}

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
    try:
        refresh_expiry_alerts(db, store_id, days)
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

    recent_invoices_q = db.query(Invoice).order_by(Invoice.id.desc()).limit(5).all()
    recent = [{"id": inv.id, "created_at": inv.created_at.isoformat() if inv.created_at else None} for inv in recent_invoices_q]

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
        "recent_invoices": recent
    }

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