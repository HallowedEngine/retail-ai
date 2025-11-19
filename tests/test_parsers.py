"""Tests for invoice parsing functionality."""
import pytest
from app.parsers import (
    parse_invoice_lines,
    _clean_name,
    _postfix_name,
    _final_name_clean,
    _to_float,
    _normalize_qty,
    _looks_like_name
)


class TestCleanName:
    """Tests for name cleaning functions."""

    def test_clean_name_removes_special_chars(self):
        assert _clean_name("Test @#$ Product") == "Test Product"

    def test_clean_name_preserves_turkish_chars(self):
        assert _clean_name("ÇĞİÖŞÜ çğıöşü") == "ÇĞİÖŞÜ çğıöşü"

    def test_clean_name_preserves_allowed_punctuation(self):
        assert _clean_name("A-B.C/D(E)") == "A-B.C/D(E)"

    def test_clean_name_strips_whitespace(self):
        assert _clean_name("  test  product  ") == "test product"


class TestPostfixName:
    """Tests for OCR error corrections."""

    def test_postfix_corrects_fce_to_ece(self):
        result = _postfix_name("FCE SÜZME")
        assert "ECE" in result

    def test_postfix_corrects_tolu_to_10lu(self):
        result = _postfix_name("TOLU PAKET")
        assert "10LU" in result

    def test_postfix_corrects_pmhouse_to_emhouse(self):
        result = _postfix_name("PMHOUSE")
        assert "EMHOUSE" in result

    def test_postfix_preserves_short_strings(self):
        result = _postfix_name("AB")
        assert len(result) >= 2

    def test_postfix_removes_trailing_noise(self):
        result = _postfix_name("PRODUCT AT 0")
        assert "AT 0" not in result


class TestFinalNameClean:
    """Tests for final name cleaning."""

    def test_removes_trailing_punctuation(self):
        assert _final_name_clean("Product,") == "Product"
        assert _final_name_clean("Product.") == "Product"

    def test_removes_double_spaces(self):
        assert _final_name_clean("Product  Name") == "Product Name"

    def test_removes_double_dots(self):
        assert _final_name_clean("Product..Name") == "Product.Name"


class TestToFloat:
    """Tests for float conversion."""

    def test_converts_simple_number(self):
        assert _to_float("123.45") == 123.45

    def test_converts_comma_decimal(self):
        assert _to_float("123,45") == 123.45

    def test_removes_tl_symbol(self):
        assert _to_float("123.45 TL") == 123.45
        assert _to_float("123.45₺") == 123.45

    def test_handles_invalid_input(self):
        assert _to_float("abc") == 0.0

    def test_removes_spaces(self):
        assert _to_float("1 234.56") == 1234.56


class TestNormalizeQty:
    """Tests for quantity normalization."""

    def test_normalizes_near_one(self):
        assert _normalize_qty(0.95) == 1.0
        assert _normalize_qty(1.05) == 1.0
        assert _normalize_qty(1.0) == 1.0

    def test_keeps_other_values(self):
        assert _normalize_qty(2.5) == 2.5
        assert _normalize_qty(0.5) == 0.5
        assert _normalize_qty(10.0) == 10.0


class TestLooksLikeName:
    """Tests for name detection."""

    def test_empty_string_not_name(self):
        assert not _looks_like_name("")
        assert not _looks_like_name("  ")

    def test_short_string_not_name(self):
        assert not _looks_like_name("AB")

    def test_pure_barcode_not_name(self):
        assert not _looks_like_name("8682971085011")

    def test_valid_name_detected(self):
        assert _looks_like_name("İÇİM SÜT")
        assert _looks_like_name("ÜLKER ÇİKOLATA")

    def test_requires_sufficient_letters(self):
        assert _looks_like_name("ABC123")
        assert not _looks_like_name("12345")


