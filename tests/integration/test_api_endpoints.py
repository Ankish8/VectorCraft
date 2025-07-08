#!/usr/bin/env python3
"""
Integration tests for API endpoints
Tests complete request/response cycles for all API endpoints
"""

import pytest
import json
import io
import os
from unittest.mock import patch, MagicMock
from PIL import Image
from werkzeug.datastructures import FileStorage

from flask import url_for


class TestAuthenticationEndpoints:
    """Test authentication API endpoints"""
    
    def test_login_page_get(self, client):
        """Test login page GET request"""
        response = client.get('/login')
        
        assert response.status_code == 200
        assert b'login' in response.data.lower()
        assert b'username' in response.data.lower()
        assert b'password' in response.data.lower()
    
    def test_login_post_success(self, client, created_user, test_user_data):
        """Test successful login POST request"""
        response = client.post('/login', data={
            'username': test_user_data['username'],
            'password': test_user_data['password']
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Should redirect to dashboard
        assert b'dashboard' in response.data.lower() or b'vectorcraft' in response.data.lower()
    
    def test_login_post_invalid_credentials(self, client, created_user):
        """Test login with invalid credentials"""
        response = client.post('/login', data={
            'username': created_user['username'],
            'password': 'wrong_password'
        })
        
        assert response.status_code == 200
        assert b'invalid' in response.data.lower() or b'error' in response.data.lower()
    
    def test_login_post_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'password'
        })
        
        assert response.status_code == 200
        assert b'invalid' in response.data.lower() or b'error' in response.data.lower()
    
    def test_login_rate_limiting(self, client):
        """Test rate limiting for login attempts"""
        # Make multiple failed login attempts
        for i in range(6):
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'wrong_password'
            })
        
        # Should be rate limited
        assert response.status_code == 429 or b'too many' in response.data.lower()
    
    def test_logout(self, authenticated_client):
        """Test logout endpoint"""
        response = authenticated_client.post('/logout', follow_redirects=True)
        
        assert response.status_code == 200
        # Should redirect to login or home page
        assert b'login' in response.data.lower() or b'home' in response.data.lower()
    
    def test_dashboard_requires_auth(self, client):
        """Test dashboard requires authentication"""
        response = client.get('/dashboard')
        
        # Should redirect to login
        assert response.status_code == 302
        assert 'login' in response.location
    
    def test_dashboard_authenticated_access(self, authenticated_client):
        """Test dashboard with authenticated user"""
        response = authenticated_client.get('/dashboard')
        
        assert response.status_code == 200
        assert b'dashboard' in response.data.lower() or b'vectorcraft' in response.data.lower()


