"""
Test suite for API Management System
"""

import unittest
import json
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from services.api_service import (
    APIService, APIAnalyticsManager, IntegrationMonitor, 
    RateLimitController, APIDocumentationGenerator
)
from services.monitoring.api_performance_tracker import APIPerformanceTracker


class TestAPIAnalyticsManager(unittest.TestCase):
    """Test API Analytics Manager"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False)
        self.analytics = APIAnalyticsManager(self.test_db.name)
    
    def tearDown(self):
        """Clean up test environment"""
        self.test_db.close()
        os.unlink(self.test_db.name)
    
    def test_track_request(self):
        """Test request tracking"""
        self.analytics.track_request(
            endpoint='/api/test',
            method='GET',
            user_id=1,
            ip_address='127.0.0.1',
            status_code=200,
            response_time=0.5
        )
        
        # Verify in-memory tracking
        self.assertEqual(self.analytics.request_metrics['/api/test']['GET'], 1)
        self.assertEqual(len(self.analytics.response_times['/api/test']), 1)
    
    def test_track_error(self):
        """Test error tracking"""
        self.analytics.track_error(
            endpoint='/api/test',
            method='GET',
            error_type='ValidationError',
            error_message='Invalid input',
            user_id=1,
            ip_address='127.0.0.1'
        )
        
        # Verify in-memory tracking
        self.assertEqual(self.analytics.error_counts['/api/test'], 1)
    
    def test_get_analytics_summary(self):
        """Test analytics summary generation"""
        # Add some test data
        self.analytics.track_request('/api/test', 'GET', status_code=200, response_time=0.1)
        self.analytics.track_request('/api/test', 'POST', status_code=201, response_time=0.2)
        self.analytics.track_error('/api/test', 'GET', 'Error', 'Test error')
        
        summary = self.analytics.get_analytics_summary(24)
        
        self.assertIn('request_stats', summary)
        self.assertIn('error_stats', summary)
        self.assertIn('period_hours', summary)
        self.assertEqual(summary['period_hours'], 24)
    
    def test_get_top_endpoints(self):
        """Test top endpoints retrieval"""
        # Add test data
        for i in range(5):
            self.analytics.track_request(f'/api/endpoint{i}', 'GET', status_code=200, response_time=0.1)
        
        top_endpoints = self.analytics.get_top_endpoints(limit=3)
        
        self.assertIsInstance(top_endpoints, list)
        self.assertLessEqual(len(top_endpoints), 3)


class TestIntegrationMonitor(unittest.TestCase):
    """Test Integration Monitor"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False)
        self.analytics = APIAnalyticsManager(self.test_db.name)
        self.monitor = IntegrationMonitor(self.analytics)
    
    def tearDown(self):
        """Clean up test environment"""
        self.test_db.close()
        os.unlink(self.test_db.name)
    
    def test_register_service(self):
        """Test service registration"""
        self.monitor.register_service(
            'test_service',
            health_check_func=lambda: True,
            timeout=30
        )
        
        self.assertIn('test_service', self.monitor.services)
        self.assertEqual(self.monitor.services['test_service']['timeout'], 30)
    
    def test_check_service_health_with_function(self):
        """Test health check with function"""
        # Register service with health check function
        self.monitor.register_service(
            'test_service',
            health_check_func=lambda: True,
            timeout=30
        )
        
        result = self.monitor.check_service_health('test_service')
        
        self.assertEqual(result['status'], 'healthy')
        self.assertIn('response_time', result)
    
    def test_check_service_health_failure(self):
        """Test health check failure"""
        # Register service with failing health check
        self.monitor.register_service(
            'failing_service',
            health_check_func=lambda: False,
            timeout=30
        )
        
        result = self.monitor.check_service_health('failing_service')
        
        self.assertEqual(result['status'], 'unhealthy')
    
    def test_check_all_services(self):
        """Test checking all services"""
        # Register multiple services
        self.monitor.register_service('service1', health_check_func=lambda: True)
        self.monitor.register_service('service2', health_check_func=lambda: True)
        
        results = self.monitor.check_all_services()
        
        self.assertEqual(len(results), 2)
        self.assertIn('service1', results)
        self.assertIn('service2', results)


