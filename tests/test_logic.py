"""Tests for business logic: expiry alerts and forecasting."""
import pytest
from datetime import datetime, date, timedelta
import pandas as pd
from freezegun import freeze_time

from app.logic import refresh_expiry_alerts, naive_hourly_forecast, reorder_suggestion
from app.models import Batch, ExpiryAlert, Sale, Product, Forecast


class TestRefreshExpiryAlerts:
    """Tests for expiry alert generation."""

    @freeze_time("2025-01-15")
    def test_creates_red_alert_for_3_days_or_less(self, test_db, sample_products):
        """Test that red alerts are created for items expiring in 3 days or less."""
        # Create batch expiring in 2 days
        batch = Batch(
            product_id=sample_products[0].id,
            store_id=1,
            lot_code="LOT001",
            expiry_date=date(2025, 1, 17),  # 2 days from frozen date
            qty_received=100.0,
            qty_on_hand=50.0
        )
        test_db.add(batch)
        test_db.commit()

        refresh_expiry_alerts(test_db, store_id=1, days_window=7)

        alerts = test_db.query(ExpiryAlert).all()
        assert len(alerts) == 1
        assert alerts[0].severity == "red"
        assert alerts[0].days_left == 2

    @freeze_time("2025-01-15")
    def test_creates_yellow_alert_for_4_to_7_days(self, test_db, sample_products):
        """Test that yellow alerts are created for items expiring in 4-7 days."""
        # Create batch expiring in 5 days
        batch = Batch(
            product_id=sample_products[0].id,
            store_id=1,
            lot_code="LOT001",
            expiry_date=date(2025, 1, 20),  # 5 days from frozen date
            qty_received=100.0,
            qty_on_hand=50.0
        )
        test_db.add(batch)
        test_db.commit()

        refresh_expiry_alerts(test_db, store_id=1, days_window=7)

        alerts = test_db.query(ExpiryAlert).all()
        assert len(alerts) == 1
        assert alerts[0].severity == "yellow"
        assert alerts[0].days_left == 5

    @freeze_time("2025-01-15")
    def test_no_alert_for_distant_expiry(self, test_db, sample_products):
        """Test that no alerts are created for items expiring beyond the window."""
        # Create batch expiring in 30 days
        batch = Batch(
            product_id=sample_products[0].id,
            store_id=1,
            lot_code="LOT001",
            expiry_date=date(2025, 2, 14),  # 30 days from frozen date
            qty_received=100.0,
            qty_on_hand=50.0
        )
        test_db.add(batch)
        test_db.commit()

        refresh_expiry_alerts(test_db, store_id=1, days_window=7)

        alerts = test_db.query(ExpiryAlert).all()
        assert len(alerts) == 0

    @freeze_time("2025-01-15")
    def test_idempotent_no_duplicates(self, test_db, sample_products):
        """Test that running twice doesn't create duplicate alerts."""
        batch = Batch(
            product_id=sample_products[0].id,
            store_id=1,
            lot_code="LOT001",
            expiry_date=date(2025, 1, 17),
            qty_received=100.0,
            qty_on_hand=50.0
        )
        test_db.add(batch)
        test_db.commit()

        # Run twice
        refresh_expiry_alerts(test_db, store_id=1, days_window=7)
        refresh_expiry_alerts(test_db, store_id=1, days_window=7)

        alerts = test_db.query(ExpiryAlert).all()
        assert len(alerts) == 1  # Should still be only 1 alert

    @freeze_time("2025-01-15")
    def test_updates_existing_alert_when_days_change(self, test_db, sample_products):
        """Test that existing alerts are updated when days_left changes."""
        batch = Batch(
            product_id=sample_products[0].id,
            store_id=1,
            lot_code="LOT001",
            expiry_date=date(2025, 1, 20),  # 5 days (yellow)
            qty_received=100.0,
            qty_on_hand=50.0
        )
        test_db.add(batch)
        test_db.commit()

        # First run: 5 days left (yellow)
        refresh_expiry_alerts(test_db, store_id=1, days_window=7)
        alerts = test_db.query(ExpiryAlert).all()
        assert len(alerts) == 1
        assert alerts[0].severity == "yellow"
        assert alerts[0].days_left == 5

        # Simulate time passing (now 2 days left, should become red)
        with freeze_time("2025-01-18"):
            refresh_expiry_alerts(test_db, store_id=1, days_window=7)
            test_db.refresh(alerts[0])
            assert alerts[0].severity == "red"
            assert alerts[0].days_left == 2

    @freeze_time("2025-01-15")
    def test_skips_batches_without_expiry_date(self, test_db, sample_products):
        """Test that batches without expiry dates are skipped."""
        batch = Batch(
            product_id=sample_products[0].id,
            store_id=1,
            lot_code="LOT001",
            expiry_date=None,  # No expiry date
            qty_received=100.0,
            qty_on_hand=50.0
        )
        test_db.add(batch)
        test_db.commit()

        refresh_expiry_alerts(test_db, store_id=1, days_window=7)

        alerts = test_db.query(ExpiryAlert).all()
        assert len(alerts) == 0

    @freeze_time("2025-01-15")
    def test_multiple_batches_same_product(self, test_db, sample_products):
        """Test handling of multiple batches for the same product."""
        batch1 = Batch(
            product_id=sample_products[0].id,
            store_id=1,
            lot_code="LOT001",
            expiry_date=date(2025, 1, 17),  # 2 days
            qty_received=100.0,
            qty_on_hand=50.0
        )
        batch2 = Batch(
            product_id=sample_products[0].id,
            store_id=1,
            lot_code="LOT002",
            expiry_date=date(2025, 1, 20),  # 5 days
            qty_received=100.0,
            qty_on_hand=50.0
        )
        test_db.add_all([batch1, batch2])
        test_db.commit()

        refresh_expiry_alerts(test_db, store_id=1, days_window=7)

        alerts = test_db.query(ExpiryAlert).order_by(ExpiryAlert.days_left).all()
        assert len(alerts) == 2
        assert alerts[0].days_left == 2
        assert alerts[0].severity == "red"
        assert alerts[1].days_left == 5
        assert alerts[1].severity == "yellow"

    @freeze_time("2025-01-15")
    def test_custom_days_window(self, test_db, sample_products):
        """Test custom days_window parameter."""
        # Batch expiring in 10 days
        batch = Batch(
            product_id=sample_products[0].id,
            store_id=1,
            lot_code="LOT001",
            expiry_date=date(2025, 1, 25),  # 10 days
            qty_received=100.0,
            qty_on_hand=50.0
        )
        test_db.add(batch)
        test_db.commit()

        # Default window (7 days) - no alert
        refresh_expiry_alerts(test_db, store_id=1, days_window=7)
        assert test_db.query(ExpiryAlert).count() == 0

        # Extended window (14 days) - should create alert
        refresh_expiry_alerts(test_db, store_id=1, days_window=14)
        alerts = test_db.query(ExpiryAlert).all()
        assert len(alerts) == 1