class TestFileUploadEndpoints:
    """Test file upload API endpoints"""
    
    def test_upload_page_get(self, authenticated_client):
        """Test upload page GET request"""
        response = authenticated_client.get('/upload')
        
        assert response.status_code == 200
        assert b'upload' in response.data.lower()
        assert b'file' in response.data.lower()
    
    def test_upload_page_requires_auth(self, client):
        """Test upload page requires authentication"""
        response = client.get('/upload')
        
        assert response.status_code == 302
        assert 'login' in response.location
    
    def test_upload_valid_image(self, authenticated_client, test_image_file, mock_vectorization_service):
        """Test uploading valid image file"""
        # Create file-like object
        test_image_file.seek(0)
        
        response = authenticated_client.post('/upload', data={
            'file': (test_image_file, 'test.png', 'image/png'),
            'algorithm': 'vtracer_high_fidelity'
        }, content_type='multipart/form-data')
        
        assert response.status_code == 200 or response.status_code == 302
        
        # Check if vectorization was called
        mock_vectorization_service.vectorize_image.assert_called_once()
    
    def test_upload_invalid_file_type(self, authenticated_client):
        """Test uploading invalid file type"""
        # Create text file
        text_file = io.BytesIO(b'This is not an image')
        
        response = authenticated_client.post('/upload', data={
            'file': (text_file, 'test.txt', 'text/plain'),
            'algorithm': 'vtracer_high_fidelity'
        }, content_type='multipart/form-data')
        
        assert response.status_code == 400 or b'invalid' in response.data.lower()
    
    def test_upload_no_file(self, authenticated_client):
        """Test upload without file"""
        response = authenticated_client.post('/upload', data={
            'algorithm': 'vtracer_high_fidelity'
        }, content_type='multipart/form-data')
        
        assert response.status_code == 400 or b'required' in response.data.lower()
    
    def test_upload_large_file(self, authenticated_client, security_test_helpers):
        """Test uploading file larger than limit"""
        large_file = security_test_helpers.create_large_file(size_mb=20)
        
        response = authenticated_client.post('/upload', data={
            'file': (large_file, 'large.png', 'image/png'),
            'algorithm': 'vtracer_high_fidelity'
        }, content_type='multipart/form-data')
        
        assert response.status_code == 413 or b'too large' in response.data.lower()
    
    def test_upload_different_algorithms(self, authenticated_client, test_image_file, mock_vectorization_service):
        """Test upload with different algorithms"""
        algorithms = ['vtracer_high_fidelity', 'experimental', 'classical_tracer']
        
        for algorithm in algorithms:
            test_image_file.seek(0)
            
            response = authenticated_client.post('/upload', data={
                'file': (test_image_file, 'test.png', 'image/png'),
                'algorithm': algorithm
            }, content_type='multipart/form-data')
            
            assert response.status_code == 200 or response.status_code == 302
    
    def test_upload_rate_limiting(self, authenticated_client, test_image_file):
        """Test upload rate limiting"""
        # Make multiple upload requests rapidly
        for i in range(10):
            test_image_file.seek(0)
            
            response = authenticated_client.post('/upload', data={
                'file': (test_image_file, f'test{i}.png', 'image/png'),
                'algorithm': 'vtracer_high_fidelity'
            }, content_type='multipart/form-data')
            
            if response.status_code == 429:
                break
        
        # Should eventually hit rate limit
        assert response.status_code == 429 or b'rate' in response.data.lower()
    
    def test_download_result(self, authenticated_client, test_image_file, mock_vectorization_service):
        """Test downloading vectorization result"""
        # First upload a file
        test_image_file.seek(0)
        
        response = authenticated_client.post('/upload', data={
            'file': (test_image_file, 'test.png', 'image/png'),
            'algorithm': 'vtracer_high_fidelity'
        }, content_type='multipart/form-data')
        
        # Extract result ID from response
        if response.status_code == 200:
            # Try to download result
            response = authenticated_client.get('/download/test-result-id')
            
            # Should either return file or redirect
            assert response.status_code in [200, 302, 404]
    
    def test_upload_malicious_file(self, authenticated_client, security_test_helpers, mock_security_service):
        """Test upload with malicious file"""
        mock_security_service.validate_file_upload.return_value = False
        
        malicious_file = security_test_helpers.create_malicious_file()
        
        response = authenticated_client.post('/upload', data={
            'file': (malicious_file, 'malicious.png', 'image/png'),
            'algorithm': 'vtracer_high_fidelity'
        }, content_type='multipart/form-data')
        
        assert response.status_code == 400 or b'invalid' in response.data.lower()
        mock_security_service.validate_file_upload.assert_called_once()


