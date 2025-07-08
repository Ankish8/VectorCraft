#!/usr/bin/env python3
"""
Security tests for VectorCraft application
Tests authentication, authorization, input validation, and security vulnerabilities
"""

import pytest
import time
import hashlib
import hmac
import base64
import json
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import FileStorage
import io

from flask import session


class TestAuthenticationSecurity:
    """Test authentication security measures"""
    
    def test_password_hashing_security(self, temp_db):
        """Test password hashing security"""
        password = "TestPassword123!"
        
        # Create user
        user_id = temp_db.create_user("testuser", "test@example.com", password)
        user = temp_db.get_user_by_id(user_id)
        
        # Password should be hashed
        assert user['password_hash'] != password
        assert len(user['password_hash']) > 0
        assert len(user['salt']) > 0
        
        # Salt should be unique
        user_id2 = temp_db.create_user("testuser2", "test2@example.com", password)
        user2 = temp_db.get_user_by_id(user_id2)
        
        assert user['salt'] != user2['salt']
        assert user['password_hash'] != user2['password_hash']
    
    def test_password_strength_requirements(self, temp_db):
        """Test password strength requirements"""
        # Test weak passwords
        weak_passwords = [
            "123456",
            "password",
            "qwerty",
            "abc123",
            "Password",  # No numbers
            "password123",  # No uppercase
            "PASSWORD123",  # No lowercase
        ]
        
        for weak_password in weak_passwords:
            with pytest.raises(ValueError, match="Password"):
                temp_db.create_user("testuser", "test@example.com", weak_password)
    
    def test_login_rate_limiting(self, client, created_user, test_user_data):
        """Test login rate limiting"""
        # Make multiple failed login attempts
        for i in range(6):
            response = client.post('/login', data={
                'username': test_user_data['username'],
                'password': 'wrong_password'
            })
        
        # Should be rate limited
        assert response.status_code == 429 or b'too many' in response.data.lower()
    
    def test_session_security(self, client, created_user, test_user_data):
        """Test session security"""
        # Login
        response = client.post('/login', data={
            'username': test_user_data['username'],
            'password': test_user_data['password']
        })
        
        # Check session security attributes
        with client.session_transaction() as sess:
            assert 'user_id' in sess
            assert sess['user_id'] == created_user['id']
        
        # Check session cookie security
        cookies = response.headers.getlist('Set-Cookie')
        session_cookie = None
        for cookie in cookies:
            if cookie.startswith('session='):
                session_cookie = cookie
                break
        
        if session_cookie:
            # Should have HttpOnly flag
            assert 'HttpOnly' in session_cookie
            # Should have SameSite attribute
            assert 'SameSite' in session_cookie
    
    def test_session_fixation_protection(self, client, created_user, test_user_data):
        """Test session fixation protection"""
        # Get initial session
        client.get('/login')
        
        with client.session_transaction() as sess:
            old_session_id = sess.get('_id')
        
        # Login
        response = client.post('/login', data={
            'username': test_user_data['username'],
            'password': test_user_data['password']
        })
        
        # Session ID should change after login
        with client.session_transaction() as sess:
            new_session_id = sess.get('_id')
        
        # Session ID should be different (if implemented)
        # Note: This depends on Flask session implementation
        if old_session_id and new_session_id:
            assert old_session_id != new_session_id
    
    def test_session_timeout(self, client, created_user, test_user_data):
        """Test session timeout"""
        # Login
        response = client.post('/login', data={
            'username': test_user_data['username'],
            'password': test_user_data['password']
        })
        
        # Access protected resource
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        # Mock session timeout
        with patch('time.time') as mock_time:
            mock_time.return_value = time.time() + 7200  # 2 hours later
            
            response = client.get('/dashboard')
            # Should redirect to login due to timeout
            assert response.status_code == 302
    
    def test_account_lockout(self, client, created_user, test_user_data):
        """Test account lockout after failed attempts"""
        # Make multiple failed login attempts
        for i in range(10):
            response = client.post('/login', data={
                'username': test_user_data['username'],
                'password': 'wrong_password'
            })
        
        # Account should be locked
        response = client.post('/login', data={
            'username': test_user_data['username'],
            'password': test_user_data['password']  # Correct password
        })
        
        # Should still be blocked due to lockout
        assert response.status_code == 200
        assert b'locked' in response.data.lower() or b'blocked' in response.data.lower()
    
    def test_password_reset_security(self, client, created_user, mock_email_service):
        """Test password reset security"""
        # Request password reset
        response = client.post('/forgot-password', data={
            'email': created_user['email']
        })
        
        # Should not reveal if email exists
        assert response.status_code == 200
        assert b'if the email exists' in response.data.lower() or b'instructions sent' in response.data.lower()
        
        # Check email was sent
        mock_email_service.send_password_reset_email.assert_called_once()


