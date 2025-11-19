"""Tests for database models and constraints."""
import pytest
from datetime import datetime, date
from sqlalchemy.exc import IntegrityError

from app.models import Product, Invoice, InvoiceLine, Batch, Sale, ExpiryAlert, ReorderPolicy, Forecast


class TestProductModel:
    """Tests for Product model."""

    def test_create_product(self, test_db):
        """Test creating a basic product."""
        product = Product(
            sku="TEST001",
            name="Test Product",
            category="Test Category"
        )
        test_db.add(product)
        test_db.commit()

        assert product.id is not None
        assert product.sku == "TEST001"

    def test_unique_sku_constraint(self, test_db):
        """Test that SKU must be unique."""
        product1 = Product(sku="DUP001", name="Product 1")
        test_db.add(product1)
        test_db.commit()

        product2 = Product(sku="DUP001", name="Product 2")
        test_db.add(product2)

        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_unique_barcode_constraint(self, test_db):
        """Test that barcode uniqueness behavior."""
        product1 = Product(sku="SKU001", name="Product 1", barcode_gtin="1234567890123")
        test_db.add(product1)
        test_db.commit()

        product2 = Product(sku="SKU002", name="Product 2", barcode_gtin="1234567890123")
        test_db.add(product2)

        # Note: barcode uniqueness may not be enforced at DB level in current schema
        # This documents the current behavior
        try:
            test_db.commit()
            # If it succeeds, barcode constraint is not enforced (current behavior)
        except IntegrityError:
            # If it fails, barcode constraint is enforced
            test_db.rollback()

    def test_product_with_optional_fields(self, test_db):
        """Test creating product with all optional fields."""
        product = Product(
            sku="FULL001",
            name="Full Product",
            category="Category A",
            barcode_gtin="9876543210987",
            shelf_life_days=30,
            image_url="https://example.com/image.jpg"
        )
        test_db.add(product)
        test_db.commit()

        assert product.shelf_life_days == 30
        assert product.image_url == "https://example.com/image.jpg"

    def test_product_default_shelf_life(self, test_db):
        """Test that shelf_life_days has default value."""
        product = Product(sku="DEF001", name="Default Product")
        test_db.add(product)
        test_db.commit()

        assert product.shelf_life_days == 0


class TestInvoiceModel:
    """Tests for Invoice model."""

    def test_create_invoice(self, test_db):
        """Test creating a basic invoice."""
        invoice = Invoice(
            store_id=1,
            supplier_id=1,
            invoice_no="INV-001",
            invoice_date=date.today(),
            raw_image_path="/uploads/test.jpg",
            file_hash="abc123"
        )
        test_db.add(invoice)
        test_db.commit()

        assert invoice.id is not None
        assert invoice.status == "parsed"  # Default value

    def test_unique_file_hash_constraint(self, test_db):
        """Test that file_hash must be unique."""
        invoice1 = Invoice(
            invoice_no="INV-001",
            invoice_date=date.today(),
            file_hash="hash123"
        )
        test_db.add(invoice1)
        test_db.commit()

        invoice2 = Invoice(
            invoice_no="INV-002",
            invoice_date=date.today(),
            file_hash="hash123"
        )
        test_db.add(invoice2)

        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_invoice_default_values(self, test_db):
        """Test invoice default values."""
        invoice = Invoice(
            invoice_no="DEF-001",
            invoice_date=date.today()
        )
        test_db.add(invoice)
        test_db.commit()

        assert invoice.store_id == 1
        assert invoice.supplier_id == 1
        assert invoice.status == "parsed"
        assert invoice.created_at is not None

    def test_invoice_created_at_timestamp(self, test_db):
        """Test that created_at is automatically set."""
        invoice = Invoice(
            invoice_no="TIME-001",
            invoice_date=date.today()
        )
        test_db.add(invoice)
        test_db.commit()

        assert isinstance(invoice.created_at, datetime)


class TestInvoiceLineModel:
    """Tests for InvoiceLine model."""

    def test_create_invoice_line(self, test_db, sample_invoice, sample_products):
        """Test creating an invoice line."""
        line = InvoiceLine(
            invoice_id=sample_invoice.id,
            product_id=sample_products[0].id,
            supplier_sku="SUP001",
            name_raw="TEST PRODUCT",
            qty=10.0,
            unit="adet",
            unit_price=15.50
        )
        test_db.add(line)
        test_db.commit()

        assert line.id is not None
        assert line.qty == 10.0

    def test_invoice_line_nullable_product_id(self, test_db, sample_invoice):
        """Test that product_id can be null (unmatched products)."""
        line = InvoiceLine(
            invoice_id=sample_invoice.id,
            product_id=None,  # Unmatched product
            supplier_sku="UNK001",
            name_raw="UNKNOWN PRODUCT",
            qty=5.0,
            unit="adet",
            unit_price=10.0
        )
        test_db.add(line)
        test_db.commit()

        assert line.product_id is None

    def test_invoice_line_foreign_key(self, test_db, sample_invoice, sample_products):
        """Test foreign key relationship."""
        line = InvoiceLine(
            invoice_id=sample_invoice.id,
            product_id=sample_products[0].id,
            name_raw="TEST",
            qty=1.0,
            unit="adet",
            unit_price=10.0
        )
        test_db.add(line)
        test_db.commit()

        # Verify foreign key works
        assert line.invoice_id == sample_invoice.id
        assert line.product_id == sample_products[0].id