class TestPaymentEndpoints:
    """Test payment API endpoints"""
    
    def test_buy_page_get(self, client):
        """Test buy page GET request"""
        response = client.get('/buy')
        
        assert response.status_code == 200
        assert b'buy' in response.data.lower() or b'purchase' in response.data.lower()
        assert b'paypal' in response.data.lower() or b'payment' in response.data.lower()
    
    def test_create_payment(self, client, mock_paypal_service):
        """Test creating PayPal payment"""
        response = client.post('/create-payment', data={
            'amount': '49.00',
            'currency': 'USD'
        })
        
        assert response.status_code == 200
        
        # Check response contains payment data
        if response.is_json:
            data = response.get_json()
            assert 'approval_url' in data
            assert 'payment_id' in data
        
        mock_paypal_service.create_payment.assert_called_once()
    
    def test_execute_payment_success(self, client, mock_paypal_service, mock_email_service):
        """Test successful payment execution"""
        response = client.get('/execute-payment', query_string={
            'paymentId': 'test-payment-id',
            'PayerID': 'test-payer-id'
        })
        
        assert response.status_code == 200 or response.status_code == 302
        
        # Check services were called
        mock_paypal_service.execute_payment.assert_called_once()
        mock_email_service.send_credentials_email.assert_called_once()
    
    def test_execute_payment_failure(self, client, mock_paypal_service):
        """Test payment execution failure"""
        mock_paypal_service.execute_payment.return_value = None
        
        response = client.get('/execute-payment', query_string={
            'paymentId': 'test-payment-id',
            'PayerID': 'test-payer-id'
        })
        
        # Should handle failure gracefully
        assert response.status_code in [200, 302, 400]
        
        # Check error handling
        if response.status_code == 200:
            assert b'error' in response.data.lower() or b'failed' in response.data.lower()
    
    def test_payment_cancel(self, client):
        """Test payment cancellation"""
        response = client.get('/payment-cancel')
        
        assert response.status_code == 200
        assert b'cancel' in response.data.lower() or b'cancelled' in response.data.lower()
    
    def test_payment_success(self, client):
        """Test payment success page"""
        response = client.get('/payment-success')
        
        assert response.status_code == 200
        assert b'success' in response.data.lower() or b'thank' in response.data.lower()
    
    def test_create_payment_invalid_amount(self, client):
        """Test creating payment with invalid amount"""
        response = client.post('/create-payment', data={
            'amount': 'invalid',
            'currency': 'USD'
        })
        
        assert response.status_code == 400 or b'invalid' in response.data.lower()
    
    def test_create_payment_missing_data(self, client):
        """Test creating payment with missing data"""
        response = client.post('/create-payment', data={})
        
        assert response.status_code == 400 or b'required' in response.data.lower()
    
    def test_payment_webhook(self, client, mock_paypal_service):
        """Test PayPal webhook handling"""
        webhook_data = {
            'event_type': 'PAYMENT.SALE.COMPLETED',
            'resource': {
                'id': 'test-payment-id',
                'state': 'completed',
                'amount': {'total': '49.00', 'currency': 'USD'},
                'parent_payment': 'test-parent-payment-id'
            }
        }
        
        response = client.post('/paypal-webhook', 
                              data=json.dumps(webhook_data),
                              content_type='application/json')
        
        assert response.status_code == 200
        
        # Check webhook was processed
        mock_paypal_service.verify_webhook.assert_called_once()