class TestRateLimitController(unittest.TestCase):
    """Test Rate Limit Controller"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False)
        self.analytics = APIAnalyticsManager(self.test_db.name)
        
        # Mock Redis service
        self.mock_redis = Mock()
        self.mock_redis.get.return_value = 0
        self.mock_redis.set.return_value = True
        self.mock_redis.increment.return_value = True
        self.mock_redis.ttl.return_value = 3600
        
        self.rate_controller = RateLimitController(self.mock_redis, self.analytics)
    
    def tearDown(self):
        """Clean up test environment"""
        self.test_db.close()
        os.unlink(self.test_db.name)
    
    def test_set_rate_limit(self):
        """Test setting rate limit"""
        self.rate_controller.set_rate_limit('/api/test', 100, 3600)
        
        self.assertIn('/api/test', self.rate_controller.rate_limits)
        self.assertEqual(self.rate_controller.rate_limits['/api/test']['limit'], 100)
        self.assertEqual(self.rate_controller.rate_limits['/api/test']['window'], 3600)
    
    def test_check_rate_limit_allowed(self):
        """Test rate limit check when allowed"""
        self.rate_controller.set_rate_limit('/api/test', 100, 3600)
        
        result = self.rate_controller.check_rate_limit('/api/test', 'user123')
        
        self.assertTrue(result['allowed'])
        self.assertEqual(result['remaining'], 99)
        self.assertEqual(result['limit'], 100)
    
    def test_check_rate_limit_exceeded(self):
        """Test rate limit check when exceeded"""
        self.rate_controller.set_rate_limit('/api/test', 100, 3600)
        
        # Mock Redis to return limit exceeded
        self.mock_redis.get.return_value = 100
        
        result = self.rate_controller.check_rate_limit('/api/test', 'user123')
        
        self.assertFalse(result['allowed'])
        self.assertEqual(result['remaining'], 0)
        self.assertEqual(result['limit'], 100)
    
    def test_get_rate_limit_stats(self):
        """Test rate limit statistics"""
        self.rate_controller.set_rate_limit('/api/test', 100, 3600)
        
        stats = self.rate_controller.get_rate_limit_stats()
        
        self.assertIn('/api/test', stats)
        self.assertEqual(stats['/api/test']['limit'], 100)
        self.assertEqual(stats['/api/test']['window'], 3600)


class TestAPIDocumentationGenerator(unittest.TestCase):
    """Test API Documentation Generator"""
    
    def setUp(self):
        """Set up test environment"""
        self.doc_generator = APIDocumentationGenerator()
    
    def test_document_endpoint(self):
        """Test endpoint documentation"""
        def test_func(param1: str, param2: int = 10):
            """Test function for documentation"""
            return {'result': 'test'}
        
        self.doc_generator.document_endpoint(
            endpoint='/api/test',
            method='GET',
            func=test_func,
            description='Test endpoint',
            parameters=[
                {'name': 'param1', 'type': 'string', 'required': True},
                {'name': 'param2', 'type': 'integer', 'required': False, 'default': 10}
            ]
        )
        
        self.assertIn('/api/test', self.doc_generator.endpoints)
        self.assertIn('GET', self.doc_generator.endpoints['/api/test'])
        
        endpoint_doc = self.doc_generator.endpoints['/api/test']['GET']
        self.assertEqual(endpoint_doc['description'], 'Test endpoint')
        self.assertEqual(len(endpoint_doc['parameters']), 2)
    
    def test_generate_openapi_spec(self):
        """Test OpenAPI specification generation"""
        def test_func():
            """Test function"""
            return {'result': 'test'}
        
        self.doc_generator.document_endpoint('/api/test', 'GET', test_func)
        
        spec = self.doc_generator.generate_openapi_spec()
        
        self.assertEqual(spec['openapi'], '3.0.0')
        self.assertIn('info', spec)
        self.assertIn('paths', spec)
        self.assertIn('/api/test', spec['paths'])
        self.assertIn('get', spec['paths']['/api/test'])
    
    def test_generate_html_docs(self):
        """Test HTML documentation generation"""
        def test_func():
            """Test function"""
            return {'result': 'test'}
        
        self.doc_generator.document_endpoint('/api/test', 'GET', test_func)
        
        html_docs = self.doc_generator.generate_html_docs()
        
        self.assertIn('<!DOCTYPE html>', html_docs)
        self.assertIn('VectorCraft API Documentation', html_docs)
        self.assertIn('/api/test', html_docs)
        self.assertIn('GET', html_docs)


class TestAPIPerformanceTracker(unittest.TestCase):
    """Test API Performance Tracker"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False)
        self.tracker = APIPerformanceTracker(self.test_db.name)
    
    def tearDown(self):
        """Clean up test environment"""
        self.test_db.close()
        os.unlink(self.test_db.name)
    
    def test_start_and_end_request_tracking(self):
        """Test request tracking lifecycle"""
        request_id = 'test_request_123'
        
        # Start tracking
        self.tracker.start_request_tracking(
            request_id=request_id,
            endpoint='/api/test',
            method='GET',
            user_id=1,
            ip_address='127.0.0.1'
        )
        
        self.assertIn(request_id, self.tracker.active_requests)
        
        # End tracking
        time.sleep(0.1)  # Ensure some response time
        self.tracker.end_request_tracking(
            request_id=request_id,
            status_code=200,
            request_size=1024,
            response_size=2048
        )
        
        self.assertNotIn(request_id, self.tracker.active_requests)
    
    def test_get_endpoint_performance(self):
        """Test endpoint performance retrieval"""
        # Add some test data
        request_id = 'test_request_456'
        self.tracker.start_request_tracking(request_id, '/api/test', 'GET')
        time.sleep(0.1)
        self.tracker.end_request_tracking(request_id, 200)
        
        performance = self.tracker.get_endpoint_performance('/api/test', 'GET')
        
        self.assertEqual(performance['endpoint'], '/api/test')
        self.assertEqual(performance['method'], 'GET')
        self.assertGreater(performance['total_requests'], 0)
        self.assertGreater(performance['avg_response_time'], 0)
    
    def test_get_system_performance_summary(self):
        """Test system performance summary"""
        # Add some test data
        for i in range(3):
            request_id = f'test_request_{i}'
            self.tracker.start_request_tracking(request_id, f'/api/test{i}', 'GET')
            time.sleep(0.05)
            self.tracker.end_request_tracking(request_id, 200)
        
        summary = self.tracker.get_system_performance_summary()
        
        self.assertIn('summary', summary)
        self.assertIn('top_endpoints', summary)
        self.assertIn('slowest_endpoints', summary)
        self.assertIn('recent_alerts', summary)
    
    def test_get_active_requests(self):
        """Test active requests retrieval"""
        request_id = 'test_active_request'
        
        # Start tracking but don't end
        self.tracker.start_request_tracking(request_id, '/api/test', 'GET')
        
        active_requests = self.tracker.get_active_requests()
        
        self.assertEqual(len(active_requests['active_requests']), 1)
        self.assertEqual(active_requests['count'], 1)
        
        # Clean up
        self.tracker.end_request_tracking(request_id, 200)
    
    def test_record_system_metric(self):
        """Test system metric recording"""
        self.tracker.record_system_metric('cpu_usage', 75.5)
        self.tracker.record_system_metric('memory_usage', 60.2)
        
        metrics = self.tracker.get_system_metrics()
        
        self.assertGreater(len(metrics), 0)
    
    def test_get_system_metrics_by_name(self):
        """Test getting system metrics by name"""
        self.tracker.record_system_metric('cpu_usage', 75.5)
        self.tracker.record_system_metric('memory_usage', 60.2)
        
        cpu_metrics = self.tracker.get_system_metrics('cpu_usage')
        
        self.assertEqual(len(cpu_metrics), 1)
        self.assertEqual(cpu_metrics[0]['metric_name'], 'cpu_usage')
        self.assertEqual(cpu_metrics[0]['metric_value'], 75.5)


