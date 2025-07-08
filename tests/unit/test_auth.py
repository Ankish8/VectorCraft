#!/usr/bin/env python3
"""
Unit tests for authentication system
Tests user registration, login, password handling, and session management
"""

import pytest
import hashlib
import secrets
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

from database import Database
from services.auth_service import AuthService
from services.security_service import SecurityService


class TestAuthService:
    """Test authentication service functionality"""
    
    def test_create_user_success(self, temp_db, test_user_data):
        """Test successful user creation"""
        auth_service = AuthService(temp_db)
        
        user_id = auth_service.create_user(
            username=test_user_data['username'],
            email=test_user_data['email'],
            password=test_user_data['password']
        )
        
        assert user_id is not None
        assert isinstance(user_id, int)
        
        # Verify user was created
        user = temp_db.get_user_by_id(user_id)
        assert user is not None
        assert user['username'] == test_user_data['username']
        assert user['email'] == test_user_data['email']
        assert user['password_hash'] is not None
        assert user['salt'] is not None
        assert user['created_at'] is not None
        assert user['is_active'] == 1
    
    def test_create_user_duplicate_username(self, temp_db, test_user_data):
        """Test user creation with duplicate username"""
        auth_service = AuthService(temp_db)
        
        # Create first user
        user_id1 = auth_service.create_user(
            username=test_user_data['username'],
            email=test_user_data['email'],
            password=test_user_data['password']
        )
        assert user_id1 is not None
        
        # Try to create user with same username
        with pytest.raises(ValueError, match="Username already exists"):
            auth_service.create_user(
                username=test_user_data['username'],
                email="different@example.com",
                password=test_user_data['password']
            )
    
    def test_create_user_duplicate_email(self, temp_db, test_user_data):
        """Test user creation with duplicate email"""
        auth_service = AuthService(temp_db)
        
        # Create first user
        user_id1 = auth_service.create_user(
            username=test_user_data['username'],
            email=test_user_data['email'],
            password=test_user_data['password']
        )
        assert user_id1 is not None
        
        # Try to create user with same email
        with pytest.raises(ValueError, match="Email already exists"):
            auth_service.create_user(
                username="different_user",
                email=test_user_data['email'],
                password=test_user_data['password']
            )
    
    def test_create_user_invalid_password(self, temp_db, test_user_data):
        """Test user creation with invalid password"""
        auth_service = AuthService(temp_db)
        
        # Test weak password
        with pytest.raises(ValueError, match="Password must be at least 8 characters"):
            auth_service.create_user(
                username=test_user_data['username'],
                email=test_user_data['email'],
                password="weak"
            )
        
        # Test password without uppercase
        with pytest.raises(ValueError, match="Password must contain"):
            auth_service.create_user(
                username=test_user_data['username'],
                email=test_user_data['email'],
                password="weakpassword123"
            )
        
        # Test password without numbers
        with pytest.raises(ValueError, match="Password must contain"):
            auth_service.create_user(
                username=test_user_data['username'],
                email=test_user_data['email'],
                password="WeakPassword"
            )
    
    def test_authenticate_user_success(self, temp_db, created_user, test_user_data):
        """Test successful user authentication"""
        auth_service = AuthService(temp_db)
        
        authenticated_user = auth_service.authenticate_user(
            username=test_user_data['username'],
            password=test_user_data['password']
        )
        
        assert authenticated_user is not None
        assert authenticated_user['id'] == created_user['id']
        assert authenticated_user['username'] == test_user_data['username']
        assert authenticated_user['email'] == test_user_data['email']
        assert authenticated_user['is_active'] == 1
    
    def test_authenticate_user_invalid_username(self, temp_db, test_user_data):
        """Test authentication with invalid username"""
        auth_service = AuthService(temp_db)
        
        authenticated_user = auth_service.authenticate_user(
            username="nonexistent",
            password=test_user_data['password']
        )
        
        assert authenticated_user is None
    
    def test_authenticate_user_invalid_password(self, temp_db, created_user, test_user_data):
        """Test authentication with invalid password"""
        auth_service = AuthService(temp_db)
        
        authenticated_user = auth_service.authenticate_user(
            username=test_user_data['username'],
            password="wrong_password"
        )
        
        assert authenticated_user is None
    
    def test_authenticate_user_inactive_account(self, temp_db, created_user, test_user_data):
        """Test authentication with inactive account"""
        auth_service = AuthService(temp_db)
        
        # Deactivate user
        temp_db.update_user(created_user['id'], {'is_active': 0})
        
        authenticated_user = auth_service.authenticate_user(
            username=test_user_data['username'],
            password=test_user_data['password']
        )
        
        assert authenticated_user is None
    
    def test_update_last_login(self, temp_db, created_user):
        """Test updating last login timestamp"""
        auth_service = AuthService(temp_db)
        
        # Mock current time
        test_time = datetime.now()
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_time
            
            auth_service.update_last_login(created_user['id'])
            
            # Verify last login was updated
            user = temp_db.get_user_by_id(created_user['id'])
            assert user['last_login'] is not None
    
    def test_change_password_success(self, temp_db, created_user, test_user_data):
        """Test successful password change"""
        auth_service = AuthService(temp_db)
        
        new_password = "NewPassword123!"
        
        success = auth_service.change_password(
            user_id=created_user['id'],
            old_password=test_user_data['password'],
            new_password=new_password
        )
        
        assert success is True
        
        # Verify old password no longer works
        authenticated_user = auth_service.authenticate_user(
            username=test_user_data['username'],
            password=test_user_data['password']
        )
        assert authenticated_user is None
        
        # Verify new password works
        authenticated_user = auth_service.authenticate_user(
            username=test_user_data['username'],
            password=new_password
        )
        assert authenticated_user is not None
    
    def test_change_password_invalid_old_password(self, temp_db, created_user):
        """Test password change with invalid old password"""
        auth_service = AuthService(temp_db)
        
        success = auth_service.change_password(
            user_id=created_user['id'],
            old_password="wrong_old_password",
            new_password="NewPassword123!"
        )
        
        assert success is False
    
    def test_change_password_invalid_new_password(self, temp_db, created_user, test_user_data):
        """Test password change with invalid new password"""
        auth_service = AuthService(temp_db)
        
        with pytest.raises(ValueError, match="Password must be at least 8 characters"):
            auth_service.change_password(
                user_id=created_user['id'],
                old_password=test_user_data['password'],
                new_password="weak"
            )
    
    def test_validate_email_format(self, temp_db):
        """Test email format validation"""
        auth_service = AuthService(temp_db)
        
        # Valid emails
        assert auth_service.validate_email("test@example.com") is True
        assert auth_service.validate_email("user.name@domain.co.uk") is True
        assert auth_service.validate_email("user+tag@example.org") is True
        
        # Invalid emails
        assert auth_service.validate_email("invalid_email") is False
        assert auth_service.validate_email("@example.com") is False
        assert auth_service.validate_email("test@") is False
        assert auth_service.validate_email("test@.com") is False
    
    def test_validate_username_format(self, temp_db):
        """Test username format validation"""
        auth_service = AuthService(temp_db)
        
        # Valid usernames
        assert auth_service.validate_username("validuser") is True
        assert auth_service.validate_username("user123") is True
        assert auth_service.validate_username("user_name") is True
        
        # Invalid usernames
        assert auth_service.validate_username("a") is False  # Too short
        assert auth_service.validate_username("a" * 51) is False  # Too long
        assert auth_service.validate_username("user@name") is False  # Invalid characters
        assert auth_service.validate_username("user name") is False  # Spaces
    
    def test_password_strength_validation(self, temp_db):
        """Test password strength validation"""
        auth_service = AuthService(temp_db)
        
        # Valid passwords
        assert auth_service.validate_password_strength("ValidPassword123!") is True
        assert auth_service.validate_password_strength("Another@Pass1") is True
        
        # Invalid passwords
        assert auth_service.validate_password_strength("weak") is False  # Too short
        assert auth_service.validate_password_strength("weakpassword") is False  # No uppercase/numbers
        assert auth_service.validate_password_strength("WEAKPASSWORD") is False  # No lowercase/numbers
        assert auth_service.validate_password_strength("WeakPassword") is False  # No numbers
        assert auth_service.validate_password_strength("weakpassword123") is False  # No uppercase
    
    def test_generate_secure_password(self, temp_db):
        """Test secure password generation"""
        auth_service = AuthService(temp_db)
        
        password = auth_service.generate_secure_password()
        
        assert len(password) >= 12
        assert auth_service.validate_password_strength(password) is True
        
        # Test multiple generations are different
        password2 = auth_service.generate_secure_password()
        assert password != password2
    
    def test_hash_password_consistency(self, temp_db):
        """Test password hashing consistency"""
        auth_service = AuthService(temp_db)
        
        password = "TestPassword123!"
        salt = "test_salt"
        
        # Hash same password multiple times
        hash1 = auth_service.hash_password(password, salt)
        hash2 = auth_service.hash_password(password, salt)
        
        assert hash1 == hash2
        
        # Different salt should produce different hash
        hash3 = auth_service.hash_password(password, "different_salt")
        assert hash1 != hash3
    
    def test_verify_password_hash(self, temp_db):
        """Test password hash verification"""
        auth_service = AuthService(temp_db)
        
        password = "TestPassword123!"
        salt = "test_salt"
        password_hash = auth_service.hash_password(password, salt)
        
        # Correct password should verify
        assert auth_service.verify_password_hash(password, password_hash, salt) is True
        
        # Wrong password should not verify
        assert auth_service.verify_password_hash("wrong_password", password_hash, salt) is False
    
    @patch('services.auth_service.secrets.token_hex')
    def test_generate_salt(self, mock_token_hex, temp_db):
        """Test salt generation"""
        auth_service = AuthService(temp_db)
        
        mock_token_hex.return_value = "test_salt"
        
        salt = auth_service.generate_salt()
        
        assert salt == "test_salt"
        mock_token_hex.assert_called_once_with(16)
    
    def test_check_rate_limiting(self, temp_db):
        """Test rate limiting for authentication attempts"""
        auth_service = AuthService(temp_db)
        
        ip_address = "192.168.1.1"
        
        # First few attempts should not be rate limited
        for i in range(5):
            assert auth_service.check_rate_limit(ip_address) is False
            auth_service.record_failed_attempt(ip_address)
        
        # After max attempts, should be rate limited
        assert auth_service.check_rate_limit(ip_address) is True
    
    def test_clear_rate_limiting(self, temp_db):
        """Test clearing rate limiting"""
        auth_service = AuthService(temp_db)
        
        ip_address = "192.168.1.1"
        
        # Trigger rate limiting
        for i in range(6):
            auth_service.record_failed_attempt(ip_address)
        
        assert auth_service.check_rate_limit(ip_address) is True
        
        # Clear rate limiting
        auth_service.clear_rate_limit(ip_address)
        assert auth_service.check_rate_limit(ip_address) is False


