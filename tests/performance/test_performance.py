#!/usr/bin/env python3
"""
Performance tests for VectorCraft application
Tests response times, throughput, and resource usage
"""

import pytest
import time
import threading
import concurrent.futures
import psutil
import os
import statistics
from unittest.mock import patch, MagicMock

from locust import HttpUser, task, between
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging


class TestResponseTimes:
    """Test response times for critical endpoints"""
    
    def test_login_page_response_time(self, client, performance_test_helpers):
        """Test login page response time"""
        performance_test_helpers.start_timer()
        
        response = client.get('/login')
        
        response_time = performance_test_helpers.end_timer('login_page')
        performance_test_helpers.assert_performance('login_page', 2.0)
        
        assert response.status_code == 200
        assert response_time < 2.0
    
    def test_health_check_response_time(self, client, performance_test_helpers):
        """Test health check response time"""
        performance_test_helpers.start_timer()
        
        response = client.get('/health')
        
        response_time = performance_test_helpers.end_timer('health_check')
        performance_test_helpers.assert_performance('health_check', 1.0)
        
        assert response.status_code == 200
        assert response_time < 1.0
    
    def test_static_file_response_time(self, client, performance_test_helpers):
        """Test static file response time"""
        performance_test_helpers.start_timer()
        
        response = client.get('/static/css/vectorcraft.css')
        
        response_time = performance_test_helpers.end_timer('static_file')
        performance_test_helpers.assert_performance('static_file', 0.5)
        
        assert response.status_code == 200
        assert response_time < 0.5
    
    def test_dashboard_response_time(self, authenticated_client, performance_test_helpers):
        """Test dashboard response time"""
        performance_test_helpers.start_timer()
        
        response = authenticated_client.get('/dashboard')
        
        response_time = performance_test_helpers.end_timer('dashboard')
        performance_test_helpers.assert_performance('dashboard', 3.0)
        
        assert response.status_code == 200
        assert response_time < 3.0
    
    def test_admin_dashboard_response_time(self, authenticated_client, performance_test_helpers, mock_monitoring_services):
        """Test admin dashboard response time"""
        performance_test_helpers.start_timer()
        
        response = authenticated_client.get('/admin')
        
        response_time = performance_test_helpers.end_timer('admin_dashboard')
        performance_test_helpers.assert_performance('admin_dashboard', 5.0)
        
        assert response.status_code == 200
        assert response_time < 5.0
    
    def test_file_upload_response_time(self, authenticated_client, test_image_file, performance_test_helpers, mock_vectorization_service):
        """Test file upload response time"""
        test_image_file.seek(0)
        
        performance_test_helpers.start_timer()
        
        response = authenticated_client.post('/upload', data={
            'file': (test_image_file, 'test.png', 'image/png'),
            'algorithm': 'vtracer_high_fidelity'
        }, content_type='multipart/form-data')
        
        response_time = performance_test_helpers.end_timer('file_upload')
        performance_test_helpers.assert_performance('file_upload', 10.0)
        
        assert response.status_code in [200, 302]
        assert response_time < 10.0
    
    def test_payment_creation_response_time(self, client, performance_test_helpers, mock_paypal_service):
        """Test payment creation response time"""
        performance_test_helpers.start_timer()
        
        response = client.post('/create-payment', data={
            'amount': '49.00',
            'currency': 'USD'
        })
        
        response_time = performance_test_helpers.end_timer('payment_creation')
        performance_test_helpers.assert_performance('payment_creation', 5.0)
        
        assert response.status_code == 200
        assert response_time < 5.0