class TestAPIServiceIntegration(unittest.TestCase):
    """Test API Service Integration"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock Redis service
        self.mock_redis = Mock()
        self.mock_redis.get.return_value = None
        self.mock_redis.set.return_value = True
        self.mock_redis.health_check.return_value = {'healthy': True}
        
        # Mock task manager
        self.mock_task_manager = Mock()
        self.mock_task_manager.health_check.return_value = {'healthy': True}
        
        # Mock vectorization service
        self.mock_vectorization_service = Mock()
        self.mock_vectorization_service.get_supported_strategies.return_value = ['vtracer']
        
        # Create API service with mocked dependencies
        with patch('services.api_service.redis_service', self.mock_redis), \
             patch('services.api_service.task_queue_manager', self.mock_task_manager), \
             patch('services.api_service.vectorization_service', self.mock_vectorization_service):
            
            self.api_service = APIService()
    
    def test_api_service_initialization(self):
        """Test API service initialization"""
        self.assertIsNotNone(self.api_service.analytics)
        self.assertIsNotNone(self.api_service.integration_monitor)
        self.assertIsNotNone(self.api_service.rate_limit_controller)
        self.assertIsNotNone(self.api_service.documentation_generator)
    
    def test_get_api_analytics(self):
        """Test API analytics retrieval"""
        analytics = self.api_service.get_api_analytics(24)
        
        self.assertIn('success', analytics)
        self.assertTrue(analytics['success'])
        self.assertIn('analytics', analytics)
    
    def test_get_integration_status(self):
        """Test integration status retrieval"""
        status = self.api_service.get_integration_status()
        
        self.assertIn('success', status)
        self.assertTrue(status['success'])
        self.assertIn('services', status)
    
    def test_get_rate_limit_status(self):
        """Test rate limit status retrieval"""
        status = self.api_service.get_rate_limit_status()
        
        self.assertIn('success', status)
        self.assertTrue(status['success'])
        self.assertIn('rate_limits', status)
    
    def test_update_rate_limit(self):
        """Test rate limit update"""
        result = self.api_service.update_rate_limit('/api/test', 100, 3600)
        
        self.assertIn('success', result)
        self.assertTrue(result['success'])
        self.assertEqual(result['endpoint'], '/api/test')
        self.assertEqual(result['limit'], 100)
        self.assertEqual(result['window'], 3600)
    
    def test_get_api_documentation(self):
        """Test API documentation retrieval"""
        # Test JSON format
        json_docs = self.api_service.get_api_documentation('json')
        
        self.assertIn('success', json_docs)
        self.assertTrue(json_docs['success'])
        self.assertEqual(json_docs['format'], 'openapi')
        
        # Test HTML format
        html_docs = self.api_service.get_api_documentation('html')
        
        self.assertIn('success', html_docs)
        self.assertTrue(html_docs['success'])
        self.assertEqual(html_docs['format'], 'html')
    
    def test_get_performance_metrics(self):
        """Test performance metrics retrieval"""
        metrics = self.api_service.get_performance_metrics()
        
        self.assertIn('success', metrics)
        self.assertTrue(metrics['success'])
        self.assertIn('metrics', metrics)


if __name__ == '__main__':
    # Run specific test suites
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(test_loader.loadTestsFromTestCase(TestAPIAnalyticsManager))
    test_suite.addTest(test_loader.loadTestsFromTestCase(TestIntegrationMonitor))
    test_suite.addTest(test_loader.loadTestsFromTestCase(TestRateLimitController))
    test_suite.addTest(test_loader.loadTestsFromTestCase(TestAPIDocumentationGenerator))
    test_suite.addTest(test_loader.loadTestsFromTestCase(TestAPIPerformanceTracker))
    test_suite.addTest(test_loader.loadTestsFromTestCase(TestAPIServiceIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\nTests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")