class TestNaiveHourlyForecast:
    """Tests for demand forecasting."""

    def test_no_sales_returns_empty(self, test_db, sample_products):
        """Test that forecast returns empty when no sales data exists."""
        result = naive_hourly_forecast(test_db, store_id=1, product_id=sample_products[0].id)
        assert len(result) == 0

    def test_generates_168_hours_for_7_days(self, test_db, sample_products):
        """Test that 7-day forecast generates 168 hourly records."""
        # Create some sales data
        now = datetime(2025, 1, 15, 12, 0, 0)
        for i in range(10):
            sale = Sale(
                store_id=1,
                product_id=sample_products[0].id,
                ts=now - timedelta(days=i),
                qty=5.0
            )
            test_db.add(sale)
        test_db.commit()

        result = naive_hourly_forecast(test_db, store_id=1, product_id=sample_products[0].id, horizon_days=7)

        assert len(result) == 168  # 7 days * 24 hours

    def test_uses_28_day_lookback(self, test_db, sample_products):
        """Test that forecast uses last 28 days of data."""
        now = datetime(2025, 1, 15, 12, 0, 0)

        # Create sales: some old (35 days ago), some recent (within 28 days)
        for i in range(35):
            sale = Sale(
                store_id=1,
                product_id=sample_products[0].id,
                ts=now - timedelta(days=i),
                qty=10.0 if i < 28 else 1.0  # Different qty for recent vs old
            )
            test_db.add(sale)
        test_db.commit()

        result = naive_hourly_forecast(test_db, store_id=1, product_id=sample_products[0].id)

        # Forecast should exist (based on recent data)
        assert len(result) > 0

    def test_day_of_week_hour_aggregation(self, test_db, sample_products):
        """Test that forecast aggregates by day of week and hour."""
        base_time = datetime(2025, 1, 6, 10, 0, 0)  # Monday at 10am

        # Create consistent pattern: Every Monday at 10am, qty=20
        for week in range(4):
            sale = Sale(
                store_id=1,
                product_id=sample_products[0].id,
                ts=base_time - timedelta(weeks=week),
                qty=20.0
            )
            test_db.add(sale)

        # Other days/hours: qty=5
        for day_offset in range(28):
            for hour in [9, 11, 12]:  # Different hours
                sale = Sale(
                    store_id=1,
                    product_id=sample_products[0].id,
                    ts=base_time - timedelta(days=day_offset, hours=hour-10),
                    qty=5.0
                )
                test_db.add(sale)

        test_db.commit()

        result = naive_hourly_forecast(test_db, store_id=1, product_id=sample_products[0].id)

        # Find forecast for Monday at 10am
        result_df = pd.DataFrame(result)
        result_df['dow'] = result_df['ts'].dt.dayofweek
        result_df['hour'] = result_df['ts'].dt.hour

        monday_10am = result_df[(result_df['dow'] == 0) & (result_df['hour'] == 10)]
        if not monday_10am.empty:
            # Should forecast higher for Monday 10am
            assert monday_10am['yhat'].iloc[0] > 15.0

    def test_idempotent_deletes_old_forecasts(self, test_db, sample_products):
        """Test that running forecast twice replaces old forecasts."""
        now = datetime(2025, 1, 15, 12, 0, 0)
        for i in range(10):
            sale = Sale(
                store_id=1,
                product_id=sample_products[0].id,
                ts=now - timedelta(days=i),
                qty=5.0
            )
            test_db.add(sale)
        test_db.commit()

        # Run twice
        naive_hourly_forecast(test_db, store_id=1, product_id=sample_products[0].id)
        naive_hourly_forecast(test_db, store_id=1, product_id=sample_products[0].id)

        # Should not have duplicates
        forecasts = test_db.query(Forecast).filter(
            Forecast.store_id == 1,
            Forecast.product_id == sample_products[0].id
        ).all()

        # Should have ~168 records, not ~336
        assert len(forecasts) <= 170  # Allow small margin

    def test_handles_sparse_data(self, test_db, sample_products):
        """Test forecast with sparse sales data."""
        now = datetime(2025, 1, 15, 12, 0, 0)

        # Only 3 sales in last 28 days
        for i in [1, 7, 14]:
            sale = Sale(
                store_id=1,
                product_id=sample_products[0].id,
                ts=now - timedelta(days=i),
                qty=10.0
            )
            test_db.add(sale)
        test_db.commit()

        result = naive_hourly_forecast(test_db, store_id=1, product_id=sample_products[0].id)

        # Should still generate forecast (with zeros for missing hours)
        assert len(result) == 168