class TestThroughput:
    """Test throughput for various endpoints"""
    
    def test_concurrent_health_checks(self, client, performance_test_helpers):
        """Test concurrent health check requests"""
        num_requests = 50
        results = []
        
        def make_request():
            start_time = time.time()
            response = client.get('/health')
            end_time = time.time()
            
            results.append({
                'status_code': response.status_code,
                'response_time': end_time - start_time
            })
        
        performance_test_helpers.start_timer()
        
        # Execute concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            concurrent.futures.wait(futures)
        
        total_time = performance_test_helpers.end_timer('concurrent_health_checks')
        
        # Analyze results
        successful_requests = [r for r in results if r['status_code'] == 200]
        assert len(successful_requests) == num_requests
        
        # Calculate throughput (requests per second)
        throughput = num_requests / total_time
        assert throughput >= 10  # At least 10 requests per second
        
        # Calculate average response time
        avg_response_time = statistics.mean([r['response_time'] for r in results])
        assert avg_response_time < 1.0  # Average under 1 second
    
    def test_concurrent_login_requests(self, client, created_user, test_user_data, performance_test_helpers):
        """Test concurrent login requests"""
        num_requests = 20
        results = []
        
        def make_request():
            start_time = time.time()
            response = client.post('/login', data={
                'username': test_user_data['username'],
                'password': test_user_data['password']
            })
            end_time = time.time()
            
            results.append({
                'status_code': response.status_code,
                'response_time': end_time - start_time
            })
        
        performance_test_helpers.start_timer()
        
        # Execute concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            concurrent.futures.wait(futures)
        
        total_time = performance_test_helpers.end_timer('concurrent_logins')
        
        # Analyze results
        successful_requests = [r for r in results if r['status_code'] in [200, 302]]
        assert len(successful_requests) >= num_requests * 0.8  # At least 80% success rate
        
        # Calculate throughput
        throughput = len(successful_requests) / total_time
        assert throughput >= 2  # At least 2 successful logins per second
    
    def test_concurrent_file_uploads(self, authenticated_client, test_image_files, performance_test_helpers, mock_vectorization_service):
        """Test concurrent file uploads"""
        num_requests = len(test_image_files)
        results = []
        
        def make_request(file_name, file_data):
            file_data.seek(0)
            start_time = time.time()
            
            response = authenticated_client.post('/upload', data={
                'file': (file_data, f'{file_name}.png', 'image/png'),
                'algorithm': 'vtracer_high_fidelity'
            }, content_type='multipart/form-data')
            
            end_time = time.time()
            
            results.append({
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'file_name': file_name
            })
        
        performance_test_helpers.start_timer()
        
        # Execute concurrent uploads
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request, name, data) 
                      for name, data in test_image_files.items()]
            concurrent.futures.wait(futures)
        
        total_time = performance_test_helpers.end_timer('concurrent_uploads')
        
        # Analyze results
        successful_requests = [r for r in results if r['status_code'] in [200, 302]]
        assert len(successful_requests) >= num_requests * 0.8  # At least 80% success rate
        
        # Calculate throughput
        throughput = len(successful_requests) / total_time
        assert throughput >= 0.5  # At least 0.5 uploads per second
    
    def test_mixed_workload_throughput(self, client, authenticated_client, performance_test_helpers, mock_vectorization_service):
        """Test mixed workload throughput"""
        results = []
        
        def health_check():
            start_time = time.time()
            response = client.get('/health')
            end_time = time.time()
            
            results.append({
                'endpoint': 'health',
                'status_code': response.status_code,
                'response_time': end_time - start_time
            })
        
        def dashboard_access():
            start_time = time.time()
            response = authenticated_client.get('/dashboard')
            end_time = time.time()
            
            results.append({
                'endpoint': 'dashboard',
                'status_code': response.status_code,
                'response_time': end_time - start_time
            })
        
        def login_page():
            start_time = time.time()
            response = client.get('/login')
            end_time = time.time()
            
            results.append({
                'endpoint': 'login',
                'status_code': response.status_code,
                'response_time': end_time - start_time
            })
        
        performance_test_helpers.start_timer()
        
        # Execute mixed workload
        tasks = [health_check, dashboard_access, login_page]
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for _ in range(30):  # 30 total requests
                task = tasks[len(futures) % len(tasks)]
                futures.append(executor.submit(task))
            
            concurrent.futures.wait(futures)
        
        total_time = performance_test_helpers.end_timer('mixed_workload')
        
        # Analyze results
        successful_requests = [r for r in results if r['status_code'] in [200, 302]]
        assert len(successful_requests) >= 25  # At least 25 successful requests
        
        # Calculate overall throughput
        throughput = len(successful_requests) / total_time
        assert throughput >= 5  # At least 5 requests per second overall