class TestPasswordSecurity:
    """Test password security features"""
    
    def test_password_hashing_algorithm(self):
        """Test password hashing uses secure algorithm"""
        password = "TestPassword123!"
        salt = "test_salt"
        
        # Test PBKDF2 with SHA256
        expected_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        ).hex()
        
        auth_service = AuthService(None)
        actual_hash = auth_service.hash_password(password, salt)
        
        assert actual_hash == expected_hash
    
    def test_password_salt_uniqueness(self):
        """Test password salts are unique"""
        auth_service = AuthService(None)
        
        salts = [auth_service.generate_salt() for _ in range(100)]
        
        # All salts should be unique
        assert len(set(salts)) == 100
    
    def test_password_complexity_requirements(self):
        """Test password complexity requirements"""
        auth_service = AuthService(None)
        
        # Test various password patterns
        test_cases = [
            ("Password123!", True),   # Valid
            ("password123!", False),  # No uppercase
            ("PASSWORD123!", False),  # No lowercase
            ("Password!", False),     # No numbers
            ("Password123", False),   # No special characters
            ("Pass123!", False),      # Too short
            ("VeryLongPasswordWithoutNumbers!", False),  # No numbers
            ("VeryLongPasswordWithNumbers123!", True),   # Valid long password
        ]
        
        for password, expected in test_cases:
            result = auth_service.validate_password_strength(password)
            assert result == expected, f"Password '{password}' should be {expected}"
    
    def test_secure_password_generation(self):
        """Test secure password generation"""
        auth_service = AuthService(None)
        
        passwords = [auth_service.generate_secure_password() for _ in range(10)]
        
        # All passwords should be unique
        assert len(set(passwords)) == 10
        
        # All passwords should meet complexity requirements
        for password in passwords:
            assert auth_service.validate_password_strength(password) is True
            assert len(password) >= 12
            assert any(c.isupper() for c in password)
            assert any(c.islower() for c in password)
            assert any(c.isdigit() for c in password)
            assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)


