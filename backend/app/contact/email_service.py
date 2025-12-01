"""
Email service for contact form notifications using Gmail SMTP.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Optional
import os
from dotenv import load_dotenv
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
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"New Contact Form Submission: {submission['subject']}"
            msg['From'] = self.sender_email
            msg['To'] = self.admin_email
            msg['Reply-To'] = submission['email']
            
            # Create HTML body
            html_body = f"""
            <html>
                <head>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            line-height: 1.6;
                            color: #333;
                        }}
                        .container {{
                            max-width: 600px;
                            margin: 0 auto;
                            padding: 20px;
                            background-color: #f9f9f9;
                            border-radius: 8px;
                        }}
                        .header {{
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            padding: 20px;
                            border-radius: 8px 8px 0 0;
                            text-align: center;
                        }}
                        .content {{
                            background: white;
                            padding: 20px;
                            border-radius: 0 0 8px 8px;
                        }}
                        .field {{
                            margin-bottom: 15px;
                        }}
                        .label {{
                            font-weight: bold;
                            color: #667eea;
                            display: block;
                            margin-bottom: 5px;
                        }}
                        .value {{
                            padding: 10px;
                            background: #f5f5f5;
                            border-radius: 4px;
                            border-left: 3px solid #667eea;
                        }}
                        .message {{
                            white-space: pre-wrap;
                        }}
                        .footer {{
                            margin-top: 20px;
                            padding-top: 20px;
                            border-top: 1px solid #ddd;
                            font-size: 12px;
                            color: #666;
                            text-align: center;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>🔔 New Contact Form Submission</h2>
                        </div>
                        <div class="content">
                            <div class="field">
                                <span class="label">From:</span>
                                <div class="value">{submission['name']}</div>
                            </div>
                            
                            <div class="field">
                                <span class="label">Email:</span>
                                <div class="value">
                                    <a href="mailto:{submission['email']}">{submission['email']}</a>
                                </div>
                            </div>
                            
                            <div class="field">
                                <span class="label">Subject:</span>
                                <div class="value">{submission['subject']}</div>
                            </div>
                            
                            <div class="field">
                                <span class="label">Message:</span>
                                <div class="value message">{submission['message']}</div>
                            </div>
                            
                            <div class="field">
                                <span class="label">Submitted:</span>
                                <div class="value">{submission.get('timestamp', datetime.now()).strftime('%B %d, %Y at %I:%M %p')}</div>
                            </div>
                        </div>
                        <div class="footer">
                            <p>This is an automated notification from Zenith Cloud Platform</p>
                            <p>Reply directly to this email to respond to {submission['name']}</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            # Create plain text version
            text_body = f"""
New Contact Form Submission

From: {submission['name']}
Email: {submission['email']}
Subject: {submission['subject']}

Message:
{submission['message']}

Submitted: {submission.get('timestamp', datetime.now()).strftime('%B %d, %Y at %I:%M %p')}

---
Reply to this email to respond to {submission['name']}
            """
            
            # Attach both versions
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Contact notification email sent to {self.admin_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
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
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "We received your message - Zenith Cloud Platform"
            msg['From'] = self.sender_email
            msg['To'] = submission['email']
            
            html_body = f"""
            <html>
                <head>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            line-height: 1.6;
                            color: #333;
                        }}
                        .container {{
                            max-width: 600px;
                            margin: 0 auto;
                            padding: 20px;
                        }}
                        .header {{
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            padding: 30px 20px;
                            border-radius: 8px 8px 0 0;
                            text-align: center;
                        }}
                        .content {{
                            background: white;
                            padding: 30px 20px;
                            border: 1px solid #ddd;
                            border-top: none;
                            border-radius: 0 0 8px 8px;
                        }}
                        .button {{
                            display: inline-block;
                            padding: 12px 30px;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            text-decoration: none;
                            border-radius: 6px;
                            margin-top: 20px;
                        }}
                        .footer {{
                            margin-top: 30px;
                            padding-top: 20px;
                            border-top: 1px solid #ddd;
                            font-size: 12px;
                            color: #666;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>✓ Message Received</h1>
                        </div>
                        <div class="content">
                            <p>Hi {submission['name']},</p>
                            
                            <p>Thank you for contacting Zenith Cloud Platform! We've received your message and will respond within 24 hours.</p>
                            
                            <p><strong>Your message:</strong></p>
                            <p style="background: #f5f5f5; padding: 15px; border-radius: 6px; border-left: 3px solid #667eea;">
                                {submission['message'][:200]}{'...' if len(submission['message']) > 200 else ''}
                            </p>
                            
                            <p>In the meantime, you can:</p>
                            <ul>
                                <li>Check our <a href="https://rajverse.me/dashboard">Dashboard</a></li>
                                <li>Start a <a href="https://rajverse.me/contact">Live Chat</a> (9 AM - 6 PM IST)</li>
                                <li>Browse our <a href="https://rajverse.me/docs">Documentation</a></li>
                            </ul>
                            
                            <a href="https://rajverse.me/dashboard" class="button">Go to Dashboard</a>
                            
                            <div class="footer">
                                <p>Best regards,<br><strong>Zenith Support Team</strong></p>
                                <p style="margin-top: 20px;">
                                    Zenith Cloud Resource Optimization Platform<br>
                                    Email: support@rajverse.me
                                </p>
                            </div>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            text_body = f"""
Hi {submission['name']},

Thank you for contacting Zenith Cloud Platform! We've received your message and will respond within 24 hours.

Your message:
{submission['message'][:200]}{'...' if len(submission['message']) > 200 else ''}

In the meantime, you can:
- Check our Dashboard: https://rajverse.me/dashboard
- Start a Live Chat (9 AM - 6 PM IST): https://rajverse.me/contact
- Browse our Documentation: https://rajverse.me/docs

Best regards,
Zenith Support Team

---
Zenith Cloud Resource Optimization Platform
Email: support@rajverse.me
            """
            
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Auto-reply sent to {submission['email']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send auto-reply: {str(e)}")
            return False


# Singleton instance
email_service = EmailService()