class TestResourceUsage:
    """Test resource usage during operations"""
    
    def test_memory_usage_login(self, client, created_user, test_user_data):
        """Test memory usage during login operations"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Perform multiple login operations
        for i in range(100):
            response = client.post('/login', data={
                'username': test_user_data['username'],
                'password': test_user_data['password']
            })
            
            # Clear any session data
            with client.session_transaction() as sess:
                sess.clear()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024
    
    def test_memory_usage_file_upload(self, authenticated_client, test_image_files, mock_vectorization_service):
        """Test memory usage during file upload operations"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Perform multiple file uploads
        for name, file_data in test_image_files.items():
            file_data.seek(0)
            
            response = authenticated_client.post('/upload', data={
                'file': (file_data, f'{name}.png', 'image/png'),
                'algorithm': 'vtracer_high_fidelity'
            }, content_type='multipart/form-data')
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024
    
    def test_cpu_usage_during_load(self, client, performance_test_helpers):
        """Test CPU usage during high load"""
        process = psutil.Process()
        
        # Monitor CPU usage
        cpu_samples = []
        
        def monitor_cpu():
            for _ in range(10):
                cpu_samples.append(process.cpu_percent(interval=0.1))
        
        def generate_load():
            for _ in range(50):
                response = client.get('/health')
                assert response.status_code == 200
        
        # Start CPU monitoring
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()
        
        # Generate load
        performance_test_helpers.start_timer()
        generate_load()
        load_time = performance_test_helpers.end_timer('cpu_load_test')
        
        # Wait for monitoring to complete
        monitor_thread.join()
        
        # Analyze CPU usage
        avg_cpu = statistics.mean(cpu_samples)
        max_cpu = max(cpu_samples)
        
        # CPU usage should be reasonable
        assert avg_cpu < 80  # Average CPU under 80%
        assert max_cpu < 95  # Max CPU under 95%
        assert load_time < 10  # Load generation under 10 seconds
    
    def test_database_connection_usage(self, temp_db, performance_test_helpers):
        """Test database connection usage"""
        initial_connections = len(temp_db.get_active_connections())
        
        # Perform multiple database operations
        performance_test_helpers.start_timer()
        
        for i in range(50):
            # Create and query user
            user_id = temp_db.create_user(f'testuser{i}', f'test{i}@example.com', 'Password123!')
            user = temp_db.get_user_by_id(user_id)
            assert user is not None
        
        db_operation_time = performance_test_helpers.end_timer('database_operations')
        
        final_connections = len(temp_db.get_active_connections())
        
        # Connection usage should be reasonable
        assert final_connections <= initial_connections + 5  # No significant connection leak
        assert db_operation_time < 5  # Database operations under 5 seconds
    
    def test_file_system_usage(self, authenticated_client, test_image_files, temp_upload_dir, mock_vectorization_service):
        """Test file system usage during uploads"""
        initial_disk_usage = psutil.disk_usage(temp_upload_dir)
        
        # Perform multiple file uploads
        for name, file_data in test_image_files.items():
            file_data.seek(0)
            
            response = authenticated_client.post('/upload', data={
                'file': (file_data, f'{name}.png', 'image/png'),
                'algorithm': 'vtracer_high_fidelity'
            }, content_type='multipart/form-data')
        
        final_disk_usage = psutil.disk_usage(temp_upload_dir)
        
        # Disk usage should be reasonable
        disk_increase = final_disk_usage.used - initial_disk_usage.used
        assert disk_increase < 10 * 1024 * 1024  # Less than 10MB increase
    
    def test_thread_usage(self, client, performance_test_helpers):
        """Test thread usage during concurrent operations"""
        process = psutil.Process()
        initial_threads = process.num_threads()
        
        def make_requests():
            for _ in range(10):
                response = client.get('/health')
                assert response.status_code == 200
        
        performance_test_helpers.start_timer()
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_requests)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        thread_test_time = performance_test_helpers.end_timer('thread_usage_test')
        
        final_threads = process.num_threads()
        
        # Thread usage should be reasonable
        assert final_threads <= initial_threads + 10  # No significant thread leak
        assert thread_test_time < 5  # Thread operations under 5 seconds