class TestSessionManagement:
    """Test session management functionality"""
    
    def test_create_session(self, temp_db, created_user):
        """Test session creation"""
        auth_service = AuthService(temp_db)
        
        session_id = auth_service.create_session(created_user['id'])
        
        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) > 0
    
    def test_validate_session(self, temp_db, created_user):
        """Test session validation"""
        auth_service = AuthService(temp_db)
        
        session_id = auth_service.create_session(created_user['id'])
        
        # Valid session should return user
        user = auth_service.validate_session(session_id)
        assert user is not None
        assert user['id'] == created_user['id']
        
        # Invalid session should return None
        invalid_user = auth_service.validate_session("invalid_session")
        assert invalid_user is None
    
    def test_invalidate_session(self, temp_db, created_user):
        """Test session invalidation"""
        auth_service = AuthService(temp_db)
        
        session_id = auth_service.create_session(created_user['id'])
        
        # Session should be valid initially
        user = auth_service.validate_session(session_id)
        assert user is not None
        
        # Invalidate session
        auth_service.invalidate_session(session_id)
        
        # Session should be invalid after invalidation
        user = auth_service.validate_session(session_id)
        assert user is None
    
    def test_session_timeout(self, temp_db, created_user):
        """Test session timeout"""
        auth_service = AuthService(temp_db)
        
        # Create session with short timeout
        session_id = auth_service.create_session(created_user['id'], timeout=1)
        
        # Session should be valid initially
        user = auth_service.validate_session(session_id)
        assert user is not None
        
        # Mock time passing
        with patch('time.time') as mock_time:
            mock_time.return_value = time.time() + 3600  # 1 hour later
            
            # Session should be invalid after timeout
            user = auth_service.validate_session(session_id)
            assert user is None
    
    def test_cleanup_expired_sessions(self, temp_db, created_user):
        """Test cleanup of expired sessions"""
        auth_service = AuthService(temp_db)
        
        # Create multiple sessions
        session_ids = []
        for i in range(5):
            session_id = auth_service.create_session(created_user['id'])
            session_ids.append(session_id)
        
        # Mock time passing to expire sessions
        with patch('time.time') as mock_time:
            mock_time.return_value = time.time() + 3600  # 1 hour later
            
            # Run cleanup
            cleaned_count = auth_service.cleanup_expired_sessions()
            
            # All sessions should be cleaned up
            assert cleaned_count == 5
            
            # All sessions should be invalid
            for session_id in session_ids:
                user = auth_service.validate_session(session_id)
                assert user is None


