"""
Optimized database layer with connection pooling and performance improvements
"""

import sqlite3
import threading
import logging
import os
import time
from contextlib import contextmanager
from queue import Queue, Empty
from datetime import datetime
from pathlib import Path
import bcrypt


class ConnectionPool:
    """Thread-safe SQLite connection pool"""
    
    def __init__(self, database_path, pool_size=10, max_overflow=5):
        self.database_path = database_path
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool = Queue(maxsize=pool_size)
        self.overflow_connections = 0
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Initialize pool with connections
        for _ in range(pool_size):
            conn = self._create_connection()
            self.pool.put(conn)
    
    def _create_connection(self):
        """Create a new database connection"""
        conn = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
            timeout=30,
            isolation_level=None  # Autocommit mode
        )
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')  # Enable WAL mode for better concurrency
        conn.execute('PRAGMA synchronous=NORMAL')  # Balance between speed and safety
        conn.execute('PRAGMA cache_size=10000')  # Increase cache size
        conn.execute('PRAGMA temp_store=MEMORY')  # Store temporary data in memory
        conn.execute('PRAGMA mmap_size=67108864')  # 64MB memory-mapped I/O
        return conn
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            try:
                # Try to get connection from pool
                conn = self.pool.get(timeout=5)
            except Empty:
                # Pool is empty, create overflow connection if allowed
                with self.lock:
                    if self.overflow_connections < self.max_overflow:
                        conn = self._create_connection()
                        self.overflow_connections += 1
                        self.logger.debug(f"Created overflow connection ({self.overflow_connections}/{self.max_overflow})")
                    else:
                        # Wait for a connection to become available
                        conn = self.pool.get(timeout=30)
            
            yield conn
            
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                try:
                    # Return connection to pool or close if overflow
                    if self.overflow_connections > 0:
                        with self.lock:
                            self.overflow_connections -= 1
                        conn.close()
                    else:
                        self.pool.put(conn)
                except Exception as e:
                    self.logger.error(f"Error returning connection to pool: {e}")
                    conn.close()
    
    def close_all(self):
        """Close all connections in the pool"""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except Empty:
                break


