#!/usr/bin/env python3
"""
Performance Monitor Service - APM Implementation
Comprehensive performance monitoring with metrics, tracing, and alerting
"""

import time
import threading
import psutil
import statistics
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
import json
import logging
from database import db

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Application Performance Monitor with comprehensive metrics"""
    
    def __init__(self):
        self.metrics = {
            'request_times': defaultdict(deque),
            'request_counts': defaultdict(int),
            'error_counts': defaultdict(int),
            'active_requests': defaultdict(int),
            'system_metrics': deque(maxlen=1000),
            'database_metrics': deque(maxlen=1000),
            'memory_usage': deque(maxlen=1000),
            'cpu_usage': deque(maxlen=1000),
            'vectorization_metrics': deque(maxlen=1000)
        }
        
        # Performance thresholds
        self.thresholds = {
            'response_time_95th': 200,  # 200ms
            'response_time_avg': 100,   # 100ms
            'error_rate': 0.05,         # 5%
            'memory_usage': 85,         # 85%
            'cpu_usage': 80,            # 80%
            'database_query_time': 50   # 50ms
        }
        
        # Start system monitoring thread
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._system_monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        logger.info("Performance Monitor initialized")
    
    def monitor_request(self, endpoint_name):
        """Decorator to monitor request performance"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                self.metrics['active_requests'][endpoint_name] += 1
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Record successful request
                    response_time = (time.time() - start_time) * 1000
                    self._record_request_metric(endpoint_name, response_time, 'success')
                    
                    return result
                    
                except Exception as e:
                    # Record failed request
                    response_time = (time.time() - start_time) * 1000
                    self._record_request_metric(endpoint_name, response_time, 'error')
                    raise
                    
                finally:
                    self.metrics['active_requests'][endpoint_name] -= 1
            
            return wrapper
        return decorator
    
    def monitor_database_query(self, query_type):
        """Decorator to monitor database query performance"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Record query performance
                    query_time = (time.time() - start_time) * 1000
                    self._record_database_metric(query_type, query_time, 'success')
                    
                    return result
                    
                except Exception as e:
                    query_time = (time.time() - start_time) * 1000
                    self._record_database_metric(query_type, query_time, 'error')
                    raise
            
            return wrapper
        return decorator
    
    def monitor_vectorization(self, algorithm_name):
        """Decorator to monitor vectorization performance"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Record vectorization performance
                    processing_time = (time.time() - start_time) * 1000
                    self._record_vectorization_metric(algorithm_name, processing_time, 'success')
                    
                    return result
                    
                except Exception as e:
                    processing_time = (time.time() - start_time) * 1000
                    self._record_vectorization_metric(algorithm_name, processing_time, 'error')
                    raise
            
            return wrapper
        return decorator
    
    def _record_request_metric(self, endpoint, response_time, status):
        """Record request performance metric"""
        timestamp = datetime.now()
        
        # Store in memory for real-time analysis
        self.metrics['request_times'][endpoint].append({
            'time': response_time,
            'timestamp': timestamp,
            'status': status
        })
        
        # Keep only last 1000 entries per endpoint
        if len(self.metrics['request_times'][endpoint]) > 1000:
            self.metrics['request_times'][endpoint].popleft()
        
        # Update counters
        self.metrics['request_counts'][endpoint] += 1
        if status == 'error':
            self.metrics['error_counts'][endpoint] += 1
        
        # Store in database for historical analysis
        db.log_performance_metric(
            metric_type='request_time',
            endpoint=endpoint,
            value=response_time,
            status=status,
            timestamp=timestamp
        )
        
        # Check performance thresholds
        self._check_performance_thresholds(endpoint, response_time)
    
    def _record_database_metric(self, query_type, query_time, status):
        """Record database query performance metric"""
        timestamp = datetime.now()
        
        self.metrics['database_metrics'].append({
            'query_type': query_type,
            'time': query_time,
            'timestamp': timestamp,
            'status': status
        })
        
        # Store in database
        db.log_performance_metric(
            metric_type='database_query',
            endpoint=query_type,
            value=query_time,
            status=status,
            timestamp=timestamp
        )
        
        # Alert if query is too slow
        if query_time > self.thresholds['database_query_time']:
            self._trigger_alert(
                'slow_database_query',
                f'Slow database query: {query_type} took {query_time:.1f}ms',
                'warning'
            )
    
    def _record_vectorization_metric(self, algorithm, processing_time, status):
        """Record vectorization performance metric"""
        timestamp = datetime.now()
        
        self.metrics['vectorization_metrics'].append({
            'algorithm': algorithm,
            'time': processing_time,
            'timestamp': timestamp,
            'status': status
        })
        
        # Store in database
        db.log_performance_metric(
            metric_type='vectorization_time',
            endpoint=algorithm,
            value=processing_time,
            status=status,
            timestamp=timestamp
        )
        
        # Alert if vectorization is too slow
        if processing_time > 30000:  # 30 seconds
            self._trigger_alert(
                'slow_vectorization',
                f'Slow vectorization: {algorithm} took {processing_time/1000:.1f}s',
                'warning'
            )
    
    def _system_monitoring_loop(self):
        """Background thread for system metrics collection"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                memory = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=1)
                disk = psutil.disk_usage('/')
                
                timestamp = datetime.now()
                
                # Store metrics
                system_metric = {
                    'timestamp': timestamp,
                    'memory_percent': memory.percent,
                    'memory_used': memory.used,
                    'memory_total': memory.total,
                    'cpu_percent': cpu_percent,
                    'disk_percent': disk.percent,
                    'disk_used': disk.used,
                    'disk_total': disk.total
                }
                
                self.metrics['system_metrics'].append(system_metric)
                self.metrics['memory_usage'].append(memory.percent)
                self.metrics['cpu_usage'].append(cpu_percent)
                
                # Store in database
                db.log_system_metric(
                    metric_type='system_resources',
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    disk_percent=disk.percent,
                    timestamp=timestamp
                )
                
                # Check system thresholds
                if memory.percent > self.thresholds['memory_usage']:
                    self._trigger_alert(
                        'high_memory_usage',
                        f'High memory usage: {memory.percent:.1f}%',
                        'critical' if memory.percent > 95 else 'warning'
                    )
                
                if cpu_percent > self.thresholds['cpu_usage']:
                    self._trigger_alert(
                        'high_cpu_usage',
                        f'High CPU usage: {cpu_percent:.1f}%',
                        'critical' if cpu_percent > 95 else 'warning'
                    )
                
                time.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in system monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def get_real_time_metrics(self):
        """Get real-time metrics for live dashboard"""
        try:
            current_time = datetime.now()
            
            # Get current system metrics
            if self.metrics['system_metrics']:
                latest_system = self.metrics['system_metrics'][-1]
            else:
                # Fallback to direct measurement
                memory = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=0.1)
                disk = psutil.disk_usage('/')
                
                latest_system = {
                    'timestamp': current_time,
                    'memory_percent': memory.percent,
                    'memory_used': memory.used,
                    'memory_total': memory.total,
                    'cpu_percent': cpu_percent,
                    'disk_percent': disk.percent,
                    'disk_used': disk.used,
                    'disk_total': disk.total
                }
            
            # Get recent response times
            recent_response_times = {}
            for endpoint, times in self.metrics['request_times'].items():
                recent_times = [
                    m['time'] for m in times
                    if m['timestamp'] > current_time - timedelta(minutes=5)
                ]
                if recent_times:
                    recent_response_times[endpoint] = recent_times[-10:]  # Last 10 requests
            
            # Get active requests
            active_requests = dict(self.metrics['active_requests'])
            
            # Get recent vectorization metrics
            recent_vectorization = list(self.metrics['vectorization_metrics'])[-10:]
            
            return {
                'timestamp': current_time.isoformat(),
                'system_metrics': latest_system,
                'recent_response_times': recent_response_times,
                'active_requests': active_requests,
                'vectorization_metrics': recent_vectorization,
                'performance_summary': self._calculate_performance_summary()
            }
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def _calculate_performance_summary(self):
        """Calculate overall performance summary"""
        try:
            summary = {
                'avg_response_time': 0,
                'p95_response_time': 0,
                'error_rate': 0,
                'throughput': 0,
                'system_health': 'healthy'
            }
            
            # Calculate average response time across all endpoints
            all_times = []
            for endpoint, times in self.metrics['request_times'].items():
                recent_times = [
                    m['time'] for m in times
                    if m['timestamp'] > datetime.now() - timedelta(minutes=5)
                ]
                all_times.extend(recent_times)
            
            if all_times:
                summary['avg_response_time'] = statistics.mean(all_times)
                summary['p95_response_time'] = statistics.quantiles(all_times, n=20)[18] if len(all_times) >= 20 else max(all_times)
            
            # Calculate error rate
            total_requests = sum(self.metrics['request_counts'].values())
            total_errors = sum(self.metrics['error_counts'].values())
            if total_requests > 0:
                summary['error_rate'] = total_errors / total_requests
            
            # Calculate throughput (requests per minute)
            recent_requests = sum(self.metrics['active_requests'].values())
            summary['throughput'] = recent_requests
            
            # Determine system health
            if summary['error_rate'] > 0.1:  # 10% error rate
                summary['system_health'] = 'critical'
            elif summary['avg_response_time'] > 500:  # 500ms average
                summary['system_health'] = 'warning'
            elif self.metrics['memory_usage'] and self.metrics['memory_usage'][-1] > 90:
                summary['system_health'] = 'warning'
            
            return summary
            
        except Exception as e:
            logger.error(f"Error calculating performance summary: {e}")
            return {
                'avg_response_time': 0,
                'p95_response_time': 0,
                'error_rate': 0,
                'throughput': 0,
                'system_health': 'unknown'
            }
    
    def _check_performance_thresholds(self, endpoint, response_time):
        """Check if performance thresholds are exceeded"""
        # Get recent metrics for this endpoint
        recent_times = [
            m['time'] for m in self.metrics['request_times'][endpoint]
            if m['timestamp'] > datetime.now() - timedelta(minutes=5)
        ]
        
        if len(recent_times) >= 10:  # Need at least 10 samples
            avg_time = statistics.mean(recent_times)
            p95_time = statistics.quantiles(recent_times, n=20)[18]  # 95th percentile
            
            # Check average response time
            if avg_time > self.thresholds['response_time_avg']:
                self._trigger_alert(
                    'slow_average_response',
                    f'Slow average response time for {endpoint}: {avg_time:.1f}ms',
                    'warning'
                )
            
            # Check 95th percentile response time
            if p95_time > self.thresholds['response_time_95th']:
                self._trigger_alert(
                    'slow_95th_response',
                    f'Slow 95th percentile response time for {endpoint}: {p95_time:.1f}ms',
                    'critical'
                )
    
    def _trigger_alert(self, alert_type, message, severity):
        """Trigger performance alert"""
        try:
            from services.monitoring.alert_manager import alert_manager
            alert_manager.create_alert(
                alert_type=alert_type,
                message=message,
                severity=severity,
                source='performance_monitor'
            )
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")
    
    def get_performance_summary(self, hours=1):
        """Get performance summary for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        summary = {
            'time_period': f'Last {hours} hour(s)',
            'endpoints': {},
            'system_metrics': {},
            'database_metrics': {},
            'vectorization_metrics': {},
            'alerts': []
        }
        
        # Endpoint performance
        for endpoint, metrics in self.metrics['request_times'].items():
            recent_metrics = [
                m for m in metrics 
                if m['timestamp'] > cutoff_time
            ]
            
            if recent_metrics:
                response_times = [m['time'] for m in recent_metrics]
                error_count = sum(1 for m in recent_metrics if m['status'] == 'error')
                
                summary['endpoints'][endpoint] = {
                    'total_requests': len(recent_metrics),
                    'error_count': error_count,
                    'error_rate': error_count / len(recent_metrics) if recent_metrics else 0,
                    'avg_response_time': statistics.mean(response_times),
                    'min_response_time': min(response_times),
                    'max_response_time': max(response_times),
                    'p95_response_time': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
                }
        
        # System metrics
        recent_system = [
            m for m in self.metrics['system_metrics']
            if m['timestamp'] > cutoff_time
        ]
        
        if recent_system:
            summary['system_metrics'] = {
                'avg_memory_usage': statistics.mean(m['memory_percent'] for m in recent_system),
                'max_memory_usage': max(m['memory_percent'] for m in recent_system),
                'avg_cpu_usage': statistics.mean(m['cpu_percent'] for m in recent_system),
                'max_cpu_usage': max(m['cpu_percent'] for m in recent_system),
                'avg_disk_usage': statistics.mean(m['disk_percent'] for m in recent_system)
            }
        
        # Database metrics
        recent_db = [
            m for m in self.metrics['database_metrics']
            if m['timestamp'] > cutoff_time
        ]
        
        if recent_db:
            query_times = [m['time'] for m in recent_db]
            summary['database_metrics'] = {
                'total_queries': len(recent_db),
                'avg_query_time': statistics.mean(query_times),
                'max_query_time': max(query_times),
                'slow_queries': sum(1 for t in query_times if t > self.thresholds['database_query_time'])
            }
        
        # Vectorization metrics
        recent_vector = [
            m for m in self.metrics['vectorization_metrics']
            if m['timestamp'] > cutoff_time
        ]
        
        if recent_vector:
            processing_times = [m['time'] for m in recent_vector]
            summary['vectorization_metrics'] = {
                'total_vectorizations': len(recent_vector),
                'avg_processing_time': statistics.mean(processing_times),
                'max_processing_time': max(processing_times),
                'success_rate': sum(1 for m in recent_vector if m['status'] == 'success') / len(recent_vector)
            }
        
        return summary
    
    def get_real_time_metrics(self):
        """Get real-time performance metrics"""
        return {
            'timestamp': datetime.now().isoformat(),
            'active_requests': dict(self.metrics['active_requests']),
            'system_metrics': {
                'memory_percent': self.metrics['memory_usage'][-1] if self.metrics['memory_usage'] else 0,
                'cpu_percent': self.metrics['cpu_usage'][-1] if self.metrics['cpu_usage'] else 0
            },
            'recent_response_times': {
                endpoint: [m['time'] for m in list(metrics)[-10:]]
                for endpoint, metrics in self.metrics['request_times'].items()
            }
        }
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread.is_alive():
            self.monitoring_thread.join()
        logger.info("Performance monitoring stopped")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Convenience decorators for easy use
def monitor_request(endpoint_name):
    """Decorator for monitoring request performance"""
    return performance_monitor.monitor_request(endpoint_name)

def monitor_database(query_type):
    """Decorator for monitoring database performance"""
    return performance_monitor.monitor_database_query(query_type)

def monitor_vectorization(algorithm_name):
    """Decorator for monitoring vectorization performance"""
    return performance_monitor.monitor_vectorization(algorithm_name)

if __name__ == '__main__':
    # Test performance monitoring
    print("🔍 Testing VectorCraft Performance Monitor...")
    
    # Simulate some metrics
    import random
    
    @monitor_request('test_endpoint')
    def test_function():
        time.sleep(random.uniform(0.05, 0.2))
        return "test result"
    
    # Generate test data
    for i in range(20):
        test_function()
    
    # Get summary
    summary = performance_monitor.get_performance_summary(hours=1)
    print(f"\n📊 Performance Summary:")
    print(json.dumps(summary, indent=2, default=str))
    
    # Stop monitoring
    performance_monitor.stop_monitoring()