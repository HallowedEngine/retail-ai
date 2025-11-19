"""Tests for product fuzzy matching functionality."""
import pytest
from app.match import build_product_name_map, fuzzy_match_product


class TestBuildProductNameMap:
    """Tests for building product name map."""

    def test_builds_map_from_products(self):
        products = [
            {"id": 1, "name": "Product A"},
            {"id": 2, "name": "Product B"},
        ]
        result = build_product_name_map(products)
        assert result == {"Product A": 1, "Product B": 2}

    def test_strips_whitespace(self):
        products = [{"id": 1, "name": "  Product A  "}]
        result = build_product_name_map(products)
        assert result == {"Product A": 1}

    def test_skips_empty_names(self):
        products = [
            {"id": 1, "name": "Product A"},
            {"id": 2, "name": ""},
            {"id": 3, "name": None},
        ]
        result = build_product_name_map(products)
        assert result == {"Product A": 1}

    def test_skips_missing_id(self):
        products = [
            {"id": 1, "name": "Product A"},
            {"name": "Product B"},
        ]
        result = build_product_name_map(products)
        assert result == {"Product A": 1}

    def test_handles_empty_list(self):
        result = build_product_name_map([])
        assert result == {}


class TestFuzzyMatchProduct:
    """Tests for fuzzy product matching."""

    def test_exact_match_returns_high_score(self):
        product_map = {"İçim Süt 1L": 1}
        product_id, score = fuzzy_match_product("İçim Süt 1L", product_map)
        assert product_id == 1
        assert score >= 95.0

    def test_close_match_above_threshold(self):
        product_map = {"İçim Süt 1L Tam Yağlı": 1}
        product_id, score = fuzzy_match_product("IÇIM SÜT 1L TAM YAGLI", product_map)
        assert product_id == 1
        assert score >= 80.0

    def test_poor_match_below_threshold_returns_none(self):
        product_map = {"İçim Süt 1L": 1}
        product_id, score = fuzzy_match_product("Completely Different Product", product_map, score_cutoff=85)
        assert product_id is None

    def test_empty_name_returns_none(self):
        product_map = {"Product A": 1}
        product_id, score = fuzzy_match_product("", product_map)
        assert product_id is None
        assert score == 0.0

    def test_empty_product_map_returns_none(self):
        product_id, score = fuzzy_match_product("Product A", {})
        assert product_id is None
        assert score == 0.0

    def test_turkish_character_similarity(self):
        """Test matching with Turkish characters."""
        product_map = {
            "Pınar Süzme Yoğurt": 1,
            "Ülker Çikolata": 2,
        }

        # Test with OCR variations
        product_id, score = fuzzy_match_product("PINAR SÜZME YOĞURT", product_map)
        assert product_id == 1

        product_id, score = fuzzy_match_product("ULKER CIKOLATA", product_map)
        assert product_id == 2

    def test_common_ocr_errors_still_match(self):
        """Test that common OCR errors still result in matches."""
        product_map = {"İçim Süt 1L": 1}

        # Test with common OCR mistakes
        variations = [
            "İcim Süt 1L",
            "IÇIM SUT 1L",
            "İçim Süt 1 L",
        ]

        for variation in variations:
            product_id, score = fuzzy_match_product(variation, product_map, score_cutoff=70)
            assert product_id == 1, f"Failed to match: {variation}"

    def test_case_insensitive_matching(self):
        """Test that matching is effectively case-insensitive."""
        product_map = {"Product Name": 1}

        product_id, score = fuzzy_match_product("PRODUCT NAME", product_map)
        assert product_id == 1

        product_id, score = fuzzy_match_product("product name", product_map)
        assert product_id == 1

    def test_partial_match_with_extra_words(self):
        """Test matching when extra words are present."""
        product_map = {"İçim Süt": 1}

        product_id, score = fuzzy_match_product("İçim Süt 1L Tam Yağlı Ekstra", product_map, score_cutoff=60)
        # Should still match but with lower score
        assert product_id is not None

    def test_selects_best_match_from_multiple(self):
        """Test that best match is selected when multiple candidates exist."""
        product_map = {
            "İçim Süt": 1,
            "İçim Süt 1L": 2,
            "İçim Süt 1L Tam Yağlı": 3,
        }

        product_id, score = fuzzy_match_product("İçim Süt 1L", product_map)
        # Should match the exact one
        assert product_id == 2

    def test_custom_score_cutoff(self):
        """Test that custom score cutoff is respected."""
        product_map = {"Product A": 1}

        # With high cutoff, partial match fails
        product_id, score = fuzzy_match_product("Product", product_map, score_cutoff=90)
        assert product_id is None

        # With lower cutoff, partial match succeeds
        product_id, score = fuzzy_match_product("Product", product_map, score_cutoff=60)
        assert product_id == 1

    def test_special_characters_in_names(self):
        """Test matching with special characters."""
        product_map = {
            "Ürün-A (500g)": 1,
            "Ürün/B [1L]": 2,
        }

        product_id, score = fuzzy_match_product("Ürün-A (500g)", product_map)
        assert product_id == 1

        product_id, score = fuzzy_match_product("Ürün/B [1L]", product_map)
        assert product_id == 2

    def test_whitespace_variations(self):
        """Test that whitespace variations are handled."""
        product_map = {"Product Name": 1}

        variations = [
            "Product  Name",
            "Product   Name",
            " Product Name ",
        ]

        for variation in variations:
            product_id, score = fuzzy_match_product(variation, product_map, score_cutoff=85)
            assert product_id == 1, f"Failed to match: '{variation}'"

    def test_numbers_in_product_names(self):
        """Test matching with numbers in product names."""
        product_map = {
            "İçim Süt 1L": 1,
            "İçim Süt 500ML": 2,
        }

        product_id, score = fuzzy_match_product("İçim Süt 1L", product_map)
        assert product_id == 1

        product_id, score = fuzzy_match_product("İçim Süt 500ML", product_map)
        assert product_id == 2

    def test_very_short_names(self):
        """Test matching with very short product names."""
        product_map = {"AB": 1, "ABC": 2}

        product_id, score = fuzzy_match_product("AB", product_map)
        assert product_id == 1

    def test_very_long_names(self):
        """Test matching with very long product names."""
        long_name = "İçim Süt 1 Litre Tam Yağlı UHT Sterilize Süt Ürünü Ekstra Vitamin D İlaveli"
        product_map = {long_name: 1}

        product_id, score = fuzzy_match_product(long_name, product_map)
        assert product_id == 1
        assert score >= 95.0
