from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True)
    barcode_gtin = Column(String, index=True)
    shelf_life_days = Column(Integer, default=0)
    image_url: str = None
    image_url = Column(String, nullable=True)

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, index=True, default=1)
    supplier_id = Column(Integer, index=True, default=1)
    invoice_no = Column(String, index=True)
    invoice_date = Column(Date)
    raw_image_path = Column(String)
    ocr_json = Column(Text)
    status = Column(String, default="parsed")
    created_at = Column(DateTime, default=datetime.utcnow)
    file_hash = Column(String(64), unique=True, index=True, nullable=True)

class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    supplier_sku = Column(String)
    name_raw = Column(String)
    qty = Column(Float)
    unit = Column(String)
    unit_price = Column(Float)

class Batch(Base):
    __tablename__ = "batches"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    store_id = Column(Integer, index=True, default=1)
    lot_code = Column(String)
    expiry_date = Column(Date)
    qty_received = Column(Float, default=0)
    qty_on_hand = Column(Float, default=0)
    received_at = Column(DateTime, default=datetime.utcnow)
    source_invoice_id = Column(Integer, ForeignKey("invoices.id"))

class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, index=True, default=1)
    product_id = Column(Integer, ForeignKey("products.id"))
    ts = Column(DateTime, index=True)
    qty = Column(Float)

class ExpiryAlert(Base):
    __tablename__ = "expiry_alerts"
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    batch_id = Column(Integer, ForeignKey("batches.id"))
    expiry_date = Column(Date)
    days_left = Column(Integer)
    severity = Column(String)  # red / yellow
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

class ReorderPolicy(Base):
    __tablename__ = "reorder_policies"
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    min_stock = Column(Float, default=0)
    max_stock = Column(Float, default=0)
    lead_time_days = Column(Integer, default=2)
    safety_stock = Column(Float, default=0)

class Forecast(Base):
    __tablename__ = "forecasts"
    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    horizon = Column(String)  # e.g. 'hourly'
    ts = Column(DateTime, index=True)
    yhat = Column(Float)
    model_ver = Column(String, default="naive_v1")
