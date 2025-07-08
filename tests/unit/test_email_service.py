#!/usr/bin/env python3
"""
Unit tests for email service functionality
Tests email sending, templating, and error handling
"""

import pytest
import smtplib
from unittest.mock import patch, MagicMock, mock_open
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
import base64
import os

from services.email_service import EmailService, EmailError


class TestEmailServiceInitialization:
    """Test email service initialization"""
    
    def test_init_with_valid_config(self):
        """Test initialization with valid configuration"""
        config = {
            'SMTP_SERVER': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': 'test@gmail.com',
            'SMTP_PASSWORD': 'password123',
            'FROM_EMAIL': 'test@gmail.com'
        }
        
        with patch.dict('os.environ', config):
            email_service = EmailService()
            
            assert email_service.smtp_server == 'smtp.gmail.com'
            assert email_service.smtp_port == 587
            assert email_service.smtp_username == 'test@gmail.com'
            assert email_service.smtp_password == 'password123'
            assert email_service.from_email == 'test@gmail.com'
    
    def test_init_with_missing_config(self):
        """Test initialization with missing configuration"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="Email configuration not found"):
                EmailService()
    
    def test_init_with_invalid_port(self):
        """Test initialization with invalid port"""
        config = {
            'SMTP_SERVER': 'smtp.gmail.com',
            'SMTP_PORT': 'invalid_port',
            'SMTP_USERNAME': 'test@gmail.com',
            'SMTP_PASSWORD': 'password123',
            'FROM_EMAIL': 'test@gmail.com'
        }
        
        with patch.dict('os.environ', config):
            with pytest.raises(ValueError, match="Invalid SMTP port"):
                EmailService()
    
    def test_init_with_godaddy_config(self):
        """Test initialization with GoDaddy configuration"""
        config = {
            'SMTP_SERVER': 'smtpout.secureserver.net',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': 'support@thevectorcraft.com',
            'SMTP_PASSWORD': 'Ankish@its123',
            'FROM_EMAIL': 'support@thevectorcraft.com'
        }
        
        with patch.dict('os.environ', config):
            email_service = EmailService()
            
            assert email_service.smtp_server == 'smtpout.secureserver.net'
            assert email_service.smtp_port == 587
            assert email_service.from_email == 'support@thevectorcraft.com'


class TestEmailConnection:
    """Test email connection functionality"""
    
    def test_connection_success(self, mock_email_service):
        """Test successful email connection"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.test_connection()
            
            assert result is True
            mock_smtp.assert_called_once_with('smtp.gmail.com', 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.quit.assert_called_once()
    
    def test_connection_failure(self, mock_email_service):
        """Test email connection failure"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPException("Connection failed")
            
            email_service = EmailService()
            result = email_service.test_connection()
            
            assert result is False
    
    def test_connection_authentication_failure(self, mock_email_service):
        """Test authentication failure"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, "Authentication failed")
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.test_connection()
            
            assert result is False
    
    def test_connection_timeout(self, mock_email_service):
        """Test connection timeout"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = TimeoutError("Connection timeout")
            
            email_service = EmailService()
            result = email_service.test_connection()
            
            assert result is False
    
    def test_connection_ssl_error(self, mock_email_service):
        """Test SSL connection error"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_server.starttls.side_effect = smtplib.SMTPException("SSL error")
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.test_connection()
            
            assert result is False


class TestEmailSending:
    """Test email sending functionality"""
    
    def test_send_email_success(self, mock_email_service):
        """Test successful email sending"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.send_email(
                to_email='test@example.com',
                subject='Test Subject',
                body='Test Body',
                html_body='<h1>Test HTML Body</h1>'
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    def test_send_email_invalid_recipient(self, mock_email_service):
        """Test sending email to invalid recipient"""
        email_service = EmailService()
        
        with pytest.raises(ValueError, match="Invalid recipient email"):
            email_service.send_email(
                to_email='invalid_email',
                subject='Test Subject',
                body='Test Body'
            )
    
    def test_send_email_empty_subject(self, mock_email_service):
        """Test sending email with empty subject"""
        email_service = EmailService()
        
        with pytest.raises(ValueError, match="Subject cannot be empty"):
            email_service.send_email(
                to_email='test@example.com',
                subject='',
                body='Test Body'
            )
    
    def test_send_email_empty_body(self, mock_email_service):
        """Test sending email with empty body"""
        email_service = EmailService()
        
        with pytest.raises(ValueError, match="Body cannot be empty"):
            email_service.send_email(
                to_email='test@example.com',
                subject='Test Subject',
                body=''
            )
    
    def test_send_email_smtp_error(self, mock_email_service):
        """Test SMTP error during email sending"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_server.send_message.side_effect = smtplib.SMTPException("SMTP error")
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            
            with pytest.raises(EmailError, match="Failed to send email"):
                email_service.send_email(
                    to_email='test@example.com',
                    subject='Test Subject',
                    body='Test Body'
                )
    
    def test_send_email_with_attachment(self, mock_email_service):
        """Test sending email with attachment"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            with patch('builtins.open', mock_open(read_data=b'fake file content')):
                email_service = EmailService()
                result = email_service.send_email(
                    to_email='test@example.com',
                    subject='Test Subject',
                    body='Test Body',
                    attachments=['test.pdf']
                )
                
                assert result is True
                mock_server.send_message.assert_called_once()
    
    def test_send_email_multiple_recipients(self, mock_email_service):
        """Test sending email to multiple recipients"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.send_email(
                to_email=['test1@example.com', 'test2@example.com'],
                subject='Test Subject',
                body='Test Body'
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    def test_send_email_with_cc_bcc(self, mock_email_service):
        """Test sending email with CC and BCC"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.send_email(
                to_email='test@example.com',
                subject='Test Subject',
                body='Test Body',
                cc=['cc@example.com'],
                bcc=['bcc@example.com']
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    def test_send_email_priority(self, mock_email_service):
        """Test sending email with priority"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.send_email(
                to_email='test@example.com',
                subject='Test Subject',
                body='Test Body',
                priority='high'
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()


class TestCredentialsEmail:
    """Test credentials email functionality"""
    
    def test_send_credentials_email_success(self, mock_email_service):
        """Test successful credentials email sending"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.send_credentials_email(
                email='test@example.com',
                username='testuser',
                password='TestPassword123!',
                order_details={'amount': 49.00, 'order_id': 'ORDER123'}
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    def test_send_credentials_email_invalid_email(self, mock_email_service):
        """Test credentials email with invalid email"""
        email_service = EmailService()
        
        with pytest.raises(ValueError, match="Invalid email address"):
            email_service.send_credentials_email(
                email='invalid_email',
                username='testuser',
                password='TestPassword123!',
                order_details={'amount': 49.00, 'order_id': 'ORDER123'}
            )
    
    def test_send_credentials_email_missing_data(self, mock_email_service):
        """Test credentials email with missing data"""
        email_service = EmailService()
        
        with pytest.raises(ValueError, match="Username is required"):
            email_service.send_credentials_email(
                email='test@example.com',
                username='',
                password='TestPassword123!',
                order_details={'amount': 49.00, 'order_id': 'ORDER123'}
            )
        
        with pytest.raises(ValueError, match="Password is required"):
            email_service.send_credentials_email(
                email='test@example.com',
                username='testuser',
                password='',
                order_details={'amount': 49.00, 'order_id': 'ORDER123'}
            )
    
    def test_send_credentials_email_template(self, mock_email_service):
        """Test credentials email template rendering"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.send_credentials_email(
                email='test@example.com',
                username='testuser',
                password='TestPassword123!',
                order_details={'amount': 49.00, 'order_id': 'ORDER123'}
            )
            
            assert result is True
            
            # Check that message was sent
            mock_server.send_message.assert_called_once()
            
            # Get the message that was sent
            sent_message = mock_server.send_message.call_args[0][0]
            message_body = str(sent_message)
            
            # Check template content
            assert 'testuser' in message_body
            assert 'TestPassword123!' in message_body
            assert '49.00' in message_body
            assert 'ORDER123' in message_body
    
    def test_send_credentials_email_with_login_url(self, mock_email_service):
        """Test credentials email with login URL"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.send_credentials_email(
                email='test@example.com',
                username='testuser',
                password='TestPassword123!',
                order_details={'amount': 49.00, 'order_id': 'ORDER123'},
                login_url='https://thevectorcraft.com/login'
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    def test_send_credentials_email_security(self, mock_email_service):
        """Test credentials email security measures"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            
            # Test that password is not logged
            with patch('logging.Logger.info') as mock_log:
                result = email_service.send_credentials_email(
                    email='test@example.com',
                    username='testuser',
                    password='TestPassword123!',
                    order_details={'amount': 49.00, 'order_id': 'ORDER123'}
                )
                
                assert result is True
                
                # Check that password is not in log messages
                for call in mock_log.call_args_list:
                    log_message = str(call)
                    assert 'TestPassword123!' not in log_message


