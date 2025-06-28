#!/usr/bin/env python3
"""
Database configuration and models for VectorCraft authentication
Uses SQLite for simplicity and Docker compatibility
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime
from pathlib import Path

class Database:
    def __init__(self, db_path='vectorcraft.db'):
        self.db_path = db_path
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
        """Create a new user"""
        password_hash, salt = self.hash_password(password)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO users (username, email, password_hash, salt)
                    VALUES (?, ?, ?, ?)
                ''', (username, email, password_hash, salt))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
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