#!/usr/bin/env python3
"""
Feature Flag Management System
Real-time feature toggles, user-based rollouts, and dependency management
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from enum import Enum
import hashlib
import random
from database import db
from services.monitoring.system_logger import system_logger

class FeatureStatus(Enum):
    """Feature flag status options"""
    DISABLED = "disabled"
    ENABLED = "enabled"
    PARTIAL = "partial"
    BETA = "beta"
    DEPRECATED = "deprecated"

class RolloutStrategy(Enum):
    """Feature rollout strategy options"""
    ALL_USERS = "all_users"
    PERCENTAGE = "percentage"
    USER_LIST = "user_list"
    BETA_USERS = "beta_users"
    GRADUAL = "gradual"

class FeatureFlagManager:
    """
    Manages feature flags with real-time updates, user-based rollouts,
    and dependency management
    """
    
    def __init__(self):
        self.logger = system_logger
        self._flags = {}
        self._lock = threading.RLock()
        self._cache = {}
        self._cache_ttl = 60  # 1 minute cache
        self._init_database()
        self._load_flags()
        
    def _init_database(self):
        """Initialize feature flag database tables"""
        try:
            with db.get_db_connection() as conn:
                # Feature flags table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS feature_flags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        status TEXT NOT NULL DEFAULT 'disabled',
                        rollout_strategy TEXT NOT NULL DEFAULT 'all_users',
                        rollout_percentage INTEGER DEFAULT 0,
                        target_users TEXT,
                        beta_users TEXT,
                        dependencies TEXT,
                        created_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_by TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT
                    )
                ''')
                
                # Feature flag history table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS feature_flag_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        flag_name TEXT NOT NULL,
                        action TEXT NOT NULL,
                        old_value TEXT,
                        new_value TEXT,
                        changed_by TEXT,
                        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        reason TEXT
                    )
                ''')
                
                # User feature access table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS user_feature_access (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        feature_name TEXT NOT NULL,
                        access_granted BOOLEAN DEFAULT 0,
                        granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        granted_by TEXT,
                        UNIQUE(user_id, feature_name)
                    )
                ''')
                
                conn.commit()
                self.logger.info("Feature flag database initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize feature flag database: {e}")
    
    def _load_flags(self):
        """Load feature flags from database"""
        try:
            with db.get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT name, description, status, rollout_strategy, 
                           rollout_percentage, target_users, beta_users,
                           dependencies, metadata
                    FROM feature_flags
                ''')
                
                for row in cursor.fetchall():
                    flag_data = {
                        'name': row['name'],
                        'description': row['description'],
                        'status': FeatureStatus(row['status']),
                        'rollout_strategy': RolloutStrategy(row['rollout_strategy']),
                        'rollout_percentage': row['rollout_percentage'],
                        'target_users': json.loads(row['target_users']) if row['target_users'] else [],
                        'beta_users': json.loads(row['beta_users']) if row['beta_users'] else [],
                        'dependencies': json.loads(row['dependencies']) if row['dependencies'] else [],
                        'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                    }
                    
                    self._flags[row['name']] = flag_data
                
                self.logger.info(f"Loaded {len(self._flags)} feature flags")
        except Exception as e:
            self.logger.error(f"Failed to load feature flags: {e}")
    
    def _save_flag(self, flag_name: str, flag_data: Dict[str, Any], user: str = None):
        """Save feature flag to database"""
        try:
            with db.get_db_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO feature_flags
                    (name, description, status, rollout_strategy, rollout_percentage,
                     target_users, beta_users, dependencies, updated_by, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    flag_name,
                    flag_data['description'],
                    flag_data['status'].value,
                    flag_data['rollout_strategy'].value,
                    flag_data['rollout_percentage'],
                    json.dumps(flag_data['target_users']),
                    json.dumps(flag_data['beta_users']),
                    json.dumps(flag_data['dependencies']),
                    user,
                    datetime.now().isoformat(),
                    json.dumps(flag_data['metadata'])
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to save feature flag {flag_name}: {e}")
    
    def _log_change(self, flag_name: str, action: str, old_value: Any, new_value: Any, user: str = None, reason: str = None):
        """Log feature flag changes"""
        try:
            with db.get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO feature_flag_history
                    (flag_name, action, old_value, new_value, changed_by, reason)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    flag_name,
                    action,
                    json.dumps(old_value) if old_value is not None else None,
                    json.dumps(new_value) if new_value is not None else None,
                    user,
                    reason
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to log feature flag change: {e}")
    
    def create_feature_flag(self, name: str, description: str = "", 
                           status: FeatureStatus = FeatureStatus.DISABLED,
                           rollout_strategy: RolloutStrategy = RolloutStrategy.ALL_USERS,
                           rollout_percentage: int = 0,
                           target_users: List[str] = None,
                           beta_users: List[str] = None,
                           dependencies: List[str] = None,
                           user: str = None) -> Dict[str, Any]:
        """Create a new feature flag"""
        
        if target_users is None:
            target_users = []
        if beta_users is None:
            beta_users = []
        if dependencies is None:
            dependencies = []
        
        with self._lock:
            if name in self._flags:
                return {
                    'success': False,
                    'error': f'Feature flag {name} already exists'
                }
            
            # Validate dependencies
            for dep in dependencies:
                if dep not in self._flags:
                    return {
                        'success': False,
                        'error': f'Dependency {dep} does not exist'
                    }
            
            flag_data = {
                'name': name,
                'description': description,
                'status': status,
                'rollout_strategy': rollout_strategy,
                'rollout_percentage': rollout_percentage,
                'target_users': target_users,
                'beta_users': beta_users,
                'dependencies': dependencies,
                'metadata': {
                    'created_by': user,
                    'created_at': datetime.now().isoformat()
                }
            }
            
            self._flags[name] = flag_data
            self._save_flag(name, flag_data, user)
            self._log_change(name, 'created', None, flag_data, user)
            
            # Clear cache
            self._cache.clear()
            
            self.logger.info(f"Feature flag {name} created by {user}")
            
            return {
                'success': True,
                'flag': flag_data,
                'created_by': user,
                'timestamp': datetime.now().isoformat()
            }
    
    def update_feature_flag(self, name: str, **kwargs) -> Dict[str, Any]:
        """Update an existing feature flag"""
        with self._lock:
            if name not in self._flags:
                return {
                    'success': False,
                    'error': f'Feature flag {name} does not exist'
                }
            
            old_flag = self._flags[name].copy()
            user = kwargs.pop('user', None)
            reason = kwargs.pop('reason', None)
            
            # Validate updates
            if 'dependencies' in kwargs:
                for dep in kwargs['dependencies']:
                    if dep not in self._flags:
                        return {
                            'success': False,
                            'error': f'Dependency {dep} does not exist'
                        }
            
            # Update flag data
            updated_fields = {}
            for key, value in kwargs.items():
                if key in ['status', 'rollout_strategy'] and isinstance(value, str):
                    if key == 'status':
                        value = FeatureStatus(value)
                    elif key == 'rollout_strategy':
                        value = RolloutStrategy(value)
                
                if key in self._flags[name]:
                    updated_fields[key] = value
                    self._flags[name][key] = value
            
            if updated_fields:
                self._save_flag(name, self._flags[name], user)
                self._log_change(name, 'updated', old_flag, self._flags[name], user, reason)
                
                # Clear cache
                self._cache.clear()
                
                self.logger.info(f"Feature flag {name} updated by {user}: {updated_fields}")
                
                return {
                    'success': True,
                    'updated_fields': updated_fields,
                    'old_flag': old_flag,
                    'new_flag': self._flags[name],
                    'updated_by': user,
                    'timestamp': datetime.now().isoformat()
                }
            
            return {
                'success': False,
                'error': 'No valid fields to update'
            }
    
    def delete_feature_flag(self, name: str, user: str = None) -> Dict[str, Any]:
        """Delete a feature flag"""
        with self._lock:
            if name not in self._flags:
                return {
                    'success': False,
                    'error': f'Feature flag {name} does not exist'
                }
            
            # Check if other flags depend on this one
            dependents = []
            for flag_name, flag_data in self._flags.items():
                if name in flag_data['dependencies']:
                    dependents.append(flag_name)
            
            if dependents:
                return {
                    'success': False,
                    'error': f'Cannot delete {name}. It is a dependency for: {dependents}'
                }
            
            old_flag = self._flags[name].copy()
            del self._flags[name]
            
            # Remove from database
            try:
                with db.get_db_connection() as conn:
                    conn.execute('DELETE FROM feature_flags WHERE name = ?', (name,))
                    conn.commit()
            except Exception as e:
                self.logger.error(f"Failed to delete feature flag {name} from database: {e}")
            
            self._log_change(name, 'deleted', old_flag, None, user)
            
            # Clear cache
            self._cache.clear()
            
            self.logger.info(f"Feature flag {name} deleted by {user}")
            
            return {
                'success': True,
                'deleted_flag': old_flag,
                'deleted_by': user,
                'timestamp': datetime.now().isoformat()
            }
    
    def is_feature_enabled(self, feature_name: str, user_id: str = None, 
                          user_email: str = None) -> bool:
        """Check if a feature is enabled for a specific user"""
        
        # Check cache first
        cache_key = f"{feature_name}:{user_id}:{user_email}"
        if cache_key in self._cache:
            cached_result, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                return cached_result
        
        with self._lock:
            if feature_name not in self._flags:
                return False
            
            flag = self._flags[feature_name]
            
            # Check if flag is globally disabled
            if flag['status'] == FeatureStatus.DISABLED:
                result = False
            elif flag['status'] == FeatureStatus.ENABLED:
                result = self._check_rollout_strategy(flag, user_id, user_email)
            elif flag['status'] == FeatureStatus.BETA:
                result = self._is_beta_user(flag, user_id, user_email)
            elif flag['status'] == FeatureStatus.DEPRECATED:
                result = False
            else:
                result = False
            
            # Check dependencies
            if result:
                for dep in flag['dependencies']:
                    if not self.is_feature_enabled(dep, user_id, user_email):
                        result = False
                        break
            
            # Cache the result
            self._cache[cache_key] = (result, time.time())
            
            return result
    
    def _check_rollout_strategy(self, flag: Dict[str, Any], user_id: str = None, user_email: str = None) -> bool:
        """Check if user should have access based on rollout strategy"""
        strategy = flag['rollout_strategy']
        
        if strategy == RolloutStrategy.ALL_USERS:
            return True
        
        elif strategy == RolloutStrategy.USER_LIST:
            return (user_id in flag['target_users'] if user_id else False) or \
                   (user_email in flag['target_users'] if user_email else False)
        
        elif strategy == RolloutStrategy.PERCENTAGE:
            if not user_id and not user_email:
                return False
            
            # Use consistent hash for percentage rollout
            identifier = user_id or user_email
            hash_input = f"{flag['name']}:{identifier}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
            percentage = hash_value % 100
            
            return percentage < flag['rollout_percentage']
        
        elif strategy == RolloutStrategy.BETA_USERS:
            return self._is_beta_user(flag, user_id, user_email)
        
        elif strategy == RolloutStrategy.GRADUAL:
            # Gradual rollout increases percentage over time
            # This is a simplified implementation
            return self._check_rollout_strategy(
                {**flag, 'rollout_strategy': RolloutStrategy.PERCENTAGE},
                user_id, user_email
            )
        
        return False
    
    def _is_beta_user(self, flag: Dict[str, Any], user_id: str = None, user_email: str = None) -> bool:
        """Check if user is a beta user for the feature"""
        return (user_id in flag['beta_users'] if user_id else False) or \
               (user_email in flag['beta_users'] if user_email else False)
    
    def get_feature_flag(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific feature flag"""
        with self._lock:
            return self._flags.get(name)
    
    def get_all_feature_flags(self) -> Dict[str, Dict[str, Any]]:
        """Get all feature flags"""
        with self._lock:
            return self._flags.copy()
    
    def get_user_features(self, user_id: str = None, user_email: str = None) -> Dict[str, bool]:
        """Get all features available to a specific user"""
        features = {}
        
        with self._lock:
            for feature_name in self._flags:
                features[feature_name] = self.is_feature_enabled(feature_name, user_id, user_email)
        
        return features
    
    def get_feature_usage_stats(self, feature_name: str = None) -> Dict[str, Any]:
        """Get usage statistics for features"""
        try:
            with db.get_db_connection() as conn:
                if feature_name:
                    # Stats for specific feature
                    cursor = conn.execute('''
                        SELECT COUNT(*) as total_users,
                               SUM(CASE WHEN access_granted = 1 THEN 1 ELSE 0 END) as enabled_users
                        FROM user_feature_access
                        WHERE feature_name = ?
                    ''', (feature_name,))
                    
                    row = cursor.fetchone()
                    return {
                        'feature_name': feature_name,
                        'total_users': row['total_users'],
                        'enabled_users': row['enabled_users'],
                        'enabled_percentage': (row['enabled_users'] / row['total_users'] * 100) if row['total_users'] > 0 else 0
                    }
                else:
                    # Stats for all features
                    cursor = conn.execute('''
                        SELECT feature_name,
                               COUNT(*) as total_users,
                               SUM(CASE WHEN access_granted = 1 THEN 1 ELSE 0 END) as enabled_users
                        FROM user_feature_access
                        GROUP BY feature_name
                    ''')
                    
                    stats = {}
                    for row in cursor.fetchall():
                        stats[row['feature_name']] = {
                            'total_users': row['total_users'],
                            'enabled_users': row['enabled_users'],
                            'enabled_percentage': (row['enabled_users'] / row['total_users'] * 100) if row['total_users'] > 0 else 0
                        }
                    
                    return stats
        except Exception as e:
            self.logger.error(f"Failed to get feature usage stats: {e}")
            return {}
    
    def emergency_disable_feature(self, feature_name: str, user: str = None, reason: str = None) -> Dict[str, Any]:
        """Emergency disable a feature flag"""
        with self._lock:
            if feature_name not in self._flags:
                return {
                    'success': False,
                    'error': f'Feature flag {feature_name} does not exist'
                }
            
            old_status = self._flags[feature_name]['status']
            self._flags[feature_name]['status'] = FeatureStatus.DISABLED
            
            self._save_flag(feature_name, self._flags[feature_name], user)
            self._log_change(feature_name, 'emergency_disabled', old_status, FeatureStatus.DISABLED, user, reason)
            
            # Clear cache
            self._cache.clear()
            
            self.logger.warning(f"Feature flag {feature_name} emergency disabled by {user}: {reason}")
            
            return {
                'success': True,
                'feature_name': feature_name,
                'old_status': old_status,
                'new_status': FeatureStatus.DISABLED,
                'disabled_by': user,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }
    
    def bulk_update_features(self, updates: Dict[str, Dict[str, Any]], user: str = None) -> Dict[str, Any]:
        """Update multiple feature flags at once"""
        results = {}
        
        for feature_name, update_data in updates.items():
            update_data['user'] = user
            result = self.update_feature_flag(feature_name, **update_data)
            results[feature_name] = result
        
        return {
            'success': True,
            'results': results,
            'updated_by': user,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_feature_history(self, feature_name: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get feature flag change history"""
        try:
            with db.get_db_connection() as conn:
                if feature_name:
                    cursor = conn.execute('''
                        SELECT * FROM feature_flag_history
                        WHERE flag_name = ?
                        ORDER BY changed_at DESC
                        LIMIT ?
                    ''', (feature_name, limit))
                else:
                    cursor = conn.execute('''
                        SELECT * FROM feature_flag_history
                        ORDER BY changed_at DESC
                        LIMIT ?
                    ''', (limit,))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'flag_name': row['flag_name'],
                        'action': row['action'],
                        'old_value': json.loads(row['old_value']) if row['old_value'] else None,
                        'new_value': json.loads(row['new_value']) if row['new_value'] else None,
                        'changed_by': row['changed_by'],
                        'changed_at': row['changed_at'],
                        'reason': row['reason']
                    })
                
                return history
        except Exception as e:
            self.logger.error(f"Failed to get feature history: {e}")
            return []


# Global feature flag manager instance
feature_flags = FeatureFlagManager()

if __name__ == '__main__':
    # Test feature flag system
    print("🎛️  Testing VectorCraft Feature Flag System...")
    
    # Create test features
    print("\n🎯 Creating Test Features:")
    
    # Basic feature
    result = feature_flags.create_feature_flag(
        name="new_ui_design",
        description="New UI design for the main dashboard",
        status=FeatureStatus.ENABLED,
        rollout_strategy=RolloutStrategy.PERCENTAGE,
        rollout_percentage=50,
        user="test-admin"
    )
    print(f"  Created new_ui_design: {result['success']}")
    
    # Beta feature
    result = feature_flags.create_feature_flag(
        name="advanced_vectorization",
        description="Advanced vectorization algorithms",
        status=FeatureStatus.BETA,
        rollout_strategy=RolloutStrategy.BETA_USERS,
        beta_users=["beta@example.com", "test@example.com"],
        user="test-admin"
    )
    print(f"  Created advanced_vectorization: {result['success']}")
    
    # Test feature checking
    print("\n🔍 Testing Feature Checks:")
    
    # Test percentage rollout
    user_id = "test-user-123"
    enabled = feature_flags.is_feature_enabled("new_ui_design", user_id=user_id)
    print(f"  new_ui_design enabled for {user_id}: {enabled}")
    
    # Test beta user
    beta_email = "beta@example.com"
    enabled = feature_flags.is_feature_enabled("advanced_vectorization", user_email=beta_email)
    print(f"  advanced_vectorization enabled for {beta_email}: {enabled}")
    
    # Test non-beta user
    regular_email = "user@example.com"
    enabled = feature_flags.is_feature_enabled("advanced_vectorization", user_email=regular_email)
    print(f"  advanced_vectorization enabled for {regular_email}: {enabled}")
    
    # Get all features
    print("\n📋 All Features:")
    all_flags = feature_flags.get_all_feature_flags()
    for name, flag in all_flags.items():
        print(f"  {name}: {flag['status'].value} ({flag['rollout_strategy'].value})")
    
    # Test emergency disable
    print("\n🚨 Testing Emergency Disable:")
    result = feature_flags.emergency_disable_feature("new_ui_design", "test-admin", "Performance issues")
    print(f"  Emergency disable result: {result['success']}")
    
    # Check feature after disable
    enabled = feature_flags.is_feature_enabled("new_ui_design", user_id=user_id)
    print(f"  new_ui_design enabled after disable: {enabled}")
    
    print("\n✅ Feature Flag System Test Complete")