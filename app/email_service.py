# app/email_service.py
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional
from pydantic import EmailStr
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class EmailSettings(BaseSettings):
    """Email configuration from environment"""
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@retailai.com")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "RetailAI Sistem")
    EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"

email_settings = EmailSettings()

class EmailService:
    """Enterprise-grade email service for alerts and notifications"""

    def __init__(self):
        self.enabled = email_settings.EMAIL_ENABLED
        if not self.enabled:
            logger.info("Email service is DISABLED. Set EMAIL_ENABLED=true to enable.")

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        """Send email with HTML and optional text fallback"""
        if not self.enabled:
            logger.info(f"[EMAIL DISABLED] Would send: {subject} to {to_emails}")
            return True

        if not email_settings.SMTP_USER or not email_settings.SMTP_PASSWORD:
            logger.error("SMTP credentials not configured")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{email_settings.SMTP_FROM_NAME} <{email_settings.SMTP_FROM_EMAIL}>"
            msg['To'] = ', '.join(to_emails)

            # Attach text and HTML parts
            if text_body:
                msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            # Send via SMTP
            with smtplib.SMTP(email_settings.SMTP_HOST, email_settings.SMTP_PORT) as server:
                server.starttls()
                server.login(email_settings.SMTP_USER, email_settings.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email sent successfully: {subject} to {to_emails}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}", exc_info=True)
            return False

    def send_expiry_alert(
        self,
        to_emails: List[str],
        product_name: str,
        product_id: int,
        batch_id: int,
        expiry_date: str,
        days_left: int,
        severity: str = "warning"
    ) -> bool:
        """Send SKT expiry alert email"""

        # Severity styling
        severity_color = "#dc2626" if severity == "red" else "#f59e0b"
        severity_label = "KRİTİK" if severity == "red" else "UYARI"

        subject = f"⚠️ SKT Uyarısı: {product_name} ({days_left} gün kaldı)"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {severity_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-radius: 0 0 8px 8px; }}
                .badge {{ display: inline-block; background: {severity_color}; color: white; padding: 6px 12px; border-radius: 4px; font-weight: bold; }}
                .info {{ background: white; padding: 15px; border-left: 4px solid {severity_color}; margin: 20px 0; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
                .btn {{ display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">🔔 SKT Uyarısı</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">RetailAI Stok Yönetim Sistemi</p>
                </div>
                <div class="content">
                    <p><span class="badge">{severity_label}</span></p>
                    <h2 style="color: #111827;">Ürün Son Kullanma Tarihi Yaklaşıyor</h2>

                    <div class="info">
                        <p><strong>Ürün:</strong> {product_name} (ID: {product_id})</p>
                        <p><strong>Batch:</strong> #{batch_id}</p>
                        <p><strong>Son Kullanma Tarihi:</strong> {expiry_date}</p>
                        <p style="font-size: 18px; color: {severity_color};"><strong>⏰ {days_left} gün kaldı</strong></p>
                    </div>

                    <p>Lütfen bu ürünü öncelikli olarak satışa sunun veya gerekli önlemleri alın.</p>

                    <a href="http://localhost:3000/alerts" class="btn">Uyarıları Görüntüle</a>

                    <p style="font-size: 12px; color: #6b7280; margin-top: 20px;">
                        Bu otomatik bir bildirimdir. RetailAI sistemi, stok ve SKT durumunuzu
                        24/7 izleyerek size fire riski olan ürünler hakkında zamanında bilgi verir.
                    </p>
                </div>
                <div class="footer">
                    <p>© 2024 RetailAI - Akıllı Stok Yönetim Sistemi</p>
                    <p>Bu e-postayı almak istemiyorsanız sistem yöneticinizle iletişime geçin.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
SKT UYARISI - {severity_label}

Ürün: {product_name} (ID: {product_id})
Batch: #{batch_id}
Son Kullanma Tarihi: {expiry_date}
Kalan Süre: {days_left} gün

Lütfen bu ürünü öncelikli olarak satışa sunun.

RetailAI Stok Yönetim Sistemi
        """

        return self.send_email(to_emails, subject, html_body, text_body)

    def send_low_stock_alert(
        self,
        to_emails: List[str],
        product_name: str,
        product_id: int,
        current_stock: float,
        min_stock: float,
        unit: str = "adet"
    ) -> bool:
        """Send low stock alert email"""

        subject = f"📦 Stok Uyarısı: {product_name} (kritik seviye)"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #f59e0b; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-radius: 0 0 8px 8px; }}
                .info {{ background: white; padding: 15px; border-left: 4px solid #f59e0b; margin: 20px 0; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
                .btn {{ display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">📦 Düşük Stok Uyarısı</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">RetailAI Stok Yönetim Sistemi</p>
                </div>
                <div class="content">
                    <h2 style="color: #111827;">Ürün Stoku Kritik Seviyede</h2>

                    <div class="info">
                        <p><strong>Ürün:</strong> {product_name} (ID: {product_id})</p>
                        <p><strong>Mevcut Stok:</strong> {current_stock} {unit}</p>
                        <p><strong>Minimum Seviye:</strong> {min_stock} {unit}</p>
                        <p style="font-size: 18px; color: #f59e0b;"><strong>⚠️ Sipariş verin!</strong></p>
                    </div>

                    <p>Stok seviyesi minimum eşiğin altına düştü. Yeni sipariş vermenizi öneririz.</p>

                    <a href="http://localhost:3000/products" class="btn">Ürünleri Görüntüle</a>
                </div>
                <div class="footer">
                    <p>© 2024 RetailAI - Akıllı Stok Yönetim Sistemi</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
DÜŞÜK STOK UYARISI

Ürün: {product_name} (ID: {product_id})
Mevcut Stok: {current_stock} {unit}
Minimum Seviye: {min_stock} {unit}

Stok kritik seviyede. Yeni sipariş verin.

RetailAI Stok Yönetim Sistemi
        """

        return self.send_email(to_emails, subject, html_body, text_body)

# Singleton instance
email_service = EmailService()
