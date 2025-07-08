#!/usr/bin/env python3
"""
Database configuration and models for VectorCraft authentication
Uses SQLite for simplicity and Docker compatibility
"""

import sqlite3
import hashlib
import secrets
import os
import logging
from datetime import datetime
from pathlib import Path

class Database:
    def __init__(self, db_path=None):
        self.logger = logging.getLogger(__name__)
        # Use data directory for persistent database storage in Docker
        if db_path is None:
            db_path = '/app/data/vectorcraft.db' if os.path.exists('/app/data') else 'vectorcraft.db'
        self.db_path = db_path
        # Ensure the data directory exists in Docker
        if '/app/data/' in self.db_path:
            os.makedirs('/app/data', exist_ok=True)
        self.init_database()
    
    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            conn.execute('''
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
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Admin monitoring tables
            conn.execute('''
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
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time INTEGER,
                    error_message TEXT,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
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
            ''')
            
            conn.execute('''
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
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_transactions_email ON transactions(email)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_system_health_component ON system_health(component)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_system_health_checked_at ON system_health(checked_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_admin_alerts_resolved ON admin_alerts(resolved)')
            
            conn.commit()
            
        # Create default admin user if no users exist
        self.create_default_users()
    
    def create_default_users(self):
        """Create default users for demo purposes"""
        if not self.get_user_by_username('admin'):
            self.create_user('admin', 'admin@vectorcraft.com', 'admin123')
            self.logger.info("Created default admin user (admin/admin123)")
            
        if not self.get_user_by_username('demo'):
            self.create_user('demo', 'demo@vectorcraft.com', 'demo123')
            self.logger.info("Created demo user (demo/demo123)")
    
    def hash_password(self, password):
        """Hash password using bcrypt"""
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        return password_hash.decode('utf-8'), salt.decode('utf-8')
    
    def create_user(self, username, email, password):
        """Create a new user and return user ID"""
        password_hash, salt = self.hash_password(password)
        
        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO users (username, email, password_hash, salt)
                    VALUES (?, ?, ?, ?)
                ''', (username, email, password_hash, salt))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Database IntegrityError: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Database Error: {e}")
            return None
    
    def verify_password(self, password, stored_hash):
        """Verify password against stored hash using bcrypt"""
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    
    def authenticate_user(self, username, password):
        """Authenticate user credentials"""
        user = self.get_user_by_username(username)
        if user and self.verify_password(password, user['password_hash']):
            # Update last login
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (user['id'],))
                conn.commit()
            return user
        return None
    
    def get_user_by_username(self, username):
        """Get user by username"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM users WHERE username = ? AND is_active = 1
            ''', (username,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_by_email(self, email):
        """Get user by email"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM users WHERE email = ? AND is_active = 1
            ''', (email,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM users WHERE id = ? AND is_active = 1
            ''', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def record_upload(self, user_id, filename, original_filename, file_size, 
                     svg_filename=None, processing_time=None, strategy_used=None):
        """Record a user upload"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO user_uploads 
                (user_id, filename, original_filename, file_size, svg_filename, 
                 processing_time, strategy_used)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, filename, original_filename, file_size, 
                  svg_filename, processing_time, strategy_used))
            conn.commit()
    
    def get_user_uploads(self, user_id, limit=50):
        """Get user's upload history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM user_uploads 
                WHERE user_id = ? 
                ORDER BY upload_date DESC 
                LIMIT ?
            ''', (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_upload_stats(self, user_id):
        """Get user's upload statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_uploads,
                    AVG(processing_time) as avg_processing_time,
                    SUM(file_size) as total_file_size
                FROM user_uploads 
                WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()
            return {
                'total_uploads': row[0] or 0,
                'avg_processing_time': round(row[1] or 0, 2),
                'total_file_size': row[2] or 0
            }
    
    # Transaction logging methods
    def log_transaction(self, transaction_id, email, username=None, amount=None, currency='USD', 
                       paypal_order_id=None, paypal_payment_id=None, status='pending', 
                       error_message=None, user_created=False, email_sent=False, metadata=None):
        """Log a transaction for monitoring"""
        import json
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO transactions 
                (transaction_id, email, username, amount, currency, paypal_order_id, 
                 paypal_payment_id, status, error_message, user_created, email_sent, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (transaction_id, email, username, amount, currency, paypal_order_id,
                  paypal_payment_id, status, error_message, int(user_created), 
                  int(email_sent), json.dumps(metadata) if metadata else None))
            conn.commit()
    
    def update_transaction(self, transaction_id, **kwargs):
        """Update transaction status and details"""
        import json
        valid_fields = ['status', 'error_message', 'user_created', 'email_sent', 
                       'paypal_payment_id', 'completed_at', 'metadata']
        
        updates = []
        values = []
        for field, value in kwargs.items():
            if field in valid_fields:
                if field in ['user_created', 'email_sent']:
                    value = int(value)
                elif field == 'metadata' and value:
                    value = json.dumps(value)
                elif field == 'completed_at' and value is True:
                    value = 'CURRENT_TIMESTAMP'
                    updates.append(f"{field} = {value}")
                    continue
                updates.append(f"{field} = ?")
                values.append(value)
        
        if updates:
            values.append(transaction_id)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f'''
                    UPDATE transactions SET {', '.join(updates)}
                    WHERE transaction_id = ?
                ''', values)
                conn.commit()
    
    def get_transaction(self, transaction_id):
        """Get transaction by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM transactions WHERE transaction_id = ?
            ''', (transaction_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_transactions(self, limit=100, status=None, email=None, date_from=None):
        """Get transactions with optional filtering"""
        query = 'SELECT * FROM transactions WHERE 1=1'
        params = []
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        if email:
            query += ' AND email = ?'
            params.append(email)
        if date_from:
            query += ' AND created_at >= ?'
            params.append(date_from)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # System health monitoring methods
    def log_health_check(self, component, status, response_time=None, error_message=None):
        """Log system health check result"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO system_health 
                (component, status, response_time, error_message)
                VALUES (?, ?, ?, ?)
            ''', (component, status, response_time, error_message))
            conn.commit()
    
    def get_health_status(self, component=None, hours=24):
        """Get current health status for components"""
        query = '''
            SELECT component, status, response_time, error_message, 
                   MAX(checked_at) as last_check
            FROM system_health 
            WHERE checked_at >= datetime('now', '-{} hours')
        '''.format(hours)
        
        if component:
            query += ' AND component = ?'
            params = [component]
        else:
            params = []
        
        query += ' GROUP BY component ORDER BY last_check DESC'
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # System logging methods
    def log_system_event(self, level, component, message, details=None, user_email=None, transaction_id=None):
        """Log system event"""
        import json
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO system_logs 
                (level, component, message, details, user_email, transaction_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (level, component, message, 
                  json.dumps(details) if details else None, 
                  user_email, transaction_id))
            conn.commit()
    
    def get_system_logs(self, limit=100, level=None, component=None, hours=24):
        """Get system logs with filtering"""
        query = '''
            SELECT * FROM system_logs 
            WHERE created_at >= datetime('now', '-{} hours')
        '''.format(hours)
        params = []
        
        if level:
            query += ' AND level = ?'
            params.append(level)
        if component:
            query += ' AND component = ?'
            params.append(component)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # Admin alerts methods
    def create_alert(self, alert_type, title, message, component=None):
        """Create admin alert"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO admin_alerts 
                (type, title, message, component)
                VALUES (?, ?, ?, ?)
            ''', (alert_type, title, message, component))
            conn.commit()
            return cursor.lastrowid
    
    def resolve_alert(self, alert_id):
        """Mark alert as resolved"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE admin_alerts 
                SET resolved = 1, resolved_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (alert_id,))
            conn.commit()
    
    def get_alerts(self, resolved=None, limit=50):
        """Get admin alerts"""
        query = 'SELECT * FROM admin_alerts WHERE 1=1'
        params = []
        
        if resolved is not None:
            query += ' AND resolved = ?'
            params.append(int(resolved))
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

# Global database instance
db = Database()

if __name__ == '__main__':
    # Test the database
    logger = logging.getLogger(__name__)
    logger.info("Testing VectorCraft Database...")
    logger.info(f"Database file: {db.db_path}")
    
    # Test authentication
    user = db.authenticate_user('admin', 'admin123')
    if user:
        logger.info(f"Authentication successful for: {user['username']}")
        logger.info(f"   Email: {user['email']}")
        logger.info(f"   Created: {user['created_at']}")
    else:
        logger.error("Authentication failed")