class TestAuthenticationMiddleware:
    """Test authentication middleware functionality"""
    
    def test_require_auth_decorator(self, client, created_user):
        """Test authentication requirement decorator"""
        from flask import session
        
        # Test protected route without authentication
        response = client.get('/dashboard')
        assert response.status_code == 302  # Redirect to login
        
        # Test protected route with authentication
        with client.session_transaction() as sess:
            sess['user_id'] = created_user['id']
            sess['username'] = created_user['username']
        
        response = client.get('/dashboard')
        assert response.status_code == 200
    
    def test_login_required_flash_message(self, client):
        """Test login required flash message"""
        response = client.get('/dashboard', follow_redirects=True)
        
        # Should redirect to login with flash message
        assert b'Please log in to access this page' in response.data
    
    def test_csrf_protection(self, client):
        """Test CSRF protection for forms"""
        # Test form submission without CSRF token
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        })
        
        # Should be rejected due to missing CSRF token
        assert response.status_code == 400
    
    def test_rate_limiting_login(self, client):
        """Test rate limiting for login attempts"""
        # Make multiple failed login attempts
        for i in range(6):
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'wrong_password'
            })
        
        # Should be rate limited after max attempts
        assert response.status_code == 429  # Too Many Requests
    
    def test_secure_session_cookies(self, app):
        """Test secure session cookie configuration"""
        assert app.config['SESSION_COOKIE_HTTPONLY'] is True
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
        
        # In production, should also be secure
        if app.config.get('FLASK_ENV') == 'production':
            assert app.config['SESSION_COOKIE_SECURE'] is True


