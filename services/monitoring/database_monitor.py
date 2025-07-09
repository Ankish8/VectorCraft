#!/usr/bin/env python3
"""
Enhanced Database Performance Monitoring System
Advanced database monitoring, query optimization, and performance analytics
"""

import sqlite3
import time
import json
import logging
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
from database import db
from services.monitoring.system_logger import system_logger

logger = logging.getLogger(__name__)

class DatabasePerformanceMonitor:
    """Advanced database performance monitoring and optimization"""
    
    def __init__(self):
        self.query_cache = {}
        self.query_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'avg_time': 0,
            'max_time': 0,
            'min_time': float('inf'),
            'errors': 0,
            'last_executed': None
        })
        
        # Real-time monitoring
        self.real_time_metrics = deque(maxlen=1000)
        self.connection_pool_stats = {
            'active_connections': 0,
            'max_connections': 10,
            'connection_errors': 0,
            'pool_exhausted_count': 0
        }
        
        # Performance thresholds
        self.slow_query_threshold = 100  # 100ms
        self.critical_query_threshold = 500  # 500ms
        self.connection_timeout = 30  # 30 seconds
        
        # Lock for thread safety
        self.stats_lock = threading.Lock()
        
        # Initialize monitoring
        self._setup_monitoring()
        
        logger.info("Database Performance Monitor initialized")
    
    def _setup_monitoring(self):
        """Set up database monitoring and optimization"""
        try:
            # Create monitoring tables if they don't exist
            self._create_monitoring_tables()
            
            # Optimize database settings
            self._optimize_database_settings()
            
            # Start background monitoring
            self._start_background_monitoring()
            
        except Exception as e:
            logger.error(f"Failed to setup database monitoring: {e}")
    
    def _create_monitoring_tables(self):
        """Create database monitoring tables"""
        monitoring_tables = [
            '''CREATE TABLE IF NOT EXISTS query_performance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_name TEXT NOT NULL,
                execution_time_ms REAL NOT NULL,
                query_hash TEXT,
                parameters_count INTEGER,
                rows_affected INTEGER,
                status TEXT CHECK(status IN ('success', 'error', 'timeout')) DEFAULT 'success',
                error_message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                thread_id TEXT,
                connection_id TEXT
            )''',
            
            '''CREATE TABLE IF NOT EXISTS database_connection_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_id TEXT NOT NULL,
                action TEXT CHECK(action IN ('connect', 'disconnect', 'timeout', 'error')) NOT NULL,
                connection_time_ms REAL,
                error_message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                thread_id TEXT
            )''',
            
            '''CREATE TABLE IF NOT EXISTS database_optimization_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                optimization_type TEXT NOT NULL,
                before_stats TEXT,
                after_stats TEXT,
                improvement_percent REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            
            '''CREATE TABLE IF NOT EXISTS database_health_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                unit TEXT,
                threshold_warning REAL,
                threshold_critical REAL,
                status TEXT CHECK(status IN ('healthy', 'warning', 'critical')) DEFAULT 'healthy',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )'''
        ]
        
        try:
            with sqlite3.connect(db.db_path) as conn:
                for table_sql in monitoring_tables:
                    conn.execute(table_sql)
                
                # Create indexes for performance
                performance_indexes = [
                    'CREATE INDEX IF NOT EXISTS idx_query_perf_name_time ON query_performance_log(query_name, timestamp)',
                    'CREATE INDEX IF NOT EXISTS idx_query_perf_status ON query_performance_log(status, timestamp)',
                    'CREATE INDEX IF NOT EXISTS idx_db_health_metric ON database_health_metrics(metric_name, timestamp)',
                    'CREATE INDEX IF NOT EXISTS idx_conn_log_action ON database_connection_log(action, timestamp)'
                ]
                
                for index_sql in performance_indexes:
                    conn.execute(index_sql)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to create monitoring tables: {e}")
    
    def _optimize_database_settings(self):
        """Optimize database settings for performance"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                optimization_settings = [
                    'PRAGMA journal_mode = WAL',
                    'PRAGMA synchronous = NORMAL',
                    'PRAGMA cache_size = 20000',  # 20MB cache
                    'PRAGMA temp_store = MEMORY',
                    'PRAGMA mmap_size = 536870912',  # 512MB mmap
                    'PRAGMA page_size = 32768',  # 32KB pages
                    'PRAGMA auto_vacuum = INCREMENTAL',
                    'PRAGMA foreign_keys = ON'
                ]
                
                for setting in optimization_settings:
                    conn.execute(setting)
                
                # Run optimization
                conn.execute('PRAGMA optimize')
                conn.execute('ANALYZE')
                
                conn.commit()
                
            logger.info("Database optimization settings applied")
            
        except Exception as e:
            logger.error(f"Failed to optimize database settings: {e}")
    
    def _start_background_monitoring(self):
        """Start background monitoring thread"""
        def monitor_thread():
            while True:
                try:
                    self._collect_health_metrics()
                    self._analyze_performance_trends()
                    self._check_optimization_opportunities()
                    time.sleep(60)  # Run every minute
                except Exception as e:
                    logger.error(f"Background monitoring error: {e}")
                    time.sleep(30)
        
        thread = threading.Thread(target=monitor_thread, daemon=True)
        thread.start()
    
    def _collect_health_metrics(self):
        """Collect database health metrics"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                # Get database statistics
                cursor = conn.execute('PRAGMA page_count')
                page_count = cursor.fetchone()[0]
                
                cursor = conn.execute('PRAGMA page_size')
                page_size = cursor.fetchone()[0]
                
                cursor = conn.execute('PRAGMA freelist_count')
                freelist_count = cursor.fetchone()[0]
                
                cursor = conn.execute('PRAGMA cache_size')
                cache_size = cursor.fetchone()[0]
                
                # Calculate metrics
                db_size_mb = (page_count * page_size) / (1024 * 1024)
                fragmentation_percent = (freelist_count / page_count) * 100 if page_count > 0 else 0
                
                # Store metrics
                metrics = [
                    ('database_size_mb', db_size_mb, 'MB', 100, 500),
                    ('fragmentation_percent', fragmentation_percent, '%', 10, 25),
                    ('cache_size_pages', cache_size, 'pages', 1000, 5000),
                    ('page_count', page_count, 'pages', 10000, 50000)
                ]
                
                for metric_name, value, unit, warn_threshold, crit_threshold in metrics:
                    status = 'healthy'
                    if value >= crit_threshold:
                        status = 'critical'
                    elif value >= warn_threshold:
                        status = 'warning'
                    
                    conn.execute('''
                        INSERT INTO database_health_metrics 
                        (metric_name, metric_value, unit, threshold_warning, threshold_critical, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (metric_name, value, unit, warn_threshold, crit_threshold, status))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to collect health metrics: {e}")
    
    def _analyze_performance_trends(self):
        """Analyze database performance trends"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                # Get recent query performance
                cursor = conn.execute('''
                    SELECT query_name, AVG(execution_time_ms) as avg_time, COUNT(*) as count
                    FROM query_performance_log
                    WHERE timestamp > datetime('now', '-1 hour')
                    GROUP BY query_name
                    ORDER BY avg_time DESC
                    LIMIT 10
                ''')
                
                slow_queries = cursor.fetchall()
                
                # Log performance trends
                for query_name, avg_time, count in slow_queries:
                    if avg_time > self.slow_query_threshold:
                        system_logger.log_system_event(
                            level='warning',
                            component='database_monitor',
                            message=f'Slow query trend detected: {query_name}',
                            details={
                                'query_name': query_name,
                                'avg_execution_time': avg_time,
                                'execution_count': count,
                                'threshold': self.slow_query_threshold
                            }
                        )
                
        except Exception as e:
            logger.error(f"Failed to analyze performance trends: {e}")
    
    def _check_optimization_opportunities(self):
        """Check for database optimization opportunities"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                # Check for missing indexes
                cursor = conn.execute('''
                    SELECT name, sql FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ''')
                
                tables = cursor.fetchall()
                
                for table_name, table_sql in tables:
                    # Analyze table for potential index opportunities
                    cursor = conn.execute(f'SELECT COUNT(*) FROM {table_name}')
                    row_count = cursor.fetchone()[0]
                    
                    if row_count > 1000:  # Only for tables with significant data
                        # Check for commonly queried columns without indexes
                        cursor = conn.execute(f'PRAGMA table_info({table_name})')
                        columns = cursor.fetchall()
                        
                        # Log optimization opportunity
                        system_logger.log_system_event(
                            level='info',
                            component='database_monitor',
                            message=f'Table {table_name} has {row_count} rows - consider indexing',
                            details={
                                'table_name': table_name,
                                'row_count': row_count,
                                'columns': [col[1] for col in columns]
                            }
                        )
                
        except Exception as e:
            logger.error(f"Failed to check optimization opportunities: {e}")
    
    def monitor_query(self, query_name, query_hash=None):
        """Decorator to monitor database query performance"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                connection_id = f"conn_{threading.current_thread().ident}_{int(time.time())}"
                
                try:
                    # Execute query
                    result = func(*args, **kwargs)
                    
                    # Calculate metrics
                    execution_time = (time.time() - start_time) * 1000
                    
                    # Update statistics
                    with self.stats_lock:
                        stats = self.query_stats[query_name]
                        stats['count'] += 1
                        stats['total_time'] += execution_time
                        stats['avg_time'] = stats['total_time'] / stats['count']
                        stats['max_time'] = max(stats['max_time'], execution_time)
                        stats['min_time'] = min(stats['min_time'], execution_time)
                        stats['last_executed'] = datetime.now().isoformat()
                        
                        # Add to real-time metrics
                        self.real_time_metrics.append({
                            'query_name': query_name,
                            'execution_time': execution_time,
                            'timestamp': datetime.now().isoformat(),
                            'status': 'success'
                        })
                    
                    # Log query performance
                    self._log_query_performance(
                        query_name, execution_time, query_hash,
                        len(args), 'success', None, connection_id
                    )
                    
                    # Check for slow queries
                    if execution_time > self.critical_query_threshold:
                        system_logger.log_system_event(
                            level='critical',
                            component='database_monitor',
                            message=f'Critical slow query: {query_name}',
                            details={
                                'query_name': query_name,
                                'execution_time': execution_time,
                                'threshold': self.critical_query_threshold
                            }
                        )
                    elif execution_time > self.slow_query_threshold:
                        system_logger.log_system_event(
                            level='warning',
                            component='database_monitor',
                            message=f'Slow query detected: {query_name}',
                            details={
                                'query_name': query_name,
                                'execution_time': execution_time,
                                'threshold': self.slow_query_threshold
                            }
                        )
                    
                    return result
                    
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000
                    
                    # Update error statistics
                    with self.stats_lock:
                        self.query_stats[query_name]['errors'] += 1
                        
                        # Add to real-time metrics
                        self.real_time_metrics.append({
                            'query_name': query_name,
                            'execution_time': execution_time,
                            'timestamp': datetime.now().isoformat(),
                            'status': 'error',
                            'error': str(e)
                        })
                    
                    # Log query error
                    self._log_query_performance(
                        query_name, execution_time, query_hash,
                        len(args), 'error', str(e), connection_id
                    )
                    
                    raise
            
            return wrapper
        return decorator
    
    def _log_query_performance(self, query_name, execution_time, query_hash, 
                             params_count, status, error_msg, connection_id):
        """Log query performance to database"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                conn.execute('''
                    INSERT INTO query_performance_log 
                    (query_name, execution_time_ms, query_hash, parameters_count, 
                     status, error_message, thread_id, connection_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    query_name, execution_time, query_hash, params_count,
                    status, error_msg, str(threading.current_thread().ident), connection_id
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log query performance: {e}")
    
    def get_performance_dashboard(self):
        """Get comprehensive performance dashboard data"""
        try:
            dashboard_data = {
                'real_time_metrics': list(self.real_time_metrics)[-50:],  # Last 50 queries
                'query_statistics': dict(self.query_stats),
                'connection_pool': self.connection_pool_stats,
                'health_metrics': self._get_current_health_metrics(),
                'slow_queries': self._get_slow_queries(),
                'performance_trends': self._get_performance_trends(),
                'optimization_suggestions': self._get_optimization_suggestions()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to get performance dashboard: {e}")
            return {}
    
    def _get_current_health_metrics(self):
        """Get current database health metrics"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.execute('''
                    SELECT metric_name, metric_value, unit, status
                    FROM database_health_metrics
                    WHERE timestamp > datetime('now', '-5 minutes')
                    ORDER BY timestamp DESC
                ''')
                
                metrics = []
                for row in cursor.fetchall():
                    metrics.append({
                        'name': row[0],
                        'value': row[1],
                        'unit': row[2],
                        'status': row[3]
                    })
                
                return metrics
                
        except Exception as e:
            logger.error(f"Failed to get health metrics: {e}")
            return []
    
    def _get_slow_queries(self):
        """Get slowest queries in the last hour"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.execute('''
                    SELECT query_name, AVG(execution_time_ms) as avg_time, 
                           COUNT(*) as count, MAX(execution_time_ms) as max_time
                    FROM query_performance_log
                    WHERE timestamp > datetime('now', '-1 hour')
                    GROUP BY query_name
                    ORDER BY avg_time DESC
                    LIMIT 10
                ''')
                
                slow_queries = []
                for row in cursor.fetchall():
                    slow_queries.append({
                        'query_name': row[0],
                        'avg_time': row[1],
                        'count': row[2],
                        'max_time': row[3]
                    })
                
                return slow_queries
                
        except Exception as e:
            logger.error(f"Failed to get slow queries: {e}")
            return []
    
    def _get_performance_trends(self):
        """Get performance trends over time"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.execute('''
                    SELECT 
                        datetime(timestamp, 'localtime') as time_bucket,
                        AVG(execution_time_ms) as avg_time,
                        COUNT(*) as query_count
                    FROM query_performance_log
                    WHERE timestamp > datetime('now', '-24 hours')
                    GROUP BY datetime(timestamp, 'localtime', 'start of hour')
                    ORDER BY time_bucket
                ''')
                
                trends = []
                for row in cursor.fetchall():
                    trends.append({
                        'time': row[0],
                        'avg_time': row[1],
                        'query_count': row[2]
                    })
                
                return trends
                
        except Exception as e:
            logger.error(f"Failed to get performance trends: {e}")
            return []
    
    def _get_optimization_suggestions(self):
        """Get database optimization suggestions"""
        suggestions = []
        
        try:
            # Check for frequently slow queries
            with self.stats_lock:
                for query_name, stats in self.query_stats.items():
                    if stats['avg_time'] > self.slow_query_threshold and stats['count'] > 10:
                        suggestions.append({
                            'type': 'slow_query',
                            'priority': 'high',
                            'description': f'Query "{query_name}" is consistently slow',
                            'suggestion': 'Consider adding indexes or optimizing query structure',
                            'metrics': {
                                'avg_time': stats['avg_time'],
                                'count': stats['count'],
                                'max_time': stats['max_time']
                            }
                        })
            
            # Check database size
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.execute('PRAGMA page_count')
                page_count = cursor.fetchone()[0]
                
                cursor = conn.execute('PRAGMA page_size')
                page_size = cursor.fetchone()[0]
                
                db_size_mb = (page_count * page_size) / (1024 * 1024)
                
                if db_size_mb > 100:  # Database larger than 100MB
                    suggestions.append({
                        'type': 'database_size',
                        'priority': 'medium',
                        'description': f'Database size is {db_size_mb:.1f}MB',
                        'suggestion': 'Consider archiving old data or implementing data retention policies',
                        'metrics': {'size_mb': db_size_mb}
                    })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to get optimization suggestions: {e}")
            return []
    
    def optimize_database(self):
        """Run database optimization"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                # Record before stats
                cursor = conn.execute('PRAGMA page_count')
                before_pages = cursor.fetchone()[0]
                
                cursor = conn.execute('PRAGMA freelist_count')
                before_freelist = cursor.fetchone()[0]
                
                # Run optimization
                conn.execute('VACUUM')
                conn.execute('ANALYZE')
                conn.execute('PRAGMA optimize')
                
                # Record after stats
                cursor = conn.execute('PRAGMA page_count')
                after_pages = cursor.fetchone()[0]
                
                cursor = conn.execute('PRAGMA freelist_count')
                after_freelist = cursor.fetchone()[0]
                
                # Calculate improvement
                page_reduction = before_pages - after_pages
                improvement_percent = (page_reduction / before_pages) * 100 if before_pages > 0 else 0
                
                # Log optimization
                conn.execute('''
                    INSERT INTO database_optimization_log 
                    (optimization_type, before_stats, after_stats, improvement_percent)
                    VALUES (?, ?, ?, ?)
                ''', (
                    'vacuum_analyze',
                    json.dumps({'pages': before_pages, 'freelist': before_freelist}),
                    json.dumps({'pages': after_pages, 'freelist': after_freelist}),
                    improvement_percent
                ))
                
                conn.commit()
                
                logger.info(f"Database optimization completed - {improvement_percent:.1f}% improvement")
                
                return {
                    'success': True,
                    'improvement_percent': improvement_percent,
                    'pages_reduced': page_reduction
                }
                
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return {'success': False, 'error': str(e)}


# Global database performance monitor instance
database_monitor = DatabasePerformanceMonitor()

# Convenience decorator for easy use
def monitor_db_query(query_name, query_hash=None):
    """Decorator for monitoring database query performance"""
    return database_monitor.monitor_query(query_name, query_hash)

if __name__ == '__main__':
    # Test database performance monitoring
    print("🔍 Testing VectorCraft Database Performance Monitor...")
    
    # Get dashboard data
    dashboard = database_monitor.get_performance_dashboard()
    
    print(f"\n📊 Performance Dashboard:")
    print(f"Real-time metrics: {len(dashboard.get('real_time_metrics', []))}")
    print(f"Query statistics: {len(dashboard.get('query_statistics', {}))}")
    print(f"Health metrics: {len(dashboard.get('health_metrics', []))}")
    print(f"Slow queries: {len(dashboard.get('slow_queries', []))}")
    print(f"Optimization suggestions: {len(dashboard.get('optimization_suggestions', []))}")
    
    # Test optimization
    result = database_monitor.optimize_database()
    print(f"\n🔧 Database Optimization:")
    print(f"Success: {result.get('success', False)}")
    if result.get('success'):
        print(f"Improvement: {result.get('improvement_percent', 0):.1f}%")
        print(f"Pages reduced: {result.get('pages_reduced', 0)}")