class OptimizedDatabase:
    """Optimized database class with connection pooling and caching"""
    
    def __init__(self, db_path=None, pool_size=10):
        self.logger = logging.getLogger(__name__)
        
        # Use data directory for persistent database storage
        if db_path is None:
            db_path = '/app/data/vectorcraft.db' if os.path.exists('/app/data') else 'vectorcraft.db'
        
        self.db_path = db_path
        
        # Ensure the data directory exists
        if '/app/data/' in self.db_path:
            os.makedirs('/app/data', exist_ok=True)
        
        # Initialize connection pool
        self.pool = ConnectionPool(self.db_path, pool_size=pool_size)
        
        # Initialize database
        self.init_database()
        
        # Cache for frequently accessed data
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutes
    
    def init_database(self):
        """Initialize the database with required tables and indexes"""
        with self.pool.get_connection() as conn:
            # Create tables
            self._create_tables(conn)
            
            # Create indexes for performance
            self._create_indexes(conn)
            
            # Create triggers for data integrity
            self._create_triggers(conn)
        
        # Create default admin user
        self.create_default_users()
    
    def _create_tables(self, conn):
        """Create database tables"""
        tables = [
            '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                login_attempts INTEGER DEFAULT 0,
                last_attempt TIMESTAMP
            )
            ''',
            '''
            CREATE TABLE IF NOT EXISTS user_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_size INTEGER,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                svg_filename TEXT,
                processing_time REAL,
                strategy_used TEXT,
                quality_score REAL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''',
            '''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                username TEXT,
                amount DECIMAL(10,2),
                currency TEXT DEFAULT 'USD',
                paypal_order_id TEXT,
                paypal_payment_id TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                user_created INTEGER DEFAULT 0,
                email_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT
            )
            ''',
            '''
            CREATE TABLE IF NOT EXISTS system_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time INTEGER,
                error_message TEXT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''',
            '''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                component TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                user_email TEXT,
                transaction_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''',
            '''
            CREATE TABLE IF NOT EXISTS admin_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                component TEXT,
                resolved INTEGER DEFAULT 0,
                email_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
            ''',
            '''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT UNIQUE NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            '''
        ]
        
        for table_sql in tables:
            conn.execute(table_sql)
    
    def _create_indexes(self, conn):
        """Create database indexes for performance"""
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)',
            'CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)',
            'CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)',
            'CREATE INDEX IF NOT EXISTS idx_uploads_user_id ON user_uploads(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_uploads_date ON user_uploads(upload_date)',
            'CREATE INDEX IF NOT EXISTS idx_transactions_email ON transactions(email)',
            'CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)',
            'CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)',
            'CREATE INDEX IF NOT EXISTS idx_system_health_component ON system_health(component)',
            'CREATE INDEX IF NOT EXISTS idx_system_health_checked_at ON system_health(checked_at)',
            'CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level)',
            'CREATE INDEX IF NOT EXISTS idx_system_logs_component ON system_logs(component)',
            'CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at)',
            'CREATE INDEX IF NOT EXISTS idx_admin_alerts_resolved ON admin_alerts(resolved)',
            'CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions(is_active)',
            'CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)'
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
    
    def _create_triggers(self, conn):
        """Create database triggers for data integrity"""
        triggers = [
            '''
            CREATE TRIGGER IF NOT EXISTS update_user_last_login
            AFTER UPDATE ON users
            WHEN NEW.last_login IS NOT NULL AND OLD.last_login IS NULL
            BEGIN
                UPDATE users SET login_attempts = 0 WHERE id = NEW.id;
            END
            ''',
            '''
            CREATE TRIGGER IF NOT EXISTS cleanup_old_sessions
            AFTER INSERT ON user_sessions
            BEGIN
                DELETE FROM user_sessions 
                WHERE expires_at < datetime('now') AND is_active = 0;
            END
            '''
        ]
        
        for trigger_sql in triggers:
            conn.execute(trigger_sql)
    
    def create_default_users(self):
        """Create default admin user with secure credentials"""
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@vectorcraft.com')
        admin_password = os.getenv('ADMIN_PASSWORD')
        
        if not self.get_user_by_username(admin_username) and admin_password:
            self.create_user(admin_username, admin_email, admin_password)
            self.logger.info(f"Created default admin user ({admin_username})")
        elif not admin_password:
            self.logger.warning("ADMIN_PASSWORD environment variable not set")
    
    def _get_cache_key(self, key_type, identifier):
        """Generate cache key"""
        return f"{key_type}:{identifier}"
    
    def _get_from_cache(self, key):
        """Get value from cache if not expired"""
        if key in self._cache:
            timestamp = self._cache_timestamps.get(key, 0)
            if time.time() - timestamp < self._cache_ttl:
                return self._cache[key]
            else:
                # Remove expired entry
                del self._cache[key]
                del self._cache_timestamps[key]
        return None
    
    def _set_cache(self, key, value):
        """Set value in cache"""
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()
    
    def hash_password(self, password):
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        return password_hash.decode('utf-8'), salt.decode('utf-8')
    
    def verify_password(self, password, stored_hash):
        """Verify password against stored hash"""
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    
    def create_user(self, username, email, password):
        """Create a new user with optimized performance"""
        password_hash, salt = self.hash_password(password)
        
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO users (username, email, password_hash, salt)
                    VALUES (?, ?, ?, ?)
                ''', (username, email, password_hash, salt))
                
                user_id = cursor.lastrowid
                
                # Clear cache for user lookups
                self._clear_user_cache(username, email)
                
                return user_id
                
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Database IntegrityError: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Database Error: {e}")
            return None
    
    def _clear_user_cache(self, username=None, email=None):
        """Clear user cache entries"""
        if username:
            key = self._get_cache_key('user_username', username)
            if key in self._cache:
                del self._cache[key]
                del self._cache_timestamps[key]
        
        if email:
            key = self._get_cache_key('user_email', email)
            if key in self._cache:
                del self._cache[key]
                del self._cache_timestamps[key]
    
    def get_user_by_username(self, username):
        """Get user by username with caching"""
        cache_key = self._get_cache_key('user_username', username)
        cached_user = self._get_from_cache(cache_key)
        
        if cached_user:
            return cached_user
        
        with self.pool.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM users WHERE username = ? AND is_active = 1
            ''', (username,))
            row = cursor.fetchone()
            
            result = dict(row) if row else None
            
            # Cache the result
            self._set_cache(cache_key, result)
            
            return result
    
    def get_user_by_email(self, email):
        """Get user by email with caching"""
        cache_key = self._get_cache_key('user_email', email)
        cached_user = self._get_from_cache(cache_key)
        
        if cached_user:
            return cached_user
        
        with self.pool.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM users WHERE email = ? AND is_active = 1
            ''', (email,))
            row = cursor.fetchone()
            
            result = dict(row) if row else None
            
            # Cache the result
            self._set_cache(cache_key, result)
            
            return result
    
    def get_user_by_id(self, user_id):
        """Get user by ID with caching"""
        cache_key = self._get_cache_key('user_id', user_id)
        cached_user = self._get_from_cache(cache_key)
        
        if cached_user:
            return cached_user
        
        with self.pool.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM users WHERE id = ? AND is_active = 1
            ''', (user_id,))
            row = cursor.fetchone()
            
            result = dict(row) if row else None
            
            # Cache the result
            self._set_cache(cache_key, result)
            
            return result
    
    def authenticate_user(self, username, password):
        """Authenticate user credentials with rate limiting"""
        user = self.get_user_by_username(username)
        
        if not user:
            return None
        
        # Check if user is rate limited
        if user.get('login_attempts', 0) >= 5:
            last_attempt = user.get('last_attempt')
            if last_attempt:
                # Parse timestamp and check if 15 minutes have passed
                try:
                    last_attempt_dt = datetime.fromisoformat(last_attempt)
                    if (datetime.now() - last_attempt_dt).total_seconds() < 900:  # 15 minutes
                        return None
                except:
                    pass
        
        # Verify password
        if self.verify_password(password, user['password_hash']):
            # Successful login - update last login and reset attempts
            with self.pool.get_connection() as conn:
                conn.execute('''
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP, login_attempts = 0
                    WHERE id = ?
                ''', (user['id'],))
            
            # Clear cache
            self._clear_user_cache(username, user['email'])
            
            return user
        else:
            # Failed login - increment attempts
            with self.pool.get_connection() as conn:
                conn.execute('''
                    UPDATE users 
                    SET login_attempts = login_attempts + 1, last_attempt = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (user['id'],))
            
            # Clear cache
            self._clear_user_cache(username, user['email'])
            
            return None
    
    def get_user_uploads(self, user_id, limit=50):
        """Get user's upload history with optimized query"""
        cache_key = self._get_cache_key('user_uploads', f"{user_id}:{limit}")
        cached_uploads = self._get_from_cache(cache_key)
        
        if cached_uploads:
            return cached_uploads
        
        with self.pool.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM user_uploads 
                WHERE user_id = ? 
                ORDER BY upload_date DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            result = [dict(row) for row in cursor.fetchall()]
            
            # Cache the result for 60 seconds (shorter TTL for dynamic data)
            self._set_cache(cache_key, result)
            
            return result
    
    def get_upload_stats(self, user_id):
        """Get user's upload statistics with caching"""
        cache_key = self._get_cache_key('upload_stats', user_id)
        cached_stats = self._get_from_cache(cache_key)
        
        if cached_stats:
            return cached_stats
        
        with self.pool.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_uploads,
                    AVG(processing_time) as avg_processing_time,
                    SUM(file_size) as total_file_size,
                    AVG(quality_score) as avg_quality_score
                FROM user_uploads 
                WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            result = {
                'total_uploads': row[0] or 0,
                'avg_processing_time': round(row[1] or 0, 2),
                'total_file_size': row[2] or 0,
                'avg_quality_score': round(row[3] or 0, 2)
            }
            
            # Cache the result
            self._set_cache(cache_key, result)
            
            return result
    
    def record_upload(self, user_id, filename, original_filename, file_size, 
                     svg_filename=None, processing_time=None, strategy_used=None, quality_score=None):
        """Record a user upload with cache invalidation"""
        with self.pool.get_connection() as conn:
            conn.execute('''
                INSERT INTO user_uploads 
                (user_id, filename, original_filename, file_size, svg_filename, 
                 processing_time, strategy_used, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, filename, original_filename, file_size, 
                  svg_filename, processing_time, strategy_used, quality_score))
        
        # Clear cache for user uploads and stats
        upload_cache_key = self._get_cache_key('user_uploads', f"{user_id}:*")
        stats_cache_key = self._get_cache_key('upload_stats', user_id)
        
        # Clear all cached entries for this user's uploads
        keys_to_remove = []
        for key in self._cache.keys():
            if key.startswith(f"user_uploads:{user_id}:") or key == stats_cache_key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            if key in self._cache:
                del self._cache[key]
                del self._cache_timestamps[key]
    
    def close(self):
        """Close the database connection pool"""
        self.pool.close_all()
        self.logger.info("Database connection pool closed")


# Global optimized database instance
db_optimized = OptimizedDatabase()


if __name__ == '__main__':
    # Test the optimized database
    logger = logging.getLogger(__name__)
    logger.info("Testing VectorCraft Optimized Database...")
    logger.info(f"Database file: {db_optimized.db_path}")
    
    # Test connection pool
    start_time = time.time()
    
    # Test multiple concurrent connections
    import threading
    
    def test_connection():
        with db_optimized.pool.get_connection() as conn:
            cursor = conn.execute('SELECT 1')
            result = cursor.fetchone()
            logger.info(f"Connection test result: {result[0]}")
    
    # Create multiple threads to test connection pooling
    threads = []
    for i in range(20):
        thread = threading.Thread(target=test_connection)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    logger.info(f"Connection pool test completed in {end_time - start_time:.2f} seconds")
    
    # Test caching
    start_time = time.time()
    admin_user = db_optimized.get_user_by_username('admin')
    end_time = time.time()
    logger.info(f"First user lookup: {end_time - start_time:.4f} seconds")
    
    start_time = time.time()
    admin_user_cached = db_optimized.get_user_by_username('admin')
    end_time = time.time()
    logger.info(f"Cached user lookup: {end_time - start_time:.4f} seconds")
    
    logger.info("Database optimization test completed successfully!")