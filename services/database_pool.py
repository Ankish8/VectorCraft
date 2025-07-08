"""
Database connection pooling for improved performance
"""

import os
import sqlite3
import time
import threading
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from queue import Queue, Empty
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Database connection wrapper with metadata"""
    
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.query_count = 0
        self.in_use = False
        self.connection_id = id(connection)
        
        # Configure connection
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = NORMAL")
        self.connection.execute("PRAGMA cache_size = 10000")
        self.connection.execute("PRAGMA temp_store = MEMORY")
        
    def execute(self, query: str, params: tuple = None):
        """Execute a query"""
        self.last_used = datetime.now()
        self.query_count += 1
        
        if params:
            return self.connection.execute(query, params)
        else:
            return self.connection.execute(query)
    
    def executemany(self, query: str, params_list: List[tuple]):
        """Execute multiple queries"""
        self.last_used = datetime.now()
        self.query_count += len(params_list)
        return self.connection.executemany(query, params_list)
    
    def commit(self):
        """Commit transaction"""
        self.last_used = datetime.now()
        return self.connection.commit()
    
    def rollback(self):
        """Rollback transaction"""
        self.last_used = datetime.now()
        return self.connection.rollback()
    
    def close(self):
        """Close connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def is_alive(self) -> bool:
        """Check if connection is alive"""
        try:
            self.connection.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False
    
    def get_age(self) -> float:
        """Get connection age in seconds"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def get_idle_time(self) -> float:
        """Get idle time in seconds"""
        return (datetime.now() - self.last_used).total_seconds()


class DatabasePool:
    """Database connection pool manager"""
    
    def __init__(self, 
                 database_path: str = None,
                 min_connections: int = 5,
                 max_connections: int = 20,
                 connection_timeout: float = 30.0,
                 max_idle_time: float = 300.0,
                 max_connection_age: float = 3600.0,
                 health_check_interval: float = 60.0):
        
        self.database_path = database_path or os.getenv('DATABASE_PATH', 'vectorcraft.db')
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.max_idle_time = max_idle_time
        self.max_connection_age = max_connection_age
        self.health_check_interval = health_check_interval
        
        # Connection pool
        self.pool = Queue(maxsize=max_connections)
        self.active_connections = {}
        self.total_connections = 0
        
        # Threading
        self.lock = threading.RLock()
        self.health_check_thread = None
        self.shutdown_event = threading.Event()
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'pool_hits': 0,
            'pool_misses': 0,
            'connections_created': 0,
            'connections_closed': 0,
            'query_count': 0,
            'avg_query_time': 0.0,
            'errors': 0
        }
        
        # Initialize pool
        self._initialize_pool()
        
        # Start health check thread
        self._start_health_check()
        
        logger.info(f"Database pool initialized: {self.database_path}")
    
    def _initialize_pool(self):
        """Initialize connection pool with minimum connections"""
        try:
            for _ in range(self.min_connections):
                conn = self._create_connection()
                if conn:
                    self.pool.put(conn)
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    def _create_connection(self) -> Optional[DatabaseConnection]:
        """Create a new database connection"""
        try:
            # Create SQLite connection
            conn = sqlite3.connect(
                self.database_path,
                timeout=self.connection_timeout,
                check_same_thread=False
            )
            
            db_conn = DatabaseConnection(conn)
            
            with self.lock:
                self.total_connections += 1
                self.stats['connections_created'] += 1
            
            logger.debug(f"Created new database connection: {db_conn.connection_id}")
            
            return db_conn
            
        except sqlite3.Error as e:
            logger.error(f"Failed to create database connection: {e}")
            with self.lock:
                self.stats['errors'] += 1
            return None
    
    def _start_health_check(self):
        """Start health check thread"""
        self.health_check_thread = threading.Thread(
            target=self._health_check_worker,
            daemon=True
        )
        self.health_check_thread.start()
    
    def _health_check_worker(self):
        """Health check worker thread"""
        while not self.shutdown_event.is_set():
            try:
                self._cleanup_connections()
                self._ensure_min_connections()
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                time.sleep(5)  # Wait before retry
    
    def _cleanup_connections(self):
        """Clean up old and idle connections"""
        with self.lock:
            # Check active connections
            expired_connections = []
            for conn_id, db_conn in self.active_connections.items():
                if not db_conn.is_alive() or \
                   db_conn.get_age() > self.max_connection_age or \
                   db_conn.get_idle_time() > self.max_idle_time:
                    expired_connections.append(conn_id)
            
            # Remove expired connections
            for conn_id in expired_connections:
                db_conn = self.active_connections.pop(conn_id)
                db_conn.close()
                self.total_connections -= 1
                self.stats['connections_closed'] += 1
                logger.debug(f"Closed expired connection: {conn_id}")
        
        # Clean up pool connections
        cleaned_connections = []
        while not self.pool.empty():
            try:
                db_conn = self.pool.get_nowait()
                
                if db_conn.is_alive() and \
                   db_conn.get_age() <= self.max_connection_age and \
                   db_conn.get_idle_time() <= self.max_idle_time:
                    cleaned_connections.append(db_conn)
                else:
                    db_conn.close()
                    with self.lock:
                        self.total_connections -= 1
                        self.stats['connections_closed'] += 1
                    logger.debug(f"Cleaned up pooled connection: {db_conn.connection_id}")
            except Empty:
                break
        
        # Put back valid connections
        for db_conn in cleaned_connections:
            self.pool.put(db_conn)
    
    def _ensure_min_connections(self):
        """Ensure minimum number of connections in pool"""
        current_pool_size = self.pool.qsize()
        
        if current_pool_size < self.min_connections:
            needed = self.min_connections - current_pool_size
            
            for _ in range(needed):
                if self.total_connections < self.max_connections:
                    conn = self._create_connection()
                    if conn:
                        self.pool.put(conn)
                    else:
                        break
    
    @contextmanager
    def get_connection(self):
        """
        Get a database connection from the pool
        
        Usage:
            with pool.get_connection() as conn:
                result = conn.execute("SELECT * FROM users")
        """
        db_conn = None
        start_time = time.time()
        
        try:
            with self.lock:
                self.stats['total_requests'] += 1
            
            # Try to get connection from pool
            try:
                db_conn = self.pool.get(timeout=1.0)
                with self.lock:
                    self.stats['pool_hits'] += 1
                logger.debug(f"Got connection from pool: {db_conn.connection_id}")
                
            except Empty:
                # Pool is empty, create new connection if possible
                if self.total_connections < self.max_connections:
                    db_conn = self._create_connection()
                    if db_conn:
                        with self.lock:
                            self.stats['pool_misses'] += 1
                        logger.debug(f"Created new connection: {db_conn.connection_id}")
                    else:
                        raise Exception("Failed to create database connection")
                else:
                    # Wait for connection to become available
                    db_conn = self.pool.get(timeout=self.connection_timeout)
                    with self.lock:
                        self.stats['pool_hits'] += 1
                    logger.debug(f"Got connection after wait: {db_conn.connection_id}")
            
            # Mark connection as in use
            if db_conn:
                db_conn.in_use = True
                with self.lock:
                    self.active_connections[db_conn.connection_id] = db_conn
                
                # Yield connection
                yield db_conn
                
        except Exception as e:
            logger.error(f"Error getting database connection: {e}")
            with self.lock:
                self.stats['errors'] += 1
            raise
            
        finally:
            # Return connection to pool
            if db_conn:
                query_time = time.time() - start_time
                
                with self.lock:
                    # Update statistics
                    self.stats['query_count'] += db_conn.query_count
                    if self.stats['query_count'] > 0:
                        self.stats['avg_query_time'] = (
                            (self.stats['avg_query_time'] * (self.stats['query_count'] - db_conn.query_count) + 
                             query_time * db_conn.query_count) / self.stats['query_count']
                        )
                    
                    # Remove from active connections
                    if db_conn.connection_id in self.active_connections:
                        del self.active_connections[db_conn.connection_id]
                
                db_conn.in_use = False
                db_conn.query_count = 0
                
                # Return to pool if connection is still valid
                if db_conn.is_alive() and db_conn.get_age() <= self.max_connection_age:
                    try:
                        self.pool.put_nowait(db_conn)
                        logger.debug(f"Returned connection to pool: {db_conn.connection_id}")
                    except:
                        # Pool is full, close connection
                        db_conn.close()
                        with self.lock:
                            self.total_connections -= 1
                            self.stats['connections_closed'] += 1
                        logger.debug(f"Closed excess connection: {db_conn.connection_id}")
                else:
                    # Connection is invalid, close it
                    db_conn.close()
                    with self.lock:
                        self.total_connections -= 1
                        self.stats['connections_closed'] += 1
                    logger.debug(f"Closed invalid connection: {db_conn.connection_id}")
    
    def execute_query(self, query: str, params: tuple = None):
        """Execute a single query"""
        with self.get_connection() as conn:
            return conn.execute(query, params)
    
    def execute_transaction(self, queries: List[tuple]):
        """
        Execute multiple queries in a transaction
        
        Args:
            queries: List of (query, params) tuples
        """
        with self.get_connection() as conn:
            try:
                for query, params in queries:
                    conn.execute(query, params)
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self.lock:
            return {
                'pool_size': self.pool.qsize(),
                'active_connections': len(self.active_connections),
                'total_connections': self.total_connections,
                'max_connections': self.max_connections,
                'min_connections': self.min_connections,
                'stats': self.stats.copy()
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get pool health status"""
        stats = self.get_stats()
        
        # Calculate health metrics
        pool_utilization = (stats['active_connections'] / stats['max_connections']) * 100
        hit_rate = (stats['stats']['pool_hits'] / max(stats['stats']['total_requests'], 1)) * 100
        
        health_status = {
            'healthy': True,
            'pool_utilization': pool_utilization,
            'hit_rate': hit_rate,
            'avg_query_time': stats['stats']['avg_query_time'],
            'error_rate': (stats['stats']['errors'] / max(stats['stats']['total_requests'], 1)) * 100,
            'timestamp': datetime.now().isoformat()
        }
        
        # Determine health
        if pool_utilization > 90 or hit_rate < 50 or health_status['error_rate'] > 5:
            health_status['healthy'] = False
        
        return health_status
    
    def close(self):
        """Close all connections and shutdown pool"""
        logger.info("Shutting down database pool...")
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Wait for health check thread to finish
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
        
        # Close all connections
        with self.lock:
            # Close active connections
            for db_conn in self.active_connections.values():
                db_conn.close()
            
            # Close pooled connections
            while not self.pool.empty():
                try:
                    db_conn = self.pool.get_nowait()
                    db_conn.close()
                except Empty:
                    break
            
            self.active_connections.clear()
            self.total_connections = 0
        
        logger.info("Database pool shutdown complete")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global database pool instance
