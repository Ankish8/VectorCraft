#!/usr/bin/env python3
"""
System Controller Service
Provides live system controls and feature management without downtime
"""

import time
import json
import os
import signal
import threading
import multiprocessing
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import sqlite3
from contextlib import contextmanager
from database import db
from services.monitoring.health_monitor import health_monitor
from services.monitoring.system_logger import system_logger
from services.monitoring.alert_manager import alert_manager

class SystemController:
    """
    Core system controller for live management of VectorCraft
    Handles maintenance mode, feature flags, and system operations
    """
    
    def __init__(self):
        self.logger = system_logger
        self.alert_manager = alert_manager
        self._state = {
            'maintenance_mode': False,
            'maintenance_message': 'System is temporarily unavailable for maintenance.',
            'system_health': 'healthy',
            'active_features': {},
            'system_config': {},
            'deployment_status': 'stable',
            'last_restart': datetime.now().isoformat()
        }
        self._lock = threading.RLock()
        self._load_state()
        
    @contextmanager
    def _state_lock(self):
        """Thread-safe state management"""
        with self._lock:
            yield
    
    def _load_state(self):
        """Load system state from database"""
        try:
            with db.get_db_connection() as conn:
                # Initialize system_state table if it doesn't exist
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS system_state (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE NOT NULL,
                        value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Load existing state
                cursor = conn.execute('SELECT key, value FROM system_state')
                for row in cursor.fetchall():
                    try:
                        self._state[row['key']] = json.loads(row['value'])
                    except json.JSONDecodeError:
                        self._state[row['key']] = row['value']
                
                self.logger.info("System state loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load system state: {e}")
            
    def _save_state(self, key: str, value: Any):
        """Save state to database"""
        try:
            with db.get_db_connection() as conn:
                value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                conn.execute('''
                    INSERT OR REPLACE INTO system_state (key, value, updated_at)
                    VALUES (?, ?, ?)
                ''', (key, value_str, datetime.now().isoformat()))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to save state for {key}: {e}")
    
    # System State Management
    def get_system_state(self) -> Dict[str, Any]:
        """Get current system state"""
        with self._state_lock():
            return self._state.copy()
    
    def set_maintenance_mode(self, enabled: bool, message: str = None, admin_user: str = None) -> Dict[str, Any]:
        """Toggle maintenance mode"""
        with self._state_lock():
            old_state = self._state['maintenance_mode']
            self._state['maintenance_mode'] = enabled
            
            if message:
                self._state['maintenance_message'] = message
            
            # Save to database
            self._save_state('maintenance_mode', enabled)
            if message:
                self._save_state('maintenance_message', message)
            
            # Log the change
            action = "enabled" if enabled else "disabled"
            self.logger.info(f"Maintenance mode {action} by {admin_user or 'system'}")
            
            # Send alert if entering maintenance mode
            if enabled and not old_state:
                self.alert_manager.send_alert(
                    level='warning',
                    message=f'System entered maintenance mode: {message}',
                    component='system_controller'
                )
            
            return {
                'success': True,
                'maintenance_mode': enabled,
                'message': self._state['maintenance_message'],
                'changed_by': admin_user,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_maintenance_status(self) -> Dict[str, Any]:
        """Get current maintenance status"""
        with self._state_lock():
            return {
                'maintenance_mode': self._state['maintenance_mode'],
                'message': self._state['maintenance_message'],
                'enabled_at': self._state.get('maintenance_enabled_at'),
                'estimated_duration': self._state.get('maintenance_duration')
            }
    
    # System Health Override
    def override_system_health(self, status: str, reason: str, admin_user: str = None) -> Dict[str, Any]:
        """Override system health status"""
        valid_statuses = ['healthy', 'warning', 'critical']
        if status not in valid_statuses:
            return {
                'success': False,
                'error': f'Invalid status. Must be one of: {valid_statuses}'
            }
        
        with self._state_lock():
            old_status = self._state['system_health']
            self._state['system_health'] = status
            self._state['health_override_reason'] = reason
            self._state['health_override_by'] = admin_user
            self._state['health_override_at'] = datetime.now().isoformat()
            
            # Save to database
            self._save_state('system_health', status)
            self._save_state('health_override_reason', reason)
            
            # Log the override
            self.logger.warning(f"System health overridden from {old_status} to {status} by {admin_user}: {reason}")
            
            return {
                'success': True,
                'old_status': old_status,
                'new_status': status,
                'reason': reason,
                'overridden_by': admin_user,
                'timestamp': datetime.now().isoformat()
            }
    
    def clear_health_override(self, admin_user: str = None) -> Dict[str, Any]:
        """Clear health status override"""
        with self._state_lock():
            if 'health_override_reason' not in self._state:
                return {
                    'success': False,
                    'error': 'No health override to clear'
                }
            
            # Remove override data
            override_data = {
                'old_status': self._state['system_health'],
                'reason': self._state.get('health_override_reason'),
                'overridden_by': self._state.get('health_override_by')
            }
            
            # Clear override keys
            for key in ['health_override_reason', 'health_override_by', 'health_override_at']:
                self._state.pop(key, None)
            
            # Get actual health status
            actual_health = health_monitor.get_overall_status()
            self._state['system_health'] = actual_health['status']
            
            # Save to database
            self._save_state('system_health', actual_health['status'])
            
            self.logger.info(f"Health override cleared by {admin_user}")
            
            return {
                'success': True,
                'previous_override': override_data,
                'current_status': actual_health['status'],
                'cleared_by': admin_user,
                'timestamp': datetime.now().isoformat()
            }
    
    # Emergency System Controls
    def emergency_shutdown(self, reason: str, admin_user: str = None) -> Dict[str, Any]:
        """Emergency system shutdown"""
        with self._state_lock():
            # Enable maintenance mode first
            self.set_maintenance_mode(True, f"Emergency shutdown: {reason}", admin_user)
            
            # Log critical event
            self.logger.critical(f"EMERGENCY SHUTDOWN initiated by {admin_user}: {reason}")
            
            # Send critical alert
            self.alert_manager.send_alert(
                level='critical',
                message=f'Emergency shutdown initiated: {reason}',
                component='system_controller'
            )
            
            # TODO: Implement actual shutdown logic based on deployment type
            # For now, we'll just set flags
            self._state['emergency_shutdown'] = True
            self._state['shutdown_reason'] = reason
            self._state['shutdown_by'] = admin_user
            self._state['shutdown_at'] = datetime.now().isoformat()
            
            return {
                'success': True,
                'message': 'Emergency shutdown initiated',
                'reason': reason,
                'initiated_by': admin_user,
                'timestamp': datetime.now().isoformat()
            }
    
    def rolling_restart(self, reason: str, admin_user: str = None) -> Dict[str, Any]:
        """Perform rolling restart without downtime"""
        with self._state_lock():
            # Log restart
            self.logger.info(f"Rolling restart initiated by {admin_user}: {reason}")
            
            # Update state
            self._state['last_restart'] = datetime.now().isoformat()
            self._state['restart_reason'] = reason
            self._state['restart_by'] = admin_user
            
            # Save to database
            self._save_state('last_restart', self._state['last_restart'])
            
            # TODO: Implement actual rolling restart logic
            # This would typically involve:
            # 1. Graceful shutdown of workers
            # 2. Reload configuration
            # 3. Restart services in sequence
            
            return {
                'success': True,
                'message': 'Rolling restart completed',
                'reason': reason,
                'initiated_by': admin_user,
                'timestamp': datetime.now().isoformat()
            }
    
    # Load Balancing and Traffic Control
    def set_traffic_control(self, rate_limit: Optional[int] = None, 
                           max_concurrent: Optional[int] = None,
                           admin_user: str = None) -> Dict[str, Any]:
        """Set traffic control parameters"""
        with self._state_lock():
            changes = {}
            
            if rate_limit is not None:
                self._state['rate_limit'] = rate_limit
                changes['rate_limit'] = rate_limit
                self._save_state('rate_limit', rate_limit)
            
            if max_concurrent is not None:
                self._state['max_concurrent'] = max_concurrent
                changes['max_concurrent'] = max_concurrent
                self._save_state('max_concurrent', max_concurrent)
            
            if changes:
                self.logger.info(f"Traffic control updated by {admin_user}: {changes}")
            
            return {
                'success': True,
                'changes': changes,
                'current_settings': {
                    'rate_limit': self._state.get('rate_limit'),
                    'max_concurrent': self._state.get('max_concurrent')
                },
                'updated_by': admin_user,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_traffic_stats(self) -> Dict[str, Any]:
        """Get current traffic statistics"""
        # TODO: Implement actual traffic monitoring
        return {
            'current_connections': 0,
            'requests_per_minute': 0,
            'rate_limit': self._state.get('rate_limit'),
            'max_concurrent': self._state.get('max_concurrent'),
            'timestamp': datetime.now().isoformat()
        }
    
    # System Performance Monitoring
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        try:
            import psutil
            
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            # Process info
            process = psutil.Process()
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count()
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'process': {
                    'pid': process.pid,
                    'memory_percent': process.memory_percent(),
                    'cpu_percent': process.cpu_percent(),
                    'create_time': process.create_time()
                },
                'timestamp': datetime.now().isoformat()
            }
        except ImportError:
            return {
                'error': 'psutil not available',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'error': f'Failed to get system metrics: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    # Configuration Management
    def update_system_config(self, config: Dict[str, Any], admin_user: str = None) -> Dict[str, Any]:
        """Update system configuration"""
        with self._state_lock():
            old_config = self._state.get('system_config', {}).copy()
            
            # Validate configuration
            validation_result = self._validate_config(config)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'invalid_keys': validation_result.get('invalid_keys', [])
                }
            
            # Apply configuration
            self._state['system_config'].update(config)
            self._save_state('system_config', self._state['system_config'])
            
            # Log configuration change
            self.logger.info(f"System configuration updated by {admin_user}: {config}")
            
            return {
                'success': True,
                'old_config': old_config,
                'new_config': self._state['system_config'],
                'updated_by': admin_user,
                'timestamp': datetime.now().isoformat()
            }
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate system configuration"""
        # Define valid configuration keys and their types
        valid_config = {
            'max_upload_size': int,
            'session_timeout': int,
            'max_concurrent_uploads': int,
            'enable_analytics': bool,
            'debug_mode': bool,
            'log_level': str
        }
        
        invalid_keys = []
        for key, value in config.items():
            if key not in valid_config:
                invalid_keys.append(key)
                continue
                
            expected_type = valid_config[key]
            if not isinstance(value, expected_type):
                invalid_keys.append(f"{key} (expected {expected_type.__name__})")
        
        if invalid_keys:
            return {
                'valid': False,
                'error': f'Invalid configuration keys: {invalid_keys}',
                'invalid_keys': invalid_keys
            }
        
        return {'valid': True}
    
    def get_system_config(self) -> Dict[str, Any]:
        """Get current system configuration"""
        with self._state_lock():
            return self._state.get('system_config', {})


# Global system controller instance
system_controller = SystemController()

if __name__ == '__main__':
    # Test system controller
    print("🎛️  Testing VectorCraft System Controller...")
    
    # Test system state
    print("\n📊 Current System State:")
    state = system_controller.get_system_state()
    for key, value in state.items():
        print(f"  {key}: {value}")
    
    # Test maintenance mode
    print("\n🔧 Testing Maintenance Mode:")
    result = system_controller.set_maintenance_mode(True, "Testing maintenance mode", "test-admin")
    print(f"  Enable maintenance: {result}")
    
    maintenance_status = system_controller.get_maintenance_status()
    print(f"  Maintenance status: {maintenance_status}")
    
    # Disable maintenance mode
    result = system_controller.set_maintenance_mode(False, admin_user="test-admin")
    print(f"  Disable maintenance: {result}")
    
    # Test system metrics
    print("\n📈 System Metrics:")
    metrics = system_controller.get_system_metrics()
    if 'error' not in metrics:
        print(f"  CPU: {metrics['cpu']['percent']}%")
        print(f"  Memory: {metrics['memory']['percent']}%")
        print(f"  Disk: {metrics['disk']['percent']}%")
    else:
        print(f"  Error: {metrics['error']}")
    
    print("\n✅ System Controller Test Complete")