class TestScalability:
    """Test scalability characteristics"""
    
    def test_user_scaling(self, client, temp_db, performance_test_helpers):
        """Test performance with increasing user count"""
        user_counts = [10, 50, 100, 200]
        performance_results = {}
        
        for user_count in user_counts:
            # Create users
            for i in range(user_count):
                temp_db.create_user(f'user{i}', f'user{i}@example.com', 'Password123!')
            
            # Test login performance
            performance_test_helpers.start_timer()
            
            response = client.post('/login', data={
                'username': f'user{user_count-1}',
                'password': 'Password123!'
            })
            
            login_time = performance_test_helpers.end_timer(f'login_{user_count}_users')
            performance_results[user_count] = login_time
            
            # Clear session
            with client.session_transaction() as sess:
                sess.clear()
        
        # Analyze scalability
        for user_count in user_counts:
            # Login time should scale reasonably
            assert performance_results[user_count] < 5.0  # Under 5 seconds
            
            # Performance degradation should be minimal
            if user_count > 10:
                previous_count = user_counts[user_counts.index(user_count) - 1]
                degradation = performance_results[user_count] / performance_results[previous_count]
                assert degradation < 2.0  # Less than 2x degradation
    
    def test_transaction_scaling(self, temp_db, performance_test_helpers):
        """Test performance with increasing transaction count"""
        transaction_counts = [100, 500, 1000, 2000]
        performance_results = {}
        
        for transaction_count in transaction_counts:
            # Create transactions
            for i in range(transaction_count):
                transaction_data = {
                    'transaction_id': f'txn-{i}',
                    'email': f'user{i}@example.com',
                    'amount': 49.00,
                    'currency': 'USD',
                    'status': 'completed'
                }
                temp_db.create_transaction(transaction_data)
            
            # Test query performance
            performance_test_helpers.start_timer()
            
            transactions = temp_db.list_transactions(page=1, per_page=10)
            
            query_time = performance_test_helpers.end_timer(f'query_{transaction_count}_transactions')
            performance_results[transaction_count] = query_time
            
            assert len(transactions) == 10
        
        # Analyze scalability
        for transaction_count in transaction_counts:
            # Query time should scale reasonably
            assert performance_results[transaction_count] < 2.0  # Under 2 seconds
    
    def test_concurrent_user_scaling(self, client, created_user, test_user_data, performance_test_helpers):
        """Test performance with increasing concurrent users"""
        concurrent_user_counts = [5, 10, 20, 30]
        performance_results = {}
        
        for concurrent_users in concurrent_user_counts:
            results = []
            
            def make_request():
                start_time = time.time()
                response = client.post('/login', data={
                    'username': test_user_data['username'],
                    'password': test_user_data['password']
                })
                end_time = time.time()
                
                results.append({
                    'status_code': response.status_code,
                    'response_time': end_time - start_time
                })
            
            performance_test_helpers.start_timer()
            
            # Execute concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [executor.submit(make_request) for _ in range(concurrent_users)]
                concurrent.futures.wait(futures)
            
            total_time = performance_test_helpers.end_timer(f'concurrent_{concurrent_users}_users')
            performance_results[concurrent_users] = total_time
            
            # Analyze results
            successful_requests = [r for r in results if r['status_code'] in [200, 302]]
            success_rate = len(successful_requests) / concurrent_users
            
            assert success_rate >= 0.8  # At least 80% success rate
            assert total_time < 10.0  # Under 10 seconds total
        
        # Verify scalability characteristics
        for concurrent_users in concurrent_user_counts:
            if concurrent_users > 5:
                # Performance should not degrade exponentially
                previous_count = concurrent_user_counts[concurrent_user_counts.index(concurrent_users) - 1]
                degradation = performance_results[concurrent_users] / performance_results[previous_count]
                assert degradation < 1.5  # Less than 1.5x degradation


