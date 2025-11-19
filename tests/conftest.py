"""Shared test fixtures for all tests."""
import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

from app.db import Base
from app.models import Product, Invoice, InvoiceLine, Batch, Sale, ExpiryAlert, ReorderPolicy, Forecast
from app.main import app, get_db


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh in-memory SQLite database for each test."""
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with dependency override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_products(test_db):
    """Create sample products for testing."""
    products = [
        Product(
            id=1,
            sku="SKU001",
            name="İçim Süt 1L Tam Yağlı",
            category="Süt Ürünleri",
            barcode_gtin="8682971085011",
            shelf_life_days=14
        ),
        Product(
            id=2,
            sku="SKU002",
            name="Ülker Çikolata",
            category="Gıda",
            barcode_gtin="8690504003014",
            shelf_life_days=180
        ),
        Product(
            id=3,
            sku="SKU003",
            name="Pınar Süzme Yoğurt",
            category="Süt Ürünleri",
            barcode_gtin="8690504005012",
            shelf_life_days=21
        ),
    ]
    for p in products:
        test_db.add(p)
    test_db.commit()
    return products


@pytest.fixture
def sample_invoice(test_db, sample_products):
    """Create a sample invoice."""
    invoice = Invoice(
        id=1,
        store_id=1,
        supplier_id=1,
        invoice_no="INV-001",
        invoice_date=date.today(),
        raw_image_path="/uploads/test.jpg",
        ocr_json='{"text": "test"}',
        status="parsed",
        file_hash="abc123"
    )
    test_db.add(invoice)
    test_db.commit()
    return invoice


@pytest.fixture
def sample_invoice_lines(test_db, sample_invoice, sample_products):
    """Create sample invoice lines."""
    lines = [
        InvoiceLine(
            invoice_id=sample_invoice.id,
            product_id=sample_products[0].id,
            supplier_sku="SUP001",
            name_raw="İÇİM SÜT 1L",
            qty=10.0,
            unit="adet",
            unit_price=12.50
        ),
        InvoiceLine(
            invoice_id=sample_invoice.id,
            product_id=sample_products[1].id,
            supplier_sku="SUP002",
            name_raw="ÜLKER ÇİKOLATA",
            qty=20.0,
            unit="adet",
            unit_price=5.75
        ),
    ]
    for line in lines:
        test_db.add(line)
    test_db.commit()
    return lines


@pytest.fixture
def sample_batches(test_db, sample_products):
    """Create sample batches with various expiry dates."""
    today = date.today()
    batches = [
        Batch(
            product_id=sample_products[0].id,
            store_id=1,
            lot_code="LOT001",
            expiry_date=today + timedelta(days=2),  # Red alert (≤3 days)
            qty_received=100.0,
            qty_on_hand=50.0
        ),
        Batch(
            product_id=sample_products[1].id,
            store_id=1,
            lot_code="LOT002",
            expiry_date=today + timedelta(days=5),  # Yellow alert (4-7 days)
            qty_received=200.0,
            qty_on_hand=150.0
        ),
        Batch(
            product_id=sample_products[2].id,
            store_id=1,
            lot_code="LOT003",
            expiry_date=today + timedelta(days=30),  # No alert
            qty_received=50.0,
            qty_on_hand=25.0
        ),
    ]
    for batch in batches:
        test_db.add(batch)
    test_db.commit()
    return batches


@pytest.fixture
def sample_sales(test_db, sample_products):
    """Create sample sales data for forecasting."""
    sales = []
    now = datetime.now()

    # Generate 28 days of hourly sales
    for day_offset in range(28):
        for hour in range(24):
            ts = now - timedelta(days=day_offset, hours=hour)
            # Simulate higher sales during business hours (9-21)
            if 9 <= ts.hour <= 21:
                qty = 5.0 + (day_offset % 7)  # Vary by day of week
            else:
                qty = 1.0

            sales.append(Sale(
                store_id=1,
                product_id=sample_products[0].id,
                ts=ts,
                qty=qty
            ))

    for sale in sales:
        test_db.add(sale)
    test_db.commit()
    return sales


@pytest.fixture
def sample_reorder_policy(test_db, sample_products):
    """Create a sample reorder policy."""
    policy = ReorderPolicy(
        store_id=1,
        product_id=sample_products[0].id,
        min_stock=20.0,
        max_stock=100.0,
        lead_time_days=3,
        safety_stock=15.0
    )
    test_db.add(policy)
    test_db.commit()
    return policy


@pytest.fixture
def auth_headers():
    """Basic authentication headers for API tests."""
    import base64
    credentials = base64.b64encode(b"admin:retailai2025").decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def invalid_auth_headers():
    """Invalid authentication headers for testing auth failures."""
    import base64
    credentials = base64.b64encode(b"admin:wrongpassword").decode("utf-8")
    return {"Authorization": f"Basic {credentials}"}
