"""
API Service Layer with caching, optimization, analytics, and monitoring
"""

import os
import json
import time
import hashlib
import logging
from functools import wraps
from typing import Dict, Any, Optional, List, Tuple, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from urllib.parse import urlparse
import inspect

from flask import request, jsonify, current_app
from werkzeug.exceptions import RequestEntityTooLarge

from services.redis_service import redis_service
from services.task_queue_manager import task_queue_manager
from services.vectorization_service import vectorization_service
from services.monitoring.system_logger import system_logger

# API Analytics imports
import sqlite3
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class APIAnalyticsManager:
    """Manager for API usage analytics and tracking"""
    
    def __init__(self, db_path: str = "api_analytics.db"):
        self.db_path = db_path
        self.init_database()
        self.request_metrics = defaultdict(lambda: defaultdict(int))
        self.response_times = defaultdict(deque)
        self.error_counts = defaultdict(int)
        self.rate_limit_hits = defaultdict(int)
        self.lock = threading.Lock()
        
    def init_database(self):
        """Initialize analytics database"""
        with self.get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS api_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    user_id INTEGER,
                    ip_address TEXT,
                    user_agent TEXT,
                    status_code INTEGER,
                    response_time REAL,
                    request_size INTEGER,
                    response_size INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS api_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    error_type TEXT,
                    error_message TEXT,
                    user_id INTEGER,
                    ip_address TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    limit_type TEXT,
                    hits INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS integration_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time REAL,
                    error_message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_requests_endpoint ON api_requests(endpoint)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON api_requests(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_errors_endpoint ON api_errors(endpoint)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_integration_service ON integration_health(service_name)')
            
    @contextmanager
    def get_db_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
            
    def track_request(self, endpoint: str, method: str, user_id: int = None, 
                     ip_address: str = None, user_agent: str = None,
                     status_code: int = None, response_time: float = None,
                     request_size: int = None, response_size: int = None):
        """Track API request"""
        with self.lock:
            # In-memory tracking
            self.request_metrics[endpoint][method] += 1
            if response_time:
                self.response_times[endpoint].append(response_time)
                # Keep only last 100 response times
                if len(self.response_times[endpoint]) > 100:
                    self.response_times[endpoint].popleft()
        
        # Database tracking
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO api_requests 
                (endpoint, method, user_id, ip_address, user_agent, status_code, 
                 response_time, request_size, response_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (endpoint, method, user_id, ip_address, user_agent, 
                  status_code, response_time, request_size, response_size))
            
    def track_error(self, endpoint: str, method: str, error_type: str, 
                   error_message: str, user_id: int = None, ip_address: str = None):
        """Track API error"""
        with self.lock:
            self.error_counts[endpoint] += 1
            
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO api_errors 
                (endpoint, method, error_type, error_message, user_id, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (endpoint, method, error_type, error_message, user_id, ip_address))
            
    def track_rate_limit(self, endpoint: str, ip_address: str, limit_type: str, hits: int):
        """Track rate limit hit"""
        with self.lock:
            self.rate_limit_hits[endpoint] += 1
            
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO rate_limits (endpoint, ip_address, limit_type, hits)
                VALUES (?, ?, ?, ?)
            ''', (endpoint, ip_address, limit_type, hits))
            
    def track_integration_health(self, service_name: str, status: str, 
                               response_time: float = None, error_message: str = None):
        """Track integration health"""
        with self.get_db_connection() as conn:
            conn.execute('''
                INSERT INTO integration_health 
                (service_name, status, response_time, error_message)
                VALUES (?, ?, ?, ?)
            ''', (service_name, status, response_time, error_message))
            
    def get_analytics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get analytics summary for the last N hours"""
        since = datetime.now() - timedelta(hours=hours)
        
        with self.get_db_connection() as conn:
            # Request statistics
            request_stats = conn.execute('''
                SELECT endpoint, method, COUNT(*) as count,
                       AVG(response_time) as avg_response_time,
                       MAX(response_time) as max_response_time,
                       MIN(response_time) as min_response_time
                FROM api_requests 
                WHERE timestamp > ? 
                GROUP BY endpoint, method
                ORDER BY count DESC
            ''', (since,)).fetchall()
            
            # Error statistics
            error_stats = conn.execute('''
                SELECT endpoint, error_type, COUNT(*) as count
                FROM api_errors 
                WHERE timestamp > ? 
                GROUP BY endpoint, error_type
                ORDER BY count DESC
            ''', (since,)).fetchall()
            
            # Rate limit statistics
            rate_limit_stats = conn.execute('''
                SELECT endpoint, ip_address, COUNT(*) as hits
                FROM rate_limits 
                WHERE timestamp > ? 
                GROUP BY endpoint, ip_address
                ORDER BY hits DESC
            ''', (since,)).fetchall()
            
            # Integration health
            integration_stats = conn.execute('''
                SELECT service_name, status, COUNT(*) as count,
                       AVG(response_time) as avg_response_time
                FROM integration_health 
                WHERE timestamp > ? 
                GROUP BY service_name, status
                ORDER BY service_name, count DESC
            ''', (since,)).fetchall()
            
        return {
            'request_stats': [dict(row) for row in request_stats],
            'error_stats': [dict(row) for row in error_stats],
            'rate_limit_stats': [dict(row) for row in rate_limit_stats],
            'integration_stats': [dict(row) for row in integration_stats],
            'period_hours': hours,
            'generated_at': datetime.now().isoformat()
        }
        
    def get_top_endpoints(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top endpoints by request count"""
        with self.get_db_connection() as conn:
            result = conn.execute('''
                SELECT endpoint, COUNT(*) as requests,
                       AVG(response_time) as avg_response_time
                FROM api_requests 
                WHERE timestamp > datetime('now', '-24 hours')
                GROUP BY endpoint 
                ORDER BY requests DESC 
                LIMIT ?
            ''', (limit,)).fetchall()
            
        return [dict(row) for row in result]
        
    def get_error_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get error trends for the last N hours"""
        since = datetime.now() - timedelta(hours=hours)
        
        with self.get_db_connection() as conn:
            trends = conn.execute('''
                SELECT strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                       COUNT(*) as error_count
                FROM api_errors 
                WHERE timestamp > ? 
                GROUP BY hour
                ORDER BY hour
            ''', (since,)).fetchall()
            
        return {
            'trends': [dict(row) for row in trends],
            'period_hours': hours
        }


class IntegrationMonitor:
    """Monitor third-party service integrations"""
    
    def __init__(self, analytics_manager: APIAnalyticsManager):
        self.analytics = analytics_manager
        self.services = {}
        self.health_checks = {}
        
    def register_service(self, service_name: str, health_check_url: str = None,
                        health_check_func: Callable = None, timeout: int = 30):
        """Register a service for monitoring"""
        self.services[service_name] = {
            'health_check_url': health_check_url,
            'health_check_func': health_check_func,
            'timeout': timeout,
            'last_check': None,
            'status': 'unknown'
        }
        
    def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check health of a specific service"""
        if service_name not in self.services:
            return {'status': 'unknown', 'error': 'Service not registered'}
            
        service = self.services[service_name]
        start_time = time.time()
        
        try:
            if service['health_check_func']:
                # Use custom health check function
                result = service['health_check_func']()
                status = 'healthy' if result else 'unhealthy'
                error_message = None
            elif service['health_check_url']:
                # Use HTTP health check
                import requests
                response = requests.get(
                    service['health_check_url'], 
                    timeout=service['timeout']
                )
                status = 'healthy' if response.status_code == 200 else 'unhealthy'
                error_message = None if response.status_code == 200 else f"HTTP {response.status_code}"
            else:
                status = 'unknown'
                error_message = 'No health check configured'
                
            response_time = time.time() - start_time
            
            # Update service status
            service['status'] = status
            service['last_check'] = datetime.now()
            
            # Track in analytics
            self.analytics.track_integration_health(
                service_name, status, response_time, error_message
            )
            
            return {
                'service_name': service_name,
                'status': status,
                'response_time': response_time,
                'error_message': error_message,
                'last_check': service['last_check'].isoformat()
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            service['status'] = 'unhealthy'
            service['last_check'] = datetime.now()
            
            error_message = str(e)
            
            # Track in analytics
            self.analytics.track_integration_health(
                service_name, 'unhealthy', response_time, error_message
            )
            
            return {
                'service_name': service_name,
                'status': 'unhealthy',
                'response_time': response_time,
                'error_message': error_message,
                'last_check': service['last_check'].isoformat()
            }
            
    def check_all_services(self) -> Dict[str, Any]:
        """Check health of all registered services"""
        results = {}
        for service_name in self.services:
            results[service_name] = self.check_service_health(service_name)
        return results
        
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get current status of a service"""
        if service_name not in self.services:
            return {'status': 'unknown', 'error': 'Service not registered'}
            
        service = self.services[service_name]
        return {
            'service_name': service_name,
            'status': service['status'],
            'last_check': service['last_check'].isoformat() if service['last_check'] else None
        }


class RateLimitController:
    """Advanced rate limiting controller"""
    
    def __init__(self, redis_service, analytics_manager: APIAnalyticsManager):
        self.redis = redis_service
        self.analytics = analytics_manager
        self.rate_limits = {}
        self.custom_limits = {}
        
    def set_rate_limit(self, endpoint: str, limit: int, window: int = 3600, 
                      key_func: Callable = None):
        """Set rate limit for an endpoint"""
        self.rate_limits[endpoint] = {
            'limit': limit,
            'window': window,
            'key_func': key_func
        }
        
    def set_custom_limit(self, key: str, limit: int, window: int = 3600):
        """Set custom rate limit"""
        self.custom_limits[key] = {
            'limit': limit,
            'window': window
        }
        
    def check_rate_limit(self, endpoint: str, identifier: str = None) -> Dict[str, Any]:
        """Check if request is within rate limit"""
        if endpoint not in self.rate_limits:
            return {'allowed': True, 'remaining': float('inf')}
            
        limit_config = self.rate_limits[endpoint]
        
        # Generate rate limit key
        if limit_config['key_func']:
            rate_key = limit_config['key_func'](endpoint, identifier)
        else:
            rate_key = f"rate_limit:{endpoint}:{identifier or 'anonymous'}"
            
        # Check current count
        current_count = self.redis.get(rate_key, prefix='rate_limit') or 0
        
        if current_count >= limit_config['limit']:
            # Track rate limit hit
            self.analytics.track_rate_limit(
                endpoint, identifier or 'anonymous', 'exceeded', current_count
            )
            
            return {
                'allowed': False,
                'remaining': 0,
                'reset_at': self.redis.ttl(rate_key, prefix='rate_limit'),
                'limit': limit_config['limit']
            }
            
        # Update count
        if current_count == 0:
            self.redis.set(rate_key, 1, ttl=limit_config['window'], prefix='rate_limit')
        else:
            self.redis.increment(rate_key, prefix='rate_limit')
            
        return {
            'allowed': True,
            'remaining': limit_config['limit'] - current_count - 1,
            'limit': limit_config['limit'],
            'reset_at': self.redis.ttl(rate_key, prefix='rate_limit')
        }
        
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limit statistics"""
        stats = {}
        for endpoint, config in self.rate_limits.items():
            stats[endpoint] = {
                'limit': config['limit'],
                'window': config['window'],
                'hits_today': self.analytics.rate_limit_hits.get(endpoint, 0)
            }
        return stats


class APIDocumentationGenerator:
    """Auto-generate API documentation"""
    
    def __init__(self):
        self.endpoints = {}
        self.models = {}
        
    def document_endpoint(self, endpoint: str, method: str, func: Callable,
                         description: str = None, parameters: List[Dict] = None,
                         responses: Dict[str, Dict] = None):
        """Document an API endpoint"""
        if endpoint not in self.endpoints:
            self.endpoints[endpoint] = {}
            
        # Extract information from function
        signature = inspect.signature(func)
        docstring = inspect.getdoc(func)
        
        self.endpoints[endpoint][method] = {
            'function': func.__name__,
            'description': description or (docstring.split('\n')[0] if docstring else ''),
            'parameters': parameters or self._extract_parameters(signature),
            'responses': responses or {'200': {'description': 'Success'}},
            'docstring': docstring
        }
        
    def _extract_parameters(self, signature: inspect.Signature) -> List[Dict]:
        """Extract parameters from function signature"""
        parameters = []
        for param_name, param in signature.parameters.items():
            if param_name in ['self', 'cls']:
                continue
                
            param_info = {
                'name': param_name,
                'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'string',
                'required': param.default == inspect.Parameter.empty,
                'default': param.default if param.default != inspect.Parameter.empty else None
            }
            parameters.append(param_info)
            
        return parameters
        
    def generate_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI specification"""
        spec = {
            'openapi': '3.0.0',
            'info': {
                'title': 'VectorCraft API',
                'version': '1.0.0',
                'description': 'VectorCraft API for image vectorization'
            },
            'paths': {}
        }
        
        for endpoint, methods in self.endpoints.items():
            spec['paths'][endpoint] = {}
            
            for method, info in methods.items():
                spec['paths'][endpoint][method.lower()] = {
                    'summary': info['description'],
                    'description': info['docstring'],
                    'parameters': [
                        {
                            'name': param['name'],
                            'in': 'query',
                            'required': param['required'],
                            'schema': {'type': param['type']}
                        }
                        for param in info['parameters']
                    ],
                    'responses': info['responses']
                }
                
        return spec
        
    def generate_html_docs(self) -> str:
        """Generate HTML documentation"""
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>VectorCraft API Documentation</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1, h2, h3 { color: #333; }
                .endpoint { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
                .method { font-weight: bold; color: #007bff; }
                .parameter { margin: 5px 0; }
                .required { color: red; }
            </style>
        </head>
        <body>
            <h1>VectorCraft API Documentation</h1>
        '''
        
        for endpoint, methods in self.endpoints.items():
            html += f'<h2>{endpoint}</h2>'
            
            for method, info in methods.items():
                html += f'''
                <div class="endpoint">
                    <h3><span class="method">{method.upper()}</span> {endpoint}</h3>
                    <p>{info['description']}</p>
                    
                    <h4>Parameters:</h4>
                    <ul>
                '''
                
                for param in info['parameters']:
                    required = '<span class="required">*</span>' if param['required'] else ''
                    html += f'''
                    <li class="parameter">
                        <strong>{param['name']}</strong> {required}
                        - {param['type']}
                        {f" (default: {param['default']})" if param['default'] else ""}
                    </li>
                    '''
                    
                html += '''
                    </ul>
                    
                    <h4>Responses:</h4>
                    <ul>
                '''
                
                for status, response in info['responses'].items():
                    html += f'<li><strong>{status}</strong>: {response["description"]}</li>'
                    
                html += '</ul></div>'
                
        html += '</body></html>'
        return html


class APIService:
    """Service layer for API operations with caching, optimization, analytics, and monitoring"""
    
    def __init__(self):
        self.redis = redis_service
        self.task_manager = task_queue_manager
        self.vectorization_service = vectorization_service
        
        # Initialize analytics and monitoring components
        self.analytics = APIAnalyticsManager()
        self.integration_monitor = IntegrationMonitor(self.analytics)
        self.rate_limit_controller = RateLimitController(self.redis, self.analytics)
        self.documentation_generator = APIDocumentationGenerator()
        
        # Cache configuration
        self.cache_ttl = {
            'short': 300,      # 5 minutes
            'medium': 3600,    # 1 hour
            'long': 86400,     # 24 hours
            'very_long': 604800  # 7 days
        }
        
        # API limits
        self.max_file_size = 16 * 1024 * 1024  # 16MB
        self.max_batch_size = 10
        self.allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
        
        # Response compression threshold
        self.compression_threshold = 1024  # bytes
        
        # Initialize rate limits
        self._setup_rate_limits()
        
        # Register services for monitoring
        self._register_services()
        
        logger.info("API Service initialized with analytics and monitoring")
    
    def _setup_rate_limits(self):
        """Setup default rate limits for API endpoints"""
        # Setup default rate limits
        self.rate_limit_controller.set_rate_limit('/api/vectorize', 100, 3600)  # 100 per hour
        self.rate_limit_controller.set_rate_limit('/api/batch_vectorize', 10, 3600)  # 10 per hour
        self.rate_limit_controller.set_rate_limit('/api/extract_palette', 200, 3600)  # 200 per hour
        self.rate_limit_controller.set_rate_limit('/api/health', 1000, 3600)  # 1000 per hour
        
    def _register_services(self):
        """Register services for monitoring"""
        # Register PayPal service
        self.integration_monitor.register_service(
            'paypal',
            health_check_func=self._check_paypal_health,
            timeout=30
        )
        
        # Register email service
        self.integration_monitor.register_service(
            'email',
            health_check_func=self._check_email_health,
            timeout=30
        )
        
        # Register Redis service
        self.integration_monitor.register_service(
            'redis',
            health_check_func=self._check_redis_health,
            timeout=10
        )
        
        # Register task queue
        self.integration_monitor.register_service(
            'task_queue',
            health_check_func=self._check_task_queue_health,
            timeout=15
        )
        
    def _check_paypal_health(self) -> bool:
        """Check PayPal service health"""
        try:
            from services.paypal_service import paypal_service
            # Simple health check - try to get an access token
            return paypal_service.get_access_token() is not None
        except Exception:
            return False
            
    def _check_email_health(self) -> bool:
        """Check email service health"""
        try:
            from services.email_service import email_service
            # Simple health check - try to connect to SMTP server
            return email_service.test_connection()
        except Exception:
            return False
            
    def _check_redis_health(self) -> bool:
        """Check Redis service health"""
        try:
            return self.redis.health_check().get('healthy', False)
        except Exception:
            return False
            
    def _check_task_queue_health(self) -> bool:
        """Check task queue health"""
        try:
            return self.task_manager.health_check().get('healthy', False)
        except Exception:
            return False
    
    def track_request(self, endpoint: str, method: str, user_id: int = None,
                     status_code: int = None, response_time: float = None,
                     request_size: int = None, response_size: int = None):
        """Track API request for analytics"""
        try:
            self.analytics.track_request(
                endpoint=endpoint,
                method=method,
                user_id=user_id,
                ip_address=getattr(request, 'remote_addr', None),
                user_agent=getattr(request, 'user_agent', {}).get('string', None),
                status_code=status_code,
                response_time=response_time,
                request_size=request_size,
                response_size=response_size
            )
        except Exception as e:
            logger.error(f"Failed to track request: {e}")
            
    def track_api_decorator(self, func: Callable) -> Callable:
        """Decorator to automatically track API requests"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint = request.endpoint or 'unknown'
            method = request.method
            
            try:
                # Check rate limits
                user_id = getattr(request, 'user_id', None)
                rate_limit_result = self.rate_limit_controller.check_rate_limit(
                    endpoint, str(user_id) if user_id else request.remote_addr
                )
                
                if not rate_limit_result['allowed']:
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'limit': rate_limit_result['limit'],
                        'remaining': rate_limit_result['remaining'],
                        'reset_at': rate_limit_result['reset_at']
                    }), 429
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Track successful request
                response_time = time.time() - start_time
                status_code = 200
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                elif isinstance(result, tuple) and len(result) > 1:
                    status_code = result[1]
                
                self.track_request(
                    endpoint=endpoint,
                    method=method,
                    user_id=user_id,
                    status_code=status_code,
                    response_time=response_time,
                    request_size=len(str(request.data)) if request.data else 0,
                    response_size=len(str(result)) if result else 0
                )
                
                return result
                
            except Exception as e:
                # Track error
                response_time = time.time() - start_time
                self.analytics.track_error(
                    endpoint=endpoint,
                    method=method,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    user_id=getattr(request, 'user_id', None),
                    ip_address=request.remote_addr
                )
                
                self.track_request(
                    endpoint=endpoint,
                    method=method,
                    user_id=getattr(request, 'user_id', None),
                    status_code=500,
                    response_time=response_time
                )
                
                raise
                
        return wrapper
    
    def cache_response(self, key: str, ttl: int = None, prefix: str = 'api_cache'):
        """
        Decorator to cache API responses
        
        Args:
            key: Cache key template (can use placeholders)
            ttl: Time to live in seconds
            prefix: Cache key prefix
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    # Generate cache key
                    cache_key = self._generate_cache_key(key, args, kwargs)
                    
                    # Try to get from cache
                    cached_response = self.redis.get(cache_key, prefix=prefix)
                    if cached_response:
                        logger.debug(f"Cache hit for key: {cache_key}")
                        return cached_response
                    
                    # Execute function
                    response = func(*args, **kwargs)
                    
                    # Cache response
                    cache_ttl = ttl or self.cache_ttl['medium']
                    self.redis.set(cache_key, response, ttl=cache_ttl, prefix=prefix)
                    
                    logger.debug(f"Response cached for key: {cache_key}")
                    
                    return response
                    
                except Exception as e:
                    logger.error(f"Cache error in {func.__name__}: {e}")
                    # Execute function without caching
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def rate_limit(self, limit: int, window: int = 3600, key_func: Callable = None):
        """
        Rate limiting decorator
        
        Args:
            limit: Maximum requests per window
            window: Time window in seconds
            key_func: Function to generate rate limit key
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    # Generate rate limit key
                    if key_func:
                        rate_key = key_func(*args, **kwargs)
                    else:
                        rate_key = f"rate_limit:{request.remote_addr}:{func.__name__}"
                    
                    # Check current count
                    current_count = self.redis.get(rate_key, prefix='rate_limit') or 0
                    
                    if current_count >= limit:
                        return jsonify({
                            'error': 'Rate limit exceeded',
                            'limit': limit,
                            'window': window,
                            'retry_after': self.redis.ttl(rate_key, prefix='rate_limit')
                        }), 429
                    
                    # Execute function
                    response = func(*args, **kwargs)
                    
                    # Update count
                    if current_count == 0:
                        self.redis.set(rate_key, 1, ttl=window, prefix='rate_limit')
                    else:
                        self.redis.increment(rate_key, prefix='rate_limit')
                    
                    return response
                    
                except Exception as e:
                    logger.error(f"Rate limit error in {func.__name__}: {e}")
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def validate_request(self, required_fields: List[str] = None, 
                        file_required: bool = False, 
                        max_file_size: int = None):
        """
        Request validation decorator
        
        Args:
            required_fields: List of required fields
            file_required: Whether file upload is required
            max_file_size: Maximum file size in bytes
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    # Validate required fields
                    if required_fields:
                        missing_fields = []
                        for field in required_fields:
                            if field not in request.form and field not in request.json:
                                missing_fields.append(field)
                        
                        if missing_fields:
                            return jsonify({
                                'error': 'Missing required fields',
                                'missing_fields': missing_fields
                            }), 400
                    
                    # Validate file upload
                    if file_required:
                        if 'file' not in request.files:
                            return jsonify({'error': 'No file uploaded'}), 400
                        
                        file = request.files['file']
                        if file.filename == '':
                            return jsonify({'error': 'No file selected'}), 400
                        
                        # Check file extension
                        if not self._allowed_file(file.filename):
                            return jsonify({
                                'error': 'Invalid file type',
                                'allowed_types': list(self.allowed_extensions)
                            }), 400
                        
                        # Check file size
                        file_size = max_file_size or self.max_file_size
                        if hasattr(file, 'content_length') and file.content_length > file_size:
                            return jsonify({
                                'error': 'File too large',
                                'max_size': file_size
                            }), 413
                    
                    return func(*args, **kwargs)
                    
                except RequestEntityTooLarge:
                    return jsonify({
                        'error': 'File too large',
                        'max_size': max_file_size or self.max_file_size
                    }), 413
                except Exception as e:
                    logger.error(f"Request validation error in {func.__name__}: {e}")
                    return jsonify({'error': 'Request validation failed'}), 400
            
            return wrapper
        return decorator
    
    def async_vectorize(self, user_id: int, file_path: str, filename: str,
                       strategy: str = 'vtracer_high_fidelity', 
                       target_time: float = 60.0,
                       vectorization_params: Dict[str, Any] = None,
                       use_palette: bool = False,
                       selected_palette: List[List[int]] = None) -> Dict[str, Any]:
        """
        Submit vectorization task asynchronously
        
        Args:
            user_id: User ID
            file_path: Path to the image file
            filename: Original filename
            strategy: Vectorization strategy
            target_time: Target processing time
            vectorization_params: Custom vectorization parameters
            use_palette: Whether to use custom palette
            selected_palette: Custom color palette
            
        Returns:
            Dict containing task information
        """
        try:
            # Submit task to queue
            task_id = self.task_manager.submit_task(
                task_name='vectorization_tasks.vectorize_image',
                args=[user_id, file_path, filename],
                kwargs={
                    'strategy': strategy,
                    'target_time': target_time,
                    'vectorization_params': vectorization_params,
                    'use_palette': use_palette,
                    'selected_palette': selected_palette
                },
                queue='vectorization',
                user_id=user_id
            )
            
            return {
                'success': True,
                'task_id': task_id,
                'status': 'submitted',
                'estimated_time': target_time,
                'message': 'Vectorization task submitted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to submit async vectorization task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def async_batch_vectorize(self, user_id: int, file_paths: List[str], 
                             filenames: List[str],
                             strategy: str = 'vtracer_high_fidelity',
                             target_time: float = 60.0,
                             vectorization_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Submit batch vectorization task asynchronously
        
        Args:
            user_id: User ID
            file_paths: List of file paths
            filenames: List of original filenames
            strategy: Vectorization strategy
            target_time: Target processing time per file
            vectorization_params: Custom vectorization parameters
            
        Returns:
            Dict containing task information
        """
        try:
            # Validate batch size
            if len(file_paths) > self.max_batch_size:
                return {
                    'success': False,
                    'error': f'Batch size exceeds maximum ({self.max_batch_size})'
                }
            
            # Submit batch task to queue
            task_id = self.task_manager.submit_task(
                task_name='vectorization_tasks.batch_vectorize',
                args=[user_id, file_paths, filenames],
                kwargs={
                    'strategy': strategy,
                    'target_time': target_time,
                    'vectorization_params': vectorization_params
                },
                queue='batch_processing',
                user_id=user_id
            )
            
            return {
                'success': True,
                'task_id': task_id,
                'status': 'submitted',
                'total_files': len(file_paths),
                'estimated_time': target_time * len(file_paths),
                'message': 'Batch vectorization task submitted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to submit batch vectorization task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def async_extract_palettes(self, file_path: str, filename: str) -> Dict[str, Any]:
        """
        Submit palette extraction task asynchronously
        
        Args:
            file_path: Path to the image file
            filename: Original filename
            
        Returns:
            Dict containing task information
        """
        try:
            # Submit task to queue
            task_id = self.task_manager.submit_task(
                task_name='vectorization_tasks.extract_palettes',
                args=[file_path, filename],
                queue='image_analysis'
            )
            
            return {
                'success': True,
                'task_id': task_id,
                'status': 'submitted',
                'message': 'Palette extraction task submitted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to submit palette extraction task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get task status and progress
        
        Args:
            task_id: Task ID
            
        Returns:
            Dict containing task status
        """
        try:
            # Get task info
            task_info = self.task_manager.get_task_info(task_id)
            
            if not task_info:
                return {
                    'success': False,
                    'error': 'Task not found'
                }
            
            # Get progress if available
            progress = self.task_manager.get_task_progress(task_id)
            
            return {
                'success': True,
                'task_id': task_id,
                'status': task_info.status.value,
                'progress': progress,
                'created_at': task_info.created_at.isoformat(),
                'started_at': task_info.started_at.isoformat() if task_info.started_at else None,
                'completed_at': task_info.completed_at.isoformat() if task_info.completed_at else None,
                'error': task_info.error,
                'runtime': task_info.runtime
            }
            
        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_task_result(self, task_id: str, timeout: float = None) -> Dict[str, Any]:
        """
        Get task result
        
        Args:
            task_id: Task ID
            timeout: Wait timeout in seconds
            
        Returns:
            Dict containing task result
        """
        try:
            success, result = self.task_manager.get_task_result(task_id, timeout)
            
            if success:
                return {
                    'success': True,
                    'task_id': task_id,
                    'result': result
                }
            else:
                return {
                    'success': False,
                    'task_id': task_id,
                    'error': result
                }
                
        except Exception as e:
            logger.error(f"Failed to get task result for {task_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cancel_task(self, task_id: str, user_id: int = None) -> Dict[str, Any]:
        """
        Cancel a task
        
        Args:
            task_id: Task ID
            user_id: User ID for authorization
            
        Returns:
            Dict containing cancellation result
        """
        try:
            success = self.task_manager.cancel_task(task_id, user_id)
            
            if success:
                return {
                    'success': True,
                    'task_id': task_id,
                    'message': 'Task cancelled successfully'
                }
            else:
                return {
                    'success': False,
                    'task_id': task_id,
                    'error': 'Failed to cancel task'
                }
                
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @cache_response(key='user_uploads:{user_id}:{limit}', ttl=300)
    def get_user_uploads(self, user_id: int, limit: int = 20) -> Dict[str, Any]:
        """
        Get user's upload history (cached)
        
        Args:
            user_id: User ID
            limit: Maximum number of uploads to return
            
        Returns:
            Dict containing upload history
        """
        try:
            uploads = self.vectorization_service.get_user_uploads(user_id, limit)
            
            return {
                'success': True,
                'uploads': uploads,
                'count': len(uploads)
            }
            
        except Exception as e:
            logger.error(f"Failed to get user uploads for {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @cache_response(key='user_stats:{user_id}', ttl=600)
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's statistics (cached)
        
        Args:
            user_id: User ID
            
        Returns:
            Dict containing user statistics
        """
        try:
            stats = self.vectorization_service.get_user_upload_stats(user_id)
            
            return {
                'success': True,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get user stats for {user_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @cache_response(key='supported_strategies', ttl=86400)
    def get_supported_strategies(self) -> Dict[str, Any]:
        """
        Get supported vectorization strategies (cached)
        
        Returns:
            Dict containing supported strategies
        """
        try:
            strategies = self.vectorization_service.get_supported_strategies()
            
            return {
                'success': True,
                'strategies': strategies
            }
            
        except Exception as e:
            logger.error(f"Failed to get supported strategies: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @cache_response(key='system_health', ttl=60)
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get system health status (cached)
        
        Returns:
            Dict containing system health
        """
        try:
            # Check various system components
            health_status = {
                'overall_healthy': True,
                'components': {},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Check task queue
            task_health = self.task_manager.health_check()
            health_status['components']['task_queue'] = task_health
            
            # Check Redis
            redis_health = self.redis.health_check()
            health_status['components']['redis'] = redis_health
            
            # Check vectorization service
            try:
                strategies = self.vectorization_service.get_supported_strategies()
                health_status['components']['vectorization'] = {
                    'healthy': len(strategies) > 0,
                    'strategies_available': len(strategies)
                }
            except Exception as e:
                health_status['components']['vectorization'] = {
                    'healthy': False,
                    'error': str(e)
                }
            
            # Update overall health
            health_status['overall_healthy'] = all(
                component.get('healthy', False) 
                for component in health_status['components'].values()
            )
            
            return {
                'success': True,
                'health': health_status
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_api_metrics(self) -> Dict[str, Any]:
        """
        Get API metrics
        
        Returns:
            Dict containing API metrics
        """
        try:
            # Get task metrics
            task_metrics = self.task_manager.get_task_metrics()
            
            # Get queue stats
            queue_stats = self.task_manager.get_queue_stats()
            
            # Get worker stats
            worker_stats = self.task_manager.get_worker_stats()
            
            # Get Redis info
            redis_info = self.redis.get_info()
            
            return {
                'success': True,
                'metrics': {
                    'tasks': task_metrics,
                    'queues': queue_stats,
                    'workers': worker_stats,
                    'redis': redis_info,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get API metrics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def invalidate_cache(self, pattern: str = None, prefix: str = 'api_cache') -> Dict[str, Any]:
        """
        Invalidate cache entries
        
        Args:
            pattern: Cache key pattern to invalidate
            prefix: Cache prefix
            
        Returns:
            Dict containing invalidation result
        """
        try:
            if pattern:
                # Invalidate specific pattern
                keys = self.redis.keys(pattern, prefix=prefix)
                for key in keys:
                    self.redis.delete(key, prefix=prefix)
                
                return {
                    'success': True,
                    'invalidated_keys': len(keys)
                }
            else:
                # Flush entire prefix
                success = self.redis.flush_prefix(prefix)
                
                return {
                    'success': success,
                    'message': f'Cache prefix {prefix} flushed'
                }
                
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_cache_key(self, key_template: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from template and arguments"""
        try:
            # Simple placeholder replacement
            cache_key = key_template
            
            # Replace placeholders with actual values
            for i, arg in enumerate(args):
                cache_key = cache_key.replace(f'{{{i}}}', str(arg))
            
            for k, v in kwargs.items():
                cache_key = cache_key.replace(f'{{{k}}}', str(v))
            
            # Add request parameters for uniqueness
            if hasattr(request, 'args'):
                request_params = dict(request.args)
                if request_params:
                    params_hash = hashlib.md5(
                        json.dumps(request_params, sort_keys=True).encode()
                    ).hexdigest()[:8]
                    cache_key = f"{cache_key}:{params_hash}"
            
            return cache_key
            
        except Exception as e:
            logger.error(f"Failed to generate cache key: {e}")
            return f"fallback_key:{int(time.time())}"
    
    def _allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    # New API Management Methods
    
    def get_api_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive API analytics"""
        try:
            analytics_summary = self.analytics.get_analytics_summary(hours)
            top_endpoints = self.analytics.get_top_endpoints()
            error_trends = self.analytics.get_error_trends(hours)
            
            return {
                'success': True,
                'analytics': {
                    'summary': analytics_summary,
                    'top_endpoints': top_endpoints,
                    'error_trends': error_trends,
                    'generated_at': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Failed to get API analytics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of all integrated services"""
        try:
            service_status = self.integration_monitor.check_all_services()
            
            return {
                'success': True,
                'services': service_status,
                'overall_healthy': all(
                    service.get('status') == 'healthy' 
                    for service in service_status.values()
                ),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get integration status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get rate limit configuration and statistics"""
        try:
            rate_limit_stats = self.rate_limit_controller.get_rate_limit_stats()
            
            return {
                'success': True,
                'rate_limits': rate_limit_stats,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_rate_limit(self, endpoint: str, limit: int, window: int = 3600) -> Dict[str, Any]:
        """Update rate limit for an endpoint"""
        try:
            self.rate_limit_controller.set_rate_limit(endpoint, limit, window)
            
            return {
                'success': True,
                'message': f'Rate limit updated for {endpoint}',
                'endpoint': endpoint,
                'limit': limit,
                'window': window
            }
        except Exception as e:
            logger.error(f"Failed to update rate limit: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_api_documentation(self, format: str = 'json') -> Dict[str, Any]:
        """Get API documentation"""
        try:
            if format == 'json':
                openapi_spec = self.documentation_generator.generate_openapi_spec()
                return {
                    'success': True,
                    'format': 'openapi',
                    'documentation': openapi_spec
                }
            elif format == 'html':
                html_docs = self.documentation_generator.generate_html_docs()
                return {
                    'success': True,
                    'format': 'html',
                    'documentation': html_docs
                }
            else:
                return {
                    'success': False,
                    'error': 'Unsupported format. Use "json" or "html"'
                }
        except Exception as e:
            logger.error(f"Failed to get API documentation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def document_api_endpoint(self, endpoint: str, method: str, func: Callable,
                            description: str = None, parameters: List[Dict] = None,
                            responses: Dict[str, Dict] = None) -> Dict[str, Any]:
        """Document an API endpoint"""
        try:
            self.documentation_generator.document_endpoint(
                endpoint, method, func, description, parameters, responses
            )
            
            return {
                'success': True,
                'message': f'Endpoint {method} {endpoint} documented successfully'
            }
        except Exception as e:
            logger.error(f"Failed to document API endpoint: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get API performance metrics"""
        try:
            # Get basic metrics
            api_metrics = self.get_api_metrics()
            
            # Get analytics data
            analytics_data = self.analytics.get_analytics_summary(24)
            
            # Calculate performance indicators
            performance_metrics = {
                'request_volume': {
                    'total_requests_24h': sum(
                        stat['count'] for stat in analytics_data['request_stats']
                    ),
                    'avg_response_time': sum(
                        stat['avg_response_time'] or 0 for stat in analytics_data['request_stats']
                    ) / len(analytics_data['request_stats']) if analytics_data['request_stats'] else 0,
                    'error_rate': len(analytics_data['error_stats']) / max(
                        sum(stat['count'] for stat in analytics_data['request_stats']), 1
                    ) * 100
                },
                'endpoint_performance': [
                    {
                        'endpoint': stat['endpoint'],
                        'method': stat['method'],
                        'request_count': stat['count'],
                        'avg_response_time': stat['avg_response_time'],
                        'max_response_time': stat['max_response_time'],
                        'min_response_time': stat['min_response_time']
                    }
                    for stat in analytics_data['request_stats']
                ],
                'integration_health': self.integration_monitor.check_all_services()
            }
            
            return {
                'success': True,
                'metrics': performance_metrics,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def clear_analytics_data(self, days: int = 30) -> Dict[str, Any]:
        """Clear old analytics data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with self.analytics.get_db_connection() as conn:
                # Clear old request data
                conn.execute(
                    'DELETE FROM api_requests WHERE timestamp < ?',
                    (cutoff_date,)
                )
                
                # Clear old error data
                conn.execute(
                    'DELETE FROM api_errors WHERE timestamp < ?',
                    (cutoff_date,)
                )
                
                # Clear old rate limit data
                conn.execute(
                    'DELETE FROM rate_limits WHERE timestamp < ?',
                    (cutoff_date,)
                )
                
                # Clear old integration health data
                conn.execute(
                    'DELETE FROM integration_health WHERE timestamp < ?',
                    (cutoff_date,)
                )
                
                conn.commit()
            
            return {
                'success': True,
                'message': f'Analytics data older than {days} days cleared'
            }
        except Exception as e:
            logger.error(f"Failed to clear analytics data: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global API service instance
api_service = APIService()


if __name__ == '__main__':
    # Test API service
    logger.info("Testing API service...")
    
    # Test system health
    health = api_service.get_system_health()
    print(f"System health: {health}")
    
    # Test supported strategies
    strategies = api_service.get_supported_strategies()
    print(f"Supported strategies: {strategies}")
    
    # Test metrics
    metrics = api_service.get_api_metrics()
    print(f"API metrics: {metrics}")
    
    logger.info("API service test completed!")