@pytest.mark.parametrize("username,email,password,expected_error", [
    ("", "test@example.com", "ValidPass123!", "Username is required"),
    ("testuser", "", "ValidPass123!", "Email is required"),
    ("testuser", "test@example.com", "", "Password is required"),
    ("ab", "test@example.com", "ValidPass123!", "Username must be at least 3 characters"),
    ("testuser", "invalid_email", "ValidPass123!", "Invalid email format"),
    ("testuser", "test@example.com", "weak", "Password must be at least 8 characters"),
])
def test_registration_validation(temp_db, username, email, password, expected_error):
    """Test registration validation with various invalid inputs"""
    auth_service = AuthService(temp_db)
    
    with pytest.raises(ValueError, match=expected_error):
        auth_service.create_user(username, email, password)


@pytest.mark.parametrize("test_input,expected", [
    ("test@example.com", True),
    ("user.name@domain.co.uk", True),
    ("user+tag@example.org", True),
    ("test@sub.domain.com", True),
    ("invalid_email", False),
    ("@example.com", False),
    ("test@", False),
    ("test@.com", False),
    ("test.example.com", False),
])
def test_email_validation_parametrized(temp_db, test_input, expected):
    """Test email validation with various inputs"""
    auth_service = AuthService(temp_db)
    assert auth_service.validate_email(test_input) == expected


class TestDatabaseIntegration:
    """Test authentication with database integration"""
    
    def test_user_persistence(self, temp_db, test_user_data):
        """Test user data persistence in database"""
        auth_service = AuthService(temp_db)
        
        # Create user
        user_id = auth_service.create_user(
            username=test_user_data['username'],
            email=test_user_data['email'],
            password=test_user_data['password']
        )
        
        # Verify user exists in database
        user = temp_db.get_user_by_id(user_id)
        assert user is not None
        assert user['username'] == test_user_data['username']
        assert user['email'] == test_user_data['email']
        
        # Verify password is hashed
        assert user['password_hash'] != test_user_data['password']
        assert len(user['password_hash']) > 0
        assert len(user['salt']) > 0
    
    def test_concurrent_user_creation(self, temp_db):
        """Test concurrent user creation scenarios"""
        auth_service = AuthService(temp_db)
        
        # Simulate concurrent creation of users with same username
        import threading
        import time
        
        results = []
        errors = []
        
        def create_user_thread(username, email, password):
            try:
                user_id = auth_service.create_user(username, email, password)
                results.append(user_id)
            except Exception as e:
                errors.append(str(e))
        
        # Create two threads trying to create same user
        thread1 = threading.Thread(target=create_user_thread, 
                                  args=("sameuser", "user1@example.com", "Password123!"))
        thread2 = threading.Thread(target=create_user_thread, 
                                  args=("sameuser", "user2@example.com", "Password123!"))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # One should succeed, one should fail
        assert len(results) == 1
        assert len(errors) == 1
        assert "Username already exists" in errors[0]
    
    def test_database_transaction_rollback(self, temp_db):
        """Test database transaction rollback on errors"""
        auth_service = AuthService(temp_db)
        
        # Mock database error during user creation
        with patch.object(temp_db, 'execute_query') as mock_execute:
            mock_execute.side_effect = Exception("Database error")
            
            with pytest.raises(Exception):
                auth_service.create_user("testuser", "test@example.com", "Password123!")
            
            # Verify no partial data was saved
            user = temp_db.get_user_by_username("testuser")
            assert user is None