database_pool = None


def initialize_database_pool(**kwargs):
    """Initialize global database pool"""
    global database_pool
    
    if database_pool is None:
        database_pool = DatabasePool(**kwargs)
    
    return database_pool


def get_database_pool() -> DatabasePool:
    """Get global database pool"""
    global database_pool
    
    if database_pool is None:
        database_pool = initialize_database_pool()
    
    return database_pool


if __name__ == '__main__':
    # Test database pool
    logger.info("Testing database pool...")
    
    # Initialize pool
    pool = DatabasePool(
        database_path='test.db',
        min_connections=2,
        max_connections=5,
        connection_timeout=10.0
    )
    
    # Test connection
    try:
        with pool.get_connection() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO test (name) VALUES (?)", ('test',))
            conn.commit()
            
            result = conn.execute("SELECT * FROM test").fetchall()
            print(f"Query result: {result}")
    
    except Exception as e:
        print(f"Error: {e}")
    
    # Get stats
    stats = pool.get_stats()
    print(f"Pool stats: {stats}")
    
    # Get health status
    health = pool.get_health_status()
    print(f"Pool health: {health}")
    
    # Close pool
    pool.close()
    
    # Clean up test database
    import os
    try:
        os.remove('test.db')
    except:
        pass
    
    logger.info("Database pool test completed!")