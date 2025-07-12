#!/usr/bin/env python3
"""
Email Service for VectorCraft
Handles email delivery using database SMTP configuration with environment fallback
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

class EmailService:
    """Email service using database SMTP configuration with environment fallback"""
    
    def __init__(self):
        self.domain_url = os.getenv('DOMAIN_URL', 'http://localhost:8080')
        self._load_smtp_settings()
    
    def _load_smtp_settings(self):
        """Load SMTP settings from database first, then environment variables as fallback"""
        try:
            # Import database here to avoid circular imports
            from database import db
            
            # Try to get settings from database first
            db_settings = db.get_smtp_settings(decrypt_password=True)
            
            if db_settings:
                # Use database settings
                self.smtp_server = db_settings['smtp_server']
                self.smtp_port_ssl = 465 if db_settings['use_ssl'] else None
                self.smtp_port_tls = db_settings['smtp_port'] if db_settings['use_tls'] else None
                self.smtp_username = db_settings['username']
                self.smtp_password = db_settings['password']
                self.from_email = db_settings['from_email']
                self.use_tls = bool(db_settings['use_tls'])
                self.use_ssl = bool(db_settings['use_ssl'])
                
                print(f"📧 Email service configured from database: {self.from_email}")
                print(f"📧 Server: {self.smtp_server}:{db_settings['smtp_port']}")
                self.enabled = True
                self.config_source = 'database'
            else:
                # Fallback to environment variables
                self._load_env_settings()
                
        except Exception as e:
            print(f"⚠️  Error loading database SMTP settings: {e}")
            # Fallback to environment variables
            self._load_env_settings()
    
    def _load_env_settings(self):
        """Load SMTP settings from environment variables"""
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtpout.secureserver.net')
        self.smtp_port_ssl = 465  # SSL
        self.smtp_port_tls = 587  # STARTTLS
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
        self.use_tls = True  # Default to TLS
        self.use_ssl = False  # Default to not SSL
        
        if not self.smtp_username or not self.smtp_password:
            print("⚠️  SMTP credentials not configured. Email sending will be simulated.")
            self.enabled = False
            self.config_source = 'none'
        else:
            print(f"📧 Email service configured from environment: {self.from_email}")
            print("📧 If SMTP fails, emails will be simulated with console output")
            self.enabled = True
            self.config_source = 'environment'
    
    def refresh_settings(self):
        """Refresh SMTP settings from database/environment"""
        self._load_smtp_settings()
    
    def _create_message(self, to_email, subject, body_text, body_html=None):
        """Create email message"""
        msg = MIMEMultipart('alternative')
        msg['From'] = self.from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add text version
        text_part = MIMEText(body_text, 'plain')
        msg.attach(text_part)
        
        # Add HTML version if provided
        if body_html:
            html_part = MIMEText(body_html, 'html')
            msg.attach(html_part)
        
        return msg
    
    def _send_email(self, message):
        """Send email via SMTP"""
        if not self.enabled:
            print("📧 SMTP not configured - simulating email send:")
            print(f"TO: {message['To']}")
            print(f"SUBJECT: {message['Subject']}")
            print("BODY:")
            print(message.get_payload()[0].get_payload())
            print("-" * 50)
            return True
        
        # Determine port and connection method based on configuration
        if hasattr(self, 'use_ssl') and self.use_ssl:
            port = getattr(self, 'smtp_port_ssl', 465)
            connection_type = 'SSL'
        elif hasattr(self, 'use_tls') and self.use_tls:
            port = getattr(self, 'smtp_port_tls', 587)
            connection_type = 'STARTTLS'
        else:
            # Fallback to trying both for environment config
            return self._send_email_fallback(message)
        
        try:
            print(f"🔄 Connecting to {self.smtp_server}:{port} ({connection_type})")
            
            if self.use_ssl:
                # Connect with SSL
                server = smtplib.SMTP_SSL(self.smtp_server, port)
            else:
                # Connect and upgrade to TLS
                server = smtplib.SMTP(self.smtp_server, port)
                if self.use_tls:
                    server.starttls()
            
            with server:
                server.set_debuglevel(0)  # Disable debug for cleaner output
                print(f"🔐 Logging in as {self.smtp_username}")
                server.login(self.smtp_username, self.smtp_password)
                
                text = message.as_string()
                server.sendmail(self.from_email, message['To'], text)
                print(f"✅ Email sent successfully to {message['To']} via {self.smtp_server}:{port}")
                return True
                
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ Authentication failed: {str(e)}")
        except smtplib.SMTPConnectError as e:
            print(f"❌ Connection failed: {str(e)}")
        except Exception as e:
            print(f"❌ SMTP error: {str(e)}")
        
        print(f"❌ SMTP connection failed for {message['To']}")
        print("📧 Falling back to email simulation:")
        print(f"TO: {message['To']}")
        print(f"SUBJECT: {message['Subject']}")
        print("BODY:")
        print(message.get_payload()[0].get_payload())
        print("-" * 50)
        return True  # Return True so the order process continues
    
    def _send_email_fallback(self, message):
        """Fallback method for environment configuration - try both ports"""
        # Try STARTTLS first (port 587), then SSL (port 465)
        for port, use_ssl in [(self.smtp_port_tls, False), (self.smtp_port_ssl, True)]:
            try:
                print(f"🔄 Trying {self.smtp_server}:{port} {'(SSL)' if use_ssl else '(STARTTLS)'}")
                
                if use_ssl:
                    server = smtplib.SMTP_SSL(self.smtp_server, port)
                else:
                    server = smtplib.SMTP(self.smtp_server, port)
                    server.starttls()
                
                with server:
                    server.set_debuglevel(0)
                    print(f"🔐 Logging in as {self.smtp_username}")
                    server.login(self.smtp_username, self.smtp_password)
                    
                    text = message.as_string()
                    server.sendmail(self.from_email, message['To'], text)
                    print(f"✅ Email sent successfully to {message['To']} via port {port}")
                    return True
                    
            except Exception as e:
                print(f"❌ Failed on port {port}: {str(e)}")
                continue
        
        return False
    
    def send_credentials_email(self, email, username, password, order_details=None):
        """Send login credentials to new customer"""
        login_url = f"{self.domain_url}/login"
        
        subject = "Welcome to VectorCraft - Your Login Credentials"
        
        # Text version
        body_text = f"""Welcome to VectorCraft!

