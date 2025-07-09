#!/usr/bin/env python3
"""
API Performance Tracking System
Real-time API monitoring, performance analytics, and endpoint optimization
"""

import time
import json
import logging
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
from flask import request, g
import psutil
from database import db
from services.monitoring.system_logger import system_logger

logger = logging.getLogger(__name__)

class APIPerformanceMonitor:
    """Advanced API performance monitoring and analytics"""
    
    def __init__(self):
        self.endpoint_stats = defaultdict(lambda: {
            'request_count': 0,
            'total_response_time': 0,
            'avg_response_time': 0,
            'max_response_time': 0,
            'min_response_time': float('inf'),
            'error_count': 0,
            'error_rate': 0,
            'status_codes': defaultdict(int),
            'last_request': None,
            'peak_memory_usage': 0,
            'peak_cpu_usage': 0
        })
        
        # Real-time metrics
        self.real_time_requests = deque(maxlen=1000)
        self.active_requests = {}
        self.request_counter = 0
        
        # Performance thresholds
        self.slow_request_threshold = 1000  # 1 second
        self.critical_request_threshold = 5000  # 5 seconds
        self.error_rate_threshold = 0.05  # 5%
        self.memory_threshold = 80  # 80% memory usage
        
        # Monitoring settings
        self.collect_detailed_metrics = True
        self.track_user_agents = True
        self.track_ip_addresses = True
        
        # Thread safety
        self.stats_lock = threading.Lock()
        
        # Initialize monitoring
        self._setup_monitoring()
        
        logger.info("API Performance Monitor initialized")
    
    def _setup_monitoring(self):
        """Set up API monitoring infrastructure"""
        try:
            # Create monitoring tables
            self._create_monitoring_tables()
            
            # Start background monitoring
            self._start_background_monitoring()
            
        except Exception as e:
            logger.error(f"Failed to setup API monitoring: {e}")
    
    def _create_monitoring_tables(self):
        """Create API monitoring tables"""
        monitoring_tables = [
            '''CREATE TABLE IF NOT EXISTS api_request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                status_code INTEGER,
                response_time_ms REAL NOT NULL,
                request_size_bytes INTEGER,
                response_size_bytes INTEGER,
                user_agent TEXT,
                ip_address TEXT,
                user_id TEXT,
                memory_usage_mb REAL,
                cpu_usage_percent REAL,
                error_message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            
            '''CREATE TABLE IF NOT EXISTS api_endpoint_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                request_count INTEGER NOT NULL,
                avg_response_time_ms REAL NOT NULL,
                max_response_time_ms REAL NOT NULL,
                min_response_time_ms REAL NOT NULL,
                error_count INTEGER NOT NULL,
                error_rate REAL NOT NULL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            
            '''CREATE TABLE IF NOT EXISTS api_performance_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                severity TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical')) NOT NULL,
                message TEXT NOT NULL,
                metrics TEXT,
                resolved BOOLEAN DEFAULT FALSE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            
            '''CREATE TABLE IF NOT EXISTS api_rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                request_count INTEGER NOT NULL,
                window_start DATETIME NOT NULL,
                blocked_count INTEGER DEFAULT 0,
                last_request DATETIME DEFAULT CURRENT_TIMESTAMP
            )'''
        ]
        
        try:
            with db.get_connection() as conn:
                for table_sql in monitoring_tables:
                    conn.execute(table_sql)
                
                # Create indexes for performance
                performance_indexes = [
                    'CREATE INDEX IF NOT EXISTS idx_api_log_endpoint_time ON api_request_log(endpoint, timestamp)',
                    'CREATE INDEX IF NOT EXISTS idx_api_log_status ON api_request_log(status_code, timestamp)',
                    'CREATE INDEX IF NOT EXISTS idx_api_log_response_time ON api_request_log(response_time_ms, timestamp)',
                    'CREATE INDEX IF NOT EXISTS idx_api_stats_endpoint ON api_endpoint_stats(endpoint, method)',
                    'CREATE INDEX IF NOT EXISTS idx_api_alerts_resolved ON api_performance_alerts(resolved, timestamp)',
                    'CREATE INDEX IF NOT EXISTS idx_rate_limits_ip ON api_rate_limits(ip_address, window_start)'
                ]
                
                for index_sql in performance_indexes:
                    conn.execute(index_sql)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to create API monitoring tables: {e}")
    
    def _start_background_monitoring(self):
        """Start background monitoring thread"""
        def monitor_thread():
            while True:
                try:
                    self._update_endpoint_statistics()
                    self._check_performance_alerts()
                    self._cleanup_old_data()
                    time.sleep(60)  # Run every minute
                except Exception as e:
                    logger.error(f"Background API monitoring error: {e}")
                    time.sleep(30)
        
        thread = threading.Thread(target=monitor_thread, daemon=True)
        thread.start()
    
    def _update_endpoint_statistics(self):
        """Update endpoint statistics in database"""
        try:
            with self.stats_lock:
                stats_to_update = dict(self.endpoint_stats)
            
            with db.get_connection() as conn:
                for endpoint, stats in stats_to_update.items():
                    # Update or insert endpoint stats
                    conn.execute('''
                        INSERT OR REPLACE INTO api_endpoint_stats
                        (endpoint, method, request_count, avg_response_time_ms, 
                         max_response_time_ms, min_response_time_ms, error_count, error_rate)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        endpoint, 'ALL', stats['request_count'], stats['avg_response_time'],
                        stats['max_response_time'], stats['min_response_time'],
                        stats['error_count'], stats['error_rate']
                    ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update endpoint statistics: {e}")
    
    def _check_performance_alerts(self):
        """Check for performance alerts"""
        try:
            with self.stats_lock:
                for endpoint, stats in self.endpoint_stats.items():
                    # Check for slow endpoints
                    if stats['avg_response_time'] > self.critical_request_threshold:
                        self._create_alert(
                            'slow_endpoint', endpoint, 'critical',
                            f'Endpoint {endpoint} has critical response time: {stats["avg_response_time"]:.1f}ms',
                            stats
                        )
                    elif stats['avg_response_time'] > self.slow_request_threshold:
                        self._create_alert(
                            'slow_endpoint', endpoint, 'high',
                            f'Endpoint {endpoint} has slow response time: {stats["avg_response_time"]:.1f}ms',
                            stats
                        )
                    
                    # Check error rates
                    if stats['error_rate'] > self.error_rate_threshold:
                        self._create_alert(
                            'high_error_rate', endpoint, 'high',
                            f'Endpoint {endpoint} has high error rate: {stats["error_rate"]:.1%}',
                            stats
                        )
                
        except Exception as e:
            logger.error(f"Failed to check performance alerts: {e}")
    
    def _create_alert(self, alert_type, endpoint, severity, message, metrics):
        """Create a performance alert"""
        try:
            with db.get_connection() as conn:
                # Check if similar alert already exists
                cursor = conn.execute('''
                    SELECT id FROM api_performance_alerts
                    WHERE alert_type = ? AND endpoint = ? AND resolved = FALSE
                    AND timestamp > datetime('now', '-1 hour')
                ''', (alert_type, endpoint))
                
                if cursor.fetchone():
                    return  # Alert already exists
                
                # Create new alert
                conn.execute('''
                    INSERT INTO api_performance_alerts
                    (alert_type, endpoint, severity, message, metrics)
                    VALUES (?, ?, ?, ?, ?)
                ''', (alert_type, endpoint, severity, message, json.dumps(metrics)))
                
                conn.commit()
                
                # Log to system logger
                system_logger.log_system_event(
                    level=severity,
                    component='api_monitor',
                    message=message,
                    details=metrics
                )
                
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        try:
            with db.get_connection() as conn:
                # Clean up old request logs (keep 30 days)
                conn.execute('''
                    DELETE FROM api_request_log
                    WHERE timestamp < datetime('now', '-30 days')
                ''')
                
                # Clean up old rate limit data (keep 7 days)
                conn.execute('''
                    DELETE FROM api_rate_limits
                    WHERE window_start < datetime('now', '-7 days')
                ''')
                
                # Clean up resolved alerts (keep 7 days)
                conn.execute('''
                    DELETE FROM api_performance_alerts
                    WHERE resolved = TRUE AND timestamp < datetime('now', '-7 days')
                ''')
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    def monitor_request(self, endpoint=None, track_memory=True, track_cpu=True):
        """Decorator to monitor API request performance"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate request ID
                request_id = f"req_{int(time.time() * 1000)}_{threading.current_thread().ident}"
                
                # Get request details
                endpoint_name = endpoint or getattr(request, 'endpoint', 'unknown')
                method = getattr(request, 'method', 'UNKNOWN')
                
                # Start monitoring
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024 if track_memory else 0
                start_cpu = psutil.Process().cpu_percent() if track_cpu else 0
                
                # Track active request
                self.active_requests[request_id] = {
                    'endpoint': endpoint_name,
                    'method': method,
                    'start_time': start_time,
                    'thread_id': threading.current_thread().ident
                }
                
                try:
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Calculate metrics
                    response_time = (time.time() - start_time) * 1000
                    end_memory = psutil.Process().memory_info().rss / 1024 / 1024 if track_memory else 0
                    end_cpu = psutil.Process().cpu_percent() if track_cpu else 0
                    
                    memory_usage = end_memory - start_memory if track_memory else 0
                    cpu_usage = end_cpu - start_cpu if track_cpu else 0
                    
                    # Get status code
                    status_code = getattr(result, 'status_code', 200) if hasattr(result, 'status_code') else 200
                    
                    # Update statistics
                    self._update_request_stats(
                        endpoint_name, response_time, status_code, 
                        memory_usage, cpu_usage, None
                    )
                    
                    # Log request
                    self._log_api_request(
                        request_id, endpoint_name, method, status_code,
                        response_time, memory_usage, cpu_usage, None
                    )
                    
                    # Check for performance issues
                    self._check_request_performance(endpoint_name, response_time, status_code)
                    
                    return result
                    
                except Exception as e:
                    # Calculate error metrics
                    response_time = (time.time() - start_time) * 1000
                    end_memory = psutil.Process().memory_info().rss / 1024 / 1024 if track_memory else 0
                    memory_usage = end_memory - start_memory if track_memory else 0
                    
                    # Update error statistics
                    self._update_request_stats(
                        endpoint_name, response_time, 500, 
                        memory_usage, 0, str(e)
                    )
                    
                    # Log error request
                    self._log_api_request(
                        request_id, endpoint_name, method, 500,
                        response_time, memory_usage, 0, str(e)
                    )
                    
                    raise
                    
                finally:
                    # Remove from active requests
                    self.active_requests.pop(request_id, None)
            
            return wrapper
        return decorator
    
    def _update_request_stats(self, endpoint, response_time, status_code, 
                            memory_usage, cpu_usage, error_message):
        """Update request statistics"""
        try:
            with self.stats_lock:
                stats = self.endpoint_stats[endpoint]
                
                # Update counters
                stats['request_count'] += 1
                stats['total_response_time'] += response_time
                stats['avg_response_time'] = stats['total_response_time'] / stats['request_count']
                stats['max_response_time'] = max(stats['max_response_time'], response_time)
                stats['min_response_time'] = min(stats['min_response_time'], response_time)
                stats['last_request'] = datetime.now().isoformat()
                
                # Update memory and CPU peaks
                stats['peak_memory_usage'] = max(stats['peak_memory_usage'], memory_usage)
                stats['peak_cpu_usage'] = max(stats['peak_cpu_usage'], cpu_usage)
                
                # Update error stats
                if error_message or status_code >= 400:
                    stats['error_count'] += 1
                
                stats['error_rate'] = stats['error_count'] / stats['request_count']
                
                # Update status codes
                stats['status_codes'][status_code] += 1
                
                # Add to real-time metrics
                self.real_time_requests.append({
                    'endpoint': endpoint,
                    'response_time': response_time,
                    'status_code': status_code,
                    'memory_usage': memory_usage,
                    'cpu_usage': cpu_usage,
                    'timestamp': datetime.now().isoformat(),
                    'error': error_message is not None
                })
                
        except Exception as e:
            logger.error(f"Failed to update request stats: {e}")
    
    def _log_api_request(self, request_id, endpoint, method, status_code,
                        response_time, memory_usage, cpu_usage, error_message):
        """Log API request to database"""
        try:
            # Get request details
            user_agent = getattr(request, 'user_agent', {}).string if hasattr(request, 'user_agent') else None
            ip_address = getattr(request, 'remote_addr', None) if hasattr(request, 'remote_addr') else None
            user_id = getattr(g, 'user_id', None) if hasattr(g, 'user_id') else None
            
            # Get request/response sizes
            request_size = len(getattr(request, 'data', b'')) if hasattr(request, 'data') else 0
            
            with db.get_connection() as conn:
                conn.execute('''
                    INSERT INTO api_request_log
                    (request_id, endpoint, method, status_code, response_time_ms,
                     request_size_bytes, user_agent, ip_address, user_id,
                     memory_usage_mb, cpu_usage_percent, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    request_id, endpoint, method, status_code, response_time,
                    request_size, user_agent, ip_address, user_id,
                    memory_usage, cpu_usage, error_message
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log API request: {e}")
    
    def _check_request_performance(self, endpoint, response_time, status_code):
        """Check individual request performance"""
        try:
            # Check for slow requests
            if response_time > self.critical_request_threshold:
                system_logger.log_system_event(
                    level='critical',
                    component='api_monitor',
                    message=f'Critical slow request: {endpoint}',
                    details={
                        'endpoint': endpoint,
                        'response_time': response_time,
                        'status_code': status_code,
                        'threshold': self.critical_request_threshold
                    }
                )
            elif response_time > self.slow_request_threshold:
                system_logger.log_system_event(
                    level='warning',
                    component='api_monitor',
                    message=f'Slow request: {endpoint}',
                    details={
                        'endpoint': endpoint,
                        'response_time': response_time,
                        'status_code': status_code,
                        'threshold': self.slow_request_threshold
                    }
                )
            
            # Check for errors
            if status_code >= 500:
                system_logger.log_system_event(
                    level='error',
                    component='api_monitor',
                    message=f'Server error: {endpoint}',
                    details={
                        'endpoint': endpoint,
                        'status_code': status_code,
                        'response_time': response_time
                    }
                )
            
        except Exception as e:
            logger.error(f"Failed to check request performance: {e}")
    
    def get_performance_dashboard(self):
        """Get API performance dashboard data"""
        try:
            dashboard_data = {
                'real_time_requests': list(self.real_time_requests)[-100:],  # Last 100 requests
                'endpoint_statistics': dict(self.endpoint_stats),
                'active_requests': len(self.active_requests),
                'performance_metrics': self._get_performance_metrics(),
                'slow_endpoints': self._get_slow_endpoints(),
                'error_analysis': self._get_error_analysis(),
                'traffic_patterns': self._get_traffic_patterns(),
                'active_alerts': self._get_active_alerts()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to get performance dashboard: {e}")
            return {}
    
    def _get_performance_metrics(self):
        """Get overall performance metrics"""
        try:
            with db.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_requests,
                        AVG(response_time_ms) as avg_response_time,
                        MAX(response_time_ms) as max_response_time,
                        MIN(response_time_ms) as min_response_time,
                        SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count,
                        SUM(CASE WHEN response_time_ms > ? THEN 1 ELSE 0 END) as slow_requests
                    FROM api_request_log
                    WHERE timestamp > datetime('now', '-1 hour')
                ''', (self.slow_request_threshold,))
                
                row = cursor.fetchone()
                
                if row and row[0] > 0:
                    return {
                        'total_requests': row[0],
                        'avg_response_time': row[1],
                        'max_response_time': row[2],
                        'min_response_time': row[3],
                        'error_count': row[4],
                        'error_rate': row[4] / row[0],
                        'slow_requests': row[5],
                        'slow_request_rate': row[5] / row[0]
                    }
                
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}
    
    def _get_slow_endpoints(self):
        """Get slowest endpoints"""
        try:
            with db.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT endpoint, AVG(response_time_ms) as avg_time, COUNT(*) as count
                    FROM api_request_log
                    WHERE timestamp > datetime('now', '-24 hours')
                    GROUP BY endpoint
                    ORDER BY avg_time DESC
                    LIMIT 10
                ''')
                
                slow_endpoints = []
                for row in cursor.fetchall():
                    slow_endpoints.append({
                        'endpoint': row[0],
                        'avg_time': row[1],
                        'count': row[2]
                    })
                
                return slow_endpoints
                
        except Exception as e:
            logger.error(f"Failed to get slow endpoints: {e}")
            return []
    
    def _get_error_analysis(self):
        """Get error analysis data"""
        try:
            with db.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT status_code, COUNT(*) as count, endpoint
                    FROM api_request_log
                    WHERE status_code >= 400 AND timestamp > datetime('now', '-24 hours')
                    GROUP BY status_code, endpoint
                    ORDER BY count DESC
                    LIMIT 20
                ''')
                
                errors = []
                for row in cursor.fetchall():
                    errors.append({
                        'status_code': row[0],
                        'count': row[1],
                        'endpoint': row[2]
                    })
                
                return errors
                
        except Exception as e:
            logger.error(f"Failed to get error analysis: {e}")
            return []
    
    def _get_traffic_patterns(self):
        """Get traffic patterns over time"""
        try:
            with db.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT 
                        datetime(timestamp, 'localtime', 'start of hour') as hour,
                        COUNT(*) as request_count,
                        AVG(response_time_ms) as avg_response_time
                    FROM api_request_log
                    WHERE timestamp > datetime('now', '-24 hours')
                    GROUP BY datetime(timestamp, 'localtime', 'start of hour')
                    ORDER BY hour
                ''')
                
                patterns = []
                for row in cursor.fetchall():
                    patterns.append({
                        'hour': row[0],
                        'request_count': row[1],
                        'avg_response_time': row[2]
                    })
                
                return patterns
                
        except Exception as e:
            logger.error(f"Failed to get traffic patterns: {e}")
            return []
    
    def _get_active_alerts(self):
        """Get active performance alerts"""
        try:
            with db.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT alert_type, endpoint, severity, message, timestamp
                    FROM api_performance_alerts
                    WHERE resolved = FALSE
                    ORDER BY timestamp DESC
                    LIMIT 50
                ''')
                
                alerts = []
                for row in cursor.fetchall():
                    alerts.append({
                        'type': row[0],
                        'endpoint': row[1],
                        'severity': row[2],
                        'message': row[3],
                        'timestamp': row[4]
                    })
                
                return alerts
                
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
    
    def get_endpoint_analytics(self, endpoint, hours=24):
        """Get detailed analytics for specific endpoint"""
        try:
            with db.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT 
                        response_time_ms,
                        status_code,
                        memory_usage_mb,
                        cpu_usage_percent,
                        timestamp
                    FROM api_request_log
                    WHERE endpoint = ? AND timestamp > datetime('now', '-{} hours')
                    ORDER BY timestamp DESC
                '''.format(hours), (endpoint,))
                
                analytics = []
                for row in cursor.fetchall():
                    analytics.append({
                        'response_time': row[0],
                        'status_code': row[1],
                        'memory_usage': row[2],
                        'cpu_usage': row[3],
                        'timestamp': row[4]
                    })
                
                return analytics
                
        except Exception as e:
            logger.error(f"Failed to get endpoint analytics: {e}")
            return []


# Global API performance monitor instance
api_monitor = APIPerformanceMonitor()

# Convenience decorator for easy use
def monitor_api_request(endpoint=None, track_memory=True, track_cpu=True):
    """Decorator for monitoring API request performance"""
    return api_monitor.monitor_request(endpoint, track_memory, track_cpu)

if __name__ == '__main__':
    # Test API performance monitoring
    print("🌐 Testing VectorCraft API Performance Monitor...")
    
    # Get dashboard data
    dashboard = api_monitor.get_performance_dashboard()
    
    print(f"\n📊 API Performance Dashboard:")
    print(f"Real-time requests: {len(dashboard.get('real_time_requests', []))}")
    print(f"Endpoint statistics: {len(dashboard.get('endpoint_statistics', {}))}")
    print(f"Active requests: {dashboard.get('active_requests', 0)}")
    print(f"Slow endpoints: {len(dashboard.get('slow_endpoints', []))}")
    print(f"Error analysis: {len(dashboard.get('error_analysis', []))}")
    print(f"Active alerts: {len(dashboard.get('active_alerts', []))}")
    
    # Get performance metrics
    metrics = dashboard.get('performance_metrics', {})
    print(f"\n⚡ Performance Metrics:")
    print(f"Total requests (1h): {metrics.get('total_requests', 0)}")
    print(f"Average response time: {metrics.get('avg_response_time', 0):.1f}ms")
    print(f"Error rate: {metrics.get('error_rate', 0):.1%}")
    print(f"Slow request rate: {metrics.get('slow_request_rate', 0):.1%}")