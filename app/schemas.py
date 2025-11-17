from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional

class InvoiceUploadResp(BaseModel):
    invoice_id: int
    lines_preview: List[dict]

class BatchScanReq(BaseModel):
    product_id: int
    store_id: int = 1
    expiry_date: date
    lot_code: Optional[str] = None
    qty: float

class SalesRow(BaseModel):
    ts: datetime
    sku: str
    qty: float

class IngestSalesReq(BaseModel):
    store_id: int = 1
    rows: List[SalesRow]

class ProductCreate(BaseModel):
    sku: str
    name: str
    category: str | None = None
    barcode_gtin: str | None = None
    shelf_life_days: int | None = None
    image_url: str | None = None  # ← YENİ