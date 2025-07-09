"""
API Performance Tracking Service
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import sqlite3
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class APIPerformanceTracker:
    """
    Advanced API performance tracking with real-time monitoring
    """
    
    def __init__(self, db_path: str = "api_performance.db"):
        self.db_path = db_path
        self.init_database()
        
        # In-memory tracking for real-time metrics
        self.active_requests = {}
        self.response_times = defaultdict(deque)
        self.request_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.throughput_data = defaultdict(list)
        
        # Performance thresholds
        self.slow_request_threshold = 1.0  # 1 second
        self.error_rate_threshold = 0.05   # 5%
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Background cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_data, daemon=True)
        self.cleanup_thread.start()
        
        logger.info("API Performance Tracker initialized")
    
    def init_database(self):
        """Initialize performance tracking database"""
        with self.get_db_connection() as conn:
            # Request performance table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS request_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    response_time REAL NOT NULL,
                    status_code INTEGER NOT NULL,
                    user_id INTEGER,
                    ip_address TEXT,
                    user_agent TEXT,
                    request_size INTEGER,
                    response_size INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Endpoint statistics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS endpoint_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    total_requests INTEGER DEFAULT 0,
                    total_errors INTEGER DEFAULT 0,
                    avg_response_time REAL DEFAULT 0,
                    max_response_time REAL DEFAULT 0,
                    min_response_time REAL DEFAULT 0,
                    p95_response_time REAL DEFAULT 0,
                    p99_response_time REAL DEFAULT 0,
                    throughput_per_minute REAL DEFAULT 0,
                    error_rate REAL DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(endpoint, method)
                )
            ''')
            
            # Performance alerts table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT,
                    threshold_value REAL,
                    actual_value REAL,
                    severity TEXT DEFAULT 'medium',
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT 0,
                    resolved_at DATETIME
                )
            ''')
            
            # System performance table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_perf_endpoint ON request_performance(endpoint)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_perf_timestamp ON request_performance(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_perf_response_time ON request_performance(response_time)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_stats_endpoint ON endpoint_stats(endpoint)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON performance_alerts(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sys_perf_metric ON system_performance(metric_name)')
    
    @contextmanager
    def get_db_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def start_request_tracking(self, request_id: str, endpoint: str, method: str, 
                             user_id: Optional[int] = None, 
                             ip_address: Optional[str] = None) -> str:
        """Start tracking a request"""
        with self.lock:
            self.active_requests[request_id] = {
                'endpoint': endpoint,
                'method': method,
                'user_id': user_id,
                'ip_address': ip_address,
                'start_time': time.time(),
                'timestamp': datetime.now()
            }
        return request_id
    
    def end_request_tracking(self, request_id: str, status_code: int, 
                           request_size: Optional[int] = None,
                           response_size: Optional[int] = None,
                           user_agent: Optional[str] = None):
        """End tracking a request and record performance data"""
        with self.lock:
            if request_id not in self.active_requests:
                logger.warning(f"Request {request_id} not found in active requests")
                return
            
            request_data = self.active_requests.pop(request_id)
            end_time = time.time()
            response_time = end_time - request_data['start_time']
            
            # Update in-memory metrics
            endpoint_key = f"{request_data['method']}:{request_data['endpoint']}"
            self.response_times[endpoint_key].append(response_time)
            self.request_counts[endpoint_key] += 1
            
            if status_code >= 400:
                self.error_counts[endpoint_key] += 1
            
            # Keep only last 1000 response times per endpoint
            if len(self.response_times[endpoint_key]) > 1000:
                self.response_times[endpoint_key].popleft()
            
            # Record in database
            self._record_request_performance(
                endpoint=request_data['endpoint'],
                method=request_data['method'],
                response_time=response_time,
                status_code=status_code,
                user_id=request_data.get('user_id'),
                ip_address=request_data.get('ip_address'),
                user_agent=user_agent,
                request_size=request_size,
                response_size=response_size,
                timestamp=request_data['timestamp']
            )
            
            # Check for performance alerts
            self._check_performance_alerts(request_data['endpoint'], request_data['method'], response_time, status_code)
    
    def _record_request_performance(self, endpoint: str, method: str, response_time: float,
                                  status_code: int, user_id: Optional[int] = None,
                                  ip_address: Optional[str] = None,
                                  user_agent: Optional[str] = None,
                                  request_size: Optional[int] = None,
                                  response_size: Optional[int] = None,
                                  timestamp: Optional[datetime] = None):
        """Record request performance in database"""
        try:
            with self.get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO request_performance 
                    (endpoint, method, response_time, status_code, user_id, ip_address, 
                     user_agent, request_size, response_size, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (endpoint, method, response_time, status_code, user_id, 
                      ip_address, user_agent, request_size, response_size, 
                      timestamp or datetime.now()))
                
                # Update endpoint statistics
                self._update_endpoint_stats(conn, endpoint, method, response_time, status_code)
        except Exception as e:
            logger.error(f"Error recording request performance: {e}")
    
    def _update_endpoint_stats(self, conn, endpoint: str, method: str, 
                              response_time: float, status_code: int):
        """Update endpoint statistics"""
        try:
            # Get current stats
            current_stats = conn.execute('''
                SELECT * FROM endpoint_stats WHERE endpoint = ? AND method = ?
            ''', (endpoint, method)).fetchone()
            
            if current_stats:
                # Update existing stats
                new_total = current_stats['total_requests'] + 1
                new_errors = current_stats['total_errors'] + (1 if status_code >= 400 else 0)
                
                # Calculate new averages
                new_avg = ((current_stats['avg_response_time'] * current_stats['total_requests']) + response_time) / new_total
                new_max = max(current_stats['max_response_time'], response_time)
                new_min = min(current_stats['min_response_time'], response_time) if current_stats['min_response_time'] > 0 else response_time
                new_error_rate = new_errors / new_total
                
                conn.execute('''
                    UPDATE endpoint_stats 
                    SET total_requests = ?, total_errors = ?, avg_response_time = ?,
                        max_response_time = ?, min_response_time = ?, error_rate = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE endpoint = ? AND method = ?
                ''', (new_total, new_errors, new_avg, new_max, new_min, new_error_rate, endpoint, method))
            else:
                # Insert new stats
                conn.execute('''
                    INSERT INTO endpoint_stats 
                    (endpoint, method, total_requests, total_errors, avg_response_time,
                     max_response_time, min_response_time, error_rate)
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?)
                ''', (endpoint, method, 1 if status_code >= 400 else 0, response_time, 
                      response_time, response_time, 1.0 if status_code >= 400 else 0.0))
        except Exception as e:
            logger.error(f"Error updating endpoint stats: {e}")
    
    def _check_performance_alerts(self, endpoint: str, method: str, 
                                 response_time: float, status_code: int):
        """Check for performance alerts"""
        try:
            alerts = []
            
            # Check slow request threshold
            if response_time > self.slow_request_threshold:
                alerts.append({
                    'alert_type': 'slow_request',
                    'endpoint': endpoint,
                    'method': method,
                    'threshold_value': self.slow_request_threshold,
                    'actual_value': response_time,
                    'severity': 'high' if response_time > self.slow_request_threshold * 2 else 'medium',
                    'message': f'Slow request detected: {response_time:.2f}s for {method} {endpoint}'
                })
            
            # Check error rate
            endpoint_key = f"{method}:{endpoint}"
            if self.request_counts[endpoint_key] >= 10:  # Only check after 10 requests
                error_rate = self.error_counts[endpoint_key] / self.request_counts[endpoint_key]
                if error_rate > self.error_rate_threshold:
                    alerts.append({
                        'alert_type': 'high_error_rate',
                        'endpoint': endpoint,
                        'method': method,
                        'threshold_value': self.error_rate_threshold,
                        'actual_value': error_rate,
                        'severity': 'high' if error_rate > self.error_rate_threshold * 2 else 'medium',
                        'message': f'High error rate detected: {error_rate:.2%} for {method} {endpoint}'
                    })
            
            # Record alerts
            if alerts:
                self._record_alerts(alerts)
        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")
    
    def _record_alerts(self, alerts: List[Dict]):
        """Record performance alerts"""
        try:
            with self.get_db_connection() as conn:
                for alert in alerts:
                    conn.execute('''
                        INSERT INTO performance_alerts 
                        (alert_type, endpoint, method, threshold_value, actual_value, 
                         severity, message)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (alert['alert_type'], alert['endpoint'], alert['method'],
                          alert['threshold_value'], alert['actual_value'], 
                          alert['severity'], alert['message']))
        except Exception as e:
            logger.error(f"Error recording alerts: {e}")
    
    def get_endpoint_performance(self, endpoint: str, method: str = None, 
                               hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics for a specific endpoint"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            with self.get_db_connection() as conn:
                # Base query
                where_clause = "WHERE endpoint = ? AND timestamp > ?"
                params = [endpoint, since]
                
                if method:
                    where_clause += " AND method = ?"
                    params.append(method)
                
                # Get detailed performance data
                perf_data = conn.execute(f'''
                    SELECT 
                        COUNT(*) as total_requests,
                        AVG(response_time) as avg_response_time,
                        MAX(response_time) as max_response_time,
                        MIN(response_time) as min_response_time,
                        COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count,
                        COUNT(CASE WHEN response_time > ? THEN 1 END) as slow_requests
                    FROM request_performance 
                    {where_clause}
                ''', [self.slow_request_threshold] + params).fetchone()
                
                # Get percentiles
                percentiles = conn.execute(f'''
                    SELECT response_time 
                    FROM request_performance 
                    {where_clause}
                    ORDER BY response_time
                ''', params).fetchall()
                
                p95 = p99 = 0
                if percentiles:
                    p95_index = int(len(percentiles) * 0.95)
                    p99_index = int(len(percentiles) * 0.99)
                    p95 = percentiles[p95_index]['response_time'] if p95_index < len(percentiles) else 0
                    p99 = percentiles[p99_index]['response_time'] if p99_index < len(percentiles) else 0
                
                # Calculate derived metrics
                error_rate = (perf_data['error_count'] / perf_data['total_requests']) * 100 if perf_data['total_requests'] > 0 else 0
                slow_request_rate = (perf_data['slow_requests'] / perf_data['total_requests']) * 100 if perf_data['total_requests'] > 0 else 0
                
                return {
                    'endpoint': endpoint,
                    'method': method,
                    'period_hours': hours,
                    'total_requests': perf_data['total_requests'],
                    'avg_response_time': round(perf_data['avg_response_time'] or 0, 3),
                    'max_response_time': round(perf_data['max_response_time'] or 0, 3),
                    'min_response_time': round(perf_data['min_response_time'] or 0, 3),
                    'p95_response_time': round(p95, 3),
                    'p99_response_time': round(p99, 3),
                    'error_count': perf_data['error_count'],
                    'error_rate': round(error_rate, 2),
                    'slow_requests': perf_data['slow_requests'],
                    'slow_request_rate': round(slow_request_rate, 2),
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error getting endpoint performance: {e}")
            return {'error': str(e)}
    
    def get_system_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get overall system performance summary"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            with self.get_db_connection() as conn:
                # Overall metrics
                overall_stats = conn.execute('''
                    SELECT 
                        COUNT(*) as total_requests,
                        AVG(response_time) as avg_response_time,
                        MAX(response_time) as max_response_time,
                        COUNT(CASE WHEN status_code >= 400 THEN 1 END) as total_errors,
                        COUNT(CASE WHEN response_time > ? THEN 1 END) as slow_requests,
                        COUNT(DISTINCT endpoint) as unique_endpoints
                    FROM request_performance 
                    WHERE timestamp > ?
                ''', (self.slow_request_threshold, since)).fetchone()
                
                # Top endpoints by request count
                top_endpoints = conn.execute('''
                    SELECT endpoint, method, COUNT(*) as requests, AVG(response_time) as avg_time
                    FROM request_performance 
                    WHERE timestamp > ?
                    GROUP BY endpoint, method
                    ORDER BY requests DESC
                    LIMIT 10
                ''', (since,)).fetchall()
                
                # Slowest endpoints
                slowest_endpoints = conn.execute('''
                    SELECT endpoint, method, AVG(response_time) as avg_time, COUNT(*) as requests
                    FROM request_performance 
                    WHERE timestamp > ?
                    GROUP BY endpoint, method
                    HAVING requests >= 5
                    ORDER BY avg_time DESC
                    LIMIT 10
                ''', (since,)).fetchall()
                
                # Recent alerts
                recent_alerts = conn.execute('''
                    SELECT * FROM performance_alerts 
                    WHERE timestamp > ? AND resolved = 0
                    ORDER BY timestamp DESC
                    LIMIT 20
                ''', (since,)).fetchall()
                
                # Calculate metrics
                error_rate = (overall_stats['total_errors'] / overall_stats['total_requests']) * 100 if overall_stats['total_requests'] > 0 else 0
                slow_request_rate = (overall_stats['slow_requests'] / overall_stats['total_requests']) * 100 if overall_stats['total_requests'] > 0 else 0
                
                return {
                    'period_hours': hours,
                    'summary': {
                        'total_requests': overall_stats['total_requests'],
                        'avg_response_time': round(overall_stats['avg_response_time'] or 0, 3),
                        'max_response_time': round(overall_stats['max_response_time'] or 0, 3),
                        'total_errors': overall_stats['total_errors'],
                        'error_rate': round(error_rate, 2),
                        'slow_requests': overall_stats['slow_requests'],
                        'slow_request_rate': round(slow_request_rate, 2),
                        'unique_endpoints': overall_stats['unique_endpoints']
                    },
                    'top_endpoints': [dict(row) for row in top_endpoints],
                    'slowest_endpoints': [dict(row) for row in slowest_endpoints],
                    'recent_alerts': [dict(row) for row in recent_alerts],
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error getting system performance summary: {e}")
            return {'error': str(e)}
    
    def get_active_requests(self) -> Dict[str, Any]:
        """Get currently active requests"""
        with self.lock:
            current_time = time.time()
            active = []
            
            for request_id, request_data in self.active_requests.items():
                duration = current_time - request_data['start_time']
                active.append({
                    'request_id': request_id,
                    'endpoint': request_data['endpoint'],
                    'method': request_data['method'],
                    'duration': round(duration, 3),
                    'user_id': request_data.get('user_id'),
                    'ip_address': request_data.get('ip_address'),
                    'started_at': request_data['timestamp'].isoformat()
                })
            
            return {
                'active_requests': active,
                'count': len(active),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_performance_alerts(self, hours: int = 24, severity: str = None) -> List[Dict]:
        """Get performance alerts"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            with self.get_db_connection() as conn:
                where_clause = "WHERE timestamp > ?"
                params = [since]
                
                if severity:
                    where_clause += " AND severity = ?"
                    params.append(severity)
                
                alerts = conn.execute(f'''
                    SELECT * FROM performance_alerts 
                    {where_clause}
                    ORDER BY timestamp DESC
                ''', params).fetchall()
                
                return [dict(row) for row in alerts]
        except Exception as e:
            logger.error(f"Error getting performance alerts: {e}")
            return []
    
    def resolve_alert(self, alert_id: int) -> bool:
        """Resolve a performance alert"""
        try:
            with self.get_db_connection() as conn:
                conn.execute('''
                    UPDATE performance_alerts 
                    SET resolved = 1, resolved_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (alert_id,))
                return True
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
    
    def _cleanup_old_data(self):
        """Background task to cleanup old performance data"""
        while True:
            try:
                # Sleep for 1 hour
                time.sleep(3600)
                
                # Remove data older than 7 days
                cutoff_date = datetime.now() - timedelta(days=7)
                
                with self.get_db_connection() as conn:
                    conn.execute('''
                        DELETE FROM request_performance 
                        WHERE timestamp < ?
                    ''', (cutoff_date,))
                    
                    conn.execute('''
                        DELETE FROM performance_alerts 
                        WHERE timestamp < ? AND resolved = 1
                    ''', (cutoff_date,))
                    
                    conn.execute('''
                        DELETE FROM system_performance 
                        WHERE timestamp < ?
                    ''', (cutoff_date,))
                    
                    conn.commit()
                
                logger.info("Cleaned up old performance data")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
    
    def record_system_metric(self, metric_name: str, metric_value: float):
        """Record a system-wide performance metric"""
        try:
            with self.get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO system_performance (metric_name, metric_value)
                    VALUES (?, ?)
                ''', (metric_name, metric_value))
        except Exception as e:
            logger.error(f"Error recording system metric: {e}")
    
    def get_system_metrics(self, metric_name: str = None, hours: int = 24) -> List[Dict]:
        """Get system performance metrics"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            with self.get_db_connection() as conn:
                if metric_name:
                    metrics = conn.execute('''
                        SELECT * FROM system_performance 
                        WHERE metric_name = ? AND timestamp > ?
                        ORDER BY timestamp DESC
                    ''', (metric_name, since)).fetchall()
                else:
                    metrics = conn.execute('''
                        SELECT * FROM system_performance 
                        WHERE timestamp > ?
                        ORDER BY timestamp DESC
                    ''', (since,)).fetchall()
                
                return [dict(row) for row in metrics]
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return []


# Global instance
api_performance_tracker = APIPerformanceTracker()