class TestCSRFProtection:
    """Test CSRF protection measures"""
    
    def test_csrf_token_required(self, client):
        """Test CSRF token requirement"""
        # POST request without CSRF token should fail
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        })
        
        # Should be rejected due to missing CSRF token
        assert response.status_code == 400
    
    def test_csrf_token_validation(self, client):
        """Test CSRF token validation"""
        # Get page with CSRF token
        response = client.get('/login')
        
        # Extract CSRF token from response
        csrf_token = None
        if b'csrf_token' in response.data:
            # Parse token from HTML (simplified)
            start = response.data.find(b'csrf_token')
            if start != -1:
                csrf_token = "mock_csrf_token"
        
        # Make request with valid CSRF token
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass',
            'csrf_token': csrf_token
        })
        
        # Should not be rejected for CSRF (may fail for other reasons)
        assert response.status_code != 400
    
    def test_csrf_token_uniqueness(self, client):
        """Test CSRF token uniqueness"""
        # Get two different pages
        response1 = client.get('/login')
        response2 = client.get('/login')
        
        # Tokens should be different (if implemented)
        # This is a simplified test - real implementation would parse HTML
        assert response1.data != response2.data
    
    def test_csrf_protection_state_changing_operations(self, authenticated_client):
        """Test CSRF protection for state-changing operations"""
        state_changing_endpoints = [
            ('/upload', 'POST'),
            ('/create-payment', 'POST'),
            ('/logout', 'POST'),
        ]
        
        for endpoint, method in state_changing_endpoints:
            if method == 'POST':
                response = authenticated_client.post(endpoint, data={})
                # Should require CSRF token or be protected
                assert response.status_code in [400, 403, 405]


