#!/usr/bin/env python3
"""
Global pytest configuration and fixtures for VectorCraft
Provides test setup, teardown, and common fixtures
"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sqlite3
import secrets
import hashlib

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set test environment variables
os.environ['FLASK_ENV'] = 'testing'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['TESTING'] = 'True'

# Mock sensitive environment variables for testing
os.environ['SMTP_SERVER'] = 'test-smtp.example.com'
os.environ['SMTP_PORT'] = '587'
os.environ['SMTP_USERNAME'] = 'test@example.com'
os.environ['SMTP_PASSWORD'] = 'test-password'
os.environ['FROM_EMAIL'] = 'test@example.com'
os.environ['PAYPAL_CLIENT_ID'] = 'test-paypal-client-id'
os.environ['PAYPAL_CLIENT_SECRET'] = 'test-paypal-client-secret'
os.environ['PAYPAL_ENVIRONMENT'] = 'sandbox'

# Import after setting environment variables
from app import app as flask_app
from database import Database


@pytest.fixture(scope="session")
def app():
    """Create Flask application for testing"""
    # Configure app for testing
    flask_app.config.update({
        'TESTING': True,
        'DEBUG': False,
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
        'SERVER_NAME': 'localhost.localdomain',
        'APPLICATION_ROOT': '/',
        'UPLOAD_FOLDER': tempfile.mkdtemp(),
        'RESULTS_FOLDER': tempfile.mkdtemp(),
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,
        'SECRET_KEY': 'test-secret-key-for-testing-only'
    })
    
    # Create application context
    with flask_app.app_context():
        yield flask_app


@pytest.fixture(scope="function")
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """Create CLI runner for testing Flask commands"""
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def temp_db():
    """Create temporary database for testing"""
    # Create temporary database file
    temp_db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db_file.close()
    
    # Initialize database
    db = Database(temp_db_file.name)
    
    yield db
    
    # Cleanup
    os.unlink(temp_db_file.name)


@pytest.fixture(scope="function")
def db_connection(temp_db):
    """Provide database connection with transaction rollback"""
    conn = sqlite3.connect(temp_db.db_path)
    conn.row_factory = sqlite3.Row
    
    # Start transaction
    conn.execute('BEGIN')
    
    yield conn
    
    # Rollback transaction and close
    conn.rollback()
    conn.close()


@pytest.fixture(scope="function")
def test_user_data():
    """Sample user data for testing"""
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'TestPassword123!',
        'first_name': 'Test',
        'last_name': 'User'
    }


@pytest.fixture(scope="function")
def test_admin_data():
    """Sample admin user data for testing"""
    return {
        'username': 'admin',
        'email': 'admin@example.com',
        'password': 'AdminPassword123!',
        'first_name': 'Admin',
        'last_name': 'User',
        'is_admin': True
    }


@pytest.fixture(scope="function")
def created_user(temp_db, test_user_data):
    """Create a test user in database"""
    user_id = temp_db.create_user(
        username=test_user_data['username'],
        email=test_user_data['email'],
        password=test_user_data['password']
    )
    
    user = temp_db.get_user_by_id(user_id)
    return user


@pytest.fixture(scope="function")
def authenticated_client(client, created_user):
    """Client with authenticated user session"""
    with client.session_transaction() as sess:
        sess['user_id'] = created_user['id']
        sess['username'] = created_user['username']
        sess['_fresh'] = True
    
    return client


@pytest.fixture(scope="function")
def mock_email_service():
    """Mock email service for testing"""
    with patch('services.email_service.email_service') as mock:
        mock.send_credentials_email.return_value = True
        mock.send_notification_email.return_value = True
        mock.test_connection.return_value = True
        yield mock


@pytest.fixture(scope="function")
def mock_paypal_service():
    """Mock PayPal service for testing"""
    with patch('services.paypal_service.paypal_service') as mock:
        mock.create_payment.return_value = {
            'id': 'test-payment-id',
            'approval_url': 'https://paypal.com/test-approval'
        }
        mock.execute_payment.return_value = {
            'id': 'test-payment-id',
            'state': 'approved',
            'payer': {'payer_info': {'email': 'test@example.com'}},
            'transactions': [{'amount': {'total': '49.00', 'currency': 'USD'}}]
        }
        mock.get_payment_status.return_value = {'state': 'approved'}
        yield mock


@pytest.fixture(scope="function")
def mock_vectorization_service():
    """Mock vectorization service for testing"""
    with patch('services.vectorization_service') as mock:
        mock.vectorize_image.return_value = {
            'success': True,
            'result_path': '/tmp/test-result.svg',
            'processing_time': 1.5
        }
        yield mock


@pytest.fixture(scope="function")
def test_image_file():
    """Create test image file for upload testing"""
    from PIL import Image
    import io
    
    # Create a simple test image
    image = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    image.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes


@pytest.fixture(scope="function")
def test_image_files():
    """Create multiple test image files"""
    files = {}
    
    # Create different test images
    for name, color in [('red', 'red'), ('blue', 'blue'), ('green', 'green')]:
        from PIL import Image
        import io
        
        image = Image.new('RGB', (100, 100), color=color)
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        files[name] = img_bytes
    
    return files


@pytest.fixture(scope="function")
def temp_upload_dir():
    """Create temporary upload directory"""
    upload_dir = tempfile.mkdtemp()
    yield upload_dir
    shutil.rmtree(upload_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def mock_file_service():
    """Mock file service for testing"""
    with patch('services.file_service') as mock:
        mock.save_uploaded_file.return_value = '/tmp/test-upload.png'
        mock.validate_file.return_value = True
        mock.get_file_info.return_value = {
            'size': 1024,
            'type': 'image/png',
            'name': 'test.png'
        }
        yield mock


@pytest.fixture(scope="function")
def mock_security_service():
    """Mock security service for testing"""
    with patch('services.security_service.security_service') as mock:
        mock.validate_file_upload.return_value = True
        mock.scan_for_malware.return_value = True
        mock.check_rate_limit.return_value = False
        mock.log_security_event.return_value = None
        yield mock


@pytest.fixture(scope="function")
def mock_monitoring_services():
    """Mock monitoring services for testing"""
    with patch('services.monitoring.health_monitor') as health_mock, \
         patch('services.monitoring.system_logger') as logger_mock, \
         patch('services.monitoring.alert_manager') as alert_mock:
        
        health_mock.check_database_health.return_value = {'status': 'healthy'}
        health_mock.check_email_service.return_value = {'status': 'healthy'}
        health_mock.check_paypal_service.return_value = {'status': 'healthy'}
        health_mock.get_system_metrics.return_value = {'cpu': 50, 'memory': 60}
        
        logger_mock.log_event.return_value = None
        logger_mock.get_recent_logs.return_value = []
        
        alert_mock.check_alerts.return_value = []
        alert_mock.create_alert.return_value = None
        
        yield {
            'health_monitor': health_mock,
            'system_logger': logger_mock,
            'alert_manager': alert_mock
        }


@pytest.fixture(scope="function")
def sample_transaction_data():
    """Sample transaction data for testing"""
    return {
        'transaction_id': 'test-txn-123',
        'email': 'test@example.com',
        'username': 'testuser',
        'amount': 49.00,
        'currency': 'USD',
        'paypal_order_id': 'test-order-123',
        'paypal_payment_id': 'test-payment-123',
        'status': 'completed'
    }


@pytest.fixture(scope="function")
def mock_datetime():
    """Mock datetime for consistent testing"""
    test_datetime = datetime(2023, 1, 1, 12, 0, 0)
    with patch('datetime.datetime') as mock:
        mock.now.return_value = test_datetime
        mock.utcnow.return_value = test_datetime
        yield mock


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Cleanup temporary files after each test"""
    yield
    
    # Clean up any temporary files in upload/results folders
    for folder in ['uploads', 'results', 'output']:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass


@pytest.fixture(scope="function")
def performance_monitor():
    """Monitor performance metrics during tests"""
    import time
    import psutil
    
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss
    
    yield
    
    end_time = time.time()
    end_memory = psutil.Process().memory_info().rss
    
    execution_time = end_time - start_time
    memory_usage = end_memory - start_memory
    
    # Log performance metrics
    print(f"Test execution time: {execution_time:.2f}s")
    print(f"Memory usage: {memory_usage / 1024 / 1024:.2f}MB")


# Test data generators
def generate_test_users(count=10):
    """Generate multiple test users"""
    users = []
    for i in range(count):
        users.append({
            'username': f'testuser{i}',
            'email': f'test{i}@example.com',
            'password': f'TestPassword{i}!',
            'first_name': f'Test{i}',
            'last_name': f'User{i}'
        })
    return users


def generate_test_transactions(count=10):
    """Generate multiple test transactions"""
    transactions = []
    for i in range(count):
        transactions.append({
            'transaction_id': f'test-txn-{i}',
            'email': f'test{i}@example.com',
            'username': f'testuser{i}',
            'amount': 49.00 + i,
            'currency': 'USD',
            'paypal_order_id': f'test-order-{i}',
            'paypal_payment_id': f'test-payment-{i}',
            'status': 'completed'
        })
    return transactions


