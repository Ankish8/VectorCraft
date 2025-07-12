#!/usr/bin/env python3
"""
Database configuration and models for VectorCraft authentication
Uses SQLite for simplicity and Docker compatibility
"""

import sqlite3
import hashlib
import secrets
import os
import base64
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet

class Database:
    def __init__(self, db_path=None):
        # Use data directory for persistent database storage in Docker
        if db_path is None:
            db_path = '/app/data/vectorcraft.db' if os.path.exists('/app/data') else 'vectorcraft.db'
        self.db_path = db_path
        # Ensure the data directory exists in Docker
        if '/app/data/' in self.db_path:
            os.makedirs('/app/data', exist_ok=True)
        self.init_database()
    
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
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS smtp_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    smtp_server TEXT NOT NULL,
                    smtp_port INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    from_email TEXT NOT NULL,
                    use_tls INTEGER DEFAULT 1,
                    use_ssl INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS paypal_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT NOT NULL,
                    client_secret TEXT NOT NULL,
                    environment TEXT NOT NULL CHECK(environment IN ('sandbox', 'live')),
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Email automation tables
            conn.execute('''
                CREATE TABLE IF NOT EXISTS email_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content_html TEXT NOT NULL,
                    content_json TEXT,
                    variables TEXT,
                    description TEXT,
                    category TEXT DEFAULT 'general',
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS email_automations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    trigger_type TEXT NOT NULL CHECK(trigger_type IN ('purchase', 'signup', 'scheduled', 'activity', 'custom')),
                    trigger_condition TEXT,
                    template_id INTEGER NOT NULL,
                    delay_hours INTEGER DEFAULT 0,
                    send_time TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (template_id) REFERENCES email_templates (id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS email_campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    template_id INTEGER NOT NULL,
                    target_audience TEXT,
                    scheduled_at TIMESTAMP,
                    sent_at TIMESTAMP,
                    status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'scheduled', 'sending', 'sent', 'cancelled')),
                    total_recipients INTEGER DEFAULT 0,
                    emails_sent INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (template_id) REFERENCES email_templates (id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS email_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient_email TEXT NOT NULL,
                    recipient_name TEXT,
                    template_id INTEGER,
                    campaign_id INTEGER,
                    automation_id INTEGER,
                    subject TEXT NOT NULL,
                    content_html TEXT NOT NULL,
                    variables_json TEXT,
                    scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    opened_at TIMESTAMP,
                    clicked_at TIMESTAMP,
                    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'sending', 'sent', 'failed', 'bounced')),
                    error_message TEXT,
                    attempts INTEGER DEFAULT 0,
                    tracking_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (template_id) REFERENCES email_templates (id),
                    FOREIGN KEY (campaign_id) REFERENCES email_campaigns (id),
                    FOREIGN KEY (automation_id) REFERENCES email_automations (id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS email_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tracking_id TEXT NOT NULL,
                    queue_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL CHECK(event_type IN ('sent', 'delivered', 'opened', 'clicked', 'bounced', 'unsubscribed')),
                    event_data TEXT,
                    user_agent TEXT,
                    ip_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (queue_id) REFERENCES email_queue (id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS email_unsubscribes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    reason TEXT,
                    unsubscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            
            # Email automation indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_templates_category ON email_templates(category)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_templates_is_active ON email_templates(is_active)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_automations_trigger_type ON email_automations(trigger_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_automations_is_active ON email_automations(is_active)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_queue(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_queue_scheduled_at ON email_queue(scheduled_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_queue_tracking_id ON email_queue(tracking_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_tracking_tracking_id ON email_tracking(tracking_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_tracking_event_type ON email_tracking(event_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_email_unsubscribes_email ON email_unsubscribes(email)')
            
            conn.commit()
            
        # Create default admin user if no users exist
        self.create_default_users()
    
    def create_default_users(self):
        """Create default users for demo purposes"""
        if not self.get_user_by_username('admin'):
            self.create_user('admin', 'admin@vectorcraft.com', 'admin123')
            print("✅ Created default admin user (admin/admin123)")
            
        if not self.get_user_by_username('demo'):
            self.create_user('demo', 'demo@vectorcraft.com', 'demo123')
            print("✅ Created demo user (demo/demo123)")
    
    def hash_password(self, password, salt=None):
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use SHA-256 with salt
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash, salt
    
    def create_user(self, username, email, password):
        """Create a new user and return user ID"""
        password_hash, salt = self.hash_password(password)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    INSERT INTO users (username, email, password_hash, salt)
                    VALUES (?, ?, ?, ?)
                ''', (username, email, password_hash, salt))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            print(f"❌ Database IntegrityError: {e}")
            return None
        except Exception as e:
            print(f"❌ Database Error: {e}")
            return None
    
    def verify_password(self, password, stored_hash, salt):
        """Verify password against stored hash"""
        password_hash, _ = self.hash_password(password, salt)
        return password_hash == stored_hash
    
    def authenticate_user(self, username, password):
        """Authenticate user credentials"""
        user = self.get_user_by_username(username)
        if user and self.verify_password(password, user['password_hash'], user['salt']):
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
    
    # SMTP Configuration methods
    def _get_encryption_key(self):
        """Get or create encryption key for SMTP passwords"""
        key_file = os.path.join(os.path.dirname(self.db_path), '.smtp_key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            return key
    
    def encrypt_password(self, password):
        """Encrypt SMTP password"""
        key = self._get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(password.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_password(self, encrypted_password):
        """Decrypt SMTP password"""
        try:
            key = self._get_encryption_key()
            f = Fernet(key)
            decoded = base64.b64decode(encrypted_password.encode())
            decrypted = f.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            print(f"❌ Error decrypting password: {e}")
            return None
    
    def save_smtp_settings(self, smtp_server, smtp_port, username, password, from_email, 
                          use_tls=True, use_ssl=False):
        """Save SMTP configuration"""
        encrypted_password = self.encrypt_password(password)
        
        # Check if settings already exist
        existing = self.get_smtp_settings()
        
        with sqlite3.connect(self.db_path) as conn:
            if existing:
                # Update existing settings
                conn.execute('''
                    UPDATE smtp_settings 
                    SET smtp_server = ?, smtp_port = ?, username = ?, password = ?, 
                        from_email = ?, use_tls = ?, use_ssl = ?, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (smtp_server, smtp_port, username, encrypted_password, from_email,
                      int(use_tls), int(use_ssl), existing['id']))
            else:
                # Insert new settings
                conn.execute('''
                    INSERT INTO smtp_settings 
                    (smtp_server, smtp_port, username, password, from_email, use_tls, use_ssl)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (smtp_server, smtp_port, username, encrypted_password, from_email,
                      int(use_tls), int(use_ssl)))
            conn.commit()
    
    def get_smtp_settings(self, decrypt_password=False):
        """Get SMTP configuration"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM smtp_settings WHERE is_active = 1 
                ORDER BY created_at DESC LIMIT 1
            ''')
            row = cursor.fetchone()
            
            if row:
                settings = dict(row)
                if decrypt_password and settings['password']:
                    settings['password'] = self.decrypt_password(settings['password'])
                elif not decrypt_password:
                    # Mask password for security
                    settings['password'] = '***ENCRYPTED***'
                return settings
            return None
    
    def test_smtp_connection(self, smtp_server, smtp_port, username, password, use_tls=True, use_ssl=False):
        """Test SMTP connection without saving"""
        import smtplib
        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                if use_tls:
                    server.starttls()
            
            with server:
                server.login(username, password)
                return True, "Connection successful"
        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed - check username and password"
        except smtplib.SMTPConnectError:
            return False, f"Cannot connect to server {smtp_server}:{smtp_port}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    # PayPal Configuration methods
    def save_paypal_settings(self, client_id, client_secret, environment='sandbox'):
        """Save PayPal configuration with encrypted client secret"""
        encrypted_secret = self.encrypt_password(client_secret)
        
        # Check if settings already exist
        existing = self.get_paypal_settings()
        
        with sqlite3.connect(self.db_path) as conn:
            if existing:
                # Update existing settings
                conn.execute('''
                    UPDATE paypal_settings 
                    SET client_id = ?, client_secret = ?, environment = ?, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (client_id, encrypted_secret, environment, existing['id']))
            else:
                # Insert new settings
                conn.execute('''
                    INSERT INTO paypal_settings 
                    (client_id, client_secret, environment)
                    VALUES (?, ?, ?)
                ''', (client_id, encrypted_secret, environment))
            conn.commit()
    
    def get_paypal_settings(self, decrypt_secret=False):
        """Get PayPal configuration"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM paypal_settings WHERE is_active = 1 
                ORDER BY created_at DESC LIMIT 1
            ''')
            row = cursor.fetchone()
            
            if row:
                settings = dict(row)
                if decrypt_secret and settings['client_secret']:
                    settings['client_secret'] = self.decrypt_password(settings['client_secret'])
                elif not decrypt_secret:
                    # Mask secret for security
                    settings['client_secret'] = '***ENCRYPTED***'
                return settings
            return None
    
    def test_paypal_connection(self, client_id, client_secret, environment='sandbox'):
        """Test PayPal connection without saving"""
        try:
            import requests
            
            # Determine the base URL based on environment
            if environment == 'sandbox':
                base_url = 'https://api-m.sandbox.paypal.com'
            else:
                base_url = 'https://api-m.paypal.com'
            
            # Test authentication by getting an access token
            auth_url = f'{base_url}/v1/oauth2/token'
            
            response = requests.post(
                auth_url,
                headers={'Accept': 'application/json'},
                auth=(client_id, client_secret),
                data={'grant_type': 'client_credentials'},
                timeout=10
            )
            
            if response.status_code == 200:
                return True, f"PayPal {environment} connection successful"
            elif response.status_code == 401:
                return False, "Invalid PayPal credentials"
            else:
                return False, f"PayPal API error: HTTP {response.status_code}"
                
        except requests.RequestException as e:
            return False, f"Connection error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    # Email Template Management
    def create_email_template(self, name, subject, content_html, content_json=None, variables=None, description=None, category='general'):
        """Create a new email template"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    INSERT INTO email_templates (name, subject, content_html, content_json, variables, description, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, subject, content_html, content_json, variables, description, category))
                return cursor.lastrowid
        except Exception as e:
            print(f"Error creating email template: {e}")
            return None
    
    def get_email_templates(self, category=None, active_only=True):
        """Get all email templates"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                query = 'SELECT * FROM email_templates'
                params = []
                
                conditions = []
                if active_only:
                    conditions.append('is_active = 1')
                if category:
                    conditions.append('category = ?')
                    params.append(category)
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
                
                query += ' ORDER BY created_at DESC'
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching email templates: {e}")
            return []
    
    def get_email_template(self, template_id):
        """Get a specific email template"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('SELECT * FROM email_templates WHERE id = ?', (template_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error fetching email template: {e}")
            return None
    
    def update_email_template(self, template_id, name=None, subject=None, content_html=None, content_json=None, variables=None, description=None, category=None):
        """Update an email template"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                updates = []
                params = []
                
                if name is not None:
                    updates.append('name = ?')
                    params.append(name)
                if subject is not None:
                    updates.append('subject = ?')
                    params.append(subject)
                if content_html is not None:
                    updates.append('content_html = ?')
                    params.append(content_html)
                if content_json is not None:
                    updates.append('content_json = ?')
                    params.append(content_json)
                if variables is not None:
                    updates.append('variables = ?')
                    params.append(variables)
                if description is not None:
                    updates.append('description = ?')
                    params.append(description)
                if category is not None:
                    updates.append('category = ?')
                    params.append(category)
                
                if updates:
                    updates.append('updated_at = CURRENT_TIMESTAMP')
                    params.append(template_id)
                    
                    query = f'UPDATE email_templates SET {", ".join(updates)} WHERE id = ?'
                    conn.execute(query, params)
                    return conn.total_changes > 0
                return False
        except Exception as e:
            print(f"Error updating email template: {e}")
            return False
    
    def delete_email_template(self, template_id):
        """Delete an email template (soft delete)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('UPDATE email_templates SET is_active = 0 WHERE id = ?', (template_id,))
                return conn.total_changes > 0
        except Exception as e:
            print(f"Error deleting email template: {e}")
            return False
    
    # Email Automation Management
    def create_email_automation(self, name, trigger_type, template_id, delay_hours=0, trigger_condition=None, description=None, send_time=None):
        """Create a new email automation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    INSERT INTO email_automations (name, description, trigger_type, trigger_condition, template_id, delay_hours, send_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, description, trigger_type, trigger_condition, template_id, delay_hours, send_time))
                return cursor.lastrowid
        except Exception as e:
            print(f"Error creating email automation: {e}")
            return None
    
    def get_email_automations(self, active_only=True):
        """Get all email automations"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                query = '''
                    SELECT a.*, t.name as template_name, t.subject as template_subject
                    FROM email_automations a
                    LEFT JOIN email_templates t ON a.template_id = t.id
                '''
                
                if active_only:
                    query += ' WHERE a.is_active = 1'
                
                query += ' ORDER BY a.created_at DESC'
                
                cursor = conn.execute(query)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching email automations: {e}")
            return []
    
    def get_email_automation(self, automation_id):
        """Get a specific email automation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT a.*, t.name as template_name, t.subject as template_subject
                    FROM email_automations a
                    LEFT JOIN email_templates t ON a.template_id = t.id
                    WHERE a.id = ?
                ''', (automation_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error fetching email automation: {e}")
            return None
    
    def update_email_automation(self, automation_id, **kwargs):
        """Update an email automation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                updates = []
                params = []
                
                allowed_fields = ['name', 'description', 'trigger_type', 'trigger_condition', 'template_id', 'delay_hours', 'send_time', 'is_active']
                
                for field, value in kwargs.items():
                    if field in allowed_fields and value is not None:
                        updates.append(f'{field} = ?')
                        params.append(value)
                
                if updates:
                    updates.append('updated_at = CURRENT_TIMESTAMP')
                    params.append(automation_id)
                    
                    query = f'UPDATE email_automations SET {", ".join(updates)} WHERE id = ?'
                    conn.execute(query, params)
                    return conn.total_changes > 0
                return False
        except Exception as e:
            print(f"Error updating email automation: {e}")
            return False
    
    def delete_email_automation(self, automation_id):
        """Delete an email automation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('DELETE FROM email_automations WHERE id = ?', (automation_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting email automation: {e}")
            return False
    
    def get_email_automations_by_trigger(self, trigger_type):
        """Get active email automations by trigger type"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT * FROM email_automations
                    WHERE trigger_type = ? AND is_active = 1
                    ORDER BY created_at ASC
                ''', (trigger_type,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching email automations by trigger: {e}")
            return []
    
    def is_email_unsubscribed(self, email):
        """Check if email is unsubscribed"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM email_unsubscribes
                    WHERE email = ?
                ''', (email,))
                return cursor.fetchone()[0] > 0
        except Exception as e:
            print(f"Error checking unsubscribe status: {e}")
            return False
    
    def record_email_tracking(self, tracking_id, event_type, queue_id=None, user_agent=None, ip_address=None, metadata=None):
        """Record email tracking event"""
        try:
            import json
            event_data = json.dumps(metadata) if metadata else None
            
            # If queue_id is not provided, try to find it from tracking_id
            if not queue_id:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute('SELECT id FROM email_queue WHERE tracking_id = ?', (tracking_id,))
                    result = cursor.fetchone()
                    if result:
                        queue_id = result[0]
                    else:
                        # If no queue_id found, just insert with NULL queue_id
                        queue_id = None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    INSERT INTO email_tracking (tracking_id, queue_id, event_type, event_data, user_agent, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (tracking_id, queue_id, event_type, event_data, user_agent, ip_address))
                return cursor.lastrowid
        except Exception as e:
            print(f"Error recording email tracking: {e}")
            return None
    
    # Email Campaign Management
    def create_email_campaign(self, name, description=None, template_id=None, status='draft', 
                             send_at=None, recipient_list=None, subject_override=None):
        """Create a new email campaign"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    INSERT INTO email_campaigns (name, description, template_id, status, 
                                               send_at, recipient_list, subject_override, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (name, description, template_id, status, send_at, recipient_list, subject_override))
                return cursor.lastrowid
        except Exception as e:
            print(f"Error creating email campaign: {e}")
            return None
    
    def get_all_email_campaigns(self):
        """Get all email campaigns with their statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                campaigns = conn.execute('''
                    SELECT 
                        c.*,
                        t.name as template_name,
                        COUNT(DISTINCT eq.id) as recipients_count,
                        COUNT(DISTINCT CASE WHEN eq.status = 'sent' THEN eq.id END) as sent_count,
                        COUNT(DISTINCT et.id) as open_count,
                        COUNT(DISTINCT CASE WHEN et.event_type = 'click' THEN et.id END) as click_count
                    FROM email_campaigns c
                    LEFT JOIN email_templates t ON c.template_id = t.id
                    LEFT JOIN email_queue eq ON c.id = eq.campaign_id
                    LEFT JOIN email_tracking et ON eq.tracking_id = et.tracking_id AND et.event_type IN ('open', 'click')
                    GROUP BY c.id
                    ORDER BY c.created_at DESC
                ''').fetchall()
                
                return [dict(campaign) for campaign in campaigns]
        except Exception as e:
            print(f"Error getting email campaigns: {e}")
            return []
    
    def get_email_campaign(self, campaign_id):
        """Get a specific email campaign"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                campaign = conn.execute('''
                    SELECT 
                        c.*,
                        t.name as template_name,
                        COUNT(DISTINCT eq.id) as recipients_count,
                        COUNT(DISTINCT CASE WHEN eq.status = 'sent' THEN eq.id END) as sent_count,
                        COUNT(DISTINCT et.id) as open_count,
                        COUNT(DISTINCT CASE WHEN et.event_type = 'click' THEN et.id END) as click_count
                    FROM email_campaigns c
                    LEFT JOIN email_templates t ON c.template_id = t.id
                    LEFT JOIN email_queue eq ON c.id = eq.campaign_id
                    LEFT JOIN email_tracking et ON eq.tracking_id = et.tracking_id AND et.event_type IN ('open', 'click')
                    WHERE c.id = ?
                    GROUP BY c.id
                ''', (campaign_id,)).fetchone()
                
                return dict(campaign) if campaign else None
        except Exception as e:
            print(f"Error getting email campaign: {e}")
            return None
    
    def update_email_campaign(self, campaign_id, **kwargs):
        """Update an email campaign"""
        try:
            if not kwargs:
                return False
                
            with sqlite3.connect(self.db_path) as conn:
                # Build dynamic UPDATE query
                updates = []
                params = []
                
                for field, value in kwargs.items():
                    if field in ['name', 'description', 'template_id', 'status', 'send_at', 
                               'recipient_list', 'subject_override']:
                        updates.append(f'{field} = ?')
                        params.append(value)
                
                if updates:
                    params.append(campaign_id)
                    query = f'UPDATE email_campaigns SET {", ".join(updates)} WHERE id = ?'
                    conn.execute(query, params)
                    return conn.total_changes > 0
                return False
        except Exception as e:
            print(f"Error updating email campaign: {e}")
            return False
    
    def delete_email_campaign(self, campaign_id):
        """Delete an email campaign"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('DELETE FROM email_campaigns WHERE id = ?', (campaign_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting email campaign: {e}")
            return False
    
    def get_campaign_statistics(self):
        """Get overall campaign statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get total campaigns
                total_campaigns = conn.execute('SELECT COUNT(*) FROM email_campaigns').fetchone()[0]
                
                # Get total recipients (unique emails across all campaigns)
                total_recipients = conn.execute('''
                    SELECT COUNT(DISTINCT recipient_email) 
                    FROM email_queue 
                    WHERE campaign_id IS NOT NULL
                ''').fetchone()[0]
                
                # Get average open rate
                open_stats = conn.execute('''
                    SELECT 
                        COUNT(DISTINCT eq.id) as total_sent,
                        COUNT(DISTINCT et.id) as total_opens
                    FROM email_queue eq
                    LEFT JOIN email_tracking et ON eq.tracking_id = et.tracking_id AND et.event_type = 'open'
                    WHERE eq.campaign_id IS NOT NULL AND eq.status = 'sent'
                ''').fetchone()
                
                # Get average click rate
                click_stats = conn.execute('''
                    SELECT 
                        COUNT(DISTINCT eq.id) as total_sent,
                        COUNT(DISTINCT et.id) as total_clicks
                    FROM email_queue eq
                    LEFT JOIN email_tracking et ON eq.tracking_id = et.tracking_id AND et.event_type = 'click'
                    WHERE eq.campaign_id IS NOT NULL AND eq.status = 'sent'
                ''').fetchone()
                
                # Calculate rates
                avg_open_rate = 0
                avg_click_rate = 0
                
                if open_stats[0] > 0:
                    avg_open_rate = (open_stats[1] / open_stats[0]) * 100
                
                if click_stats[0] > 0:
                    avg_click_rate = (click_stats[1] / click_stats[0]) * 100
                
                return {
                    'total_campaigns': total_campaigns,
                    'total_recipients': total_recipients,
                    'avg_open_rate': round(avg_open_rate, 1),
                    'avg_click_rate': round(avg_click_rate, 1)
                }
        except Exception as e:
            print(f"Error getting campaign statistics: {e}")
            return {
                'total_campaigns': 0,
                'total_recipients': 0,
                'avg_open_rate': 0.0,
                'avg_click_rate': 0.0
            }
    
    # Email Queue Management
    def queue_email(self, to_email=None, subject=None, content_html=None, template_id=None, automation_id=None, 
                   tracking_id=None, send_time=None, context_data=None, recipient_email=None, campaign_id=None,
                   recipient_name=None, variables_json=None, scheduled_at=None):
        """Add email to queue"""
        try:
            import uuid
            import json
            
            # Handle both old and new parameter names for backward compatibility
            email = to_email or recipient_email
            send_at = send_time or scheduled_at
            
            if not tracking_id:
                tracking_id = str(uuid.uuid4())
            
            # Convert context_data to JSON string if provided
            variables = variables_json
            if context_data:
                variables = json.dumps(context_data)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    INSERT INTO email_queue (recipient_email, recipient_name, template_id, campaign_id, automation_id, 
                                           subject, content_html, variables_json, scheduled_at, tracking_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (email, recipient_name, template_id, campaign_id, automation_id, 
                      subject, content_html, variables, send_at, tracking_id))
                
                return cursor.lastrowid, tracking_id
        except Exception as e:
            print(f"Error queueing email: {e}")
            return None, None
    
    def get_pending_emails(self, limit=100):
        """Get pending emails from queue"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                # Get current UTC timestamp for comparison
                from datetime import datetime
                current_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                
                cursor = conn.execute('''
                    SELECT * FROM email_queue 
                    WHERE status = 'pending'
                    ORDER BY scheduled_at ASC
                    LIMIT ?
                ''', (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching pending emails: {e}")
            return []
    
    def update_email_status(self, queue_id, status, error_message=None, sent_at=None):
        """Update email status in queue"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if sent_at:
                    conn.execute('''
                        UPDATE email_queue 
                        SET status = ?, error_message = ?, sent_at = ?, attempts = attempts + 1
                        WHERE id = ?
                    ''', (status, error_message, sent_at, queue_id))
                else:
                    conn.execute('''
                        UPDATE email_queue 
                        SET status = ?, error_message = ?, attempts = attempts + 1
                        WHERE id = ?
                    ''', (status, error_message, queue_id))
                return conn.total_changes > 0
        except Exception as e:
            print(f"Error updating email status: {e}")
            return False
    
    # Email Tracking
    def track_email_event(self, tracking_id, event_type, event_data=None, user_agent=None, ip_address=None):
        """Track email events (open, click, etc.)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get queue_id from tracking_id
                cursor = conn.execute('SELECT id FROM email_queue WHERE tracking_id = ?', (tracking_id,))
                queue_row = cursor.fetchone()
                
                if queue_row:
                    queue_id = queue_row[0]
                    
                    # Insert tracking event
                    conn.execute('''
                        INSERT INTO email_tracking (tracking_id, queue_id, event_type, event_data, user_agent, ip_address)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (tracking_id, queue_id, event_type, event_data, user_agent, ip_address))
                    
                    # Update queue record for quick access
                    if event_type == 'opened':
                        conn.execute('UPDATE email_queue SET opened_at = CURRENT_TIMESTAMP WHERE id = ?', (queue_id,))
                    elif event_type == 'clicked':
                        conn.execute('UPDATE email_queue SET clicked_at = CURRENT_TIMESTAMP WHERE id = ?', (queue_id,))
                    
                    return True
                return False
        except Exception as e:
            print(f"Error tracking email event: {e}")
            return False
    
    # Email Analytics
    def get_email_analytics(self, days=30):
        """Get email analytics for the last N days"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Email sending stats
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_sent,
                        COUNT(CASE WHEN opened_at IS NOT NULL THEN 1 END) as total_opened,
                        COUNT(CASE WHEN clicked_at IS NOT NULL THEN 1 END) as total_clicked,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as total_failed
                    FROM email_queue 
                    WHERE sent_at >= datetime('now', '-' || ? || ' days')
                ''', (days,))
                
                stats = dict(cursor.fetchone())
                
                # Calculate rates
                if stats['total_sent'] > 0:
                    stats['open_rate'] = (stats['total_opened'] / stats['total_sent']) * 100
                    stats['click_rate'] = (stats['total_clicked'] / stats['total_sent']) * 100
                    stats['failure_rate'] = (stats['total_failed'] / stats['total_sent']) * 100
                else:
                    stats['open_rate'] = 0
                    stats['click_rate'] = 0
                    stats['failure_rate'] = 0
                
                return stats
        except Exception as e:
            print(f"Error getting email analytics: {e}")
            return {}
    
    def get_top_performing_templates(self, limit=5, days=30):
        """Get top performing email templates"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                templates = conn.execute('''
                    SELECT 
                        t.id,
                        t.name,
                        COUNT(DISTINCT eq.id) as sent_count,
                        COUNT(DISTINCT CASE WHEN et.event_type = 'open' THEN et.id END) as open_count,
                        COUNT(DISTINCT CASE WHEN et.event_type = 'click' THEN et.id END) as click_count,
                        CASE 
                            WHEN COUNT(DISTINCT eq.id) > 0 
                            THEN (COUNT(DISTINCT CASE WHEN et.event_type = 'open' THEN et.id END) * 100.0 / COUNT(DISTINCT eq.id))
                            ELSE 0 
                        END as open_rate,
                        CASE 
                            WHEN COUNT(DISTINCT eq.id) > 0 
                            THEN (COUNT(DISTINCT CASE WHEN et.event_type = 'click' THEN et.id END) * 100.0 / COUNT(DISTINCT eq.id))
                            ELSE 0 
                        END as click_rate
                    FROM email_templates t
                    LEFT JOIN email_queue eq ON t.id = eq.template_id 
                        AND eq.sent_at >= datetime('now', '-' || ? || ' days')
                    LEFT JOIN email_tracking et ON eq.tracking_id = et.tracking_id
                    GROUP BY t.id, t.name
                    HAVING sent_count > 0
                    ORDER BY open_rate DESC, sent_count DESC
                    LIMIT ?
                ''', (days, limit)).fetchall()
                
                return [dict(template) for template in templates]
        except Exception as e:
            print(f"Error getting top performing templates: {e}")
            return []
    
    def get_recent_email_activity(self, limit=10):
        """Get recent email activity events"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                activities = []
                
                # Get recent email sends
                recent_sends = conn.execute('''
                    SELECT 
                        'email_sent' as type,
                        'Email sent: ' || COALESCE(t.name, 'Unknown Template') as message,
                        eq.sent_at as timestamp,
                        eq.recipient_email
                    FROM email_queue eq
                    LEFT JOIN email_templates t ON eq.template_id = t.id
                    WHERE eq.status = 'sent' AND eq.sent_at IS NOT NULL
                    ORDER BY eq.sent_at DESC
                    LIMIT ?
                ''', (limit//2,)).fetchall()
                
                # Get recent email opens and clicks
                recent_events = conn.execute('''
                    SELECT 
                        et.event_type as type,
                        CASE et.event_type
                            WHEN 'open' THEN 'Email opened: ' || COALESCE(t.name, 'Unknown Template')
                            WHEN 'click' THEN 'Email clicked: ' || COALESCE(t.name, 'Unknown Template')
                            ELSE 'Email event: ' || et.event_type
                        END as message,
                        et.timestamp,
                        eq.recipient_email
                    FROM email_tracking et
                    LEFT JOIN email_queue eq ON et.tracking_id = eq.tracking_id
                    LEFT JOIN email_templates t ON eq.template_id = t.id
                    WHERE et.timestamp >= datetime('now', '-1 day')
                    ORDER BY et.timestamp DESC
                    LIMIT ?
                ''', (limit//2,)).fetchall()
                
                # Combine and sort all activities
                for activity in recent_sends:
                    activities.append(dict(activity))
                
                for activity in recent_events:
                    # Map event types to consistent format
                    event_type = activity['type']
                    if event_type == 'open':
                        event_type = 'email_opened'
                    elif event_type == 'click':
                        event_type = 'email_clicked'
                    
                    activities.append({
                        'type': event_type,
                        'message': activity['message'],
                        'timestamp': activity['timestamp'],
                        'recipient_email': activity['recipient_email']
                    })
                
                # Sort by timestamp and limit
                activities.sort(key=lambda x: x['timestamp'] or '', reverse=True)
                return activities[:limit]
                
        except Exception as e:
            print(f"Error getting recent email activity: {e}")
            return []

# Global database instance
db = Database()

if __name__ == '__main__':
    # Test the database
    print("🗄️ Testing VectorCraft Database...")
    print(f"Database file: {db.db_path}")
    
    # Test authentication
    user = db.authenticate_user('admin', 'admin123')
    if user:
        print(f"✅ Authentication successful for: {user['username']}")
        print(f"   Email: {user['email']}")
        print(f"   Created: {user['created_at']}")
    else:
        print("❌ Authentication failed")