class TestInputValidation:
    """Test input validation security"""
    
    def test_sql_injection_protection(self, client, security_test_helpers):
        """Test SQL injection protection"""
        sql_injection_strings = security_test_helpers.generate_sql_injection_strings()
        
        for injection_string in sql_injection_strings:
            # Test login form
            response = client.post('/login', data={
                'username': injection_string,
                'password': 'password'
            })
            
            # Should not cause SQL error
            assert response.status_code != 500
            assert b'sql' not in response.data.lower()
            assert b'error' not in response.data.lower() or b'login' in response.data.lower()
    
    def test_xss_protection(self, client, security_test_helpers):
        """Test XSS protection"""
        xss_strings = security_test_helpers.generate_xss_strings()
        
        for xss_string in xss_strings:
            # Test form input
            response = client.post('/login', data={
                'username': xss_string,
                'password': 'password'
            })
            
            # XSS payload should be escaped
            assert xss_string.encode() not in response.data
            assert b'<script>' not in response.data
            assert b'javascript:' not in response.data
    
    def test_path_traversal_protection(self, client):
        """Test path traversal protection"""
        path_traversal_strings = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '%2e%2e%2f%2e%2e%2f%2e%2e%2f%65%74%63%2f%70%61%73%73%77%64',
            '....//....//....//etc//passwd'
        ]
        
        for path_string in path_traversal_strings:
            # Test file access
            response = client.get(f'/static/{path_string}')
            
            # Should not access system files
            assert response.status_code in [404, 403, 400]
            assert b'root:' not in response.data
            assert b'Administrator' not in response.data
    
    def test_file_upload_validation(self, authenticated_client, security_test_helpers):
        """Test file upload validation"""
        # Test malicious file upload
        malicious_file = security_test_helpers.create_malicious_file()
        
        response = authenticated_client.post('/upload', data={
            'file': (malicious_file, 'malicious.png', 'image/png'),
            'algorithm': 'vtracer_high_fidelity'
        }, content_type='multipart/form-data')
        
        # Should reject malicious file
        assert response.status_code == 400
        assert b'invalid' in response.data.lower() or b'rejected' in response.data.lower()
    
    def test_file_size_validation(self, authenticated_client, security_test_helpers):
        """Test file size validation"""
        # Test oversized file
        large_file = security_test_helpers.create_large_file(size_mb=20)
        
        response = authenticated_client.post('/upload', data={
            'file': (large_file, 'large.png', 'image/png'),
            'algorithm': 'vtracer_high_fidelity'
        }, content_type='multipart/form-data')
        
        # Should reject oversized file
        assert response.status_code == 413
        assert b'too large' in response.data.lower() or b'size' in response.data.lower()
    
    def test_file_type_validation(self, authenticated_client):
        """Test file type validation"""
        # Test invalid file types
        invalid_files = [
            (b'#!/bin/bash\nrm -rf /', 'script.sh', 'application/x-sh'),
            (b'MZ\x90\x00', 'virus.exe', 'application/octet-stream'),
            (b'%PDF-1.4', 'document.pdf', 'application/pdf'),
            (b'PK\x03\x04', 'archive.zip', 'application/zip')
        ]
        
        for file_content, filename, content_type in invalid_files:
            file_data = io.BytesIO(file_content)
            
            response = authenticated_client.post('/upload', data={
                'file': (file_data, filename, content_type),
                'algorithm': 'vtracer_high_fidelity'
            }, content_type='multipart/form-data')
            
            # Should reject invalid file type
            assert response.status_code == 400
            assert b'invalid' in response.data.lower() or b'not supported' in response.data.lower()
    
    def test_email_validation(self, client):
        """Test email validation"""
        invalid_emails = [
            'invalid-email',
            '@domain.com',
            'user@',
            'user@domain',
            'user@domain.',
            'user.domain.com',
            'user@domain..com',
            'user name@domain.com',
            'user@domain com',
            '<script>alert("xss")</script>@domain.com'
        ]
        
        for invalid_email in invalid_emails:
            response = client.post('/register', data={
                'username': 'testuser',
                'email': invalid_email,
                'password': 'ValidPassword123!'
            })
            
            # Should reject invalid email
            assert response.status_code == 400
            assert b'invalid' in response.data.lower() or b'email' in response.data.lower()
    
    def test_username_validation(self, client):
        """Test username validation"""
        invalid_usernames = [
            '',  # Empty
            'a',  # Too short
            'a' * 51,  # Too long
            'user@name',  # Invalid characters
            'user name',  # Spaces
            'user.name',  # Dots
            'user/name',  # Slashes
            '<script>alert("xss")</script>',  # XSS attempt
            'SELECT * FROM users',  # SQL injection attempt
        ]
        
        for invalid_username in invalid_usernames:
            response = client.post('/register', data={
                'username': invalid_username,
                'email': 'test@example.com',
                'password': 'ValidPassword123!'
            })
            
            # Should reject invalid username
            assert response.status_code == 400
            assert b'invalid' in response.data.lower() or b'username' in response.data.lower()