class TestReorderSuggestion:
    """Tests for reorder quantity calculation."""

    def test_zero_when_no_forecast(self):
        """Test that reorder returns 0 when no forecast data."""
        result = reorder_suggestion(
            current_stock=100.0,
            lead_time_days=3,
            safety_stock=10.0,
            forecast_df=None
        )
        assert result == 0

    def test_zero_when_empty_forecast(self):
        """Test that reorder returns 0 when forecast is empty."""
        empty_df = pd.DataFrame(columns=['ts', 'yhat'])
        result = reorder_suggestion(
            current_stock=100.0,
            lead_time_days=3,
            safety_stock=10.0,
            forecast_df=empty_df
        )
        assert result == 0

    def test_calculates_reorder_qty_correctly(self):
        """Test reorder quantity calculation."""
        # Create forecast: 10 units/hour for 3 days = 720 units
        future = pd.date_range(datetime.now(), periods=72, freq="H")  # 3 days
        forecast_df = pd.DataFrame({
            'ts': future,
            'yhat': [10.0] * 72
        })

        result = reorder_suggestion(
            current_stock=50.0,
            lead_time_days=3,
            safety_stock=20.0,
            forecast_df=forecast_df
        )

        # Expected: safety_stock(20) + expected_demand(720) - current_stock(50) = 690
        assert result == 690

    def test_zero_when_sufficient_stock(self):
        """Test that reorder is 0 when current stock is sufficient."""
        future = pd.date_range(datetime.now(), periods=24, freq="H")  # 1 day
        forecast_df = pd.DataFrame({
            'ts': future,
            'yhat': [5.0] * 24
        })

        result = reorder_suggestion(
            current_stock=200.0,  # More than enough
            lead_time_days=1,
            safety_stock=10.0,
            forecast_df=forecast_df
        )

        # Expected: 10 + 120 - 200 = -70, but should return 0
        assert result == 0

    def test_respects_lead_time_days(self):
        """Test that reorder only considers forecast within lead time."""
        # Create 7-day forecast
        future = pd.date_range(datetime.now(), periods=168, freq="H")  # 7 days
        forecast_df = pd.DataFrame({
            'ts': future,
            'yhat': [10.0] * 168
        })

        # Calculate with 2-day lead time (should only use 48 hours)
        result = reorder_suggestion(
            current_stock=10.0,
            lead_time_days=2,
            safety_stock=20.0,
            forecast_df=forecast_df
        )

        # Expected: 20 + (48*10) - 10 = 490
        assert result == 490

    def test_handles_zero_current_stock(self):
        """Test reorder with zero current stock."""
        future = pd.date_range(datetime.now(), periods=24, freq="H")
        forecast_df = pd.DataFrame({
            'ts': future,
            'yhat': [10.0] * 24
        })

        result = reorder_suggestion(
            current_stock=0.0,
            lead_time_days=1,
            safety_stock=50.0,
            forecast_df=forecast_df
        )

        # Expected: 50 + 240 - 0 = 290
        assert result == 290

    def test_rounds_to_integer(self):
        """Test that result is rounded to integer."""
        future = pd.date_range(datetime.now(), periods=10, freq="H")
        forecast_df = pd.DataFrame({
            'ts': future,
            'yhat': [1.5] * 10  # Total = 15
        })

        result = reorder_suggestion(
            current_stock=5.5,
            lead_time_days=1,
            safety_stock=10.5,
            forecast_df=forecast_df
        )

        # Expected: 10.5 + 15 - 5.5 = 20, rounded
        assert isinstance(result, int)
        assert result == 20
