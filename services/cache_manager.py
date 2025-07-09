#!/usr/bin/env python3
"""
Cache Manager for VectorCraft Real-Time Analytics
Provides caching mechanisms for performance optimization
"""

import json
import time
import threading
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """In-memory cache manager with TTL support"""
    
    def __init__(self, default_ttl=300):
        self.cache = {}
        self.cache_times = {}
        self.default_ttl = default_ttl  # 5 minutes default
        self.lock = threading.RLock()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
    
    def get(self, key, default=None):
        """Get value from cache"""
        with self.lock:
            if key in self.cache and not self._is_expired(key):
                return self.cache[key]
            return default
    
    def set(self, key, value, ttl=None):
        """Set value in cache with optional TTL"""
        if ttl is None:
            ttl = self.default_ttl
        
        with self.lock:
            self.cache[key] = value
            self.cache_times[key] = {
                'created': time.time(),
                'ttl': ttl
            }
    
    def delete(self, key):
        """Delete key from cache"""
        with self.lock:
            self.cache.pop(key, None)
            self.cache_times.pop(key, None)
    
    def clear(self):
        """Clear all cache"""
        with self.lock:
            self.cache.clear()
            self.cache_times.clear()
    
    def _is_expired(self, key):
        """Check if cache key is expired"""
        if key not in self.cache_times:
            return True
        
        cache_time = self.cache_times[key]
        return time.time() - cache_time['created'] > cache_time['ttl']
    
    def _cleanup_expired(self):
        """Background thread to cleanup expired cache entries"""
        while True:
            try:
                with self.lock:
                    expired_keys = [
                        key for key in self.cache_times.keys()
                        if self._is_expired(key)
                    ]
                    
                    for key in expired_keys:
                        self.cache.pop(key, None)
                        self.cache_times.pop(key, None)
                
                time.sleep(60)  # Cleanup every minute
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                time.sleep(60)
    
    def get_stats(self):
        """Get cache statistics"""
        with self.lock:
            return {
                'size': len(self.cache),
                'memory_usage': sum(len(str(v)) for v in self.cache.values()),
                'hit_ratio': getattr(self, '_hit_ratio', 0.0)
            }

class MetricsCache:
    """Specialized cache for metrics data"""
    
    def __init__(self):
        self.cache_manager = CacheManager(default_ttl=60)  # 1 minute TTL
        self.aggregated_cache = CacheManager(default_ttl=300)  # 5 minutes for aggregated data
        
    def get_live_metrics(self):
        """Get cached live metrics"""
        return self.cache_manager.get('live_metrics')
    
    def set_live_metrics(self, metrics):
        """Cache live metrics"""
        self.cache_manager.set('live_metrics', metrics, ttl=30)  # 30 seconds
    
    def get_revenue_analytics(self, timeframe):
        """Get cached revenue analytics"""
        key = f'revenue_analytics_{timeframe}'
        return self.aggregated_cache.get(key)
    
    def set_revenue_analytics(self, timeframe, data):
        """Cache revenue analytics"""
        key = f'revenue_analytics_{timeframe}'
        ttl = 300 if timeframe == 'hourly' else 600  # 5min for hourly, 10min for daily/weekly
        self.aggregated_cache.set(key, data, ttl=ttl)
    
    def get_user_activity(self):
        """Get cached user activity"""
        return self.cache_manager.get('user_activity')
    
    def set_user_activity(self, data):
        """Cache user activity data"""
        self.cache_manager.set('user_activity', data, ttl=120)  # 2 minutes
    
    def get_performance_metrics(self):
        """Get cached performance metrics"""
        return self.cache_manager.get('performance_metrics')
    
    def set_performance_metrics(self, data):
        """Cache performance metrics"""
        self.cache_manager.set('performance_metrics', data, ttl=60)  # 1 minute
    
    def invalidate_related(self, metric_type):
        """Invalidate related cached data"""
        if metric_type in ['transaction', 'payment']:
            self.cache_manager.delete('live_metrics')
            self.aggregated_cache.delete('revenue_analytics_hourly')
            self.aggregated_cache.delete('revenue_analytics_daily')
            self.aggregated_cache.delete('revenue_analytics_weekly')
        elif metric_type == 'user_activity':
            self.cache_manager.delete('user_activity')
        elif metric_type == 'performance':
            self.cache_manager.delete('performance_metrics')
    
    def get_health_status(self):
        """Get cached health status"""
        return self.cache_manager.get('health_status')
    
    def set_health_status(self, data):
        """Cache health status"""
        self.cache_manager.set('health_status', data, ttl=30)  # 30 seconds