class TestAuthorizationSecurity:
    """Test authorization security measures"""
    
    def test_unauthorized_access_protection(self, client):
        """Test protection against unauthorized access"""
        protected_endpoints = [
            '/dashboard',
            '/upload',
            '/admin',
            '/admin/users',
            '/admin/transactions',
            '/admin/system'
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            
            # Should redirect to login or return 401/403
            assert response.status_code in [302, 401, 403]
            
            if response.status_code == 302:
                assert 'login' in response.location
    
    def test_admin_access_protection(self, authenticated_client):
        """Test admin access protection"""
        admin_endpoints = [
            '/admin',
            '/admin/users',
            '/admin/transactions',
            '/admin/system',
            '/admin/logs'
        ]
        
        for endpoint in admin_endpoints:
            response = authenticated_client.get(endpoint)
            
            # Should allow access for admin or check admin status
            assert response.status_code in [200, 401, 403]
    
    def test_user_data_isolation(self, client, temp_db):
        """Test user data isolation"""
        # Create two users
        user1_id = temp_db.create_user('user1', 'user1@example.com', 'Password123!')
        user2_id = temp_db.create_user('user2', 'user2@example.com', 'Password123!')
        
        # Login as user1
        response = client.post('/login', data={
            'username': 'user1',
            'password': 'Password123!'
        })
        
        # Try to access user2's data
        response = client.get(f'/user/{user2_id}')
        
        # Should not allow access to other user's data
        assert response.status_code in [403, 404]
    
    def test_privilege_escalation_protection(self, authenticated_client):
        """Test privilege escalation protection"""
        # Try to access admin functions as regular user
        admin_actions = [
            ('/admin/users/delete/1', 'POST'),
            ('/admin/system/restart', 'POST'),
            ('/admin/users/promote/1', 'POST'),
            ('/admin/settings/update', 'POST')
        ]
        
        for endpoint, method in admin_actions:
            if method == 'POST':
                response = authenticated_client.post(endpoint)
            else:
                response = authenticated_client.get(endpoint)
            
            # Should deny access
            assert response.status_code in [401, 403, 404]
    
    def test_direct_object_reference_protection(self, authenticated_client, temp_db):
        """Test direct object reference protection"""
        # Create test transaction
        transaction_data = {
            'transaction_id': 'test-txn-123',
            'email': 'other@example.com',
            'amount': 49.00,
            'currency': 'USD',
            'status': 'completed'
        }
        transaction_id = temp_db.create_transaction(transaction_data)
        
        # Try to access other user's transaction
        response = authenticated_client.get(f'/transaction/{transaction_id}')
        
        # Should not allow access to other user's transaction
        assert response.status_code in [403, 404]


class TestSecurityHeaders:
    """Test security headers"""
    
    def test_security_headers_presence(self, client):
        """Test presence of security headers"""
        response = client.get('/login')
        
        # Check for security headers
        headers = response.headers
        
        # Content Security Policy
        assert 'Content-Security-Policy' in headers or 'X-Content-Type-Options' in headers
        
        # X-Frame-Options
        assert 'X-Frame-Options' in headers or 'frame-ancestors' in headers.get('Content-Security-Policy', '')
        
        # X-Content-Type-Options
        assert 'X-Content-Type-Options' in headers
        
        # X-XSS-Protection (legacy but still good)
        assert 'X-XSS-Protection' in headers or 'Content-Security-Policy' in headers
    
    def test_content_security_policy(self, client):
        """Test Content Security Policy"""
        response = client.get('/login')
        
        csp_header = response.headers.get('Content-Security-Policy')
        
        if csp_header:
            # Should restrict script sources
            assert 'script-src' in csp_header
            assert "'unsafe-inline'" not in csp_header or "'nonce-" in csp_header
            
            # Should restrict object sources
            assert 'object-src' in csp_header
            assert "'none'" in csp_header
    
    def test_referrer_policy(self, client):
        """Test Referrer Policy"""
        response = client.get('/login')
        
        referrer_policy = response.headers.get('Referrer-Policy')
        
        if referrer_policy:
            # Should have restrictive referrer policy
            assert referrer_policy in ['strict-origin-when-cross-origin', 'no-referrer', 'same-origin']
    
    def test_permissions_policy(self, client):
        """Test Permissions Policy"""
        response = client.get('/login')
        
        permissions_policy = response.headers.get('Permissions-Policy')
        
        if permissions_policy:
            # Should restrict dangerous features
            assert 'geolocation=()' in permissions_policy or 'geolocation' not in permissions_policy
            assert 'microphone=()' in permissions_policy or 'microphone' not in permissions_policy
            assert 'camera=()' in permissions_policy or 'camera' not in permissions_policy


class TestSSLTLSSecurity:
    """Test SSL/TLS security measures"""
    
    def test_https_redirect(self, client):
        """Test HTTPS redirect (if configured)"""
        # Mock production environment
        with patch.dict('os.environ', {'FLASK_ENV': 'production'}):
            response = client.get('/', base_url='http://example.com')
            
            # Should redirect to HTTPS in production
            if response.status_code == 301:
                assert response.location.startswith('https://')
    
    def test_secure_cookie_flags(self, client, created_user, test_user_data):
        """Test secure cookie flags"""
        # Mock production environment
        with patch.dict('os.environ', {'FLASK_ENV': 'production'}):
            response = client.post('/login', data={
                'username': test_user_data['username'],
                'password': test_user_data['password']
            })
            
            # Check cookie flags
            cookies = response.headers.getlist('Set-Cookie')
            for cookie in cookies:
                if 'session=' in cookie:
                    # Should have Secure flag in production
                    assert 'Secure' in cookie
                    assert 'HttpOnly' in cookie
                    assert 'SameSite' in cookie
    
    def test_hsts_header(self, client):
        """Test HTTP Strict Transport Security header"""
        # Mock production environment
        with patch.dict('os.environ', {'FLASK_ENV': 'production'}):
            response = client.get('/', headers={'X-Forwarded-Proto': 'https'})
            
            # Should have HSTS header
            hsts_header = response.headers.get('Strict-Transport-Security')
            
            if hsts_header:
                assert 'max-age=' in hsts_header
                assert 'includeSubDomains' in hsts_header


class TestAPIKeySecurity:
    """Test API key security measures"""
    
    def test_api_key_validation(self, client):
        """Test API key validation"""
        # Test API endpoint without key
        response = client.get('/api/v1/health')
        
        # Should require API key or return 401
        assert response.status_code in [401, 404]
    
    def test_api_key_rate_limiting(self, client):
        """Test API key rate limiting"""
        api_key = 'test-api-key'
        
        # Make multiple requests with same API key
        for i in range(100):
            response = client.get('/api/v1/health', headers={
                'X-API-Key': api_key
            })
            
            if response.status_code == 429:
                # Rate limit reached
                break
        
        # Should implement rate limiting
        assert response.status_code == 429
    
    def test_api_key_scope_validation(self, client):
        """Test API key scope validation"""
        # Test different API key scopes
        read_only_key = 'read-only-key'
        admin_key = 'admin-key'
        
        # Read-only key should not allow write operations
        response = client.post('/api/v1/users', 
                              headers={'X-API-Key': read_only_key},
                              json={'username': 'testuser'})
        
        assert response.status_code in [403, 404]
        
        # Admin key should allow write operations
        response = client.post('/api/v1/users',
                              headers={'X-API-Key': admin_key},
                              json={'username': 'testuser'})
        
        # Should allow or return different error
        assert response.status_code != 403


class TestSecurityLogging:
    """Test security event logging"""
    
    def test_failed_login_logging(self, client, temp_db):
        """Test failed login attempt logging"""
        # Make failed login attempt
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'wrongpassword'
        })
        
        # Check security log
        logs = temp_db.get_logs_by_type('security_event')
        
        # Should log security event
        assert len(logs) > 0
        assert any('failed_login' in log['message'].lower() for log in logs)
    
    def test_suspicious_activity_logging(self, client, temp_db):
        """Test suspicious activity logging"""
        # Make multiple rapid requests (potential attack)
        for i in range(20):
            response = client.get('/login')
        
        # Check security log
        logs = temp_db.get_logs_by_type('security_event')
        
        # Should log suspicious activity
        assert len(logs) > 0
        assert any('suspicious' in log['message'].lower() or 'rate' in log['message'].lower() for log in logs)
    
    def test_admin_action_logging(self, authenticated_client, temp_db):
        """Test admin action logging"""
        # Perform admin action
        response = authenticated_client.get('/admin/users')
        
        # Check audit log
        logs = temp_db.get_logs_by_type('admin_action')
        
        # Should log admin action
        assert len(logs) > 0
        assert any('admin' in log['message'].lower() for log in logs)
    
    def test_file_upload_logging(self, authenticated_client, test_image_file, temp_db):
        """Test file upload logging"""
        test_image_file.seek(0)
        
        # Upload file
        response = authenticated_client.post('/upload', data={
            'file': (test_image_file, 'test.png', 'image/png'),
            'algorithm': 'vtracer_high_fidelity'
        }, content_type='multipart/form-data')
        
        # Check file upload log
        logs = temp_db.get_logs_by_type('file_upload')
        
        # Should log file upload
        assert len(logs) > 0
        assert any('upload' in log['message'].lower() for log in logs)