Thank you for your purchase. Your account has been created successfully.

LOGIN CREDENTIALS:
Username: {username}
Password: {password}
Login URL: {login_url}

You now have lifetime access to VectorCraft's professional vector conversion tools.

Features included:
• High-quality image to vector conversion
• Multiple output formats (SVG, PDF, EPS)
• Advanced color palette extraction
• Professional-grade results
• Unlimited conversions

Get started by logging in at: {login_url}

Thank you for choosing VectorCraft!

---
VectorCraft Team
Support: support@vectorcraft.com
"""
        
        # HTML version
        body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
        .credentials {{ background: white; padding: 20px; border-radius: 6px; border-left: 4px solid #667eea; margin: 20px 0; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .features {{ background: white; padding: 20px; border-radius: 6px; margin: 20px 0; }}
        .features ul {{ margin: 0; padding-left: 20px; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to VectorCraft!</h1>
            <p>Professional Vector Conversion</p>
        </div>
        
        <div class="content">
            <p>Thank you for your purchase! Your account has been created successfully.</p>
            
            <div class="credentials">
                <h3>🔑 Your Login Credentials</h3>
                <p><strong>Username:</strong> {username}</p>
                <p><strong>Password:</strong> {password}</p>
                <p><strong>Login URL:</strong> <a href="{login_url}">{login_url}</a></p>
            </div>
            
            <div style="text-align: center;">
                <a href="{login_url}" class="button">Login to VectorCraft</a>
            </div>
            
            <div class="features">
                <h3>🚀 What's Included</h3>
                <ul>
                    <li>High-quality image to vector conversion</li>
                    <li>Multiple output formats (SVG, PDF, EPS)</li>
                    <li>Advanced color palette extraction</li>
                    <li>Professional-grade results</li>
                    <li>Unlimited conversions</li>
                    <li>Lifetime access</li>
                </ul>
            </div>
            
            <p>You now have lifetime access to VectorCraft's professional vector conversion tools.</p>
            
            <div class="footer">
                <p>Thank you for choosing VectorCraft!</p>
                <p>VectorCraft Team | Support: support@vectorcraft.com</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
        
        message = self._create_message(email, subject, body_text, body_html)
        return self._send_email(message)
    
    def send_purchase_confirmation(self, email, order_details):
        """Send purchase confirmation email"""
        subject = "VectorCraft Purchase Confirmation"
        
        amount = order_details.get('amount', 49.00)
        order_id = order_details.get('order_id', 'N/A')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        body_text = f"""Purchase Confirmation - VectorCraft

Thank you for your purchase!

ORDER DETAILS:
Order ID: {order_id}
Amount: ${amount:.2f} USD
Date: {timestamp}
Product: VectorCraft Professional (Lifetime Access)

Your login credentials will be sent in a separate email shortly.

Thank you for choosing VectorCraft!

---
VectorCraft Team
"""
        
        message = self._create_message(email, subject, body_text)
        return self._send_email(message)
    
    def send_error_notification(self, email, error_details):
        """Send error notification email"""
        subject = "VectorCraft - Payment Processing Issue"
        
        body_text = f"""Payment Processing Issue

We encountered an issue processing your VectorCraft purchase.

Error Details: {error_details.get('message', 'Unknown error')}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Please contact our support team for assistance:
Email: support@vectorcraft.com

We apologize for the inconvenience and will resolve this quickly.

---
VectorCraft Team
"""
        
        message = self._create_message(email, subject, body_text)
        return self._send_email(message)
    
    def send_admin_notification(self, subject, message):
        """Send notification to admin"""
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
        
        body_text = f"""VectorCraft Admin Notification

{message}

Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        msg = self._create_message(admin_email, f"[VectorCraft] {subject}", body_text)
        return self._send_email(msg)

# Global email service instance
email_service = EmailService()