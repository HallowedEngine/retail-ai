"""Tests for API authentication."""
import pytest
import base64


class TestAuthentication:
    """Tests for HTTP Basic authentication."""

    def test_valid_credentials_accepted(self, client, test_db):
        """Test that valid credentials grant access."""
        response = client.get("/dashboard/summary", auth=("admin", "retailai2025"))
        assert response.status_code == 200

    def test_invalid_username_rejected(self, client, test_db):
        """Test that invalid username is rejected."""
        response = client.get("/dashboard/summary", auth=("wronguser", "retailai2025"))
        assert response.status_code == 401

    def test_invalid_password_rejected(self, client, test_db):
        """Test that invalid password is rejected."""
        response = client.get("/dashboard/summary", auth=("admin", "wrongpassword"))
        assert response.status_code == 401

    def test_empty_credentials_rejected(self, client, test_db):
        """Test that empty credentials are rejected."""
        response = client.get("/dashboard/summary")
        assert response.status_code == 401

    def test_malformed_auth_header_rejected(self, client, test_db):
        """Test that malformed auth header is rejected."""
        response = client.get(
            "/dashboard/summary",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401

    def test_case_sensitive_password(self, client, test_db):
        """Test that password is case-sensitive."""
        response = client.get("/dashboard/summary", auth=("admin", "RETAILAI2025"))
        assert response.status_code == 401

    def test_health_endpoint_unauthenticated(self, client, test_db):
        """Test that /health endpoint requires authentication (global auth)."""
        response = client.get("/health")
        # Due to global auth dependency on FastAPI app, even /health requires auth
        assert response.status_code == 401

    def test_multiple_endpoints_require_auth(self, client, test_db):
        """Test that multiple endpoints require authentication."""
        endpoints = [
            "/products",
            "/alerts/expiry",
            "/dashboard/summary",
            "/invoices/recent",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require auth"

    def test_post_endpoints_require_auth(self, client, test_db):
        """Test that POST endpoints require authentication."""
        response = client.post("/products", json={"sku": "TEST", "name": "Test Product"})
        assert response.status_code == 401

    def test_auth_with_encoded_credentials(self, client, test_db):
        """Test authentication with manually encoded credentials."""
        credentials = base64.b64encode(b"admin:retailai2025").decode("utf-8")
        response = client.get(
            "/dashboard/summary",
            headers={"Authorization": f"Basic {credentials}"}
        )
        assert response.status_code == 200