class TestNotificationEmails:
    """Test notification email functionality"""
    
    def test_send_notification_email_success(self, mock_email_service):
        """Test successful notification email sending"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.send_notification_email(
                email='admin@example.com',
                subject='New User Registration',
                message='A new user has registered: testuser',
                notification_type='user_registration'
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    def test_send_admin_alert_email(self, mock_email_service):
        """Test admin alert email sending"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.send_admin_alert(
                subject='System Alert',
                message='High CPU usage detected',
                alert_level='warning'
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    def test_send_payment_confirmation_email(self, mock_email_service):
        """Test payment confirmation email sending"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.send_payment_confirmation(
                email='customer@example.com',
                transaction_id='TXN123456',
                amount=49.00,
                currency='USD',
                order_details={'product': 'VectorCraft Access'}
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    def test_send_password_reset_email(self, mock_email_service):
        """Test password reset email sending"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.send_password_reset(
                email='user@example.com',
                reset_token='reset_token_123',
                reset_url='https://example.com/reset?token=reset_token_123'
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    def test_send_welcome_email(self, mock_email_service):
        """Test welcome email sending"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            result = email_service.send_welcome_email(
                email='newuser@example.com',
                username='newuser',
                features=['Vector conversion', 'Multiple algorithms', 'High quality output']
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()


class TestEmailTemplates:
    """Test email template functionality"""
    
    def test_load_email_template(self, mock_email_service):
        """Test loading email template"""
        template_content = """
        <html>
        <body>
            <h1>Welcome {{username}}!</h1>
            <p>Your password is: {{password}}</p>
            <p>Order ID: {{order_id}}</p>
            <p>Amount: ${{amount}}</p>
        </body>
        </html>
        """
        
        with patch('builtins.open', mock_open(read_data=template_content)):
            email_service = EmailService()
            template = email_service.load_template('credentials_email.html')
            
            assert template is not None
            assert '{{username}}' in template
            assert '{{password}}' in template
    
    def test_render_email_template(self, mock_email_service):
        """Test rendering email template"""
        template_content = """
        <html>
        <body>
            <h1>Welcome {{username}}!</h1>
            <p>Your password is: {{password}}</p>
            <p>Order ID: {{order_id}}</p>
            <p>Amount: ${{amount}}</p>
        </body>
        </html>
        """
        
        with patch('builtins.open', mock_open(read_data=template_content)):
            email_service = EmailService()
            rendered = email_service.render_template('credentials_email.html', {
                'username': 'testuser',
                'password': 'TestPassword123!',
                'order_id': 'ORDER123',
                'amount': '49.00'
            })
            
            assert 'Welcome testuser!' in rendered
            assert 'TestPassword123!' in rendered
            assert 'ORDER123' in rendered
            assert '$49.00' in rendered
    
    def test_template_not_found(self, mock_email_service):
        """Test handling of missing template"""
        with patch('builtins.open', side_effect=FileNotFoundError()):
            email_service = EmailService()
            
            with pytest.raises(EmailError, match="Template not found"):
                email_service.load_template('nonexistent_template.html')
    
    def test_template_security(self, mock_email_service):
        """Test template security measures"""
        malicious_template = """
        <html>
        <body>
            <script>alert('xss')</script>
            <h1>Welcome {{username}}!</h1>
            <iframe src="javascript:alert('xss')"></iframe>
        </body>
        </html>
        """
        
        with patch('builtins.open', mock_open(read_data=malicious_template)):
            email_service = EmailService()
            rendered = email_service.render_template('malicious_template.html', {
                'username': 'testuser'
            })
            
            # Should sanitize or remove dangerous elements
            assert '<script>' not in rendered or '&lt;script&gt;' in rendered
            assert 'javascript:' not in rendered
    
    def test_template_variable_escaping(self, mock_email_service):
        """Test template variable escaping"""
        template_content = """
        <html>
        <body>
            <h1>Welcome {{username}}!</h1>
            <p>Message: {{message}}</p>
        </body>
        </html>
        """
        
        with patch('builtins.open', mock_open(read_data=template_content)):
            email_service = EmailService()
            rendered = email_service.render_template('test_template.html', {
                'username': 'testuser',
                'message': '<script>alert("xss")</script>'
            })
            
            # Should escape HTML in variables
            assert '<script>' not in rendered or '&lt;script&gt;' in rendered
    
    def test_template_missing_variables(self, mock_email_service):
        """Test template with missing variables"""
        template_content = """
        <html>
        <body>
            <h1>Welcome {{username}}!</h1>
            <p>Your password is: {{password}}</p>
            <p>Missing: {{missing_var}}</p>
        </body>
        </html>
        """
        
        with patch('builtins.open', mock_open(read_data=template_content)):
            email_service = EmailService()
            rendered = email_service.render_template('test_template.html', {
                'username': 'testuser',
                'password': 'TestPassword123!'
            })
            
            # Should handle missing variables gracefully
            assert 'testuser' in rendered
            assert 'TestPassword123!' in rendered
            assert '{{missing_var}}' not in rendered or rendered.count('{{') == 0


class TestEmailValidation:
    """Test email validation functionality"""
    
    def test_validate_email_valid(self, mock_email_service):
        """Test valid email validation"""
        email_service = EmailService()
        
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'user+tag@example.org',
            'user123@example123.com',
            'user@sub.domain.com'
        ]
        
        for email in valid_emails:
            assert email_service.validate_email(email) is True
    
    def test_validate_email_invalid(self, mock_email_service):
        """Test invalid email validation"""
        email_service = EmailService()
        
        invalid_emails = [
            'invalid_email',
            '@domain.com',
            'user@',
            'user@domain',
            'user@domain.',
            'user.domain.com',
            'user@domain..com',
            'user name@domain.com',
            'user@domain com',
            '',
            None
        ]
        
        for email in invalid_emails:
            assert email_service.validate_email(email) is False
    
    def test_validate_email_list(self, mock_email_service):
        """Test email list validation"""
        email_service = EmailService()
        
        # Valid email list
        valid_emails = ['test1@example.com', 'test2@example.com']
        assert email_service.validate_email_list(valid_emails) is True
        
        # Invalid email in list
        invalid_emails = ['test1@example.com', 'invalid_email']
        assert email_service.validate_email_list(invalid_emails) is False
        
        # Empty list
        assert email_service.validate_email_list([]) is False
    
    def test_sanitize_email_content(self, mock_email_service):
        """Test email content sanitization"""
        email_service = EmailService()
        
        malicious_content = """
        <script>alert('xss')</script>
        <h1>Hello World</h1>
        <iframe src="javascript:alert('xss')"></iframe>
        <p>Normal text</p>
        """
        
        sanitized = email_service.sanitize_content(malicious_content)
        
        # Should remove dangerous elements
        assert '<script>' not in sanitized
        assert 'javascript:' not in sanitized
        assert '<iframe>' not in sanitized
        
        # Should keep safe elements
        assert '<h1>Hello World</h1>' in sanitized
        assert '<p>Normal text</p>' in sanitized
    
    def test_validate_attachment_security(self, mock_email_service):
        """Test attachment security validation"""
        email_service = EmailService()
        
        # Valid attachments
        valid_files = ['document.pdf', 'image.png', 'data.csv']
        for file in valid_files:
            assert email_service.validate_attachment(file) is True
        
        # Invalid/dangerous attachments
        invalid_files = ['script.exe', 'virus.bat', 'malware.scr', 'dangerous.com']
        for file in invalid_files:
            assert email_service.validate_attachment(file) is False


class TestEmailQueue:
    """Test email queue functionality"""
    
    def test_queue_email(self, mock_email_service):
        """Test queuing email for later sending"""
        email_service = EmailService()
        
        email_data = {
            'to_email': 'test@example.com',
            'subject': 'Test Subject',
            'body': 'Test Body',
            'priority': 'normal'
        }
        
        queue_id = email_service.queue_email(email_data)
        
        assert queue_id is not None
        assert isinstance(queue_id, str)
        assert len(queue_id) > 0
    
    def test_process_email_queue(self, mock_email_service):
        """Test processing email queue"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            
            # Queue some emails
            email_data = {
                'to_email': 'test@example.com',
                'subject': 'Test Subject',
                'body': 'Test Body',
                'priority': 'normal'
            }
            
            queue_id1 = email_service.queue_email(email_data)
            queue_id2 = email_service.queue_email(email_data)
            
            # Process queue
            processed_count = email_service.process_queue()
            
            assert processed_count == 2
            assert mock_server.send_message.call_count == 2
    
    def test_priority_email_processing(self, mock_email_service):
        """Test priority email processing"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            
            # Queue emails with different priorities
            normal_email = {
                'to_email': 'test@example.com',
                'subject': 'Normal Priority',
                'body': 'Normal Body',
                'priority': 'normal'
            }
            
            high_email = {
                'to_email': 'test@example.com',
                'subject': 'High Priority',
                'body': 'High Body',
                'priority': 'high'
            }
            
            # Queue in order: normal, high, normal
            email_service.queue_email(normal_email)
            email_service.queue_email(high_email)
            email_service.queue_email(normal_email)
            
            # Process queue
            processed_count = email_service.process_queue(max_emails=1)
            
            assert processed_count == 1
            
            # High priority email should be processed first
            sent_message = mock_server.send_message.call_args[0][0]
            assert 'High Priority' in str(sent_message)
    
    def test_email_retry_mechanism(self, mock_email_service):
        """Test email retry mechanism"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_server.send_message.side_effect = [
                smtplib.SMTPException("Temporary failure"),
                None  # Success on retry
            ]
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            
            # Queue email
            email_data = {
                'to_email': 'test@example.com',
                'subject': 'Test Subject',
                'body': 'Test Body',
                'priority': 'normal'
            }
            
            queue_id = email_service.queue_email(email_data)
            
            # Process queue (should retry on failure)
            processed_count = email_service.process_queue()
            
            assert processed_count == 1
            assert mock_server.send_message.call_count == 2
    
    def test_failed_email_handling(self, mock_email_service):
        """Test handling of permanently failed emails"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_server.send_message.side_effect = smtplib.SMTPRecipientsRefused({
                'invalid@example.com': (550, 'User unknown')
            })
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            
            # Queue email to invalid address
            email_data = {
                'to_email': 'invalid@example.com',
                'subject': 'Test Subject',
                'body': 'Test Body',
                'priority': 'normal'
            }
            
            queue_id = email_service.queue_email(email_data)
            
            # Process queue
            processed_count = email_service.process_queue()
            
            # Should handle permanent failure
            assert processed_count == 0
            
            # Email should be marked as failed
            failed_emails = email_service.get_failed_emails()
            assert len(failed_emails) == 1
            assert failed_emails[0]['to_email'] == 'invalid@example.com'


class TestEmailLogging:
    """Test email logging functionality"""
    
    def test_email_sending_logging(self, mock_email_service):
        """Test logging of email sending"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            with patch('logging.Logger.info') as mock_log:
                email_service = EmailService()
                result = email_service.send_email(
                    to_email='test@example.com',
                    subject='Test Subject',
                    body='Test Body'
                )
                
                assert result is True
                
                # Check that email sending was logged
                mock_log.assert_called()
                log_messages = [str(call) for call in mock_log.call_args_list]
                assert any('email sent' in msg.lower() for msg in log_messages)
    
    def test_email_failure_logging(self, mock_email_service):
        """Test logging of email failures"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_server.send_message.side_effect = smtplib.SMTPException("SMTP error")
            mock_smtp.return_value = mock_server
            
            with patch('logging.Logger.error') as mock_log:
                email_service = EmailService()
                
                try:
                    email_service.send_email(
                        to_email='test@example.com',
                        subject='Test Subject',
                        body='Test Body'
                    )
                except EmailError:
                    pass
                
                # Check that email failure was logged
                mock_log.assert_called()
                log_messages = [str(call) for call in mock_log.call_args_list]
                assert any('failed' in msg.lower() for msg in log_messages)
    
    def test_email_security_logging(self, mock_email_service):
        """Test logging of email security events"""
        with patch('logging.Logger.warning') as mock_log:
            email_service = EmailService()
            
            # Try to send email with malicious content
            try:
                email_service.send_email(
                    to_email='test@example.com',
                    subject='<script>alert("xss")</script>',
                    body='Test Body'
                )
            except ValueError:
                pass
            
            # Check that security event was logged
            mock_log.assert_called()
            log_messages = [str(call) for call in mock_log.call_args_list]
            assert any('security' in msg.lower() or 'malicious' in msg.lower() for msg in log_messages)


class TestEmailMetrics:
    """Test email metrics functionality"""
    
    def test_email_delivery_metrics(self, mock_email_service):
        """Test email delivery metrics"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            
            # Send multiple emails
            for i in range(10):
                email_service.send_email(
                    to_email=f'test{i}@example.com',
                    subject=f'Test Subject {i}',
                    body=f'Test Body {i}'
                )
            
            # Get metrics
            metrics = email_service.get_metrics()
            
            assert metrics['emails_sent'] == 10
            assert metrics['success_rate'] == 100.0
            assert metrics['failure_rate'] == 0.0
    
    def test_email_performance_metrics(self, mock_email_service):
        """Test email performance metrics"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            
            # Send email and measure performance
            import time
            start_time = time.time()
            
            email_service.send_email(
                to_email='test@example.com',
                subject='Test Subject',
                body='Test Body'
            )
            
            end_time = time.time()
            
            # Get performance metrics
            metrics = email_service.get_performance_metrics()
            
            assert 'average_send_time' in metrics
            assert 'total_emails_sent' in metrics
            assert 'emails_per_minute' in metrics
    
    def test_email_error_metrics(self, mock_email_service):
        """Test email error metrics"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_server.send_message.side_effect = [
                None,  # Success
                smtplib.SMTPException("Error"),  # Failure
                None,  # Success
            ]
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            
            # Send multiple emails with mixed results
            for i in range(3):
                try:
                    email_service.send_email(
                        to_email=f'test{i}@example.com',
                        subject=f'Test Subject {i}',
                        body=f'Test Body {i}'
                    )
                except EmailError:
                    pass
            
            # Get error metrics
            metrics = email_service.get_error_metrics()
            
            assert metrics['total_attempts'] == 3
            assert metrics['successful_sends'] == 2
            assert metrics['failed_sends'] == 1
            assert metrics['error_rate'] == 33.33  # 1/3 * 100


