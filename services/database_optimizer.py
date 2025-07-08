#!/usr/bin/env python3
"""
Database Optimization Service
Optimizes database queries, manages indexes, and monitors DB performance
"""

import sqlite3
import time
import logging
from datetime import datetime, timedelta
from functools import wraps
from database import db
from services.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """Database optimization and performance monitoring"""
    
    def __init__(self):
        self.query_cache = {}
        self.slow_query_threshold = 50  # 50ms
        self.logger = logger
        
        # Initialize database optimization
        self.optimize_database()
        
        self.logger.info("Database Optimizer initialized")
    
    def optimize_database(self):
        """Optimize database with performance improvements"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                # Enable WAL mode for better concurrency
                conn.execute('PRAGMA journal_mode = WAL')
                
                # Optimize for performance
                conn.execute('PRAGMA synchronous = NORMAL')
                conn.execute('PRAGMA cache_size = 10000')  # 10MB cache
                conn.execute('PRAGMA temp_store = MEMORY')
                conn.execute('PRAGMA mmap_size = 268435456')  # 256MB mmap
                
                # Enable query optimization
                conn.execute('PRAGMA optimize')
                
                # Analyze tables for better query planning
                conn.execute('ANALYZE')
                
                conn.commit()
                
            self.logger.info("Database optimization complete")
            
        except Exception as e:
            self.logger.error(f"Database optimization failed: {e}")
    
    def create_performance_indexes(self):
        """Create additional indexes for performance-critical queries"""
        indexes = [
            # User-related indexes
            ('idx_users_email_active', 'users', 'email, is_active'),
            ('idx_users_created_at', 'users', 'created_at'),
            
            # Upload-related indexes
            ('idx_uploads_user_date', 'user_uploads', 'user_id, upload_date'),
            ('idx_uploads_processing_time', 'user_uploads', 'processing_time'),
            ('idx_uploads_strategy', 'user_uploads', 'strategy_used'),
            
            # Transaction indexes
            ('idx_transactions_email_status', 'transactions', 'email, status'),
            ('idx_transactions_paypal_order', 'transactions', 'paypal_order_id'),
            ('idx_transactions_completed_at', 'transactions', 'completed_at'),
            
            # Performance monitoring indexes
            ('idx_perf_metrics_composite', 'performance_metrics', 'metric_type, endpoint, timestamp'),
            ('idx_system_metrics_composite', 'system_metrics', 'metric_type, timestamp'),
            
            # Health monitoring indexes
            ('idx_health_component_status', 'system_health', 'component, status, checked_at'),
            ('idx_logs_level_component', 'system_logs', 'level, component, created_at'),
            
            # Alert indexes
            ('idx_alerts_type_resolved', 'admin_alerts', 'type, resolved, created_at')
        ]
        
        try:
            with sqlite3.connect(db.db_path) as conn:
                for index_name, table_name, columns in indexes:
                    conn.execute(f'''
                        CREATE INDEX IF NOT EXISTS {index_name} 
                        ON {table_name} ({columns})
                    ''')
                
                conn.commit()
                
            self.logger.info(f"Created {len(indexes)} performance indexes")
            
        except Exception as e:
            self.logger.error(f"Failed to create performance indexes: {e}")
    
    def monitor_query_performance(self, query_name):
        """Decorator to monitor database query performance"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Calculate query time
                    query_time = (time.time() - start_time) * 1000  # Convert to ms
                    
                    # Log performance metric
                    performance_monitor._record_database_metric(
                        query_name, query_time, 'success'
                    )
                    
                    # Check if query is slow
                    if query_time > self.slow_query_threshold:
                        self.logger.warning(
                            f"Slow query detected: {query_name} took {query_time:.1f}ms"
                        )
                        
                        # Log slow query for analysis
                        self.log_slow_query(query_name, query_time, args, kwargs)
                    
                    return result
                    
                except Exception as e:
                    query_time = (time.time() - start_time) * 1000
                    
                    # Log error metric
                    performance_monitor._record_database_metric(
                        query_name, query_time, 'error'
                    )
                    
                    self.logger.error(f"Database query error in {query_name}: {e}")
                    raise
            
            return wrapper
        return decorator
    
    def log_slow_query(self, query_name, query_time, args, kwargs):
        """Log slow query for analysis"""
        try:
            db.log_system_event(
                level='warning',
                component='database_optimizer',
                message=f'Slow query: {query_name}',
                details={
                    'query_name': query_name,
                    'query_time_ms': query_time,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs),
                    'timestamp': datetime.now().isoformat()
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to log slow query: {e}")
    
    def get_query_performance_stats(self, hours=24):
        """Get database query performance statistics"""
        try:
            metrics = db.get_performance_metrics(
                metric_type='database_query',
                hours=hours
            )
            
            if not metrics:
                return {
                    'total_queries': 0,
                    'avg_query_time': 0,
                    'slow_queries': 0,
                    'error_rate': 0
                }
            
            # Calculate statistics
            query_times = [m['value'] for m in metrics]
            error_count = sum(1 for m in metrics if m['status'] == 'error')
            slow_count = sum(1 for t in query_times if t > self.slow_query_threshold)
            
            return {
                'total_queries': len(metrics),
                'avg_query_time': sum(query_times) / len(query_times),
                'min_query_time': min(query_times),
                'max_query_time': max(query_times),
                'slow_queries': slow_count,
                'error_count': error_count,
                'error_rate': error_count / len(metrics) if metrics else 0,
                'slow_query_rate': slow_count / len(metrics) if metrics else 0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get query performance stats: {e}")
            return {}
    
    def optimize_query_cache(self):
        """Optimize query cache settings"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                # Get current cache statistics
                cursor = conn.execute('PRAGMA cache_size')
                cache_size = cursor.fetchone()[0]
                
                cursor = conn.execute('PRAGMA page_size')
                page_size = cursor.fetchone()[0]
                
                # Calculate optimal cache size based on available memory
                import psutil
                available_memory = psutil.virtual_memory().available
                
                # Use 5% of available memory for SQLite cache
                optimal_cache_pages = int((available_memory * 0.05) / page_size)
                
                # Set reasonable limits
                optimal_cache_pages = max(1000, min(50000, optimal_cache_pages))
                
                if optimal_cache_pages != cache_size:
                    conn.execute(f'PRAGMA cache_size = {optimal_cache_pages}')
                    self.logger.info(f"Optimized cache size: {optimal_cache_pages} pages")
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to optimize query cache: {e}")
    
    def run_maintenance(self):
        """Run database maintenance tasks"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                # Vacuum database to reclaim space
                conn.execute('VACUUM')
                
                # Update statistics for query optimizer
                conn.execute('ANALYZE')
                
                # Optimize query plans
                conn.execute('PRAGMA optimize')
                
                conn.commit()
                
            self.logger.info("Database maintenance completed")
            
        except Exception as e:
            self.logger.error(f"Database maintenance failed: {e}")
    
    def get_database_health(self):
        """Get database health information"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                # Get database size
                cursor = conn.execute('PRAGMA page_count')
                page_count = cursor.fetchone()[0]
                
                cursor = conn.execute('PRAGMA page_size')
                page_size = cursor.fetchone()[0]
                
                db_size = page_count * page_size
                
                # Get fragmentation info
                cursor = conn.execute('PRAGMA freelist_count')
                freelist_count = cursor.fetchone()[0]
                
                # Get cache hit ratio
                cursor = conn.execute('PRAGMA cache_size')
                cache_size = cursor.fetchone()[0]
                
                # Get journal mode
                cursor = conn.execute('PRAGMA journal_mode')
                journal_mode = cursor.fetchone()[0]
                
                # Get integrity check
                cursor = conn.execute('PRAGMA integrity_check')
                integrity_result = cursor.fetchone()[0]
                
                return {
                    'database_size_bytes': db_size,
                    'database_size_mb': db_size / (1024 * 1024),
                    'page_count': page_count,
                    'page_size': page_size,
                    'freelist_count': freelist_count,
                    'fragmentation_percent': (freelist_count / page_count) * 100 if page_count > 0 else 0,
                    'cache_size_pages': cache_size,
                    'journal_mode': journal_mode,
                    'integrity_check': integrity_result,
                    'health_status': 'healthy' if integrity_result == 'ok' else 'error'
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get database health: {e}")
            return {
                'health_status': 'error',
                'error_message': str(e)
            }
    
    def get_slow_queries(self, limit=20):
        """Get slowest database queries"""
        try:
            return db.get_performance_metrics(
                metric_type='database_query',
                hours=24,
                limit=limit
            )
        except Exception as e:
            self.logger.error(f"Failed to get slow queries: {e}")
            return []


# Global database optimizer instance
database_optimizer = DatabaseOptimizer()

# Create performance indexes
database_optimizer.create_performance_indexes()

# Convenience decorator for easy use
def monitor_query(query_name):
    """Decorator for monitoring database query performance"""
    return database_optimizer.monitor_query_performance(query_name)

if __name__ == '__main__':
    # Test database optimization
    print("🔧 Testing VectorCraft Database Optimizer...")
    
    # Run optimization
    database_optimizer.optimize_database()
    database_optimizer.optimize_query_cache()
    
    # Get database health
    health = database_optimizer.get_database_health()
    print(f"\n📊 Database Health:")
    print(f"Size: {health.get('database_size_mb', 0):.2f} MB")
    print(f"Fragmentation: {health.get('fragmentation_percent', 0):.1f}%")
    print(f"Journal Mode: {health.get('journal_mode', 'unknown')}")
    print(f"Health Status: {health.get('health_status', 'unknown')}")
    
    # Get performance stats
    stats = database_optimizer.get_query_performance_stats()
    print(f"\n⚡ Query Performance:")
    print(f"Total Queries: {stats.get('total_queries', 0)}")
    print(f"Average Query Time: {stats.get('avg_query_time', 0):.1f}ms")
    print(f"Slow Queries: {stats.get('slow_queries', 0)}")
    print(f"Error Rate: {stats.get('error_rate', 0):.1%}")