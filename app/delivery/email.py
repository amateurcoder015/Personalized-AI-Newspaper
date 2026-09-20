import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from pathlib import Path
from app.config import AppConfig

logger = logging.getLogger(__name__)


class EmailDelivery:
    """Delivers generated HTML executive daily digest and PDF edition via SMTP email."""

    def __init__(self, config: AppConfig):
        self.config = config

    def send_newspaper(self, html_content: str, pdf_path: str = "", recipient: str = None) -> bool:
        if not self.config.email_enabled:
            logger.info("Email delivery is disabled in configuration.")
            return False

        sender = self.config.email_address
        password = self.config.email_app_password
        target_recipient = recipient or self.config.email_recipient or sender

        if not sender or not password or not target_recipient:
            logger.warning("Email credentials or recipient missing in .env config.")
            return False

        today_str = datetime.now().strftime("%Y-%m-%d")
        subject = f"Your Daily Brief — {today_str}"

        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = f"The Daily Brief <{sender}>"
        msg["To"] = target_recipient

        # Create Email Teaser Digest HTML Body
        email_teaser_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', -apple-system, sans-serif; background: #fcfbf9; color: #1a1a1a; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; padding: 24px; border: 1px solid #cbd5e1; border-radius: 6px; }}
                .title {{ font-family: Georgia, serif; font-size: 24px; font-weight: bold; color: #0f172a; text-transform: uppercase; margin-bottom: 4px; }}
                .sub {{ font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 20px; }}
                .cta-button {{ display: inline-block; background: #1e3a8a; color: #ffffff !important; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; margin: 20px 0; }}
                .footer {{ font-size: 11px; color: #94a3b8; text-align: center; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="title">The Daily Brief</div>
                <div class="sub">Executive Daily Edition — {today_str}</div>
                <p>Good morning!</p>
                <p>Today's executive daily brief is ready. Your issue includes top story briefs, markets, precious metals, sector pulse, GitHub finds, causal connections, and today's Finance Concept.</p>
                
                <a href="#" class="cta-button">READ TODAY'S FULL EDITION →</a>
                
                <p style="font-size: 13px; color: #475569;">The complete PDF publication is attached to this email.</p>
                
                <div class="footer">
                    © The Daily Brief — Personal AI Newspaper Project
                </div>
            </div>
        </body>
        </html>
        """

        msg_body = MIMEMultipart("alternative")
        msg_body.attach(MIMEText(f"Good morning! Your Daily Brief for {today_str} is ready.", "plain", "utf-8"))
        msg_body.attach(MIMEText(email_teaser_html, "html", "utf-8"))
        msg.attach(msg_body)

        # Attach PDF if available
        if pdf_path and Path(pdf_path).exists():
            try:
                with open(pdf_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=Path(pdf_path).name)
                part['Content-Disposition'] = f'attachment; filename="{Path(pdf_path).name}"'
                msg.attach(part)
                logger.info(f"Attached PDF edition: {pdf_path}")
            except Exception as e:
                logger.warning(f"Failed to attach PDF to email: {e}")

        try:
            logger.info(f"Connecting to SMTP server {self.config.email_smtp_server}:{self.config.email_smtp_port}...")
            with smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port) as server:
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, [target_recipient], msg.as_string())
            logger.info(f"Email newspaper digest successfully sent to {target_recipient}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email newspaper digest: {e}")
            return False

    def test_connection(self) -> bool:
        """Test SMTP server login credentials."""
        if not self.config.email_address or not self.config.email_app_password:
            logger.warning("Test email failed: Email address or password not configured.")
            return False

        try:
            with smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port) as server:
                server.starttls()
                server.login(self.config.email_address, self.config.email_app_password)
            logger.info("SMTP email test login successful!")
            return True
        except Exception as e:
            logger.error(f"SMTP email test login failed: {e}")
            return False