# Test utilities
class TestUtils:
    """Utility functions for testing"""
    
    @staticmethod
    def create_test_image(width=100, height=100, color='red', format='PNG'):
        """Create test image in memory"""
        from PIL import Image
        import io
        
        image = Image.new('RGB', (width, height), color=color)
        img_bytes = io.BytesIO()
        image.save(img_bytes, format=format)
        img_bytes.seek(0)
        return img_bytes
    
    @staticmethod
    def hash_password(password, salt=None):
        """Hash password for testing"""
        if salt is None:
            salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return password_hash.hex(), salt
    
    @staticmethod
    def create_test_svg():
        """Create test SVG content"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect width="100" height="100" fill="red"/>
</svg>'''
    
    @staticmethod
    def assert_response_success(response, expected_status=200):
        """Assert response is successful"""
        assert response.status_code == expected_status
        assert response.is_json or response.mimetype == 'text/html'
    
    @staticmethod
    def assert_json_response(response, expected_keys=None):
        """Assert JSON response format"""
        assert response.is_json
        data = response.get_json()
        if expected_keys:
            for key in expected_keys:
                assert key in data
        return data
    
    @staticmethod
    def assert_redirect_response(response, expected_location=None):
        """Assert redirect response"""
        assert response.status_code in [301, 302, 303, 307, 308]
        if expected_location:
            assert expected_location in response.location


# Export TestUtils for use in tests
pytest.test_utils = TestUtils


# Database test helpers
@pytest.fixture(scope="function")
def db_test_helpers(temp_db):
    """Database testing helper functions"""
    
    class DBTestHelpers:
        def __init__(self, db):
            self.db = db
        
        def count_users(self):
            """Count users in database"""
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM users")
                return cursor.fetchone()[0]
        
        def count_transactions(self):
            """Count transactions in database"""
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM transactions")
                return cursor.fetchone()[0]
        
        def get_user_by_email(self, email):
            """Get user by email"""
            return self.db.get_user_by_email(email)
        
        def clear_all_data(self):
            """Clear all test data"""
            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute("DELETE FROM users")
                conn.execute("DELETE FROM transactions")
                conn.execute("DELETE FROM system_logs")
                conn.commit()
    
    return DBTestHelpers(temp_db)


# Performance testing helpers
@pytest.fixture(scope="function")
def performance_test_helpers():
    """Performance testing utilities"""
    
    class PerformanceTestHelpers:
        def __init__(self):
            self.start_time = None
            self.metrics = {}
        
        def start_timer(self):
            """Start performance timer"""
            import time
            self.start_time = time.time()
        
        def end_timer(self, test_name):
            """End performance timer and record metric"""
            import time
            if self.start_time:
                elapsed = time.time() - self.start_time
                self.metrics[test_name] = elapsed
                return elapsed
            return None
        
        def assert_performance(self, test_name, max_time):
            """Assert performance meets requirements"""
            if test_name in self.metrics:
                assert self.metrics[test_name] <= max_time, \
                    f"Test {test_name} took {self.metrics[test_name]:.2f}s, expected <= {max_time}s"
        
        def get_metrics(self):
            """Get all performance metrics"""
            return self.metrics.copy()
    
    return PerformanceTestHelpers()


# Security testing helpers
@pytest.fixture(scope="function")
def security_test_helpers():
    """Security testing utilities"""
    
    class SecurityTestHelpers:
        @staticmethod
        def create_malicious_file():
            """Create test file with malicious content"""
            import io
            content = b'<script>alert("xss")</script>'
            return io.BytesIO(content)
        
        @staticmethod
        def create_large_file(size_mb=20):
            """Create large file for testing upload limits"""
            import io
            content = b'x' * (size_mb * 1024 * 1024)
            return io.BytesIO(content)
        
        @staticmethod
        def generate_sql_injection_strings():
            """Generate SQL injection test strings"""
            return [
                "'; DROP TABLE users; --",
                "1' OR '1'='1",
                "admin'--",
                "1' UNION SELECT * FROM users--"
            ]
        
        @staticmethod
        def generate_xss_strings():
            """Generate XSS test strings"""
            return [
                "<script>alert('xss')</script>",
                "javascript:alert('xss')",
                "<img src=x onerror=alert('xss')>",
                "&#60;script&#62;alert('xss')&#60;/script&#62;"
            ]
    
    return SecurityTestHelpers()


# Configure pytest-html for better reporting
def pytest_configure(config):
    """Configure pytest with custom settings"""
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers"""
    for item in items:
        # Add markers based on test file names
        if "test_unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
        elif "test_auth" in item.nodeid:
            item.add_marker(pytest.mark.auth)
        elif "test_api" in item.nodeid:
            item.add_marker(pytest.mark.api)
        elif "test_performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)
        elif "test_security" in item.nodeid:
            item.add_marker(pytest.mark.security)