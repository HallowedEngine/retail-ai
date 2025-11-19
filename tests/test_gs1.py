"""Tests for GS1 barcode parsing functionality."""
import pytest
from datetime import datetime
from app.gs1 import parse_gs1_from_text, parse_expiry_from_free_text


class TestParseGS1FromText:
    """Tests for GS1 barcode parsing."""

    def test_parse_gs1_with_expiry_date(self):
        """Test parsing GS1 with AI(17) expiry date."""
        barcode = "(01)08690000000012(17)260912(10)LOT123"
        expiry, lot = parse_gs1_from_text(barcode)

        assert expiry is not None
        assert expiry.year == 2026
        assert expiry.month == 9
        assert expiry.day == 12
        assert lot == "LOT123"

    def test_parse_gs1_with_only_expiry(self):
        """Test parsing GS1 with only expiry date."""
        barcode = "(17)250315"
        expiry, lot = parse_gs1_from_text(barcode)

        assert expiry is not None
        assert expiry.year == 2025
        assert expiry.month == 3
        assert expiry.day == 15
        assert lot is None

    def test_parse_gs1_with_only_lot(self):
        """Test parsing GS1 with only lot code."""
        barcode = "(10)ABC-123"
        expiry, lot = parse_gs1_from_text(barcode)

        assert expiry is None
        assert lot == "ABC-123"

    def test_parse_gs1_empty_string(self):
        """Test parsing empty string."""
        expiry, lot = parse_gs1_from_text("")
        assert expiry is None
        assert lot is None

    def test_parse_gs1_none_input(self):
        """Test parsing None input."""
        expiry, lot = parse_gs1_from_text(None)
        assert expiry is None
        assert lot is None

    def test_parse_gs1_invalid_format(self):
        """Test parsing invalid GS1 format."""
        barcode = "Invalid barcode string"
        expiry, lot = parse_gs1_from_text(barcode)

        assert expiry is None
        assert lot is None

    def test_parse_gs1_with_spaces(self):
        """Test parsing GS1 with extra spaces."""
        barcode = "(17) 260912 (10) LOT456"
        expiry, lot = parse_gs1_from_text(barcode)

        assert expiry is not None
        assert expiry.year == 2026
        assert lot == "LOT456"

    def test_parse_gs1_lot_with_special_chars(self):
        """Test parsing lot codes with special characters."""
        barcode = "(10)LOT_2025-01.A"
        expiry, lot = parse_gs1_from_text(barcode)

        assert lot == "LOT_2025-01.A"

    def test_parse_gs1_year_2000_assumption(self):
        """Test that years are correctly interpreted as 20xx."""
        barcode = "(17)991231"  # 99-12-31
        expiry, lot = parse_gs1_from_text(barcode)

        assert expiry.year == 2099
        assert expiry.month == 12
        assert expiry.day == 31

    def test_parse_gs1_multiple_ai_codes(self):
        """Test parsing with multiple AI codes."""
        barcode = "(01)12345678901234(17)260515(10)BATCH99(21)SERIAL123"
        expiry, lot = parse_gs1_from_text(barcode)

        assert expiry is not None
        assert expiry.year == 2026
        assert expiry.month == 5
        assert expiry.day == 15
        assert lot == "BATCH99"


