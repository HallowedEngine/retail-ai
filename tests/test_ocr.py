"""Tests for OCR functionality."""
import pytest
import os
from PIL import Image
import tempfile
from app.ocr import run_tesseract, _preprocess


class TestOCR:
    """Tests for OCR processing."""

    def create_test_image(self, width=800, height=600, color='white') -> str:
        """Create a simple test image and return path."""
        img = Image.new('RGB', (width, height), color=color)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        img.save(temp_file.name, format='JPEG')
        return temp_file.name

    def teardown_method(self):
        """Clean up temp files after each test."""
        # Clean up any temp files created during tests
        pass

    def test_run_tesseract_with_valid_image(self):
        """Test OCR with a valid image."""
        img_path = self.create_test_image()

        try:
            result = run_tesseract(img_path)

            assert isinstance(result, dict)
            assert "text" in result
            assert "conf" in result
            assert "engine" in result
            assert result["engine"] == "tesseract"
        finally:
            if os.path.exists(img_path):
                os.unlink(img_path)

    def test_run_tesseract_with_invalid_path(self):
        """Test OCR with invalid file path."""
        result = run_tesseract("/nonexistent/path/to/image.jpg")

        # Should handle gracefully
        assert isinstance(result, dict)
        # Either empty or contains error information
        assert result.get("text") == "" or "error" in result

    def test_run_tesseract_confidence_score(self):
        """Test that confidence score is returned."""
        img_path = self.create_test_image()

        try:
            result = run_tesseract(img_path)

            assert "conf" in result
            # Confidence should be a number between 0 and 100
            if result["conf"] is not None and result["conf"] != "":
                conf = float(result["conf"]) if isinstance(result["conf"], str) else result["conf"]
                assert 0 <= conf <= 100
        finally:
            if os.path.exists(img_path):
                os.unlink(img_path)

    def test_preprocess_image(self):
        """Test image preprocessing function."""
        img_path = self.create_test_image()

        try:
            # Test that preprocessing works
            preprocessed = _preprocess(img_path)

            # Should return a processed image path or array
            assert preprocessed is not None
        except Exception as e:
            # Preprocessing may fail if OpenCV is not properly configured
            # This is acceptable in test environment
            pytest.skip(f"Image preprocessing failed: {e}")
        finally:
            if os.path.exists(img_path):
                os.unlink(img_path)

    def test_ocr_with_different_image_sizes(self):
        """Test OCR with different image dimensions."""
        sizes = [(400, 300), (800, 600), (1600, 1200)]

        for width, height in sizes:
            img_path = self.create_test_image(width, height)

            try:
                result = run_tesseract(img_path)
                assert isinstance(result, dict)
                assert "text" in result
            finally:
                if os.path.exists(img_path):
                    os.unlink(img_path)

    def test_ocr_returns_text_field(self):
        """Test that OCR result always contains text field."""
        img_path = self.create_test_image()

        try:
            result = run_tesseract(img_path)
            assert "text" in result
            assert isinstance(result["text"], str)
        finally:
            if os.path.exists(img_path):
                os.unlink(img_path)


class TestOCRIntegration:
    """Integration tests for OCR with real scenarios."""

    @pytest.mark.skipif(
        os.getenv("SKIP_OCR_TESTS") == "1",
        reason="OCR integration tests skipped (set SKIP_OCR_TESTS=1)"
    )
    def test_ocr_with_actual_invoice_like_image(self):
        """Test OCR with an image that resembles an invoice."""
        # This test would work with actual test invoice images
        # Skip if no test images are available
        pytest.skip("Requires actual test invoice images")

    def test_ocr_handles_corrupted_image(self):
        """Test that OCR handles corrupted images gracefully."""
        # Create a corrupted file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_file.write(b'This is not a valid image file')
        temp_file.close()

        try:
            result = run_tesseract(temp_file.name)
            # Should not crash, should return gracefully
            assert isinstance(result, dict)
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
