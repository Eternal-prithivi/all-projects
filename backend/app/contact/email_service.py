"""
Email service for contact form notifications using Gmail SMTP.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Dict, Optional

from dotenv import load_dotenv

from app.contact.email_templates import (
    admin_customer_reply_html,
    admin_customer_reply_text,
    agent_reply_html,
    agent_reply_text,
    contact_admin_html,
    contact_admin_text,
    contact_auto_reply_html,
    contact_auto_reply_text,
    reference_code,
    subject_label,
    ticket_otp_html,
    ticket_otp_text,
    ticket_resolved_html,
    ticket_resolved_text,
)
from app.utils.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)


class EmailService:
    """Handles sending emails via Gmail SMTP"""
    
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv("GMAIL_SENDER_EMAIL")
        self.sender_password = os.getenv("GMAIL_APP_PASSWORD")  # Gmail App Password
        self.admin_email = os.getenv("ADMIN_EMAIL", self.sender_email)
        
        if not self.sender_email or not self.sender_password:
            logger.warning("Gmail credentials not configured. Email notifications disabled.")

    def _from_header(self) -> str:
        return formataddr(("Zenith Support", self.sender_email))

    def _send_html_email(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        reply_to: Optional[str] = None,
    ) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from_header()
        msg["To"] = to_email
        if reply_to:
            msg["Reply-To"] = reply_to
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
        return True

    def send_contact_notification(self, submission: Dict) -> bool:
        """
        Send email notification to admin when contact form is submitted.
        
        Args:
            submission: Contact form submission data
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.sender_email or not self.sender_password:
            logger.warning("Email credentials not configured, skipping email notification")
            return False
        
        try:
            category = subject_label(submission.get("subject", ""))
            ref_code = reference_code(submission)
            ref_suffix = f" [{ref_code}]" if ref_code else ""
            subject = f"[Zenith Contact] {category} — {submission['name']}{ref_suffix}"

            self._send_html_email(
                to_email=self.admin_email,
                subject=subject,
                html_body=contact_admin_html(submission),
                text_body=contact_admin_text(submission),
                reply_to=submission["email"],
            )

            logger.info("Contact notification email sent to %s", self.admin_email)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False

    def send_verification_email(
        self,
        *,
        to_email: str,
        username: str,
        verify_link: str,
    ) -> bool:
        """Send email address verification link after registration."""
        if not self.sender_email or not self.sender_password:
            logger.warning("Email credentials not configured, skipping verification email")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Verify your Zenith email"
            msg["From"] = self.sender_email
            msg["To"] = to_email

            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 560px;">
                <h2 style="color: #b8860b;">Verify your email</h2>
                <p>Hello {username},</p>
                <p>Thanks for signing up for Zenith. Confirm your email to activate your account.</p>
                <p style="margin: 24px 0;">
                  <a href="{verify_link}"
                     style="background: #d4af37; color: #111; padding: 12px 24px; text-decoration: none;
                            border-radius: 8px; font-weight: bold;">Verify email</a>
                </p>
                <p style="font-size: 12px; color: #666;">Or copy this link:<br>{verify_link}</p>
              </body>
            </html>
            """
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info("Verification email sent to %s", to_email)
            return True
        except Exception as e:
            logger.error("Failed to send verification email: %s", str(e))
            return False

    def send_password_reset(
        self,
        *,
        to_email: str,
        username: str,
        reset_link: str,
        expires_hours: int = 1,
    ) -> bool:
        """Send password reset link email."""
        if not self.sender_email or not self.sender_password:
            logger.warning("Email credentials not configured, skipping password reset email")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Reset your Zenith password"
            msg["From"] = self.sender_email
            msg["To"] = to_email

            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 560px;">
                <h2 style="color: #b8860b;">Zenith — Password reset</h2>
                <p>Hello {username},</p>
                <p>We received a request to reset your password. Click the button below to choose a new password.
                   This link expires in <strong>{expires_hours} hour(s)</strong>.</p>
                <p style="margin: 24px 0;">
                  <a href="{reset_link}"
                     style="background: #d4af37; color: #111; padding: 12px 24px; text-decoration: none;
                            border-radius: 8px; font-weight: bold;">Reset password</a>
                </p>
                <p style="font-size: 12px; color: #666;">Or copy this link:<br>{reset_link}</p>
                <p style="font-size: 12px; color: #666;">If you did not request this, you can ignore this email.</p>
              </body>
            </html>
            """
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info(f"Password reset email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            return False

    def send_security_alert(self, *, to_email: str, username: str, unencrypted_sensitive_count: int) -> bool:
        """
        Send a security alert email to a user.

        This uses the existing Gmail SMTP configuration to keep the platform zero-cost.
        """
        if not self.sender_email or not self.sender_password:
            logger.warning("Email credentials not configured, skipping security alert email")
            return False

        try:
            subject = "Zenith Security Alert: Sensitive files need encryption"
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = to_email

            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2>Zenith Security Alert</h2>
                <p>Hello {username},</p>
                <p>
                  We detected <strong>{unencrypted_sensitive_count}</strong> sensitive file(s) that are not encrypted yet.
                  Please open the <strong>Security</strong> page and complete encryption to protect your data.
                </p>
                <p style="color: #666; font-size: 12px;">
                  If you recently encrypted your files, this alert may resolve after the next refresh.
                </p>
              </body>
            </html>
            """
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info(f"Security alert email sent to {to_email} for user {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to send security alert email: {str(e)}")
            return False
    
    def send_auto_reply(self, submission: Dict) -> bool:
        """
        Send automatic reply to user confirming we received their message.
        
        Args:
            submission: Contact form submission data
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.sender_email or not self.sender_password:
            return False
        
        try:
            ref_code = reference_code(submission)
            ref_suffix = f" ({ref_code})" if ref_code else ""
            subject = f"We received your message — Zenith Support{ref_suffix}"

            self._send_html_email(
                to_email=submission["email"],
                subject=subject,
                html_body=contact_auto_reply_html(submission),
                text_body=contact_auto_reply_text(submission),
            )

            logger.info("Auto-reply sent to %s", submission["email"])
            return True
            
        except Exception as e:
            logger.error(f"Failed to send auto-reply: {str(e)}")
            return False

    def send_ticket_otp_email(self, to_email: str, ref_code: str, otp: str) -> bool:
        if not self.sender_email or not self.sender_password:
            return False
        try:
            self._send_html_email(
                to_email=to_email,
                subject=f"Your Zenith support code — {ref_code}",
                html_body=ticket_otp_html(ref_code, otp),
                text_body=ticket_otp_text(ref_code, otp),
            )
            return True
        except Exception as e:
            logger.error("Failed to send ticket OTP: %s", e)
            return False

    def send_agent_reply_email(self, ticket: Dict, message_body: str) -> bool:
        if not self.sender_email or not self.sender_password:
            return False
        try:
            ref = ticket.get("reference_code", "")
            name = ticket.get("requester_name", "there")
            email = ticket.get("requester_email", "")
            logged_in = bool(ticket.get("user_id"))
            self._send_html_email(
                to_email=email,
                subject=f"Re: {ref} — Zenith Support replied",
                html_body=agent_reply_html(
                    requester_name=name,
                    ref_code=ref,
                    message_preview=message_body,
                    for_logged_in=logged_in,
                ),
                text_body=agent_reply_text(
                    requester_name=name,
                    ref_code=ref,
                    message_preview=message_body,
                    for_logged_in=logged_in,
                ),
            )
            return True
        except Exception as e:
            logger.error("Failed to send agent reply email: %s", e)
            return False

    def send_ticket_resolved_email(self, ticket: Dict) -> bool:
        if not self.sender_email or not self.sender_password:
            return False
        try:
            ref = ticket.get("reference_code", "")
            name = ticket.get("requester_name", "there")
            email = ticket.get("requester_email", "")
            self._send_html_email(
                to_email=email,
                subject=f"{ref} resolved — Zenith Support",
                html_body=ticket_resolved_html(name, ref),
                text_body=ticket_resolved_text(name, ref),
            )
            return True
        except Exception as e:
            logger.error("Failed to send resolved email: %s", e)
            return False

    def send_admin_customer_reply_notification(
        self, ticket: Dict, message_body: str
    ) -> bool:
        if not self.sender_email or not self.sender_password:
            return False
        try:
            ref = ticket.get("reference_code", "")
            name = ticket.get("requester_name", "Customer")
            self._send_html_email(
                to_email=self.admin_email,
                subject=f"[Zenith] Customer reply on {ref}",
                html_body=admin_customer_reply_html(ref, name, message_body),
                text_body=admin_customer_reply_text(ref, name, message_body),
                reply_to=ticket.get("requester_email"),
            )
            return True
        except Exception as e:
            logger.error("Failed to send admin customer reply notice: %s", e)
            return False


# Singleton instance
email_service = EmailService()