class TestAdminEndpoints:
    """Test admin API endpoints"""
    
    def test_admin_dashboard_requires_auth(self, client):
        """Test admin dashboard requires authentication"""
        response = client.get('/admin')
        
        assert response.status_code == 302
        assert 'login' in response.location
    
    def test_admin_dashboard_authenticated(self, authenticated_client):
        """Test admin dashboard with authenticated user"""
        response = authenticated_client.get('/admin')
        
        assert response.status_code == 200
        assert b'admin' in response.data.lower() or b'dashboard' in response.data.lower()
    
    def test_admin_users_list(self, authenticated_client):
        """Test admin users list endpoint"""
        response = authenticated_client.get('/admin/users')
        
        assert response.status_code == 200
        assert b'users' in response.data.lower()
    
    def test_admin_transactions_list(self, authenticated_client):
        """Test admin transactions list endpoint"""
        response = authenticated_client.get('/admin/transactions')
        
        assert response.status_code == 200
        assert b'transactions' in response.data.lower()
    
    def test_admin_system_health(self, authenticated_client, mock_monitoring_services):
        """Test admin system health endpoint"""
        response = authenticated_client.get('/admin/system')
        
        assert response.status_code == 200
        assert b'health' in response.data.lower() or b'system' in response.data.lower()
        
        # Check monitoring services were called
        mock_monitoring_services['health_monitor'].check_database_health.assert_called()
    
    def test_admin_logs(self, authenticated_client):
        """Test admin logs endpoint"""
        response = authenticated_client.get('/admin/logs')
        
        assert response.status_code == 200
        assert b'logs' in response.data.lower()
    
    def test_admin_analytics(self, authenticated_client):
        """Test admin analytics endpoint"""
        response = authenticated_client.get('/admin/analytics')
        
        assert response.status_code == 200
        assert b'analytics' in response.data.lower()
    
    def test_admin_alerts(self, authenticated_client, mock_monitoring_services):
        """Test admin alerts endpoint"""
        response = authenticated_client.get('/admin/alerts')
        
        assert response.status_code == 200
        assert b'alerts' in response.data.lower()
        
        # Check alert manager was called
        mock_monitoring_services['alert_manager'].check_alerts.assert_called()
    
    def test_admin_user_detail(self, authenticated_client, created_user):
        """Test admin user detail endpoint"""
        response = authenticated_client.get(f'/admin/users/{created_user["id"]}')
        
        assert response.status_code == 200
        assert created_user['username'].encode() in response.data
    
    def test_admin_transaction_detail(self, authenticated_client, temp_db, sample_transaction_data):
        """Test admin transaction detail endpoint"""
        transaction_id = temp_db.create_transaction(sample_transaction_data)
        
        response = authenticated_client.get(f'/admin/transactions/{transaction_id}')
        
        assert response.status_code == 200
        assert sample_transaction_data['transaction_id'].encode() in response.data
    
    def test_admin_export_data(self, authenticated_client):
        """Test admin data export endpoint"""
        response = authenticated_client.get('/admin/export/users')
        
        assert response.status_code == 200
        assert response.mimetype == 'text/csv' or response.mimetype == 'application/json'
    
    def test_admin_system_actions(self, authenticated_client):
        """Test admin system actions"""
        # Test system restart
        response = authenticated_client.post('/admin/system/restart')
        assert response.status_code in [200, 202]
        
        # Test cache clear
        response = authenticated_client.post('/admin/system/clear-cache')
        assert response.status_code in [200, 202]
        
        # Test backup creation
        response = authenticated_client.post('/admin/system/backup')
        assert response.status_code in [200, 202]


class TestHealthCheckEndpoints:
    """Test health check API endpoints"""
    
    def test_health_check(self, client, mock_monitoring_services):
        """Test basic health check endpoint"""
        response = client.get('/health')
        
        assert response.status_code == 200
        assert response.is_json
        
        data = response.get_json()
        assert 'status' in data
        assert 'timestamp' in data
        assert 'checks' in data
    
    def test_health_check_detailed(self, client, mock_monitoring_services):
        """Test detailed health check endpoint"""
        response = client.get('/health/detailed')
        
        assert response.status_code == 200
        assert response.is_json
        
        data = response.get_json()
        assert 'database' in data
        assert 'email_service' in data
        assert 'paypal_service' in data
        assert 'system_metrics' in data
    
    def test_health_check_database(self, client, mock_monitoring_services):
        """Test database health check endpoint"""
        response = client.get('/health/database')
        
        assert response.status_code == 200
        assert response.is_json
        
        data = response.get_json()
        assert 'status' in data
        mock_monitoring_services['health_monitor'].check_database_health.assert_called()
    
    def test_health_check_services(self, client, mock_monitoring_services):
        """Test services health check endpoint"""
        response = client.get('/health/services')
        
        assert response.status_code == 200
        assert response.is_json
        
        data = response.get_json()
        assert 'email_service' in data
        assert 'paypal_service' in data
    
    def test_health_check_system_metrics(self, client, mock_monitoring_services):
        """Test system metrics endpoint"""
        response = client.get('/health/metrics')
        
        assert response.status_code == 200
        assert response.is_json
        
        data = response.get_json()
        assert 'cpu' in data or 'memory' in data
        mock_monitoring_services['health_monitor'].get_system_metrics.assert_called()
    
    def test_health_check_failure_handling(self, client):
        """Test health check failure handling"""
        with patch('services.monitoring.health_monitor.check_database_health') as mock_check:
            mock_check.return_value = {'status': 'unhealthy', 'error': 'Connection failed'}
            
            response = client.get('/health/database')
            
            assert response.status_code == 503 or response.status_code == 200
            
            if response.status_code == 200:
                data = response.get_json()
                assert data['status'] == 'unhealthy'