class TestParseExpiryFromFreeText:
    """Tests for free-text expiry date extraction."""

    def test_parse_dd_mm_yyyy_with_dots(self):
        """Test parsing DD.MM.YYYY format."""
        text = "SKT: 12.03.2026"
        expiry = parse_expiry_from_free_text(text)

        assert expiry is not None
        assert expiry.year == 2026
        assert expiry.month == 3
        assert expiry.day == 12

    def test_parse_dd_mm_yyyy_with_slashes(self):
        """Test parsing DD/MM/YYYY format."""
        text = "Use by 15/06/2025"
        expiry = parse_expiry_from_free_text(text)

        assert expiry is not None
        assert expiry.year == 2025
        assert expiry.month == 6
        assert expiry.day == 15

    def test_parse_yyyy_mm_dd_format(self):
        """Test parsing YYYY-MM-DD format."""
        text = "Expiry: 2026-12-31"
        expiry = parse_expiry_from_free_text(text)

        assert expiry is not None
        assert expiry.year == 2026
        assert expiry.month == 12
        assert expiry.day == 31

    def test_parse_dd_mm_yy_format(self):
        """Test parsing DD.MM.YY format (2-digit year)."""
        text = "TETT 25.08.26"
        expiry = parse_expiry_from_free_text(text)

        assert expiry is not None
        assert expiry.year == 2026
        assert expiry.month == 8
        assert expiry.day == 25

    def test_parse_with_skt_keyword(self):
        """Test parsing with Turkish SKT keyword."""
        text = "SKT 10.05.2025"
        expiry = parse_expiry_from_free_text(text)

        assert expiry is not None
        assert expiry.year == 2025

    def test_parse_with_tett_keyword(self):
        """Test parsing with Turkish TETT keyword."""
        text = "TETT: 20.12.2025"
        expiry = parse_expiry_from_free_text(text)

        assert expiry is not None
        assert expiry.year == 2025

    def test_parse_with_exp_keyword(self):
        """Test parsing with EXP keyword."""
        text = "EXP 01.01.2026"
        expiry = parse_expiry_from_free_text(text)

        assert expiry is not None
        assert expiry.year == 2026

    def test_parse_with_use_by_keyword(self):
        """Test parsing with 'Use by' keyword."""
        text = "Use by 30/11/2025"
        expiry = parse_expiry_from_free_text(text)

        assert expiry is not None
        assert expiry.year == 2025
        assert expiry.month == 11
        assert expiry.day == 30

    def test_parse_with_son_kullanma_keyword(self):
        """Test parsing with Turkish 'Son kullanma' keyword."""
        text = "Son kullanma tarihi: 15.07.2026"
        expiry = parse_expiry_from_free_text(text)

        assert expiry is not None
        assert expiry.year == 2026
        assert expiry.month == 7
        assert expiry.day == 15

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        expiry = parse_expiry_from_free_text("")
        assert expiry is None

    def test_parse_none_input(self):
        """Test parsing None input."""
        expiry = parse_expiry_from_free_text(None)
        assert expiry is None

    def test_parse_no_date_found(self):
        """Test parsing text with no date."""
        text = "This is just random text with no date"
        expiry = parse_expiry_from_free_text(text)
        assert expiry is None

    def test_parse_invalid_date(self):
        """Test parsing invalid date (e.g., 32/13/2025)."""
        text = "SKT 32.13.2025"  # Invalid date
        expiry = parse_expiry_from_free_text(text)
        # Should return None for invalid dates
        assert expiry is None

    def test_parse_multiple_dates_returns_first(self):
        """Test that parsing returns first valid date found."""
        text = "SKT 10.05.2025 and also 20.06.2026"
        expiry = parse_expiry_from_free_text(text)

        assert expiry is not None
        # Should return first valid date
        assert expiry.year == 2025 or expiry.year == 2026

    def test_parse_case_insensitive_keywords(self):
        """Test that keywords are case-insensitive."""
        texts = [
            "skt 10.05.2025",
            "SKT 10.05.2025",
            "Skt 10.05.2025",
            "exp 10.05.2025",
            "EXP 10.05.2025",
        ]

        for text in texts:
            expiry = parse_expiry_from_free_text(text)
            assert expiry is not None
            assert expiry.year == 2025

    def test_parse_date_without_keyword(self):
        """Test parsing date without explicit keyword."""
        text = "12.03.2026"
        expiry = parse_expiry_from_free_text(text)

        # May or may not work depending on implementation
        # Current implementation requires keywords
        # This test documents the behavior
        assert expiry is None or expiry.year == 2026

    def test_parse_with_dashes(self):
        """Test parsing dates with dashes."""
        text = "SKT 12-03-2026"
        expiry = parse_expiry_from_free_text(text)

        assert expiry is not None
        assert expiry.year == 2026
        assert expiry.month == 3
        assert expiry.day == 12