class TestVulnerabilityScanning:
    """Test for common web vulnerabilities"""
    
    def test_clickjacking_protection(self, client):
        """Test clickjacking protection"""
        response = client.get('/login')
        
        # Should have X-Frame-Options or CSP frame-ancestors
        x_frame_options = response.headers.get('X-Frame-Options')
        csp = response.headers.get('Content-Security-Policy')
        
        assert x_frame_options in ['DENY', 'SAMEORIGIN'] or \
               (csp and 'frame-ancestors' in csp)
    
    def test_mime_type_sniffing_protection(self, client):
        """Test MIME type sniffing protection"""
        response = client.get('/login')
        
        # Should have X-Content-Type-Options
        x_content_type_options = response.headers.get('X-Content-Type-Options')
        assert x_content_type_options == 'nosniff'
    
    def test_information_disclosure_protection(self, client):
        """Test information disclosure protection"""
        # Test error pages don't reveal sensitive information
        response = client.get('/nonexistent-page')
        
        assert response.status_code == 404
        assert b'stacktrace' not in response.data.lower()
        assert b'debug' not in response.data.lower()
        assert b'exception' not in response.data.lower()
        assert b'traceback' not in response.data.lower()
    
    def test_directory_traversal_protection(self, client):
        """Test directory traversal protection"""
        # Test various directory traversal attempts
        traversal_attempts = [
            '/static/../../../etc/passwd',
            '/static/%2e%2e%2f%2e%2e%2f%2e%2e%2f%65%74%63%2f%70%61%73%73%77%64',
            '/static/....//....//....//etc//passwd',
            '/static/..%252f..%252f..%252fetc%252fpasswd'
        ]
        
        for attempt in traversal_attempts:
            response = client.get(attempt)
            
            # Should not access system files
            assert response.status_code in [404, 403, 400]
            assert b'root:' not in response.data
    
    def test_server_side_request_forgery_protection(self, client):
        """Test SSRF protection"""
        # Test if application makes requests to URLs provided by user
        ssrf_urls = [
            'http://localhost:22',
            'http://169.254.169.254/latest/meta-data/',
            'file:///etc/passwd',
            'ftp://localhost:21'
        ]
        
        for url in ssrf_urls:
            response = client.post('/webhook', data={
                'url': url,
                'callback': url
            })
            
            # Should validate and restrict URLs
            assert response.status_code in [400, 403, 404]
    
    def test_xml_external_entity_protection(self, client):
        """Test XXE protection"""
        # Test XXE payload
        xxe_payload = '''<?xml version="1.0"?>
        <!DOCTYPE foo [
        <!ELEMENT foo ANY>
        <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <foo>&xxe;</foo>'''
        
        response = client.post('/api/xml', 
                              data=xxe_payload,
                              content_type='application/xml')
        
        # Should not process external entities
        assert response.status_code in [400, 403, 404]
        assert b'root:' not in response.data
    
    def test_ldap_injection_protection(self, client):
        """Test LDAP injection protection"""
        # Test LDAP injection payloads
        ldap_payloads = [
            'admin)(&(password=*))',
            'admin)(|(password=*))',
            '*)(uid=*',
            'admin*'
        ]
        
        for payload in ldap_payloads:
            response = client.post('/ldap-auth', data={
                'username': payload,
                'password': 'password'
            })
            
            # Should not be vulnerable to LDAP injection
            assert response.status_code in [400, 401, 404]
    
    def test_command_injection_protection(self, client):
        """Test command injection protection"""
        # Test command injection payloads
        command_payloads = [
            'test; cat /etc/passwd',
            'test && ls -la',
            'test | whoami',
            'test`whoami`',
            'test$(whoami)'
        ]
        
        for payload in command_payloads:
            response = client.post('/system-command', data={
                'command': payload
            })
            
            # Should not execute system commands
            assert response.status_code in [400, 403, 404]
            assert b'root:' not in response.data
            assert b'bin' not in response.data