@pytest.mark.parametrize("email,expected_valid", [
    ('test@example.com', True),
    ('user.name@domain.co.uk', True),
    ('user+tag@example.org', True),
    ('invalid_email', False),
    ('@domain.com', False),
    ('user@', False),
    ('user@domain.', False),
    ('user name@domain.com', False),
    ('', False),
])
def test_email_validation_parametrized(mock_email_service, email, expected_valid):
    """Test email validation with parametrized inputs"""
    email_service = EmailService()
    result = email_service.validate_email(email)
    assert result == expected_valid


class TestEmailIntegration:
    """Test email service integration"""
    
    def test_integration_with_user_registration(self, mock_email_service, temp_db):
        """Test email integration with user registration"""
        # Create user
        user_id = temp_db.create_user('testuser', 'test@example.com', 'Password123!')
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            
            # Send welcome email
            result = email_service.send_welcome_email(
                email='test@example.com',
                username='testuser',
                features=['Vector conversion', 'Multiple algorithms']
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    def test_integration_with_payment_system(self, mock_email_service, temp_db):
        """Test email integration with payment system"""
        # Create transaction
        transaction_data = {
            'transaction_id': 'txn-123',
            'email': 'customer@example.com',
            'amount': 49.00,
            'currency': 'USD',
            'status': 'completed'
        }
        
        transaction_id = temp_db.create_transaction(transaction_data)
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            
            # Send payment confirmation
            result = email_service.send_payment_confirmation(
                email='customer@example.com',
                transaction_id='txn-123',
                amount=49.00,
                currency='USD',
                order_details={'product': 'VectorCraft Access'}
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    def test_integration_with_monitoring_system(self, mock_email_service, mock_monitoring_services):
        """Test email integration with monitoring system"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            email_service = EmailService()
            
            # Send system alert
            result = email_service.send_admin_alert(
                subject='System Alert: High CPU Usage',
                message='CPU usage has exceeded 90% for 5 minutes',
                alert_level='critical'
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()


if __name__ == '__main__':
    # Run email service tests
    pytest.main([__file__, '-v'])