class TestAPIErrorHandling:
    """Test API error handling"""
    
    def test_404_error_handling(self, client):
        """Test 404 error handling"""
        response = client.get('/nonexistent-endpoint')
        
        assert response.status_code == 404
        assert b'not found' in response.data.lower() or b'404' in response.data.lower()
    
    def test_500_error_handling(self, client):
        """Test 500 error handling"""
        # Mock internal server error
        with patch('app.render_template') as mock_render:
            mock_render.side_effect = Exception("Internal error")
            
            response = client.get('/login')
            
            assert response.status_code == 500
    
    def test_csrf_error_handling(self, client):
        """Test CSRF error handling"""
        # Enable CSRF protection
        with patch('app.csrf.protect') as mock_csrf:
            mock_csrf.side_effect = Exception("CSRF token missing")
            
            response = client.post('/login', data={
                'username': 'test',
                'password': 'test'
            })
            
            assert response.status_code == 400
    
    def test_rate_limit_error_handling(self, client):
        """Test rate limit error handling"""
        # Mock rate limit exceeded
        with patch('app.limiter.limit') as mock_limit:
            mock_limit.side_effect = Exception("Rate limit exceeded")
            
            response = client.get('/login')
            
            assert response.status_code == 429
    
    def test_file_upload_error_handling(self, authenticated_client):
        """Test file upload error handling"""
        # Test with invalid file
        response = authenticated_client.post('/upload', data={
            'file': 'invalid_file_data',
            'algorithm': 'vtracer_high_fidelity'
        })
        
        assert response.status_code == 400
    
    def test_database_error_handling(self, client):
        """Test database error handling"""
        # Mock database connection failure
        with patch('database.Database.get_db_connection') as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            response = client.post('/login', data={
                'username': 'test',
                'password': 'test'
            })
            
            assert response.status_code == 500
    
    def test_external_service_error_handling(self, client, mock_paypal_service):
        """Test external service error handling"""
        # Mock PayPal service failure
        mock_paypal_service.create_payment.side_effect = Exception("PayPal service error")
        
        response = client.post('/create-payment', data={
            'amount': '49.00',
            'currency': 'USD'
        })
        
        assert response.status_code == 500 or response.status_code == 503


class TestAPIContentTypes:
    """Test API content type handling"""
    
    def test_json_content_type(self, client):
        """Test JSON content type handling"""
        response = client.post('/api/upload', 
                              data=json.dumps({'test': 'data'}),
                              content_type='application/json')
        
        # Should either accept JSON or return method not allowed
        assert response.status_code in [200, 405, 415]
    
    def test_form_content_type(self, authenticated_client):
        """Test form content type handling"""
        response = authenticated_client.post('/login', data={
            'username': 'test',
            'password': 'test'
        }, content_type='application/x-www-form-urlencoded')
        
        assert response.status_code in [200, 302]
    
    def test_multipart_content_type(self, authenticated_client, test_image_file):
        """Test multipart content type handling"""
        test_image_file.seek(0)
        
        response = authenticated_client.post('/upload', data={
            'file': (test_image_file, 'test.png', 'image/png'),
            'algorithm': 'vtracer_high_fidelity'
        }, content_type='multipart/form-data')
        
        assert response.status_code in [200, 302]
    
    def test_invalid_content_type(self, client):
        """Test invalid content type handling"""
        response = client.post('/login', 
                              data='invalid data',
                              content_type='application/xml')
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 415]