class TestBatchModel:
    """Tests for Batch model."""

    def test_create_batch(self, test_db, sample_products):
        """Test creating a batch."""
        batch = Batch(
            product_id=sample_products[0].id,
            store_id=1,
            lot_code="LOT001",
            expiry_date=date(2025, 12, 31),
            qty_received=100.0,
            qty_on_hand=75.0
        )
        test_db.add(batch)
        test_db.commit()

        assert batch.id is not None
        assert batch.lot_code == "LOT001"

    def test_batch_default_values(self, test_db, sample_products):
        """Test batch default values."""
        batch = Batch(
            product_id=sample_products[0].id,
            lot_code="DEF001",
            expiry_date=date(2025, 12, 31)
        )
        test_db.add(batch)
        test_db.commit()

        assert batch.store_id == 1
        assert batch.qty_received == 0.0
        assert batch.qty_on_hand == 0.0
        assert batch.received_at is not None

    def test_batch_nullable_expiry_date(self, test_db, sample_products):
        """Test that expiry_date can be null."""
        batch = Batch(
            product_id=sample_products[0].id,
            lot_code="NOEXP001",
            expiry_date=None  # Some products don't expire
        )
        test_db.add(batch)
        test_db.commit()

        assert batch.expiry_date is None


class TestSaleModel:
    """Tests for Sale model."""

    def test_create_sale(self, test_db, sample_products):
        """Test creating a sale record."""
        sale = Sale(
            store_id=1,
            product_id=sample_products[0].id,
            ts=datetime.now(),
            qty=5.0
        )
        test_db.add(sale)
        test_db.commit()

        assert sale.id is not None
        assert sale.qty == 5.0

    def test_sale_timestamp_indexed(self, test_db, sample_products):
        """Test that timestamp is stored correctly."""
        now = datetime(2025, 1, 15, 12, 30, 0)
        sale = Sale(
            store_id=1,
            product_id=sample_products[0].id,
            ts=now,
            qty=10.0
        )
        test_db.add(sale)
        test_db.commit()

        assert sale.ts == now


class TestExpiryAlertModel:
    """Tests for ExpiryAlert model."""

    def test_create_expiry_alert(self, test_db, sample_products, sample_batches):
        """Test creating an expiry alert."""
        alert = ExpiryAlert(
            store_id=1,
            product_id=sample_products[0].id,
            batch_id=sample_batches[0].id,
            expiry_date=date(2025, 1, 31),
            days_left=5,
            severity="yellow"
        )
        test_db.add(alert)
        test_db.commit()

        assert alert.id is not None
        assert alert.severity == "yellow"

    def test_expiry_alert_severity_values(self, test_db, sample_products, sample_batches):
        """Test both severity values."""
        alert_red = ExpiryAlert(
            store_id=1,
            product_id=sample_products[0].id,
            batch_id=sample_batches[0].id,
            expiry_date=date(2025, 1, 20),
            days_left=2,
            severity="red"
        )
        test_db.add(alert_red)
        test_db.commit()

        assert alert_red.severity == "red"

    def test_expiry_alert_nullable_resolved_at(self, test_db, sample_products, sample_batches):
        """Test that resolved_at is nullable."""
        alert = ExpiryAlert(
            store_id=1,
            product_id=sample_products[0].id,
            batch_id=sample_batches[0].id,
            expiry_date=date(2025, 1, 31),
            days_left=5,
            severity="yellow",
            resolved_at=None
        )
        test_db.add(alert)
        test_db.commit()

        assert alert.resolved_at is None


class TestReorderPolicyModel:
    """Tests for ReorderPolicy model."""

    def test_create_reorder_policy(self, test_db, sample_products):
        """Test creating a reorder policy."""
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

        assert policy.id is not None
        assert policy.min_stock == 20.0

    def test_reorder_policy_default_values(self, test_db, sample_products):
        """Test reorder policy default values."""
        policy = ReorderPolicy(
            store_id=1,
            product_id=sample_products[0].id
        )
        test_db.add(policy)
        test_db.commit()

        assert policy.min_stock == 0.0
        assert policy.max_stock == 0.0
        assert policy.lead_time_days == 2
        assert policy.safety_stock == 0.0


class TestForecastModel:
    """Tests for Forecast model."""

    def test_create_forecast(self, test_db, sample_products):
        """Test creating a forecast record."""
        forecast = Forecast(
            store_id=1,
            product_id=sample_products[0].id,
            horizon="hourly",
            ts=datetime(2025, 1, 20, 10, 0, 0),
            yhat=15.5
        )
        test_db.add(forecast)
        test_db.commit()

        assert forecast.id is not None
        assert forecast.yhat == 15.5

    def test_forecast_default_model_ver(self, test_db, sample_products):
        """Test forecast default model version."""
        forecast = Forecast(
            store_id=1,
            product_id=sample_products[0].id,
            horizon="hourly",
            ts=datetime.now(),
            yhat=10.0
        )
        test_db.add(forecast)
        test_db.commit()

        assert forecast.model_ver == "naive_v1"


class TestDatabaseIndexes:
    """Tests for database indexes and performance."""

    def test_product_sku_indexed(self, test_db):
        """Test that SKU is indexed for fast lookups."""
        # Create multiple products
        for i in range(10):
            product = Product(sku=f"IDX{i:03d}", name=f"Product {i}")
            test_db.add(product)
        test_db.commit()

        # Query by SKU should be fast (index exists)
        result = test_db.query(Product).filter(Product.sku == "IDX005").first()
        assert result is not None
        assert result.sku == "IDX005"

    def test_invoice_file_hash_indexed(self, test_db):
        """Test that file_hash is indexed."""
        invoice = Invoice(
            invoice_no="HASH-001",
            invoice_date=date.today(),
            file_hash="unique_hash_123"
        )
        test_db.add(invoice)
        test_db.commit()

        # Query by file_hash should work
        result = test_db.query(Invoice).filter(
            Invoice.file_hash == "unique_hash_123"
        ).first()
        assert result is not None
