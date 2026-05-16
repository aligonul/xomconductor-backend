"""Gmail SMTP integration for sending emails."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dataclasses import dataclass
from typing import Optional


@dataclass
class EmailResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


def is_configured() -> bool:
    """Check if Gmail SMTP is configured."""
    return all([
        os.getenv("GMAIL_ADDRESS"),
        os.getenv("GMAIL_APP_PASSWORD"),
    ])


def send_email(
    to_address: str,
    subject: str,
    body: str,
    cc_address: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> EmailResult:
    """
    Send an email via Gmail SMTP.

    Requires:
    - GMAIL_ADDRESS: Your Gmail address
    - GMAIL_APP_PASSWORD: App-specific password (not your regular password)

    To get an app password:
    1. Enable 2FA on your Google account
    2. Go to https://myaccount.google.com/apppasswords
    3. Generate a new app password for "Mail"
    """
    gmail_address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    default_cc = os.getenv("GMAIL_DEFAULT_CC", "global_cms@xometry.com")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = to_address

    # Add CC
    cc_list = []
    if cc_address:
        cc_list.append(cc_address)
    if default_cc and default_cc not in cc_list:
        cc_list.append(default_cc)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    if reply_to:
        msg["Reply-To"] = reply_to

    # Plain text body
    msg.attach(MIMEText(body, "plain"))

    # All recipients (To + CC)
    all_recipients = [to_address] + cc_list

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, app_password)
            server.sendmail(gmail_address, all_recipients, msg.as_string())

        return EmailResult(success=True, message_id=msg["Message-ID"])

    except smtplib.SMTPAuthenticationError:
        return EmailResult(
            success=False,
            error="Gmail authentication failed. Check your app password.",
        )
    except Exception as e:
        return EmailResult(success=False, error=str(e))


def send_html_email(
    to_address: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    cc_address: Optional[str] = None,
) -> EmailResult:
    """Send an HTML email with plain text fallback."""
    gmail_address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    default_cc = os.getenv("GMAIL_DEFAULT_CC", "global_cms@xometry.com")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = to_address

    cc_list = []
    if cc_address:
        cc_list.append(cc_address)
    if default_cc and default_cc not in cc_list:
        cc_list.append(default_cc)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    # Add both plain text and HTML
    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    all_recipients = [to_address] + cc_list

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, app_password)
            server.sendmail(gmail_address, all_recipients, msg.as_string())

        return EmailResult(success=True, message_id=msg["Message-ID"])

    except Exception as e:
        return EmailResult(success=False, error=str(e))
