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
        # Check if Gmail override is set for better deliverability
        use_gmail = os.getenv('USE_GMAIL_SMTP', 'false').lower() == 'true'
        
        if use_gmail:
            # Gmail SMTP settings for better deliverability
            self.smtp_server = 'smtp.gmail.com'
            self.smtp_port_ssl = 465  # SSL
            self.smtp_port_tls = 587  # STARTTLS
            self.smtp_username = os.getenv('GMAIL_USERNAME', '')
            self.smtp_password = os.getenv('GMAIL_APP_PASSWORD', '')  # App password required
            self.from_email = self.smtp_username
            self.use_tls = True
            self.use_ssl = False
            print(f"📧 Using Gmail SMTP for better deliverability: {self.from_email}")
        else:
            # Original GoDaddy SMTP settings
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
        """Create email message with proper headers to avoid spam"""
        msg = MIMEMultipart('alternative')
        
        # Essential headers to avoid spam
        msg['From'] = f"VectorCraft Support <{self.from_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Set Reply-To to company domain even when using Gmail
        company_email = "support@thevectorcraft.com"
        if "@gmail.com" in self.from_email:
            msg['Reply-To'] = company_email  # Direct replies to company domain
        else:
            msg['Reply-To'] = self.from_email
        
        # Anti-spam headers  
        msg['Message-ID'] = f"<{datetime.now().strftime('%Y%m%d%H%M%S')}.{hash(to_email + subject) % 100000}@thevectorcraft.com>"
        
        # Fix date header with proper timezone
        from email.utils import formatdate
        msg['Date'] = formatdate(localtime=True)
        msg['MIME-Version'] = '1.0'
        msg['X-Mailer'] = 'VectorCraft Email Service'
        msg['X-Priority'] = '3'
        msg['Importance'] = 'Normal'
        
        # Content headers
        msg['Content-Type'] = 'multipart/alternative'
        
        # Add text version
        text_part = MIMEText(body_text, 'plain', 'utf-8')
        text_part['Content-Type'] = 'text/plain; charset=utf-8'
        text_part['Content-Transfer-Encoding'] = '8bit'
        msg.attach(text_part)
        
        # Add HTML version if provided
        if body_html:
            html_part = MIMEText(body_html, 'html', 'utf-8')
            html_part['Content-Type'] = 'text/html; charset=utf-8'
            html_part['Content-Transfer-Encoding'] = '8bit'
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
    
    def replace_variables(self, content, variables):
        """Replace template variables with actual values"""
        if not content:
            return content
            
        # Define variable mapping
        var_map = {
            '{{username}}': str(variables.get('username', '')),
            '{{email}}': str(variables.get('email', '')),
            '{{password}}': str(variables.get('password', '')),
            '{{amount}}': str(variables.get('amount', '')),
            '{{order_id}}': str(variables.get('order_id', '')),
            '{{login_url}}': str(variables.get('login_url', f"{self.domain_url}/login")),
            '{{support_email}}': str(variables.get('support_email', 'support@thevectorcraft.com')),
            '{{company_name}}': str(variables.get('company_name', 'VectorCraft')),
            '{{tracking_pixel_url}}': str(variables.get('tracking_pixel_url', ''))
        }
        
        # Replace all variables
        result = content
        for var, value in var_map.items():
            result = result.replace(var, value)
            
        return result
    
    def send_template_email(self, to_email, template_data, variables):
        """Send email using a custom template with variable replacement"""
        try:
            # Replace variables in subject and content
            subject = self.replace_variables(template_data.get('subject', 'Email from VectorCraft'), variables)
            html_content = self.replace_variables(template_data.get('content_html', ''), variables)
            
            # Generate text version from HTML if no text version provided
            text_content = template_data.get('content_text', '')
            if not text_content and html_content:
                # Simple HTML to text conversion
                import re
                text_content = re.sub('<[^<]+?>', '', html_content)
                text_content = text_content.replace('&nbsp;', ' ').replace('&amp;', '&')
                text_content = '\n'.join(line.strip() for line in text_content.split('\n') if line.strip())
            
            text_content = self.replace_variables(text_content, variables)
            
            # Create and send message
            message = self._create_message(to_email, subject, text_content, html_content)
            return self._send_email(message)
            
        except Exception as e:
            print(f"❌ Error sending template email: {e}")
            return False

    def send_credentials_email(self, email, username, password, order_details=None):
        """Send login credentials to new customer"""
        login_url = f"{self.domain_url}/login"
        
        subject = "Your VectorCraft Account is Ready"
        
        # Text version
        body_text = f"""Hello {username.title()},

Thank you for choosing VectorCraft. Your account is now active and ready to use.

Your Login Details:
Username: {username}
Password: {password}
Access: {login_url}

Your VectorCraft subscription includes:
- Image to vector conversion
- SVG, PDF, EPS output formats  
- Color palette extraction
- Unlimited usage

Access VectorCraft: {login_url}

Best regards,
The VectorCraft Team
support@thevectorcraft.com
"""
        
        # HTML version - cleaner, less promotional
        body_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #f8f9fa; padding: 20px; text-align: center; border-bottom: 1px solid #e9ecef; }}
        .content {{ padding: 30px; background: white; }}
        .credentials {{ background: #f8f9fa; padding: 20px; border-radius: 4px; margin: 20px 0; }}
        .button {{ display: inline-block; background: #0d6efd; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #6c757d; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef; }}
        ul {{ margin: 0; padding-left: 20px; }}
        ul li {{ margin-bottom: 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0; color: #495057;">VectorCraft</h2>
            <p style="margin: 5px 0 0 0; color: #6c757d;">Your account is ready</p>
        </div>
        
        <div class="content">
            <p>Hello {username.title()},</p>
            <p>Thank you for choosing VectorCraft. Your account is now active and ready to use.</p>
            
            <div class="credentials">
                <h3 style="margin-top: 0;">Login Details</h3>
                <p><strong>Username:</strong> {username}</p>
                <p><strong>Password:</strong> {password}</p>
                <p><strong>Access:</strong> <a href="{login_url}" style="color: #0d6efd;">{login_url}</a></p>
            </div>
            
            <div style="text-align: center;">
                <a href="{login_url}" class="button">Access VectorCraft</a>
            </div>
            
            <h3>Your Subscription Includes:</h3>
            <ul>
                <li>Image to vector conversion</li>
                <li>SVG, PDF, EPS output formats</li>
                <li>Color palette extraction</li>
                <li>Unlimited usage</li>
            </ul>
            
            <div class="footer">
                <p>Best regards,<br>The VectorCraft Team</p>
                <p><a href="mailto:support@thevectorcraft.com" style="color: #6c757d;">support@thevectorcraft.com</a></p>
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
    
    def send_automated_email(self, to_email, subject, content_html, tracking_id=None, variables=None):
        """
        Send an automated email with tracking and variable substitution
        
        Args:
            to_email (str): Recipient email address
            subject (str): Email subject
            content_html (str): HTML content of email
            tracking_id (str): Tracking ID for analytics
            variables (dict): Variables to substitute in content
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Replace variables in subject and content if provided
            if variables:
                subject = self._replace_variables(subject, variables)
                content_html = self._replace_variables(content_html, variables)
            
            # Add tracking pixels and links if tracking_id provided
            if tracking_id:
                content_html = self._add_tracking_elements(content_html, tracking_id)
            
            # Create multipart message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add HTML content
            html_part = MIMEText(content_html, 'html')
            msg.attach(html_part)
            
            # Send the email
            return self._send_email(msg)
            
        except Exception as e:
            print(f"Error sending automated email to {to_email}: {e}")
            return False
    
    def send_plain_email(self, to_email, subject, message):
        """
        Send a plain text email (for testing)
        
        Args:
            to_email (str): Recipient email address
            subject (str): Email subject
            message (str): Plain text message
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Create simple text message
            msg = MIMEText(message, 'plain')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Send the email
            return self._send_email(msg)
            
        except Exception as e:
            print(f"Error sending plain email to {to_email}: {e}")
            return False
    
    def _replace_variables(self, content, variables):
        """
        Replace variables in content using {{variable_name}} syntax
        
        Args:
            content (str): Content with variables
            variables (dict): Variable substitutions
            
        Returns:
            str: Content with variables replaced
        """
        import re
        
        if not variables:
            return content
            
        # Replace variables in format {{variable_name}}
        for key, value in variables.items():
            # Handle both {{key}} and {key} formats
            content = re.sub(rf'\{{\{{\s*{re.escape(key)}\s*\}}\}}', str(value), content)
            content = re.sub(rf'\{{\s*{re.escape(key)}\s*\}}', str(value), content)
            
        return content
    
    def _add_tracking_elements(self, content_html, tracking_id):
        """
        Add tracking pixel and update links for tracking
        
        Args:
            content_html (str): HTML content
            tracking_id (str): Tracking ID
            
        Returns:
            str: HTML content with tracking elements
        """
        # Fix domain URL - don't use localhost in production
        domain_url = self.domain_url
        if 'localhost' in domain_url or '127.0.0.1' in domain_url:
            domain_url = 'https://thevectorcraft.com'  # Use production domain
            
        # Add tracking pixel at the end of the email
        tracking_pixel = f'<img src="{domain_url}/track/open/{tracking_id}" width="1" height="1" style="display:none;" alt="">'
        
        # Insert tracking pixel before closing body tag, or at the end if no body tag
        if '</body>' in content_html:
            content_html = content_html.replace('</body>', f'{tracking_pixel}</body>')
        else:
            content_html += tracking_pixel
            
        # Update links to include tracking (basic implementation)
        import re
        
        def add_tracking_to_link(match):
            href = match.group(1)
            if href.startswith('http') and 'track/click' not in href:
                # Create tracked link with fixed domain
                tracked_url = f"{domain_url}/track/click/{tracking_id}?url={href}"
                return f'href="{tracked_url}"'
            return match.group(0)
        
        content_html = re.sub(r'href="([^"]*)"', add_tracking_to_link, content_html)
        
        return content_html

# Global email service instance
email_service = EmailService()