class TestLoadTesting:
    """Test application under load using Locust"""
    
    class VectorCraftUser(HttpUser):
        """Locust user class for load testing"""
        wait_time = between(1, 3)
        
        def on_start(self):
            """Called when a user starts"""
            self.login()
        
        def login(self):
            """Login user"""
            response = self.client.post('/login', data={
                'username': 'testuser',
                'password': 'TestPassword123!'
            })
            
            if response.status_code == 200:
                # Extract session data if needed
                pass
        
        @task(3)
        def view_dashboard(self):
            """View dashboard"""
            self.client.get('/dashboard')
        
        @task(2)
        def view_health(self):
            """View health check"""
            self.client.get('/health')
        
        @task(1)
        def view_login(self):
            """View login page"""
            self.client.get('/login')
        
        @task(1)
        def upload_file(self):
            """Upload file"""
            # Create test file
            test_file = io.BytesIO(b'fake image data')
            
            response = self.client.post('/upload', files={
                'file': ('test.png', test_file, 'image/png')
            }, data={
                'algorithm': 'vtracer_high_fidelity'
            })
    
    def test_load_test_basic(self, app):
        """Basic load test"""
        # Setup Locust environment
        env = Environment(user_classes=[self.VectorCraftUser])
        env.create_local_runner()
        
        # Start load test
        env.runner.start(user_count=10, spawn_rate=2)
        
        # Run for 30 seconds
        time.sleep(30)
        
        # Stop load test
        env.runner.stop()
        
        # Analyze results
        stats = env.runner.stats
        
        # Check basic metrics
        assert stats.total.num_requests > 0
        assert stats.total.num_failures < stats.total.num_requests * 0.05  # Less than 5% failures
        assert stats.total.avg_response_time < 2000  # Average response time under 2 seconds
        assert stats.total.max_response_time < 10000  # Max response time under 10 seconds
    
    def test_stress_test(self, app):
        """Stress test with high load"""
        # Setup Locust environment
        env = Environment(user_classes=[self.VectorCraftUser])
        env.create_local_runner()
        
        # Start stress test
        env.runner.start(user_count=50, spawn_rate=10)
        
        # Run for 60 seconds
        time.sleep(60)
        
        # Stop stress test
        env.runner.stop()
        
        # Analyze results
        stats = env.runner.stats
        
        # Check stress test metrics
        assert stats.total.num_requests > 0
        assert stats.total.num_failures < stats.total.num_requests * 0.10  # Less than 10% failures
        assert stats.total.avg_response_time < 5000  # Average response time under 5 seconds
    
    def test_spike_test(self, app):
        """Spike test with sudden load increase"""
        # Setup Locust environment
        env = Environment(user_classes=[self.VectorCraftUser])
        env.create_local_runner()
        
        # Start with low load
        env.runner.start(user_count=5, spawn_rate=1)
        time.sleep(10)
        
        # Spike to high load
        env.runner.start(user_count=30, spawn_rate=30)
        time.sleep(20)
        
        # Return to normal load
        env.runner.start(user_count=5, spawn_rate=1)
        time.sleep(10)
        
        # Stop test
        env.runner.stop()
        
        # Analyze results
        stats = env.runner.stats
        
        # Check spike test metrics
        assert stats.total.num_requests > 0
        assert stats.total.num_failures < stats.total.num_requests * 0.15  # Less than 15% failures


class TestPerformanceRegression:
    """Test for performance regression"""
    
    def test_baseline_performance(self, client, performance_test_helpers):
        """Establish baseline performance metrics"""
        baseline_metrics = {}
        
        # Test key endpoints
        endpoints = [
            ('/health', 1.0),
            ('/login', 2.0),
            ('/buy', 2.0),
        ]
        
        for endpoint, max_time in endpoints:
            performance_test_helpers.start_timer()
            
            response = client.get(endpoint)
            
            response_time = performance_test_helpers.end_timer(f'baseline_{endpoint}')
            baseline_metrics[endpoint] = response_time
            
            assert response.status_code == 200
            assert response_time < max_time
        
        # Store baseline metrics for comparison
        return baseline_metrics
    
    def test_performance_comparison(self, client, performance_test_helpers):
        """Compare current performance with baseline"""
        current_metrics = {}
        
        # Test same endpoints as baseline
        endpoints = ['/health', '/login', '/buy']
        
        for endpoint in endpoints:
            performance_test_helpers.start_timer()
            
            response = client.get(endpoint)
            
            response_time = performance_test_helpers.end_timer(f'current_{endpoint}')
            current_metrics[endpoint] = response_time
            
            assert response.status_code == 200
        
        # Compare with baseline (mock baseline for testing)
        baseline_metrics = {
            '/health': 0.5,
            '/login': 1.0,
            '/buy': 1.5
        }
        
        for endpoint in endpoints:
            current_time = current_metrics[endpoint]
            baseline_time = baseline_metrics[endpoint]
            
            # Performance should not degrade more than 50%
            regression_threshold = baseline_time * 1.5
            assert current_time < regression_threshold, \
                f"Performance regression detected for {endpoint}: {current_time}s vs baseline {baseline_time}s"
    
    def test_memory_leak_detection(self, client, performance_test_helpers):
        """Test for memory leaks over time"""
        process = psutil.Process()
        memory_samples = []
        
        # Perform operations and monitor memory
        for i in range(100):
            response = client.get('/health')
            assert response.status_code == 200
            
            # Sample memory every 10 requests
            if i % 10 == 0:
                memory_samples.append(process.memory_info().rss)
        
        # Analyze memory trend
        if len(memory_samples) >= 3:
            # Calculate memory growth rate
            initial_memory = memory_samples[0]
            final_memory = memory_samples[-1]
            memory_growth = final_memory - initial_memory
            
            # Memory growth should be minimal (less than 50MB)
            assert memory_growth < 50 * 1024 * 1024, \
                f"Potential memory leak detected: {memory_growth / 1024 / 1024:.2f}MB growth"
    
    def test_database_performance_regression(self, temp_db, performance_test_helpers):
        """Test for database performance regression"""
        # Create test data
        for i in range(1000):
            temp_db.create_user(f'user{i}', f'user{i}@example.com', 'Password123!')
        
        # Test query performance
        performance_test_helpers.start_timer()
        
        user = temp_db.get_user_by_username('user500')
        
        query_time = performance_test_helpers.end_timer('db_query_regression')
        
        assert user is not None
        assert query_time < 0.1  # Query should be under 100ms
        
        # Test bulk operations
        performance_test_helpers.start_timer()
        
        users = temp_db.list_users(page=1, per_page=100)
        
        bulk_query_time = performance_test_helpers.end_timer('db_bulk_query_regression')
        
        assert len(users) == 100
        assert bulk_query_time < 0.5  # Bulk query should be under 500ms