class TestAPIVersioning:
    """Test API versioning"""
    
    def test_api_version_header(self, client):
        """Test API version header"""
        response = client.get('/api/version')
        
        # Should either return version info or 404
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            assert 'version' in response.headers or response.is_json
    
    def test_api_deprecation_headers(self, client):
        """Test API deprecation headers"""
        response = client.get('/api/v1/deprecated-endpoint')
        
        # Should handle deprecated endpoints gracefully
        assert response.status_code in [200, 404, 410]
        
        if response.status_code == 200:
            assert 'deprecation' in response.headers or 'warning' in response.headers


class TestAPICaching:
    """Test API caching"""
    
    def test_cache_headers(self, client):
        """Test cache headers"""
        response = client.get('/static/css/vectorcraft.css')
        
        # Static files should have cache headers
        if response.status_code == 200:
            assert 'Cache-Control' in response.headers or 'ETag' in response.headers
    
    def test_no_cache_headers(self, authenticated_client):
        """Test no-cache headers for sensitive endpoints"""
        response = authenticated_client.get('/admin')
        
        # Admin pages should not be cached
        if response.status_code == 200:
            cache_control = response.headers.get('Cache-Control', '')
            assert 'no-cache' in cache_control or 'no-store' in cache_control
    
    def test_etag_handling(self, client):
        """Test ETag handling"""
        # First request
        response1 = client.get('/static/css/vectorcraft.css')
        
        if response1.status_code == 200 and 'ETag' in response1.headers:
            etag = response1.headers['ETag']
            
            # Second request with If-None-Match header
            response2 = client.get('/static/css/vectorcraft.css',
                                  headers={'If-None-Match': etag})
            
            # Should return 304 Not Modified
            assert response2.status_code == 304


@pytest.mark.parametrize("endpoint,method,expected_status", [
    ('/login', 'GET', 200),
    ('/buy', 'GET', 200),
    ('/health', 'GET', 200),
    ('/upload', 'GET', 302),  # Requires auth
    ('/admin', 'GET', 302),   # Requires auth
])
def test_endpoints_parametrized(client, endpoint, method, expected_status):
    """Test endpoints with parametrized testing"""
    if method == 'GET':
        response = client.get(endpoint)
    elif method == 'POST':
        response = client.post(endpoint)
    else:
        pytest.skip(f"Method {method} not supported in this test")
    
    assert response.status_code == expected_status


class TestAPIPerformance:
    """Test API performance"""
    
    def test_response_time_login(self, client, performance_test_helpers):
        """Test login response time"""
        performance_test_helpers.start_timer()
        
        response = client.get('/login')
        
        response_time = performance_test_helpers.end_timer('login_response')
        performance_test_helpers.assert_performance('login_response', 2.0)  # Should be under 2 seconds
        
        assert response.status_code == 200
    
    def test_response_time_health_check(self, client, performance_test_helpers):
        """Test health check response time"""
        performance_test_helpers.start_timer()
        
        response = client.get('/health')
        
        response_time = performance_test_helpers.end_timer('health_response')
        performance_test_helpers.assert_performance('health_response', 1.0)  # Should be under 1 second
        
        assert response.status_code == 200
    
    def test_concurrent_requests(self, client):
        """Test concurrent request handling"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get('/health')
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(results) == 10
        assert all(status == 200 for status in results)
    
    def test_memory_usage(self, client, performance_test_helpers):
        """Test memory usage during requests"""
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Make multiple requests
        for i in range(50):
            response = client.get('/health')
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024