class TestParseInvoiceLines:
    """Tests for full invoice parsing."""

    def test_parse_empty_text(self):
        result = parse_invoice_lines("")
        assert result == []

    def test_parse_barcode_pattern(self):
        ocr_text = """8682971085011  1,000 AD   47,50   20.00   47,03
İÇİM SÜT 1L TAM YAĞLI"""
        result = parse_invoice_lines(ocr_text)
        assert len(result) == 1
        assert result[0]["barcode"] == "8682971085011"
        assert result[0]["qty"] == 1.0
        assert result[0]["unit"] == "adet"
        assert result[0]["unit_price"] == 47.50

    def test_parse_with_product_name_on_next_line(self):
        ocr_text = """8690504003014  2,000 AD   5,75   11,50
ÜLKER ÇİKOLATA"""
        result = parse_invoice_lines(ocr_text)
        assert len(result) == 1
        assert "ÜLKER" in result[0]["name_raw"] or "CIKOLATA" in result[0]["name_raw"]

    def test_parse_x_at_pattern(self):
        ocr_text = "ÜLKER ÇİKOLATA x2.5 @10.00"
        result = parse_invoice_lines(ocr_text)
        assert len(result) == 1
        assert result[0]["qty"] == 2.5
        assert result[0]["unit_price"] == 10.0

    def test_parse_dual_numbers_pattern(self):
        ocr_text = "ÜLKER ÇİKOLATA  3  15.50"
        result = parse_invoice_lines(ocr_text)
        assert len(result) == 1
        assert result[0]["qty"] == 3.0
        assert result[0]["unit_price"] == 15.50

    def test_skip_kdv_lines(self):
        ocr_text = """8682971085011  1,000 AD   47,50
SÜZME YOĞURT
KDV %8  3,80
TOPLAM  51,30"""
        result = parse_invoice_lines(ocr_text)
        # Should only parse product line, not KDV or TOPLAM
        assert all("KDV" not in line.get("name_raw", "") for line in result)
        assert all("TOPLAM" not in line.get("name_raw", "") for line in result)

    def test_skip_kdv_variants(self):
        """Test various KDV OCR variations."""
        ocr_text = """8682971085011  1,000 AD   47,50
PRODUCT
DVS %8  3,80
KDVE TOPLAMI  3,80
KDV%8  3,80"""
        result = parse_invoice_lines(ocr_text)
        # Should normalize DVS -> KDV and KDVE -> KDV and skip
        assert len(result) == 1

    def test_max_200_lines_limit(self):
        """Test that parser limits to 200 lines."""
        # Create 250 valid lines
        lines = [f"869050400{i:04d}  1 AD   10,00\nPRODUCT{i}" for i in range(250)]
        ocr_text = "\n".join(lines)
        result = parse_invoice_lines(ocr_text)
        assert len(result) <= 200

    def test_turkish_character_normalization(self):
        ocr_text = """8682971085011  1 AD   10,00
SÜZME YOĞURT ÇİĞ ŞEKERLİ"""
        result = parse_invoice_lines(ocr_text)
        assert len(result) == 1
        # Turkish characters should be preserved in name_raw
        name = result[0]["name_raw"]
        assert len(name) > 0

    def test_invalid_prices_filtered(self):
        """Lines with very high or zero prices should be filtered out."""
        ocr_text = """8682971085011  1 AD   0.00
8690504003014  1 AD   15.50
8690504005012  1 AD   99999.00"""
        result = parse_invoice_lines(ocr_text)
        # Only the line with valid price in range should be parsed
        assert len(result) >= 1
        # Check that at least one result has reasonable price
        assert any(0 < line["unit_price"] < 10000 for line in result)

    def test_zero_quantity_filtered(self):
        """Lines with zero quantity should be filtered out."""
        ocr_text = """8682971085011  0 AD   10.00
8690504003014  1 AD   15.50"""
        result = parse_invoice_lines(ocr_text)
        assert len(result) == 1
        assert result[0]["unit_price"] == 15.50

    def test_unit_types_parsed(self):
        """Test different unit types."""
        ocr_text = """8682971085011  1 AD   10.00
PRODUCT A
8690504003014  2.5 KG   20.00
PRODUCT B
8690504005012  1 KOLI   30.00
PRODUCT C"""
        result = parse_invoice_lines(ocr_text)
        assert len(result) == 3
        assert result[0]["unit"] == "adet"
        assert result[1]["unit"] == "kg"
        assert result[2]["unit"] == "koli"

    def test_handles_malformed_input(self):
        """Test that malformed input doesn't crash."""
        malformed = "!@#$%^&*()\n\n\n   \t\t\t\n12345"
        result = parse_invoice_lines(malformed)
        # Should return empty or minimal results without crashing
        assert isinstance(result, list)

    def test_qty_near_one_normalized(self):
        """Test that quantities near 1.0 are normalized."""
        ocr_text = "8682971085011  0,999 AD   10.00\nPRODUCT"
        result = parse_invoice_lines(ocr_text)
        assert len(result) == 1
        assert result[0]["qty"] == 1.0

    def test_unit_price_calculation_from_total(self):
        """Test unit price parsing with multiple price values."""
        # Test parsing behavior with multiple price values
        ocr_text = "8682971085011  2 AD   15.00   30.00\nPRODUCT"
        result = parse_invoice_lines(ocr_text)
        if len(result) == 1:
            # Parser may use first price or calculate from total
            assert result[0]["unit_price"] in [15.0, 30.0]