@pytest.mark.performance
class TestPerformanceMetrics:
    """Test performance metrics collection"""
    
    def test_response_time_distribution(self, client, performance_test_helpers):
        """Test response time distribution"""
        response_times = []
        
        # Collect response times
        for _ in range(100):
            performance_test_helpers.start_timer()
            
            response = client.get('/health')
            
            response_time = performance_test_helpers.end_timer('health_distribution')
            response_times.append(response_time)
            
            assert response.status_code == 200
        
        # Calculate statistics
        avg_time = statistics.mean(response_times)
        median_time = statistics.median(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        p99_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
        
        # Verify performance characteristics
        assert avg_time < 1.0  # Average under 1 second
        assert median_time < 0.5  # Median under 500ms
        assert p95_time < 2.0  # 95th percentile under 2 seconds
        assert p99_time < 5.0  # 99th percentile under 5 seconds
    
    def test_throughput_metrics(self, client, performance_test_helpers):
        """Test throughput metrics"""
        num_requests = 100
        
        performance_test_helpers.start_timer()
        
        # Execute requests
        for _ in range(num_requests):
            response = client.get('/health')
            assert response.status_code == 200
        
        total_time = performance_test_helpers.end_timer('throughput_test')
        
        # Calculate throughput
        throughput = num_requests / total_time
        
        # Verify throughput meets requirements
        assert throughput >= 50  # At least 50 requests per second
    
    def test_error_rate_under_load(self, client, performance_test_helpers):
        """Test error rate under load"""
        num_requests = 200
        error_count = 0
        
        # Execute requests rapidly
        for _ in range(num_requests):
            response = client.get('/health')
            if response.status_code != 200:
                error_count += 1
        
        # Calculate error rate
        error_rate = error_count / num_requests
        
        # Verify error rate is acceptable
        assert error_rate < 0.01  # Less than 1% error rate


@pytest.mark.slow
class TestLongRunningPerformance:
    """Test long-running performance characteristics"""
    
    def test_sustained_load_performance(self, client, performance_test_helpers):
        """Test performance under sustained load"""
        duration = 300  # 5 minutes
        start_time = time.time()
        request_count = 0
        error_count = 0
        
        while time.time() - start_time < duration:
            response = client.get('/health')
            request_count += 1
            
            if response.status_code != 200:
                error_count += 1
            
            time.sleep(0.1)  # Small delay between requests
        
        # Calculate metrics
        total_time = time.time() - start_time
        throughput = request_count / total_time
        error_rate = error_count / request_count
        
        # Verify sustained performance
        assert throughput >= 5  # At least 5 requests per second
        assert error_rate < 0.05  # Less than 5% error rate
        assert request_count > 1000  # Processed significant number of requests
    
    def test_memory_stability_over_time(self, client):
        """Test memory stability over extended period"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Run for extended period
        for i in range(1000):
            response = client.get('/health')
            assert response.status_code == 200
            
            # Check memory periodically
            if i % 100 == 0:
                current_memory = process.memory_info().rss
                memory_growth = current_memory - initial_memory
                
                # Memory growth should be controlled
                assert memory_growth < 100 * 1024 * 1024  # Less than 100MB growth


if __name__ == '__main__':
    # Run performance tests
    pytest.main([__file__, '-v', '-m', 'performance'])