class ErrorHandler:
    """Centralized error handling for analytics"""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.error_times = defaultdict(list)
        self.circuit_breakers = {}
    
    def handle_api_error(self, endpoint, error):
        """Handle API errors with circuit breaker pattern"""
        error_key = f"{endpoint}_error"
        self.error_counts[error_key] += 1
        self.error_times[error_key].append(time.time())
        
        # Clean old errors (last 5 minutes)
        cutoff_time = time.time() - 300
        self.error_times[error_key] = [
            t for t in self.error_times[error_key] 
            if t > cutoff_time
        ]
        
        # Check if circuit breaker should trip
        if len(self.error_times[error_key]) > 10:  # 10 errors in 5 minutes
            self.circuit_breakers[endpoint] = {
                'tripped': True,
                'trip_time': time.time(),
                'reset_time': time.time() + 300  # Reset after 5 minutes
            }
            logger.warning(f"Circuit breaker tripped for {endpoint}")
    
    def is_circuit_open(self, endpoint):
        """Check if circuit breaker is open"""
        breaker = self.circuit_breakers.get(endpoint)
        if not breaker:
            return False
        
        if breaker['tripped'] and time.time() > breaker['reset_time']:
            # Reset circuit breaker
            self.circuit_breakers[endpoint] = {
                'tripped': False,
                'trip_time': None,
                'reset_time': None
            }
            logger.info(f"Circuit breaker reset for {endpoint}")
            return False
        
        return breaker['tripped']
    
    def get_error_summary(self):
        """Get error summary for dashboard"""
        return {
            'total_errors': sum(self.error_counts.values()),
            'error_by_endpoint': dict(self.error_counts),
            'active_circuit_breakers': [
                endpoint for endpoint, breaker in self.circuit_breakers.items()
                if breaker.get('tripped', False)
            ]
        }

class RateLimiter:
    """Rate limiting for API endpoints"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = threading.RLock()
    
    def is_allowed(self, identifier, limit=100, window=60):
        """Check if request is allowed (requests per minute)"""
        with self.lock:
            now = time.time()
            cutoff = now - window
            
            # Clean old requests
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > cutoff
            ]
            
            # Check if limit exceeded
            if len(self.requests[identifier]) >= limit:
                return False
            
            # Record this request
            self.requests[identifier].append(now)
            return True
    
    def get_stats(self):
        """Get rate limiting statistics"""
        with self.lock:
            return {
                'active_identifiers': len(self.requests),
                'total_requests': sum(len(reqs) for reqs in self.requests.values())
            }

# Global instances
metrics_cache = MetricsCache()
error_handler = ErrorHandler()
rate_limiter = RateLimiter()

# Decorator for caching API responses
def cache_response(ttl=300, cache_key_func=None):
    """Decorator to cache API responses"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = metrics_cache.cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            try:
                result = func(*args, **kwargs)
                metrics_cache.cache_manager.set(cache_key, result, ttl=ttl)
                return result
            except Exception as e:
                error_handler.handle_api_error(func.__name__, e)
                raise
        
        return wrapper
    return decorator

# Decorator for error handling
def handle_errors(fallback_response=None):
    """Decorator for error handling with fallback"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_api_error(func.__name__, e)
                logger.error(f"Error in {func.__name__}: {e}")
                
                if fallback_response is not None:
                    return fallback_response
                return {'success': False, 'error': str(e)}
        
        return wrapper
    return decorator

if __name__ == '__main__':
    # Test cache manager
    print("🧪 Testing Cache Manager...")
    
    cache = CacheManager(default_ttl=2)
    
    # Test basic operations
    cache.set('test_key', 'test_value')
    print(f"Get: {cache.get('test_key')}")
    
    # Test TTL
    print("Waiting for TTL expiration...")
    time.sleep(3)
    print(f"After TTL: {cache.get('test_key', 'expired')}")
    
    # Test metrics cache
    print("\n📊 Testing Metrics Cache...")
    metrics_cache.set_live_metrics({'cpu': 50, 'memory': 60})
    print(f"Live metrics: {metrics_cache.get_live_metrics()}")
    
    print("\n✅ Cache manager tests completed!")