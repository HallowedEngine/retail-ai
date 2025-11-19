"""Tests for invoice API endpoints."""
import pytest
import io
from PIL import Image


class TestInvoiceAPI:
    """Tests for invoice-related API endpoints."""

    def test_get_invoice_details(self, client, auth_headers, sample_invoice, sample_invoice_lines):
        """Test retrieving invoice details."""
        response = client.get(f"/invoice/{sample_invoice.id}", auth=("admin", "retailai2025"))
        assert response.status_code == 200

        data = response.json()
        assert "invoice_id" in data
        assert "lines" in data
        assert data["invoice_id"] == sample_invoice.id
        assert len(data["lines"]) == 2

    def test_get_nonexistent_invoice_returns_404(self, client, test_db):
        """Test that getting nonexistent invoice returns 404."""
        response = client.get("/invoice/99999", auth=("admin", "retailai2025"))
        assert response.status_code == 404

    def test_update_invoice_line(self, client, sample_invoice_lines):
        """Test updating an invoice line."""
        line = sample_invoice_lines[0]

        response = client.post(
            "/invoice/line/update",
            json={
                "line_id": line.id,
                "qty": 15.0,
                "unit_price": 13.50
            },
            auth=("admin", "retailai2025")
        )

        assert response.status_code == 200
        data = response.json()
        assert data["qty"] == 15.0
        assert data["unit_price"] == 13.50

    def test_update_invoice_line_product_id(self, client, sample_invoice_lines, sample_products):
        """Test updating product_id in invoice line."""
        line = sample_invoice_lines[0]

        response = client.post(
            "/invoice/line/update",
            json={
                "line_id": line.id,
                "product_id": sample_products[1].id
            },
            auth=("admin", "retailai2025")
        )

        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == sample_products[1].id

    def test_update_nonexistent_line_returns_404(self, client, test_db):
        """Test updating nonexistent line returns 404."""
        response = client.post(
            "/invoice/line/update",
            json={"line_id": 99999, "qty": 10.0},
            auth=("admin", "retailai2025")
        )

        assert response.status_code == 404

    def test_get_recent_invoices(self, client, sample_invoice):
        """Test getting recent invoices list."""
        response = client.get("/invoices/recent", auth=("admin", "retailai2025"))
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_export_invoice_csv(self, client, sample_invoice, sample_invoice_lines):
        """Test exporting invoice to CSV."""
        response = client.get(
            f"/invoice/{sample_invoice.id}/export.csv",
            auth=("admin", "retailai2025")
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]

        # Check CSV content
        csv_content = response.text
        assert "name_raw" in csv_content or "qty" in csv_content

    def test_invoice_requires_authentication(self, client, sample_invoice):
        """Test that invoice endpoints require authentication."""
        response = client.get(f"/invoice/{sample_invoice.id}")
        assert response.status_code == 401


class TestInvoiceUpload:
    """Tests for invoice upload functionality."""

    def create_test_image(self) -> bytes:
        """Create a simple test image."""
        img = Image.new('RGB', (800, 600), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes.getvalue()

    def test_upload_invoice_requires_auth(self, client, test_db):
        """Test that upload requires authentication."""
        img_data = self.create_test_image()
        files = {'file': ('test_invoice.jpg', io.BytesIO(img_data), 'image/jpeg')}

        response = client.post("/upload_invoice", files=files)
        assert response.status_code == 401

    def test_upload_invoice_valid_image(self, client, sample_products):
        """Test uploading a valid invoice image."""
        img_data = self.create_test_image()
        files = {'file': ('test_invoice.jpg', io.BytesIO(img_data), 'image/jpeg')}

        response = client.post(
            "/upload_invoice",
            files=files,
            auth=("admin", "retailai2025")
        )

        # Should succeed (though OCR may not find lines)
        assert response.status_code == 200
        data = response.json()
        assert "invoice_id" in data

    def test_upload_unsupported_file_type(self, client, test_db):
        """Test that unsupported file types are rejected."""
        files = {'file': ('test.txt', io.BytesIO(b'not an image'), 'text/plain')}

        response = client.post(
            "/upload_invoice",
            files=files,
            auth=("admin", "retailai2025")
        )

        # Should fail validation or return error
        assert response.status_code in [400, 422, 500]