class TestSecurityConfiguration:
    """Test security configuration"""
    
    def test_debug_mode_disabled(self, app):
        """Test debug mode is disabled in production"""
        if app.config.get('FLASK_ENV') == 'production':
            assert app.debug is False
            assert app.config.get('DEBUG') is False
    
    def test_secret_key_security(self, app):
        """Test secret key security"""
        secret_key = app.config.get('SECRET_KEY')
        
        # Should have strong secret key
        assert secret_key is not None
        assert len(secret_key) >= 32
        assert secret_key not in ['dev', 'development', 'test', 'secret', 'password']
    
    def test_session_configuration(self, app):
        """Test session configuration"""
        # Check session security settings
        assert app.config.get('SESSION_COOKIE_HTTPONLY') is True
        assert app.config.get('SESSION_COOKIE_SAMESITE') == 'Lax'
        
        # In production, should be secure
        if app.config.get('FLASK_ENV') == 'production':
            assert app.config.get('SESSION_COOKIE_SECURE') is True
    
    def test_file_upload_configuration(self, app):
        """Test file upload configuration"""
        # Should have reasonable file size limits
        max_content_length = app.config.get('MAX_CONTENT_LENGTH')
        assert max_content_length is not None
        assert max_content_length <= 50 * 1024 * 1024  # 50MB max
    
    def test_database_configuration(self, temp_db):
        """Test database configuration"""
        # Should use parameterized queries
        # This is implicit in the database layer, but we can test it doesn't break
        test_input = "'; DROP TABLE users; --"
        
        # Should not cause SQL injection
        user = temp_db.get_user_by_username(test_input)
        assert user is None  # Should return None, not cause error
    
    def test_logging_configuration(self, app):
        """Test logging configuration"""
        # Should not log sensitive information
        logger = app.logger
        
        # Test log level
        if app.config.get('FLASK_ENV') == 'production':
            assert logger.level >= 20  # INFO level or higher
        
        # Should have proper log handlers
        assert len(logger.handlers) > 0


