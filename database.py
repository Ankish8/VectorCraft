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
from contextlib import contextmanager
import bcrypt

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
            
            # User activity tracking table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    activity_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Performance monitoring tables
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    value REAL NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type TEXT NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_percent REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Email tracking and management tables
            conn.execute('''
                CREATE TABLE IF NOT EXISTS email_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT,
                    email_type TEXT NOT NULL,
                    recipient_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    template_id TEXT,
                    status TEXT DEFAULT 'pending',
                    smtp_response TEXT,
                    delivery_attempts INTEGER DEFAULT 0,
                    sent_at TIMESTAMP,
                    delivered_at TIMESTAMP,
                    opened_at TIMESTAMP,
                    clicked_at TIMESTAMP,
                    bounced_at TIMESTAMP,
                    complaint_at TIMESTAMP,
                    error_message TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS email_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body_text TEXT NOT NULL,
                    body_html TEXT,
                    template_type TEXT NOT NULL,
                    variables TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS email_campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    template_id TEXT NOT NULL,
                    status TEXT DEFAULT 'draft',
                    scheduled_at TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    total_recipients INTEGER DEFAULT 0,
                    sent_count INTEGER DEFAULT 0,
                    delivered_count INTEGER DEFAULT 0,
                    opened_count INTEGER DEFAULT 0,
                    clicked_count INTEGER DEFAULT 0,
                    bounced_count INTEGER DEFAULT 0,
                    complaint_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (template_id) REFERENCES email_templates (template_id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notification_id TEXT UNIQUE NOT NULL,
                    user_id INTEGER,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    priority TEXT DEFAULT 'medium',
                    category TEXT,
                    status TEXT DEFAULT 'unread',
                    action_url TEXT,
                    action_text TEXT,
                    expires_at TIMESTAMP,
                    read_at TIMESTAMP,
                    dismissed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS communication_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_id TEXT UNIQUE NOT NULL,
                    user_id INTEGER,
                    email_address TEXT,
                    communication_type TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    subject TEXT,
                    content TEXT,
                    status TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS email_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    template_id TEXT,
                    emails_sent INTEGER DEFAULT 0,
                    emails_delivered INTEGER DEFAULT 0,
                    emails_opened INTEGER DEFAULT 0,
                    emails_clicked INTEGER DEFAULT 0,
                    emails_bounced INTEGER DEFAULT 0,
                    emails_complained INTEGER DEFAULT 0,
                    avg_delivery_time REAL,
                    avg_open_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS notification_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    notification_type TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    is_enabled BOOLEAN DEFAULT 1,
                    settings TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
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
            
            # User activity indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_user_activities_user_id ON user_activities(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_user_activities_type ON user_activities(activity_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_user_activities_timestamp ON user_activities(timestamp)')
            
            # Performance monitoring indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_performance_metrics_type ON performance_metrics(metric_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_performance_metrics_endpoint ON performance_metrics(endpoint)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_system_metrics_type ON system_metrics(metric_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp)')
            
            # Email and notification indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_logs_recipient ON email_logs(recipient_email)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_logs_created_at ON email_logs(created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_logs_transaction_id ON email_logs(transaction_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_logs_email_type ON email_logs(email_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_templates_template_id ON email_templates(template_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_templates_type ON email_templates(template_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_campaigns_status ON email_campaigns(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_campaigns_created_at ON email_campaigns(created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_communication_logs_user_id ON communication_logs(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_communication_logs_email ON communication_logs(email_address)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_communication_logs_type ON communication_logs(communication_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_communication_logs_created_at ON communication_logs(created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_performance_date ON email_performance(date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_performance_template_id ON email_performance(template_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_notification_settings_user_id ON notification_settings(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_notification_settings_type ON notification_settings(notification_type)')
            
            conn.commit()
            
        # Create default admin user if no users exist
        self.create_default_users()
    
    def create_default_users(self):
        """Create default admin user with secure credentials from environment"""
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@vectorcraft.com')
        admin_password = os.getenv('ADMIN_PASSWORD')
        
        # Only create admin if it doesn't exist and password is provided
        if not self.get_user_by_username(admin_username) and admin_password:
            self.create_user(admin_username, admin_email, admin_password)
            self.logger.info(f"Created default admin user ({admin_username})")
        elif not admin_password:
            self.logger.warning("ADMIN_PASSWORD environment variable not set - admin user not created")
            self.logger.warning("Set ADMIN_PASSWORD environment variable to create admin user")
    
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
    
    def log_performance_metric(self, metric_type, endpoint, value, status, timestamp=None):
        """Log performance metric"""
        if timestamp is None:
            timestamp = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO performance_metrics (metric_type, endpoint, value, status, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (metric_type, endpoint, value, status, timestamp))
            conn.commit()
    
    def log_system_metric(self, metric_type, cpu_percent=None, memory_percent=None, disk_percent=None, timestamp=None):
        """Log system metric"""
        if timestamp is None:
            timestamp = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO system_metrics (metric_type, cpu_percent, memory_percent, disk_percent, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (metric_type, cpu_percent, memory_percent, disk_percent, timestamp))
            conn.commit()
    
    def get_performance_metrics(self, metric_type=None, endpoint=None, hours=24, limit=1000):
        """Get performance metrics for specified time period"""
        query = '''
            SELECT * FROM performance_metrics 
            WHERE timestamp > datetime('now', '-{} hours')
        '''.format(hours)
        params = []
        
        if metric_type:
            query += ' AND metric_type = ?'
            params.append(metric_type)
        
        if endpoint:
            query += ' AND endpoint = ?'
            params.append(endpoint)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_system_metrics(self, metric_type=None, hours=24, limit=1000):
        """Get system metrics for specified time period"""
        query = '''
            SELECT * FROM system_metrics 
            WHERE timestamp > datetime('now', '-{} hours')
        '''.format(hours)
        params = []
        
        if metric_type:
            query += ' AND metric_type = ?'
            params.append(metric_type)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_performance_summary(self, hours=24):
        """Get performance summary for dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get request performance summary
            cursor = conn.execute('''
                SELECT 
                    endpoint,
                    COUNT(*) as total_requests,
                    AVG(value) as avg_response_time,
                    MIN(value) as min_response_time,
                    MAX(value) as max_response_time,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
                FROM performance_metrics
                WHERE metric_type = 'request_time' 
                AND timestamp > datetime('now', '-{} hours')
                GROUP BY endpoint
                ORDER BY total_requests DESC
            '''.format(hours))
            
            endpoint_stats = [dict(row) for row in cursor.fetchall()]
            
            # Get system performance summary
            cursor = conn.execute('''
                SELECT 
                    AVG(cpu_percent) as avg_cpu,
                    MAX(cpu_percent) as max_cpu,
                    AVG(memory_percent) as avg_memory,
                    MAX(memory_percent) as max_memory,
                    AVG(disk_percent) as avg_disk,
                    MAX(disk_percent) as max_disk
                FROM system_metrics
                WHERE timestamp > datetime('now', '-{} hours')
            '''.format(hours))
            
            system_stats = dict(cursor.fetchone()) if cursor.fetchone() else {}
            
            return {
                'endpoint_stats': endpoint_stats,
                'system_stats': system_stats,
                'time_period': f'Last {hours} hours'
            }
    
    # Email management methods
    def log_email(self, transaction_id, email_type, recipient_email, subject, template_id=None, 
                  status='pending', smtp_response=None, metadata=None):
        """Log email sending attempt"""
        import json
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO email_logs 
                (transaction_id, email_type, recipient_email, subject, template_id, 
                 status, smtp_response, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (transaction_id, email_type, recipient_email, subject, template_id,
                  status, smtp_response, json.dumps(metadata) if metadata else None))
            conn.commit()
            return cursor.lastrowid
    
    def update_email_status(self, email_log_id, status, **kwargs):
        """Update email log status and tracking fields"""
        valid_fields = ['delivered_at', 'opened_at', 'clicked_at', 'bounced_at', 
                       'complaint_at', 'error_message', 'smtp_response', 'delivery_attempts']
        
        updates = ['status = ?']
        values = [status]
        
        for field, value in kwargs.items():
            if field in valid_fields:
                if field.endswith('_at') and value is True:
                    value = 'CURRENT_TIMESTAMP'
                    updates.append(f"{field} = {value}")
                    continue
                elif field == 'delivery_attempts' and isinstance(value, str) and value == 'increment':
                    updates.append(f"{field} = {field} + 1")
                    continue
                updates.append(f"{field} = ?")
                values.append(value)
        
        if len(updates) > 1:
            values.append(email_log_id)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f'''
                    UPDATE email_logs SET {', '.join(updates)}
                    WHERE id = ?
                ''', values)
                conn.commit()
    
    def get_email_logs(self, limit=100, status=None, email_type=None, 
                      recipient_email=None, hours=None):
        """Get email logs with filtering"""
        query = 'SELECT * FROM email_logs WHERE 1=1'
        params = []
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        if email_type:
            query += ' AND email_type = ?'
            params.append(email_type)
        if recipient_email:
            query += ' AND recipient_email = ?'
            params.append(recipient_email)
        if hours:
            query += ' AND created_at >= datetime("now", "-{} hours")'.format(hours)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_email_analytics(self, days=30, template_id=None):
        """Get email analytics for dashboard"""
        query = '''
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as total_sent,
                SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
                SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) as clicked,
                SUM(CASE WHEN bounced_at IS NOT NULL THEN 1 ELSE 0 END) as bounced,
                SUM(CASE WHEN complaint_at IS NOT NULL THEN 1 ELSE 0 END) as complained,
                email_type
            FROM email_logs 
            WHERE created_at >= date('now', '-{} days')
        '''.format(days)
        params = []
        
        if template_id:
            query += ' AND template_id = ?'
            params.append(template_id)
        
        query += ' GROUP BY DATE(created_at), email_type ORDER BY date DESC'
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_email_performance_summary(self, hours=24):
        """Get email performance summary for dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_emails,
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as delivered,
                    SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
                    SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) as clicked,
                    SUM(CASE WHEN bounced_at IS NOT NULL THEN 1 ELSE 0 END) as bounced,
                    SUM(CASE WHEN complaint_at IS NOT NULL THEN 1 ELSE 0 END) as complained,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(delivery_attempts) as avg_delivery_attempts
                FROM email_logs 
                WHERE created_at >= datetime('now', '-{} hours')
            '''.format(hours))
            
            result = dict(cursor.fetchone())
            
            # Calculate rates
            total = result['total_emails'] or 1
            result['delivery_rate'] = (result['delivered'] / total) * 100 if total > 0 else 0
            result['open_rate'] = (result['opened'] / total) * 100 if total > 0 else 0
            result['click_rate'] = (result['clicked'] / total) * 100 if total > 0 else 0
            result['bounce_rate'] = (result['bounced'] / total) * 100 if total > 0 else 0
            result['complaint_rate'] = (result['complained'] / total) * 100 if total > 0 else 0
            
            return result
    
    # Email template management methods
    def create_email_template(self, template_id, name, subject, body_text, body_html=None, 
                             template_type='transactional', variables=None):
        """Create email template"""
        import json
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO email_templates 
                (template_id, name, subject, body_text, body_html, template_type, variables)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (template_id, name, subject, body_text, body_html, template_type,
                  json.dumps(variables) if variables else None))
            conn.commit()
            return cursor.lastrowid
    
    def update_email_template(self, template_id, **kwargs):
        """Update email template"""
        import json
        valid_fields = ['name', 'subject', 'body_text', 'body_html', 
                       'template_type', 'variables', 'is_active']
        
        updates = ['updated_at = CURRENT_TIMESTAMP']
        values = []
        
        for field, value in kwargs.items():
            if field in valid_fields:
                if field == 'variables' and value:
                    value = json.dumps(value)
                elif field == 'is_active':
                    value = int(value)
                updates.append(f"{field} = ?")
                values.append(value)
        
        if len(updates) > 1:
            values.append(template_id)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f'''
                    UPDATE email_templates SET {', '.join(updates)}
                    WHERE template_id = ?
                ''', values)
                conn.commit()
    
    def get_email_templates(self, template_type=None, is_active=None):
        """Get email templates"""
        query = 'SELECT * FROM email_templates WHERE 1=1'
        params = []
        
        if template_type:
            query += ' AND template_type = ?'
            params.append(template_type)
        if is_active is not None:
            query += ' AND is_active = ?'
            params.append(int(is_active))
        
        query += ' ORDER BY created_at DESC'
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_email_template(self, template_id):
        """Get single email template"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM email_templates WHERE template_id = ?
            ''', (template_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # Notification management methods
    def create_notification(self, notification_id, user_id, notification_type, title, message, 
                           priority='medium', category=None, action_url=None, 
                           action_text=None, expires_at=None):
        """Create notification"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO notifications 
                (notification_id, user_id, type, title, message, priority, category, 
                 action_url, action_text, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (notification_id, user_id, notification_type, title, message, 
                  priority, category, action_url, action_text, expires_at))
            conn.commit()
            return cursor.lastrowid
    
    def update_notification_status(self, notification_id, status, **kwargs):
        """Update notification status"""
        valid_fields = ['read_at', 'dismissed_at']
        
        updates = ['status = ?']
        values = [status]
        
        for field, value in kwargs.items():
            if field in valid_fields:
                if field.endswith('_at') and value is True:
                    value = 'CURRENT_TIMESTAMP'
                    updates.append(f"{field} = {value}")
                    continue
                updates.append(f"{field} = ?")
                values.append(value)
        
        if len(updates) > 1:
            values.append(notification_id)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f'''
                    UPDATE notifications SET {', '.join(updates)}
                    WHERE notification_id = ?
                ''', values)
                conn.commit()
    
    def get_notifications(self, user_id=None, status=None, notification_type=None, 
                         limit=50, include_expired=False):
        """Get notifications"""
        query = 'SELECT * FROM notifications WHERE 1=1'
        params = []
        
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)
        if status:
            query += ' AND status = ?'
            params.append(status)
        if notification_type:
            query += ' AND type = ?'
            params.append(notification_type)
        if not include_expired:
            query += ' AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)'
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_notification_summary(self, user_id=None):
        """Get notification summary for dashboard"""
        query = '''
            SELECT 
                COUNT(*) as total_notifications,
                SUM(CASE WHEN status = 'unread' THEN 1 ELSE 0 END) as unread_count,
                SUM(CASE WHEN status = 'read' THEN 1 ELSE 0 END) as read_count,
                SUM(CASE WHEN priority = 'high' AND status = 'unread' THEN 1 ELSE 0 END) as high_priority_unread,
                SUM(CASE WHEN expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP THEN 1 ELSE 0 END) as expired_count
            FROM notifications 
            WHERE 1=1
        '''
        params = []
        
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return dict(cursor.fetchone())
    
    # Communication log methods
    def log_communication(self, log_id, user_id, email_address, communication_type, 
                         direction, subject=None, content=None, status='sent', metadata=None):
        """Log communication event"""
        import json
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO communication_logs 
                (log_id, user_id, email_address, communication_type, direction, 
                 subject, content, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (log_id, user_id, email_address, communication_type, direction,
                  subject, content, status, json.dumps(metadata) if metadata else None))
            conn.commit()
            return cursor.lastrowid
    
    def get_communication_logs(self, user_id=None, email_address=None, 
                              communication_type=None, limit=100, hours=None):
        """Get communication logs"""
        query = 'SELECT * FROM communication_logs WHERE 1=1'
        params = []
        
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)
        if email_address:
            query += ' AND email_address = ?'
            params.append(email_address)
        if communication_type:
            query += ' AND communication_type = ?'
            params.append(communication_type)
        if hours:
            query += ' AND created_at >= datetime("now", "-{} hours")'.format(hours)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_communication_summary(self, hours=24):
        """Get communication summary for dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT 
                    communication_type,
                    direction,
                    COUNT(*) as total_count,
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count
                FROM communication_logs 
                WHERE created_at >= datetime('now', '-{} hours')
                GROUP BY communication_type, direction
                ORDER BY total_count DESC
            '''.format(hours))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # Advanced User Management Methods
    def get_all_users(self, page=1, per_page=50, search=None, status=None, sort_by='created_at', sort_order='DESC'):
        """Get all users with pagination, search, and filtering"""
        offset = (page - 1) * per_page
        
        query = '''
            SELECT u.*, 
                   (SELECT COUNT(*) FROM user_uploads WHERE user_id = u.id) as upload_count,
                   (SELECT COUNT(*) FROM user_activities WHERE user_id = u.id) as activity_count,
                   (SELECT upload_date FROM user_uploads WHERE user_id = u.id ORDER BY upload_date DESC LIMIT 1) as last_upload
            FROM users u
            WHERE 1=1
        '''
        params = []
        
        if search:
            query += ' AND (u.username LIKE ? OR u.email LIKE ?)'
            params.extend([f'%{search}%', f'%{search}%'])
        
        if status is not None:
            query += ' AND u.is_active = ?'
            params.append(int(status))
        
        # Add sorting
        valid_sort_fields = ['username', 'email', 'created_at', 'last_login', 'upload_count']
        if sort_by in valid_sort_fields:
            query += f' ORDER BY {sort_by} {sort_order}'
        else:
            query += ' ORDER BY created_at DESC'
        
        query += ' LIMIT ? OFFSET ?'
        params.extend([per_page, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            users = [dict(row) for row in cursor.fetchall()]
            
            # Get total count for pagination
            count_query = 'SELECT COUNT(*) FROM users WHERE 1=1'
            count_params = []
            
            if search:
                count_query += ' AND (username LIKE ? OR email LIKE ?)'
                count_params.extend([f'%{search}%', f'%{search}%'])
            
            if status is not None:
                count_query += ' AND is_active = ?'
                count_params.append(int(status))
            
            cursor = conn.execute(count_query, count_params)
            total = cursor.fetchone()[0]
            
            return users, total
    
    def get_user_activity_timeline(self, user_id, limit=100, activity_type=None):
        """Get comprehensive user activity timeline"""
        query = '''
            SELECT 
                ua.activity_type,
                ua.description,
                ua.ip_address,
                ua.user_agent,
                ua.details,
                ua.timestamp,
                'activity' as source_type
            FROM user_activities ua
            WHERE ua.user_id = ?
        '''
        params = [user_id]
        
        if activity_type:
            query += ' AND ua.activity_type = ?'
            params.append(activity_type)
        
        query += '''
            UNION ALL
            SELECT 
                'upload' as activity_type,
                'Uploaded file: ' || uu.original_filename as description,
                NULL as ip_address,
                NULL as user_agent,
                json_object(
                    'filename', uu.filename,
                    'file_size', uu.file_size,
                    'processing_time', uu.processing_time,
                    'strategy_used', uu.strategy_used
                ) as details,
                uu.upload_date as timestamp,
                'upload' as source_type
            FROM user_uploads uu
            WHERE uu.user_id = ?
        '''
        params.append(user_id)
        
        # Add login activity from transactions if available
        query += '''
            UNION ALL
            SELECT 
                'transaction' as activity_type,
                'Payment completed: $' || t.amount as description,
                NULL as ip_address,
                NULL as user_agent,
                json_object(
                    'amount', t.amount,
                    'currency', t.currency,
                    'transaction_id', t.transaction_id,
                    'paypal_order_id', t.paypal_order_id
                ) as details,
                t.completed_at as timestamp,
                'transaction' as source_type
            FROM transactions t
            WHERE t.email = (SELECT email FROM users WHERE id = ?) 
                AND t.status = 'completed'
                AND t.completed_at IS NOT NULL
        '''
        params.append(user_id)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def log_user_activity(self, user_id, activity_type, description, ip_address=None, user_agent=None, details=None):
        """Log user activity"""
        import json
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO user_activities 
                (user_id, activity_type, description, ip_address, user_agent, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, activity_type, description, ip_address, user_agent, 
                  json.dumps(details) if details else None))
            conn.commit()
    
    def bulk_update_users(self, user_ids, updates):
        """Bulk update users (activate/deactivate)"""
        if not user_ids or not updates:
            return False
        
        valid_fields = ['is_active']
        update_clauses = []
        values = []
        
        for field, value in updates.items():
            if field in valid_fields:
                update_clauses.append(f"{field} = ?")
                values.append(int(value) if field == 'is_active' else value)
        
        if not update_clauses:
            return False
        
        placeholders = ','.join(['?' for _ in user_ids])
        query = f'''
            UPDATE users 
            SET {', '.join(update_clauses)}
            WHERE id IN ({placeholders})
        '''
        values.extend(user_ids)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, values)
            conn.commit()
            return cursor.rowcount
    
    def delete_users(self, user_ids):
        """Delete users (soft delete by setting is_active=0)"""
        if not user_ids:
            return False
        
        placeholders = ','.join(['?' for _ in user_ids])
        query = f'''
            UPDATE users 
            SET is_active = 0
            WHERE id IN ({placeholders})
        '''
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, user_ids)
            conn.commit()
            return cursor.rowcount
    
    def get_user_segments(self):
        """Get user segmentation data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Active vs Inactive users
            cursor = conn.execute('''
                SELECT 
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_users,
                    SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as inactive_users,
                    COUNT(*) as total_users
                FROM users
            ''')
            user_status = dict(cursor.fetchone())
            
            # Users by registration date
            cursor = conn.execute('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as user_count
                FROM users
                WHERE created_at >= date('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''')
            registration_trend = [dict(row) for row in cursor.fetchall()]
            
            # Users by activity level
            cursor = conn.execute('''
                SELECT 
                    CASE 
                        WHEN upload_count = 0 THEN 'No Activity'
                        WHEN upload_count BETWEEN 1 AND 5 THEN 'Low Activity'
                        WHEN upload_count BETWEEN 6 AND 20 THEN 'Medium Activity'
                        ELSE 'High Activity'
                    END as activity_level,
                    COUNT(*) as user_count
                FROM (
                    SELECT u.id, COUNT(uu.id) as upload_count
                    FROM users u
                    LEFT JOIN user_uploads uu ON u.id = uu.user_id
                    WHERE u.is_active = 1
                    GROUP BY u.id
                ) user_activity
                GROUP BY activity_level
            ''')
            activity_segments = [dict(row) for row in cursor.fetchall()]
            
            # Recent vs Old users
            cursor = conn.execute('''
                SELECT 
                    CASE 
                        WHEN created_at >= date('now', '-7 days') THEN 'New (Last 7 days)'
                        WHEN created_at >= date('now', '-30 days') THEN 'Recent (Last 30 days)'
                        ELSE 'Established'
                    END as user_age,
                    COUNT(*) as user_count
                FROM users
                WHERE is_active = 1
                GROUP BY user_age
            ''')
            age_segments = [dict(row) for row in cursor.fetchall()]
            
            return {
                'status_distribution': user_status,
                'registration_trend': registration_trend,
                'activity_segments': activity_segments,
                'age_segments': age_segments
            }
    
    def get_user_analytics(self, user_id):
        """Get detailed analytics for a specific user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Basic user info
            cursor = conn.execute('''
                SELECT * FROM users WHERE id = ?
            ''', (user_id,))
            user_info = dict(cursor.fetchone() or {})
            
            # Upload statistics
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_uploads,
                    AVG(file_size) as avg_file_size,
                    SUM(file_size) as total_file_size,
                    AVG(processing_time) as avg_processing_time,
                    MIN(upload_date) as first_upload,
                    MAX(upload_date) as last_upload
                FROM user_uploads
                WHERE user_id = ?
            ''', (user_id,))
            upload_stats = dict(cursor.fetchone() or {})
            
            # Activity statistics
            cursor = conn.execute('''
                SELECT 
                    activity_type,
                    COUNT(*) as count
                FROM user_activities
                WHERE user_id = ?
                GROUP BY activity_type
            ''', (user_id,))
            activity_stats = [dict(row) for row in cursor.fetchall()]
            
            # Recent activity
            cursor = conn.execute('''
                SELECT 
                    activity_type,
                    description,
                    timestamp
                FROM user_activities
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 10
            ''', (user_id,))
            recent_activity = [dict(row) for row in cursor.fetchall()]
            
            # Upload history by date
            cursor = conn.execute('''
                SELECT 
                    DATE(upload_date) as date,
                    COUNT(*) as upload_count
                FROM user_uploads
                WHERE user_id = ?
                GROUP BY DATE(upload_date)
                ORDER BY date DESC
                LIMIT 30
            ''', (user_id,))
            upload_history = [dict(row) for row in cursor.fetchall()]
            
            return {
                'user_info': user_info,
                'upload_stats': upload_stats,
                'activity_stats': activity_stats,
                'recent_activity': recent_activity,
                'upload_history': upload_history
            }

# Global database instance
db = Database()

if __name__ == '__main__':
    # Test the database
    logger = logging.getLogger(__name__)
    logger.info("Testing VectorCraft Database...")
    logger.info(f"Database file: {db.db_path}")
    
    # Test database initialization
    logger.info("Database initialization complete")
    
    # Check if admin user exists
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    user = db.get_user_by_username(admin_username)
    if user:
        logger.info(f"Admin user exists: {user['username']}")
        logger.info(f"   Email: {user['email']}")
        logger.info(f"   Created: {user['created_at']}")
    else:
        logger.warning("No admin user found. Set ADMIN_PASSWORD environment variable to create one.")
    
    # Real-time analytics methods
    def get_transactions_since(self, since):
        """Get transactions since a specific datetime"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM transactions 
                WHERE created_at >= ? 
                ORDER BY created_at DESC
            ''', (since.isoformat(),))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_transactions_between(self, start_time, end_time):
        """Get transactions between two datetimes"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM transactions 
                WHERE created_at >= ? AND created_at < ? 
                ORDER BY created_at DESC
            ''', (start_time.isoformat(), end_time.isoformat()))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_user_activities(self, limit=50):
        """Get recent user activities"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT ua.*, u.username, u.email 
                FROM user_activities ua
                JOIN users u ON ua.user_id = u.id
                ORDER BY ua.timestamp DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_active_users(self, minutes=30):
        """Get users active within the last N minutes"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT DISTINCT u.id, u.username, u.email, u.last_login
                FROM users u
                JOIN user_activities ua ON u.id = ua.user_id
                WHERE ua.timestamp >= datetime('now', '-{} minutes')
                ORDER BY u.last_login DESC
            '''.format(minutes))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_vectorization_activities(self, limit=20):
        """Get recent vectorization activities"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT uu.*, u.username, u.email 
                FROM user_uploads uu
                JOIN users u ON uu.user_id = u.id
                ORDER BY uu.upload_date DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def log_user_activity(self, user_id, activity_type, description, ip_address=None, user_agent=None, details=None):
        """Log user activity for tracking"""
        import json
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO user_activities 
                (user_id, activity_type, description, ip_address, user_agent, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, activity_type, description, ip_address, user_agent, 
                  json.dumps(details) if details else None))
            conn.commit()
    
    def log_performance_metric(self, metric_type, endpoint, value, status='normal'):
        """Log performance metric"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO performance_metrics 
                (metric_type, endpoint, value, status)
                VALUES (?, ?, ?, ?)
            ''', (metric_type, endpoint, value, status))
            conn.commit()
    
    def log_system_metric(self, metric_type, cpu_percent=None, memory_percent=None, disk_percent=None):
        """Log system metric"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO system_metrics 
                (metric_type, cpu_percent, memory_percent, disk_percent)
                VALUES (?, ?, ?, ?)
            ''', (metric_type, cpu_percent, memory_percent, disk_percent))
            conn.commit()
    
    def get_system_metrics(self, hours=24, metric_type=None):
        """Get system metrics for a time period"""
        query = '''
            SELECT * FROM system_metrics 
            WHERE timestamp >= datetime('now', '-{} hours')
        '''.format(hours)
        params = []
        
        if metric_type:
            query += ' AND metric_type = ?'
            params.append(metric_type)
        
        query += ' ORDER BY timestamp DESC'
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_performance_metrics(self, hours=24, endpoint=None):
        """Get performance metrics for a time period"""
        query = '''
            SELECT * FROM performance_metrics 
            WHERE timestamp >= datetime('now', '-{} hours')
        '''.format(hours)
        params = []
        
        if endpoint:
            query += ' AND endpoint = ?'
            params.append(endpoint)
        
        query += ' ORDER BY timestamp DESC'
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]