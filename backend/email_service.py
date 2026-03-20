"""
email_service.py
----------------
OTP email delivery via Resend API.

Why Resend over raw SMTP:
  - No SMTP credentials to manage
  - Reliable deliverability out of the box
  - Simple REST API with Python SDK
  - Free tier: 3,000 emails/month

If you prefer SMTP (Gmail / SendGrid), see the smtp_fallback()
function at the bottom — swap send_otp_email() to use it.
"""

import logging
from typing import Optional

import resend

from database import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialise Resend client
resend.api_key = settings.RESEND_API_KEY


# ── Email templates ───────────────────────────────────────────────────────────

def _build_otp_html(otp: str, expires_minutes: int) -> str:
    """
    Clean, professional OTP email template.
    Returns HTML string — inline styles for maximum email client compatibility.
    """
    return f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Verify your email</title></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:40px 20px;">
    <tr><td align="center">
      <table width="100%" style="max-width:480px;background:#ffffff;border-radius:12px;
             padding:40px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
        <tr><td>
          <h1 style="margin:0 0 8px;font-size:22px;font-weight:600;color:#111827;">
            Verify your email
          </h1>
          <p style="margin:0 0 28px;font-size:15px;color:#6b7280;line-height:1.6;">
            Use the code below to verify your AI Resume Screener account.
            This code expires in <strong>{expires_minutes} minutes</strong>.
          </p>

          <div style="background:#f0f9ff;border:2px solid #bae6fd;border-radius:10px;
                      padding:24px;text-align:center;margin-bottom:28px;">
            <span style="font-size:36px;font-weight:700;letter-spacing:10px;
                         color:#0369a1;font-family:'Courier New',monospace;">
              {otp}
            </span>
          </div>

          <p style="margin:0 0 8px;font-size:13px;color:#9ca3af;line-height:1.6;">
            If you didn't create an account, you can safely ignore this email.
            Someone may have entered your email address by mistake.
          </p>
          <p style="margin:0;font-size:13px;color:#9ca3af;">
            For security, never share this code with anyone.
          </p>
        </td></tr>
      </table>

      <p style="margin:16px 0 0;font-size:12px;color:#9ca3af;">
        AI Resume Screener &mdash; Automated email, please do not reply.
      </p>
    </td></tr>
  </table>
</body>
</html>
"""


def _build_otp_text(otp: str, expires_minutes: int) -> str:
    """Plain-text fallback for email clients that don't render HTML."""
    return (
        f"AI Resume Screener — Email Verification\n"
        f"{'=' * 45}\n\n"
        f"Your verification code is: {otp}\n\n"
        f"This code expires in {expires_minutes} minutes.\n\n"
        f"If you did not request this, please ignore this email.\n"
        f"Never share this code with anyone.\n"
    )


# ── Send functions ────────────────────────────────────────────────────────────

def send_otp_email(
    to_email: str,
    otp: str,
    expires_minutes: Optional[int] = None,
) -> tuple[bool, Optional[str]]:
    """
    Send an OTP verification email via Resend.

    Args:
        to_email:        Recipient email address
        otp:             Plain-text 6-digit OTP (never logged)
        expires_minutes: OTP expiry (defaults to settings.OTP_EXPIRE_MINUTES)

    Returns:
        (True, None)         on success
        (False, error_str)   on failure

    Never raises — always returns (bool, error).
    """
    if expires_minutes is None:
        expires_minutes = settings.OTP_EXPIRE_MINUTES

    try:
        response = resend.Emails.send({
            "from":    settings.EMAIL_FROM,
            "to":      [to_email],
            "subject": "Your verification code — AI Resume Screener",
            "html":    _build_otp_html(otp, expires_minutes),
            "text":    _build_otp_text(otp, expires_minutes),
        })

        # Resend returns {"id": "..."} on success
        if response and response.get("id"):
            logger.info(
                "OTP email sent to %s (Resend ID: %s)",
                to_email, response["id"],
            )
            return True, None
        else:
            logger.error("Resend returned unexpected response: %s", response)
            return False, "Email service returned an unexpected response."

    except Exception as e:
        logger.error("Failed to send OTP email to %s: %s", to_email, e)
        return False, f"Email delivery failed: {str(e)}"


# ── SMTP fallback (optional — swap send_otp_email to use this) ───────────────

def send_otp_email_smtp(
    to_email: str,
    otp: str,
    expires_minutes: Optional[int] = None,
) -> tuple[bool, Optional[str]]:
    """
    SMTP-based OTP email (Gmail / any SMTP provider).

    To use Gmail:
      1. Enable 2FA on your Google account
      2. Create an App Password: Google Account → Security → App passwords
      3. Add to .env:
            SMTP_HOST=smtp.gmail.com
            SMTP_PORT=587
            SMTP_USER=you@gmail.com
            SMTP_PASSWORD=your-app-password

    Then replace send_otp_email() calls with send_otp_email_smtp().
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    if expires_minutes is None:
        expires_minutes = settings.OTP_EXPIRE_MINUTES

    smtp_host     = getattr(settings, "SMTP_HOST",     "smtp.gmail.com")
    smtp_port     = getattr(settings, "SMTP_PORT",     587)
    smtp_user     = getattr(settings, "SMTP_USER",     "")
    smtp_password = getattr(settings, "SMTP_PASSWORD", "")

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your verification code — AI Resume Screener"
        msg["From"]    = smtp_user
        msg["To"]      = to_email

        msg.attach(MIMEText(_build_otp_text(otp, expires_minutes), "plain"))
        msg.attach(MIMEText(_build_otp_html(otp, expires_minutes), "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())

        logger.info("OTP email sent via SMTP to %s", to_email)
        return True, None

    except Exception as e:
        logger.error("SMTP send failed to %s: %s", to_email, e)
        return False, f"Email delivery failed: {str(e)}"