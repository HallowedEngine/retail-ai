# Test Suite

This directory contains comprehensive tests for the retail-ai application.

## Running Tests

### Install dependencies
```bash
pip install -r requirements-dev.txt
```

### Run all tests
```bash
pytest
```

### Run with coverage report
```bash
pytest --cov=app --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_parsers.py -v
```

## Test Organization

### Priority 1: Critical Business Logic
- `test_parsers.py` - Invoice parsing and OCR text extraction (39 tests)
- `test_match.py` - Product fuzzy matching (22 tests)
- `test_logic.py` - Expiry alerts and demand forecasting (20 tests)

### Priority 2: API Endpoints
- `test_auth.py` - Authentication (10 tests)
- `test_api_invoices.py` - Invoice upload and management (9 tests)
- `test_api_products.py` - Product CRUD and bulk operations (17 tests)

### Priority 3: Integration & Database
- `test_ocr.py` - OCR engine integration (7 tests)
- `test_models.py` - Database models and constraints (19 tests)
- `test_gs1.py` - Barcode parsing (28 tests)

## Test Coverage

Current test coverage: **~65%** (143 passing tests)

### Coverage by Module:
- `app/parsers.py`: ~85%
- `app/match.py`: ~90%
- `app/logic.py`: ~80%
- `app/models.py`: ~75%
- `app/gs1.py`: ~95%
- `app/main.py` (API): ~50%
- `app/ocr.py`: ~40% (requires Tesseract)

## Known Test Limitations

### OCR Tests
OCR tests require Tesseract to be installed on the system:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from https://github.com/UB-Mannheim/tesseract/wiki
```

If Tesseract is not available, OCR tests will be skipped.

### Fuzzy Matching Tests
Fuzzy matching scores may vary slightly depending on whether RapidFuzz or difflib is used.
Tests are designed to be tolerant of minor score differences.

## Fixtures

Test fixtures are defined in `conftest.py`:
- `test_db` - Fresh in-memory SQLite database for each test
- `client` - FastAPI test client with auth override
- `sample_products` - Pre-populated product data
- `sample_invoices` - Sample invoice records
- `sample_batches` - Sample batch data for expiry testing
- `sample_sales` - Sample sales data for forecasting
- `auth_headers` - Valid authentication headers

## Adding New Tests

1. Create test file following naming convention: `test_*.py`
2. Use fixtures from `conftest.py` for database and auth
3. Organize tests into classes by feature area
4. Add docstrings explaining what each test validates
5. Run tests locally before committing

## CI/CD Integration

Tests can be run in CI/CD pipelines:
```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements-dev.txt
    pytest --cov=app --cov-report=xml
```

## Test Data

Sample test data is located in `tests/fixtures/`:
- `sample_data.json` - Mock product and invoice data
- `sample_invoices/` - Test invoice images (if available)

## Troubleshooting

### "No module named 'sqlalchemy'"
```bash
pip install -r requirements.txt
```

### "ModuleNotFoundError: No module named 'pytest'"
```bash
pip install -r requirements-dev.txt
```

### "tesseract is not installed"
Install Tesseract (see OCR Tests section above) or skip OCR tests:
```bash
SKIP_OCR_TESTS=1 pytest
```

### Database errors
Tests use in-memory SQLite databases that are created fresh for each test.
If you see table errors, ensure `conftest.py` is properly setting up the database.
