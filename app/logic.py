# app/logic.py
from datetime import datetime, date, timedelta
import pandas as pd
import logging
from sqlalchemy.orm import Session
from .models import Batch, ExpiryAlert, Sale, Forecast, Product
from .email_service import email_service
import os

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def refresh_expiry_alerts(db: Session, store_id: int, days_window: int = 7):
    """
    Idempotent: aynı batch_id için duplicate oluşturmaz.
    Eğer aynı batch için alert varsa günceller; yoksa yeni ekler.
    Yeni kritik uyarılar için e-posta gönderir (MVP).
    """
    logger.info(f"[ALERT] Refreshing expiry alerts for store_id={store_id}, days_window={days_window}")

    today = datetime.utcnow().date()
    cutoff = today + timedelta(days=days_window)

    # cutoff içinde kalan batchleri al
    batches = db.query(Batch).filter(
        Batch.store_id == store_id,
        Batch.expiry_date != None,
        Batch.expiry_date <= cutoff
    ).all()

    new_critical_alerts = []

    for b in batches:
        if not b.expiry_date:
            continue
        days_left = (b.expiry_date - today).days
        if days_left > days_window:
            continue

        sev = "red" if days_left <= 3 else "yellow"

        # Eğer aynı batch için zaten bir alert varsa güncelle, yoksa ekle.
        existing = db.query(ExpiryAlert).filter_by(
            store_id=store_id,
            batch_id=b.id,
            product_id=b.product_id
        ).first()

        if existing:
            changed = False
            if existing.days_left != days_left:
                existing.days_left = days_left
                changed = True
            if existing.severity != sev:
                # Severity changed to critical
                if sev == "red" and existing.severity != "red":
                    new_critical_alerts.append((b, days_left, sev))
                existing.severity = sev
                changed = True
            if changed:
                db.add(existing)
                logger.info(f"[ALERT] Updated alert for batch_id={b.id}, days_left={days_left}, severity={sev}")
        else:
            new_alert = ExpiryAlert(
                store_id=store_id,
                product_id=b.product_id,
                batch_id=b.id,
                expiry_date=b.expiry_date,
                days_left=days_left,
                severity=sev
            )
            db.add(new_alert)
            logger.info(f"[ALERT] Created new alert for batch_id={b.id}, days_left={days_left}, severity={sev}")

            # Track new critical alerts
            if sev == "red":
                new_critical_alerts.append((b, days_left, sev))

    db.commit()

    # Send email notifications for new critical alerts
    if new_critical_alerts:
        logger.info(f"[EMAIL] Sending {len(new_critical_alerts)} critical expiry alert emails")
        send_expiry_alert_emails(db, new_critical_alerts)


def send_expiry_alert_emails(db: Session, alerts_data: list):
    """Send email notifications for critical expiry alerts"""
    # Get alert recipients from env (MVP: single email list)
    alert_emails = os.getenv("ALERT_EMAILS", "").split(",")
    alert_emails = [e.strip() for e in alert_emails if e.strip()]

    if not alert_emails:
        logger.warning("[EMAIL] No alert emails configured. Set ALERT_EMAILS env variable.")
        return

    for batch, days_left, severity in alerts_data:
        # Get product info
        product = db.query(Product).filter_by(id=batch.product_id).first()
        product_name = product.name if product else f"Ürün #{batch.product_id}"

        try:
            email_service.send_expiry_alert(
                to_emails=alert_emails,
                product_name=product_name,
                product_id=batch.product_id,
                batch_id=batch.id,
                expiry_date=str(batch.expiry_date),
                days_left=days_left,
                severity=severity
            )
            logger.info(f"[EMAIL] Sent expiry alert for product_id={batch.product_id}, batch_id={batch.id}")
        except Exception as e:
            logger.error(f"[EMAIL] Failed to send alert for batch_id={batch.id}: {str(e)}")


def naive_hourly_forecast(db: Session, store_id: int, product_id: int, horizon_days: int = 7):
    rows = db.query(Sale).filter(Sale.store_id == store_id, Sale.product_id == product_id).all()
    if not rows:
        return []

    df = pd.DataFrame([{"ts": r.ts, "qty": r.qty} for r in rows]).sort_values("ts")
    if not pd.api.types.is_datetime64_any_dtype(df["ts"]):
        df["ts"] = pd.to_datetime(df["ts"])

    df["dow"] = df["ts"].dt.dayofweek
    df["hour"] = df["ts"].dt.hour

    end = df["ts"].max()
    recent_cutoff = end - pd.Timedelta(days=28)
    recent = df[df["ts"] >= recent_cutoff]
    if recent.empty:
        recent = df

    grp = recent.groupby(["dow", "hour"])["qty"].mean().rename("yhat").reset_index()

    future = pd.date_range(end + pd.Timedelta(hours=1), periods=horizon_days * 24, freq="H")
    fut = pd.DataFrame({"ts": future})
    fut["dow"] = fut["ts"].dt.dayofweek
    fut["hour"] = fut["ts"].dt.hour
    fut = fut.merge(grp, on=["dow", "hour"], how="left").fillna(0.0)

    # Idempotent: aynı zaman aralığındaki eski Forecast'leri sil
    try:
        db.query(Forecast).filter(
            Forecast.store_id == store_id,
            Forecast.product_id == product_id,
            Forecast.horizon == "hourly",
            Forecast.ts >= fut["ts"].min(),
            Forecast.ts <= fut["ts"].max()
        ).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()

    for _, r in fut.iterrows():
        rec = Forecast(
            store_id=store_id,
            product_id=product_id,
            horizon="hourly",
            ts=r["ts"].to_pydatetime(),
            yhat=float(r["yhat"])
        )
        db.add(rec)
    db.commit()
    return fut


def reorder_suggestion(current_stock: float, lead_time_days: int, safety_stock: float, forecast_df) -> int:
    if forecast_df is None or forecast_df.empty:
        return 0
    start = forecast_df["ts"].min()
    horizon_limit = forecast_df[forecast_df["ts"] <= (start + pd.Timedelta(days=lead_time_days))]
    expected = float(horizon_limit["yhat"].sum()) if not horizon_limit.empty else 0.0
    qty_to_order = max(0, int(round(safety_stock + expected - float(current_stock))))
    return qty_to_order
