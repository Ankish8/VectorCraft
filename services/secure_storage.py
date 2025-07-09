#!/usr/bin/env python3
"""
Secure Storage Service for VectorCraft
Provides encrypted credential storage and management
"""

import os
import json
import logging
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import secrets
import sqlite3
from typing import Dict, Any, Optional, List

class SecureStorage:
    """Secure storage for encrypted credentials and configuration"""
    
    def __init__(self, db_path: str = "vectorcraft.db"):
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.master_key = self._get_or_create_master_key()
        self.cipher_suite = Fernet(self.master_key)
        self._init_database()
        
    def _get_or_create_master_key(self) -> bytes:
        """Get or create the master encryption key"""
        key_file = os.path.join(os.path.dirname(self.db_path), '.vectorcraft_master_key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Secure the key file
            os.chmod(key_file, 0o600)
            self.logger.info("Generated new master encryption key")
            return key
    
    def _init_database(self):
        """Initialize secure storage database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create secure_config table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS secure_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key_name TEXT NOT NULL,
                    encrypted_value TEXT NOT NULL,
                    value_type TEXT DEFAULT 'string',
                    description TEXT,
                    is_sensitive BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1,
                    UNIQUE(category, key_name)
                )
            ''')
            
            # Create config_history table for versioning
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key_name TEXT NOT NULL,
                    encrypted_value TEXT NOT NULL,
                    value_type TEXT DEFAULT 'string',
                    version INTEGER NOT NULL,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    changed_by TEXT DEFAULT 'system'
                )
            ''')
            
            # Create API usage tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key_name TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    last_used TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            conn.commit()
            conn.close()
            self.logger.info("Secure storage database initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize secure storage: {e}")
            raise
    
    def encrypt_value(self, value: Any) -> str:
        """Encrypt a value for storage"""
        try:
            # Convert to JSON string if not already string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            # Encrypt the value
            encrypted = self.cipher_suite.encrypt(value.encode())
            return base64.b64encode(encrypted).decode()
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt value: {e}")
            raise
    
    def decrypt_value(self, encrypted_value: str, value_type: str = 'string') -> Any:
        """Decrypt a value from storage"""
        try:
            # Decode and decrypt
            encrypted_bytes = base64.b64decode(encrypted_value.encode())
            decrypted = self.cipher_suite.decrypt(encrypted_bytes)
            value = decrypted.decode()
            
            # Convert back to original type
            if value_type == 'json':
                return json.loads(value)
            elif value_type == 'boolean':
                return value.lower() in ['true', '1', 'yes']
            elif value_type == 'integer':
                return int(value)
            elif value_type == 'float':
                return float(value)
            else:
                return value
                
        except Exception as e:
            self.logger.error(f"Failed to decrypt value: {e}")
            raise
    
    def store_config(self, category: str, key_name: str, value: Any, 
                    description: str = None, is_sensitive: bool = True,
                    value_type: str = 'string', changed_by: str = 'system') -> bool:
        """Store configuration value securely"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Encrypt the value
            encrypted_value = self.encrypt_value(value)
            
            # Check if config exists
            cursor.execute('''
                SELECT version FROM secure_config 
                WHERE category = ? AND key_name = ?
            ''', (category, key_name))
            
            existing = cursor.fetchone()
            new_version = (existing[0] + 1) if existing else 1
            
            # Store in history first
            cursor.execute('''
                INSERT INTO config_history 
                (category, key_name, encrypted_value, value_type, version, changed_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (category, key_name, encrypted_value, value_type, new_version, changed_by))
            
            # Update or insert current config
            cursor.execute('''
                INSERT OR REPLACE INTO secure_config 
                (category, key_name, encrypted_value, value_type, description, 
                 is_sensitive, updated_at, version)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            ''', (category, key_name, encrypted_value, value_type, description, 
                  is_sensitive, new_version))
            
            # Update usage tracking
            cursor.execute('''
                INSERT OR REPLACE INTO api_usage 
                (category, key_name, usage_count, status)
                VALUES (?, ?, COALESCE((SELECT usage_count FROM api_usage 
                                      WHERE category = ? AND key_name = ?), 0), 'active')
            ''', (category, key_name, category, key_name))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Stored secure config: {category}.{key_name} (v{new_version})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store config {category}.{key_name}: {e}")
            return False
    
    def get_config(self, category: str, key_name: str, default_value: Any = None) -> Any:
        """Retrieve configuration value"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT encrypted_value, value_type FROM secure_config 
                WHERE category = ? AND key_name = ?
            ''', (category, key_name))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                encrypted_value, value_type = result
                decrypted_value = self.decrypt_value(encrypted_value, value_type)
                
                # Update usage tracking
                self._update_usage(category, key_name)
                
                return decrypted_value
            else:
                return default_value
                
        except Exception as e:
            self.logger.error(f"Failed to get config {category}.{key_name}: {e}")
            return default_value
    
    def get_category_config(self, category: str) -> Dict[str, Any]:
        """Get all configuration for a category"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT key_name, encrypted_value, value_type, description, is_sensitive
                FROM secure_config WHERE category = ?
            ''', (category,))
            
            results = cursor.fetchall()
            conn.close()
            
            config = {}
            for key_name, encrypted_value, value_type, description, is_sensitive in results:
                if is_sensitive:
                    # Return masked value for sensitive data
                    config[key_name] = {
                        'value': '***ENCRYPTED***',
                        'type': value_type,
                        'description': description,
                        'is_sensitive': True
                    }
                else:
                    config[key_name] = {
                        'value': self.decrypt_value(encrypted_value, value_type),
                        'type': value_type,
                        'description': description,
                        'is_sensitive': False
                    }
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to get category config {category}: {e}")
            return {}
    
    def get_config_with_metadata(self, category: str, key_name: str) -> Dict[str, Any]:
        """Get configuration with full metadata"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT encrypted_value, value_type, description, is_sensitive,
                       created_at, updated_at, version
                FROM secure_config 
                WHERE category = ? AND key_name = ?
            ''', (category, key_name))
            
            result = cursor.fetchone()
            
            if result:
                encrypted_value, value_type, description, is_sensitive, created_at, updated_at, version = result
                
                # Get usage stats
                cursor.execute('''
                    SELECT usage_count, last_used, status
                    FROM api_usage WHERE category = ? AND key_name = ?
                ''', (category, key_name))
                
                usage_result = cursor.fetchone()
                usage_count, last_used, status = usage_result if usage_result else (0, None, 'inactive')
                
                conn.close()
                
                return {
                    'category': category,
                    'key_name': key_name,
                    'value': '***ENCRYPTED***' if is_sensitive else self.decrypt_value(encrypted_value, value_type),
                    'actual_value': self.decrypt_value(encrypted_value, value_type),
                    'value_type': value_type,
                    'description': description,
                    'is_sensitive': is_sensitive,
                    'created_at': created_at,
                    'updated_at': updated_at,
                    'version': version,
                    'usage_count': usage_count,
                    'last_used': last_used,
                    'status': status
                }
            else:
                conn.close()
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get config metadata {category}.{key_name}: {e}")
            return None
    
    def delete_config(self, category: str, key_name: str) -> bool:
        """Delete configuration value"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM secure_config 
                WHERE category = ? AND key_name = ?
            ''', (category, key_name))
            
            cursor.execute('''
                UPDATE api_usage SET status = 'deleted'
                WHERE category = ? AND key_name = ?
            ''', (category, key_name))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Deleted config: {category}.{key_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete config {category}.{key_name}: {e}")
            return False
    
    def get_config_history(self, category: str, key_name: str) -> List[Dict[str, Any]]:
        """Get configuration change history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT version, changed_at, changed_by, value_type
                FROM config_history 
                WHERE category = ? AND key_name = ?
                ORDER BY version DESC
            ''', (category, key_name))
            
            results = cursor.fetchall()
            conn.close()
            
            history = []
            for version, changed_at, changed_by, value_type in results:
                history.append({
                    'version': version,
                    'changed_at': changed_at,
                    'changed_by': changed_by,
                    'value_type': value_type
                })
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get config history {category}.{key_name}: {e}")
            return []
    
    def _update_usage(self, category: str, key_name: str):
        """Update API usage statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO api_usage 
                (category, key_name, usage_count, last_used, status)
                VALUES (?, ?, 
                        COALESCE((SELECT usage_count FROM api_usage 
                                 WHERE category = ? AND key_name = ?), 0) + 1,
                        CURRENT_TIMESTAMP, 'active')
            ''', (category, key_name, category, key_name))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to update usage for {category}.{key_name}: {e}")
    
    def export_config(self, category: str = None, include_sensitive: bool = False) -> Dict[str, Any]:
        """Export configuration (for backup/migration)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT category, key_name, encrypted_value, value_type, 
                           description, is_sensitive, created_at, updated_at, version
                    FROM secure_config WHERE category = ?
                ''', (category,))
            else:
                cursor.execute('''
                    SELECT category, key_name, encrypted_value, value_type, 
                           description, is_sensitive, created_at, updated_at, version
                    FROM secure_config
                ''')
            
            results = cursor.fetchall()
            conn.close()
            
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'config': []
            }
            
            for row in results:
                cat, key_name, encrypted_value, value_type, description, is_sensitive, created_at, updated_at, version = row
                
                config_item = {
                    'category': cat,
                    'key_name': key_name,
                    'value_type': value_type,
                    'description': description,
                    'is_sensitive': is_sensitive,
                    'created_at': created_at,
                    'updated_at': updated_at,
                    'version': version
                }
                
                if include_sensitive or not is_sensitive:
                    config_item['value'] = self.decrypt_value(encrypted_value, value_type)
                else:
                    config_item['value'] = '***REDACTED***'
                
                export_data['config'].append(config_item)
            
            return export_data
            
        except Exception as e:
            self.logger.error(f"Failed to export config: {e}")
            return {}
    
    def get_all_categories(self) -> List[str]:
        """Get all configuration categories"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT DISTINCT category FROM secure_config ORDER BY category')
            results = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in results]
            
        except Exception as e:
            self.logger.error(f"Failed to get categories: {e}")
            return []

# Global secure storage instance
secure_storage = SecureStorage()