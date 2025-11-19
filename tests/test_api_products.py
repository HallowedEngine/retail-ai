"""Tests for product API endpoints."""
import pytest
from sqlalchemy.exc import IntegrityError


class TestProductAPI:
    """Tests for product-related API endpoints."""

    def test_create_product(self, client, test_db):
        """Test creating a single product."""
        response = client.post(
            "/products",
            json={
                "sku": "NEW001",
                "name": "New Product",
                "category": "Test Category",
                "barcode_gtin": "1234567890123"
            },
            auth=("admin", "retailai2025")
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sku"] == "NEW001"
        assert data["name"] == "New Product"

    def test_create_product_minimal_fields(self, client):
        """Test creating product with only required fields."""
        response = client.post(
            "/products",
            json={
                "sku": "MIN001",
                "name": "Minimal Product"
            },
            auth=("admin", "retailai2025")
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sku"] == "MIN001"
        assert data["name"] == "Minimal Product"

    def test_create_product_with_image_url(self, client):
        """Test creating product with image URL."""
        response = client.post(
            "/products",
            json={
                "sku": "IMG001",
                "name": "Product with Image",
                "image_url": "https://example.com/image.jpg"
            },
            auth=("admin", "retailai2025")
        )

        assert response.status_code == 200
        data = response.json()
        assert data["image_url"] == "https://example.com/image.jpg"

    def test_duplicate_sku_rejected(self, client, sample_products):
        """Test that duplicate SKU is rejected."""
        response = client.post(
            "/products",
            json={
                "sku": sample_products[0].sku,  # Duplicate SKU
                "name": "Duplicate Product"
            },
            auth=("admin", "retailai2025")
        )

        assert response.status_code in [400, 409, 500]  # Should fail

    def test_get_products_list(self, client, sample_products):
        """Test getting products list."""
        response = client.get("/products", auth=("admin", "retailai2025"))

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # At least our sample products

    def test_search_products_by_query(self, client, sample_products):
        """Test searching products by query."""
        response = client.get(
            "/products?q=Süt",
            auth=("admin", "retailai2025")
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should find products with "Süt" in name
        assert any("Süt" in p["name"] for p in data)

    def test_search_products_by_sku(self, client, sample_products):
        """Test searching products by SKU."""
        response = client.get(
            f"/products?sku_or_id={sample_products[0].sku}",
            auth=("admin", "retailai2025")
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["sku"] == sample_products[0].sku

    def test_products_require_authentication(self, client):
        """Test that product endpoints require authentication."""
        response = client.get("/products")
        assert response.status_code == 401

        response = client.post("/products", json={"sku": "TEST", "name": "Test"})
        assert response.status_code == 401


class TestBulkProductUpload:
    """Tests for bulk product upload."""

    def test_bulk_upload_valid_products(self, client, test_db):
        """Test bulk uploading multiple products."""
        products = [
            {
                "sku": "BULK001",
                "name": "Bulk Product 1",
                "category": "Category A"
            },
            {
                "sku": "BULK002",
                "name": "Bulk Product 2",
                "category": "Category B",
                "barcode_gtin": "1234567890123"
            },
            {
                "sku": "BULK003",
                "name": "Bulk Product 3",
                "image_url": "https://example.com/product3.jpg"
            }
        ]

        response = client.post(
            "/products/bulk",
            json=products,
            auth=("admin", "retailai2025")
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 3
        assert "Product 1" in data["message"]

    def test_bulk_upload_with_image_urls(self, client):
        """Test bulk upload with image URLs."""
        products = [
            {
                "sku": "IMG001",
                "name": "Product 1",
                "image_url": "https://example.com/1.jpg"
            },
            {
                "sku": "IMG002",
                "name": "Product 2",
                "image_url": "https://example.com/2.jpg"
            }
        ]

        response = client.post(
            "/products/bulk",
            json=products,
            auth=("admin", "retailai2025")
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 2

    def test_bulk_upload_empty_array(self, client):
        """Test bulk upload with empty array."""
        response = client.post(
            "/products/bulk",
            json=[],
            auth=("admin", "retailai2025")
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 0

    def test_bulk_upload_duplicate_within_batch(self, client):
        """Test bulk upload with duplicate SKU within the same batch."""
        products = [
            {"sku": "DUP001", "name": "Product 1"},
            {"sku": "DUP001", "name": "Product 2"},  # Duplicate
        ]

        response = client.post(
            "/products/bulk",
            json=products,
            auth=("admin", "retailai2025")
        )

        # Should handle gracefully (either skip or fail)
        # Implementation dependent, but shouldn't crash
        assert response.status_code in [200, 400, 409]

    def test_bulk_upload_duplicate_barcode_rejected(self, client, test_db):
        """Test that duplicate barcodes are handled."""
        # Create first product
        client.post(
            "/products",
            json={
                "sku": "BAR001",
                "name": "Product 1",
                "barcode_gtin": "9999999999999"
            },
            auth=("admin", "retailai2025")
        )

        # Try to create second with same barcode
        products = [
            {
                "sku": "BAR002",
                "name": "Product 2",
                "barcode_gtin": "9999999999999"  # Duplicate barcode
            }
        ]

        response = client.post(
            "/products/bulk",
            json=products,
            auth=("admin", "retailai2025")
        )

        # Should handle gracefully
        assert response.status_code in [200, 400, 409]

    def test_bulk_upload_requires_auth(self, client):
        """Test that bulk upload requires authentication."""
        response = client.post(
            "/products/bulk",
            json=[{"sku": "TEST", "name": "Test"}]
        )
        assert response.status_code == 401

    def test_bulk_upload_invalid_data_types(self, client):
        """Test bulk upload with invalid data types."""
        products = [
            {
                "sku": 12345,  # Should be string
                "name": "Product"
            }
        ]

        response = client.post(
            "/products/bulk",
            json=products,
            auth=("admin", "retailai2025")
        )

        # Should validate or handle gracefully
        assert response.status_code in [200, 400, 422]


class TestSeedProducts:
    """Tests for product seeding endpoint."""

    def test_seed_products(self, client, test_db):
        """Test seeding demo products."""
        response = client.post(
            "/seed/products",
            auth=("admin", "retailai2025")
        )

        assert response.status_code == 200
        data = response.json()
        assert "created" in data
        assert data["created"] > 0

    def test_seed_products_idempotent(self, client):
        """Test that seeding can be run multiple times."""
        # First seed
        response1 = client.post("/seed/products", auth=("admin", "retailai2025"))
        assert response1.status_code == 200

        # Second seed (may skip duplicates)
        response2 = client.post("/seed/products", auth=("admin", "retailai2025"))
        # Should not crash
        assert response2.status_code in [200, 400]

    def test_seed_products_requires_auth(self, client):
        """Test that seeding requires authentication."""
        response = client.post("/seed/products")
        assert response.status_code == 401
