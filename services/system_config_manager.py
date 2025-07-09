#!/usr/bin/env python3
"""
System Configuration Manager for VectorCraft
Provides comprehensive system configuration management with secure storage
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from .secure_storage import secure_storage
from .paypal_service import PayPalService
from .email_service import EmailService

class ConfigStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"

@dataclass
class ConfigResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

class SystemConfigManager:
    """System configuration manager with secure storage and real-time validation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.secure_storage = secure_storage
        self.logger.info("System Configuration Manager initialized")
        
        # Initialize default configurations
        self._init_default_configs()
    
    def _init_default_configs(self):
        """Initialize default system configurations"""
        try:
            # PayPal default configuration
            paypal_defaults = {
                'environment': 'sandbox',
                'currency': 'USD',
                'product_name': 'VectorCraft Professional',
                'product_price': 49.00,
                'webhook_enabled': True,
                'auto_capture': True
            }
            
            for key, value in paypal_defaults.items():
                if not self.secure_storage.get_config('paypal', key):
                    self.secure_storage.store_config(
                        'paypal', key, value, 
                        description=f"PayPal {key} configuration",
                        is_sensitive=False
                    )
            
            # Email default configuration
            email_defaults = {
                'smtp_server': 'smtpout.secureserver.net',
                'smtp_port_ssl': 465,
                'smtp_port_tls': 587,
                'email_signature': 'VectorCraft Team',
                'max_retries': 3,
                'retry_delay': 5,
                'bounce_handling': True
            }
            
            for key, value in email_defaults.items():
                if not self.secure_storage.get_config('email', key):
                    self.secure_storage.store_config(
                        'email', key, value,
                        description=f"Email {key} configuration",
                        is_sensitive=False
                    )
            
            # System environment defaults
            system_defaults = {
                'debug_mode': False,
                'log_level': 'INFO',
                'feature_flags': json.dumps({
                    'advanced_vectorization': True,
                    'batch_processing': True,
                    'api_access': True,
                    'user_analytics': True
                }),
                'cache_enabled': True,
                'cache_ttl': 3600,
                'maintenance_mode': False
            }
            
            for key, value in system_defaults.items():
                if not self.secure_storage.get_config('system', key):
                    self.secure_storage.store_config(
                        'system', key, value,
                        description=f"System {key} configuration",
                        is_sensitive=False,
                        value_type='json' if key == 'feature_flags' else 'string'
                    )
            
            self.logger.info("Default configurations initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize default configs: {e}")
    
    # PayPal Configuration Management
    def get_paypal_config(self) -> Dict[str, Any]:
        """Get PayPal configuration"""
        try:
            config = self.secure_storage.get_category_config('paypal')
            
            # Add sensitive fields
            sensitive_fields = ['client_id', 'client_secret']
            for field in sensitive_fields:
                value = self.secure_storage.get_config('paypal', field)
                if value:
                    config[field] = {
                        'value': '***ENCRYPTED***',
                        'type': 'string',
                        'description': f"PayPal {field}",
                        'is_sensitive': True,
                        'configured': True
                    }
                else:
                    config[field] = {
                        'value': '',
                        'type': 'string',
                        'description': f"PayPal {field}",
                        'is_sensitive': True,
                        'configured': False
                    }
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to get PayPal config: {e}")
            return {}
    
    def update_paypal_config(self, config_data: Dict[str, Any], changed_by: str = 'admin') -> ConfigResult:
        """Update PayPal configuration"""
        try:
            errors = []
            
            # Validate configuration
            if 'environment' in config_data:
                if config_data['environment'] not in ['sandbox', 'live']:
                    errors.append("Environment must be 'sandbox' or 'live'")
            
            if 'product_price' in config_data:
                try:
                    price = float(config_data['product_price'])
                    if price <= 0:
                        errors.append("Product price must be greater than 0")
                except ValueError:
                    errors.append("Product price must be a valid number")
            
            if errors:
                return ConfigResult(success=False, message="Validation failed", errors=errors)
            
            # Store configuration
            for key, value in config_data.items():
                is_sensitive = key in ['client_id', 'client_secret']
                value_type = 'float' if key == 'product_price' else 'string'
                
                self.secure_storage.store_config(
                    'paypal', key, value,
                    description=f"PayPal {key} configuration",
                    is_sensitive=is_sensitive,
                    value_type=value_type,
                    changed_by=changed_by
                )
            
            self.logger.info(f"PayPal configuration updated by {changed_by}")
            return ConfigResult(success=True, message="PayPal configuration updated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to update PayPal config: {e}")
            return ConfigResult(success=False, message=f"Failed to update configuration: {str(e)}")
    
    def test_paypal_connection(self) -> ConfigResult:
        """Test PayPal API connection"""
        try:
            # Get configuration
            client_id = self.secure_storage.get_config('paypal', 'client_id')
            client_secret = self.secure_storage.get_config('paypal', 'client_secret')
            environment = self.secure_storage.get_config('paypal', 'environment', 'sandbox')
            
            if not client_id or not client_secret:
                return ConfigResult(
                    success=False, 
                    message="PayPal credentials not configured",
                    errors=["Missing client_id or client_secret"]
                )
            
            # Create temporary PayPal service for testing
            os.environ['PAYPAL_CLIENT_ID'] = client_id
            os.environ['PAYPAL_CLIENT_SECRET'] = client_secret
            os.environ['PAYPAL_ENVIRONMENT'] = environment
            
            paypal_service = PayPalService()
            
            # Test token generation
            token = paypal_service._get_access_token()
            
            if token:
                return ConfigResult(
                    success=True, 
                    message="PayPal connection successful",
                    data={
                        'environment': environment,
                        'token_length': len(token),
                        'tested_at': datetime.now().isoformat()
                    }
                )
            else:
                return ConfigResult(
                    success=False, 
                    message="Failed to authenticate with PayPal",
                    errors=["Authentication failed"]
                )
                
        except Exception as e:
            self.logger.error(f"PayPal connection test failed: {e}")
            return ConfigResult(
                success=False, 
                message=f"Connection test failed: {str(e)}",
                errors=[str(e)]
            )
    
    # Email Configuration Management
    def get_email_config(self) -> Dict[str, Any]:
        """Get Email configuration"""
        try:
            config = self.secure_storage.get_category_config('email')
            
            # Add sensitive fields
            sensitive_fields = ['smtp_username', 'smtp_password']
            for field in sensitive_fields:
                value = self.secure_storage.get_config('email', field)
                if value:
                    config[field] = {
                        'value': '***ENCRYPTED***',
                        'type': 'string',
                        'description': f"Email {field}",
                        'is_sensitive': True,
                        'configured': True
                    }
                else:
                    config[field] = {
                        'value': '',
                        'type': 'string',
                        'description': f"Email {field}",
                        'is_sensitive': True,
                        'configured': False
                    }
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to get Email config: {e}")
            return {}
    
    def update_email_config(self, config_data: Dict[str, Any], changed_by: str = 'admin') -> ConfigResult:
        """Update Email configuration"""
        try:
            errors = []
            
            # Validate configuration
            if 'smtp_port_ssl' in config_data:
                try:
                    port = int(config_data['smtp_port_ssl'])
                    if port <= 0 or port > 65535:
                        errors.append("SMTP SSL port must be between 1 and 65535")
                except ValueError:
                    errors.append("SMTP SSL port must be a valid number")
            
            if 'smtp_port_tls' in config_data:
                try:
                    port = int(config_data['smtp_port_tls'])
                    if port <= 0 or port > 65535:
                        errors.append("SMTP TLS port must be between 1 and 65535")
                except ValueError:
                    errors.append("SMTP TLS port must be a valid number")
            
            if errors:
                return ConfigResult(success=False, message="Validation failed", errors=errors)
            
            # Store configuration
            for key, value in config_data.items():
                is_sensitive = key in ['smtp_username', 'smtp_password']
                value_type = 'integer' if 'port' in key else 'string'
                
                self.secure_storage.store_config(
                    'email', key, value,
                    description=f"Email {key} configuration",
                    is_sensitive=is_sensitive,
                    value_type=value_type,
                    changed_by=changed_by
                )
            
            self.logger.info(f"Email configuration updated by {changed_by}")
            return ConfigResult(success=True, message="Email configuration updated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to update Email config: {e}")
            return ConfigResult(success=False, message=f"Failed to update configuration: {str(e)}")
    
    def test_email_connection(self) -> ConfigResult:
        """Test Email SMTP connection"""
        try:
            # Get configuration
            smtp_server = self.secure_storage.get_config('email', 'smtp_server', 'smtpout.secureserver.net')
            smtp_username = self.secure_storage.get_config('email', 'smtp_username')
            smtp_password = self.secure_storage.get_config('email', 'smtp_password')
            
            if not smtp_username or not smtp_password:
                return ConfigResult(
                    success=False, 
                    message="Email credentials not configured",
                    errors=["Missing smtp_username or smtp_password"]
                )
            
            # Create temporary email service for testing
            os.environ['SMTP_USERNAME'] = smtp_username
            os.environ['SMTP_PASSWORD'] = smtp_password
            
            email_service = EmailService()
            
            # Test SMTP connection (simplified)
            import smtplib
            try:
                server = smtplib.SMTP(smtp_server, 587)
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.quit()
                
                return ConfigResult(
                    success=True, 
                    message="Email connection successful",
                    data={
                        'smtp_server': smtp_server,
                        'smtp_username': smtp_username,
                        'tested_at': datetime.now().isoformat()
                    }
                )
            except Exception as smtp_e:
                return ConfigResult(
                    success=False, 
                    message=f"SMTP connection failed: {str(smtp_e)}",
                    errors=[str(smtp_e)]
                )
                
        except Exception as e:
            self.logger.error(f"Email connection test failed: {e}")
            return ConfigResult(
                success=False, 
                message=f"Connection test failed: {str(e)}",
                errors=[str(e)]
            )
    
    # System Environment Management
    def get_system_config(self) -> Dict[str, Any]:
        """Get System configuration"""
        try:
            config = self.secure_storage.get_category_config('system')
            
            # Parse feature flags
            if 'feature_flags' in config:
                feature_flags_str = self.secure_storage.get_config('system', 'feature_flags', '{}')
                try:
                    feature_flags = json.loads(feature_flags_str)
                    config['feature_flags']['value'] = feature_flags
                except json.JSONDecodeError:
                    config['feature_flags']['value'] = {}
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to get System config: {e}")
            return {}
    
    def update_system_config(self, config_data: Dict[str, Any], changed_by: str = 'admin') -> ConfigResult:
        """Update System configuration"""
        try:
            errors = []
            
            # Validate configuration
            if 'log_level' in config_data:
                valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                if config_data['log_level'] not in valid_levels:
                    errors.append(f"Log level must be one of: {', '.join(valid_levels)}")
            
            if 'cache_ttl' in config_data:
                try:
                    ttl = int(config_data['cache_ttl'])
                    if ttl < 0:
                        errors.append("Cache TTL must be non-negative")
                except ValueError:
                    errors.append("Cache TTL must be a valid number")
            
            if errors:
                return ConfigResult(success=False, message="Validation failed", errors=errors)
            
            # Store configuration
            for key, value in config_data.items():
                value_type = 'string'
                if key in ['debug_mode', 'cache_enabled', 'maintenance_mode']:
                    value_type = 'boolean'
                elif key in ['cache_ttl']:
                    value_type = 'integer'
                elif key == 'feature_flags':
                    value_type = 'json'
                    value = json.dumps(value)
                
                self.secure_storage.store_config(
                    'system', key, value,
                    description=f"System {key} configuration",
                    is_sensitive=False,
                    value_type=value_type,
                    changed_by=changed_by
                )
            
            self.logger.info(f"System configuration updated by {changed_by}")
            return ConfigResult(success=True, message="System configuration updated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to update System config: {e}")
            return ConfigResult(success=False, message=f"Failed to update configuration: {str(e)}")
    
    # API Keys Management
    def get_api_keys(self) -> Dict[str, Any]:
        """Get API keys configuration"""
        try:
            config = self.secure_storage.get_category_config('api_keys')
            
            # Add metadata for each key
            for key_name, key_data in config.items():
                metadata = self.secure_storage.get_config_with_metadata('api_keys', key_name)
                if metadata:
                    key_data.update({
                        'usage_count': metadata.get('usage_count', 0),
                        'last_used': metadata.get('last_used'),
                        'status': metadata.get('status', 'active')
                    })
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to get API keys: {e}")
            return {}
    
    def add_api_key(self, key_name: str, key_value: str, description: str = None, 
                   changed_by: str = 'admin') -> ConfigResult:
        """Add new API key"""
        try:
            # Validate key name
            if not key_name or not key_name.strip():
                return ConfigResult(success=False, message="Key name is required")
            
            if not key_value or not key_value.strip():
                return ConfigResult(success=False, message="Key value is required")
            
            # Store API key
            self.secure_storage.store_config(
                'api_keys', key_name, key_value,
                description=description or f"API key: {key_name}",
                is_sensitive=True,
                changed_by=changed_by
            )
            
            self.logger.info(f"API key '{key_name}' added by {changed_by}")
            return ConfigResult(success=True, message=f"API key '{key_name}' added successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to add API key: {e}")
            return ConfigResult(success=False, message=f"Failed to add API key: {str(e)}")
    
    def delete_api_key(self, key_name: str, changed_by: str = 'admin') -> ConfigResult:
        """Delete API key"""
        try:
            success = self.secure_storage.delete_config('api_keys', key_name)
            
            if success:
                self.logger.info(f"API key '{key_name}' deleted by {changed_by}")
                return ConfigResult(success=True, message=f"API key '{key_name}' deleted successfully")
            else:
                return ConfigResult(success=False, message=f"Failed to delete API key '{key_name}'")
                
        except Exception as e:
            self.logger.error(f"Failed to delete API key: {e}")
            return ConfigResult(success=False, message=f"Failed to delete API key: {str(e)}")
    
    # Database Configuration Management
    def get_database_config(self) -> Dict[str, Any]:
        """Get Database configuration"""
        try:
            config = self.secure_storage.get_category_config('database')
            
            # Add connection status
            config['connection_status'] = {
                'value': self._test_database_connection(),
                'type': 'boolean',
                'description': 'Database connection status',
                'is_sensitive': False
            }
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to get Database config: {e}")
            return {}
    
    def _test_database_connection(self) -> bool:
        """Test database connection"""
        try:
            import sqlite3
            conn = sqlite3.connect('vectorcraft.db')
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            conn.close()
            return True
        except Exception:
            return False
    
    # Export/Import Configuration
    def export_configuration(self, categories: List[str] = None, 
                           include_sensitive: bool = False) -> Dict[str, Any]:
        """Export system configuration"""
        try:
            if categories is None:
                categories = self.secure_storage.get_all_categories()
            
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'categories': categories,
                'include_sensitive': include_sensitive,
                'configuration': {}
            }
            
            for category in categories:
                export_data['configuration'][category] = self.secure_storage.export_config(
                    category, include_sensitive
                )
            
            return export_data
            
        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            return {}
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get configuration summary for dashboard"""
        try:
            categories = self.secure_storage.get_all_categories()
            summary = {
                'total_categories': len(categories),
                'categories': {},
                'overall_status': 'healthy',
                'last_updated': datetime.now().isoformat()
            }
            
            for category in categories:
                config = self.secure_storage.get_category_config(category)
                summary['categories'][category] = {
                    'total_keys': len(config),
                    'configured_keys': len([k for k, v in config.items() if v.get('value') not in ['', '***ENCRYPTED***']]),
                    'sensitive_keys': len([k for k, v in config.items() if v.get('is_sensitive', False)])
                }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get configuration summary: {e}")
            return {}

# Global system configuration manager instance
system_config_manager = SystemConfigManager()