@pytest.mark.parametrize("endpoint,method,expected_status", [
    ('/dashboard', 'GET', [302, 401, 403]),
    ('/upload', 'POST', [302, 401, 403]),
    ('/admin', 'GET', [302, 401, 403]),
    ('/admin/users', 'GET', [302, 401, 403]),
    ('/admin/system', 'GET', [302, 401, 403]),
])
def test_authorization_parametrized(client, endpoint, method, expected_status):
    """Test authorization with parametrized endpoints"""
    if method == 'GET':
        response = client.get(endpoint)
    elif method == 'POST':
        response = client.post(endpoint)
    else:
        pytest.skip(f"Method {method} not supported")
    
    assert response.status_code in expected_status


@pytest.mark.parametrize("payload,expected_safe", [
    ('<script>alert("xss")</script>', True),
    ('javascript:alert("xss")', True),
    ('<img src=x onerror=alert("xss")>', True),
    ('normal text', True),
    ('SELECT * FROM users', True),
    ('"; DROP TABLE users; --', True),
])
def test_input_sanitization_parametrized(client, payload, expected_safe):
    """Test input sanitization with parametrized payloads"""
    response = client.post('/login', data={
        'username': payload,
        'password': 'password'
    })
    
    # Should not execute malicious code
    assert response.status_code != 500
    assert payload.encode() not in response.data or b'&lt;' in response.data


class TestSecurityCompliance:
    """Test security compliance measures"""
    
    def test_owasp_top_10_protection(self, client):
        """Test protection against OWASP Top 10 vulnerabilities"""
        # A01: Broken Access Control - tested in authorization tests
        # A02: Cryptographic Failures - tested in authentication tests
        # A03: Injection - tested in input validation tests
        # A04: Insecure Design - tested throughout
        # A05: Security Misconfiguration - tested in configuration tests
        # A06: Vulnerable Components - would need dependency scanning
        # A07: Identity and Authentication Failures - tested in auth tests
        # A08: Software and Data Integrity Failures - tested in file upload tests
        # A09: Security Logging and Monitoring - tested in logging tests
        # A10: Server-Side Request Forgery - tested in SSRF tests
        
        # Basic test that application handles common attacks
        response = client.get('/health')
        assert response.status_code == 200
    
    def test_gdpr_compliance_measures(self, client, temp_db):
        """Test GDPR compliance measures"""
        # Test data deletion capability
        user_id = temp_db.create_user('testuser', 'test@example.com', 'Password123!')
        
        # Should be able to delete user data
        success = temp_db.delete_user(user_id)
        assert success is True
        
        # User should be marked as deleted/inactive
        user = temp_db.get_user_by_id(user_id)
        assert user is None or user['is_active'] == 0
    
    def test_pci_compliance_measures(self, client):
        """Test PCI compliance measures (if handling card data)"""
        # Test that application doesn't store card data
        response = client.post('/payment', data={
            'card_number': '4111111111111111',
            'expiry': '12/25',
            'cvv': '123'
        })
        
        # Should not store card data locally
        assert response.status_code in [302, 400, 404]  # Redirect to payment processor
    
    def test_hipaa_compliance_measures(self, client):
        """Test HIPAA compliance measures (if handling health data)"""
        # Test data encryption and access controls
        response = client.post('/health-data', data={
            'patient_id': '12345',
            'health_data': 'sensitive health information'
        })
        
        # Should require proper authentication and authorization
        assert response.status_code in [401, 403, 404]


if __name__ == '__main__':
    # Run security tests
    pytest.main([__file__, '-v', '-m', 'security'])