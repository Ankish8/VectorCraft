#!/usr/bin/env python3
"""
Advanced Permission Manager Service for VectorCraft
Provides comprehensive role-based access control with granular permissions
"""

import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
from flask import request, session, current_app
from flask_login import current_user

from database import db


class PermissionType(Enum):
    """Permission types for different operations"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class ResourceType(Enum):
    """Resource types in the system"""
    USER = "user"
    TRANSACTION = "transaction"
    SYSTEM = "system"
    ANALYTICS = "analytics"
    EMAIL = "email"
    FILE = "file"
    API = "api"
    ROLE = "role"
    PERMISSION = "permission"
    VECTORIZATION = "vectorization"
    MONITORING = "monitoring"


@dataclass
class Permission:
    """Permission data structure"""
    id: int
    name: str
    description: str
    resource: str
    action: str
    is_system_permission: bool = False
    created_at: datetime = None


@dataclass
class Role:
    """Role data structure"""
    id: int
    name: str
    description: str
    parent_role_id: Optional[int] = None
    is_system_role: bool = False
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class UserRole:
    """User role assignment data structure"""
    id: int
    user_id: int
    role_id: int
    assigned_by: int
    assigned_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    approval_status: str = "approved"


class PermissionManager:
    """Core permission management service"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._permission_cache = {}
        self._role_cache = {}
        self._user_permissions_cache = {}
        self._cache_timeout = 300  # 5 minutes
        
        # Initialize default permissions and roles
        self._ensure_default_permissions()
        self._ensure_default_roles()
    
    def _ensure_default_permissions(self):
        """Create default system permissions if they don't exist"""
        default_permissions = [
            # User management
            ("user.read", "View user information", "user", "read"),
            ("user.write", "Modify user information", "user", "write"),
            ("user.delete", "Delete users", "user", "delete"),
            ("user.admin", "Full user administration", "user", "admin"),
            
            # Transaction management
            ("transaction.read", "View transactions", "transaction", "read"),
            ("transaction.write", "Modify transactions", "transaction", "write"),
            ("transaction.admin", "Full transaction administration", "transaction", "admin"),
            
            # System management
            ("system.read", "View system information", "system", "read"),
            ("system.write", "Modify system settings", "system", "write"),
            ("system.admin", "Full system administration", "system", "admin"),
            
            # Analytics
            ("analytics.read", "View analytics", "analytics", "read"),
            ("analytics.write", "Modify analytics settings", "analytics", "write"),
            ("analytics.admin", "Full analytics administration", "analytics", "admin"),
            
            # Email management
            ("email.read", "View email logs", "email", "read"),
            ("email.write", "Send emails", "email", "write"),
            ("email.admin", "Full email administration", "email", "admin"),
            
            # File management
            ("file.read", "View files", "file", "read"),
            ("file.write", "Upload/modify files", "file", "write"),
            ("file.delete", "Delete files", "file", "delete"),
            ("file.admin", "Full file administration", "file", "admin"),
            
            # API management
            ("api.read", "View API endpoints", "api", "read"),
            ("api.write", "Modify API settings", "api", "write"),
            ("api.admin", "Full API administration", "api", "admin"),
            
            # Role and permission management
            ("role.read", "View roles", "role", "read"),
            ("role.write", "Modify roles", "role", "write"),
            ("role.admin", "Full role administration", "role", "admin"),
            
            ("permission.read", "View permissions", "permission", "read"),
            ("permission.write", "Modify permissions", "permission", "write"),
            ("permission.admin", "Full permission administration", "permission", "admin"),
            
            # Vectorization
            ("vectorization.read", "View vectorization jobs", "vectorization", "read"),
            ("vectorization.write", "Create vectorization jobs", "vectorization", "write"),
            ("vectorization.admin", "Full vectorization administration", "vectorization", "admin"),
            
            # Monitoring
            ("monitoring.read", "View monitoring data", "monitoring", "read"),
            ("monitoring.write", "Modify monitoring settings", "monitoring", "write"),
            ("monitoring.admin", "Full monitoring administration", "monitoring", "admin"),
        ]
        
        with db.get_db_connection() as conn:
            for name, description, resource, action in default_permissions:
                try:
                    conn.execute('''
                        INSERT OR IGNORE INTO permissions (name, description, resource, action, is_system_permission)
                        VALUES (?, ?, ?, ?, 1)
                    ''', (name, description, resource, action))
                except Exception as e:
                    self.logger.error(f"Error creating default permission {name}: {e}")
            
            conn.commit()
    
    def _ensure_default_roles(self):
        """Create default system roles if they don't exist"""
        default_roles = [
            ("super_admin", "Super Administrator with full system access", None),
            ("admin", "Administrator with limited system access", None),
            ("moderator", "Content moderator with user management access", None),
            ("user", "Regular user with basic access", None),
            ("guest", "Guest user with read-only access", None),
        ]
        
        with db.get_db_connection() as conn:
            for name, description, parent_role_id in default_roles:
                try:
                    conn.execute('''
                        INSERT OR IGNORE INTO roles (name, description, parent_role_id, is_system_role)
                        VALUES (?, ?, ?, 1)
                    ''', (name, description, parent_role_id))
                except Exception as e:
                    self.logger.error(f"Error creating default role {name}: {e}")
            
            conn.commit()
            
            # Assign permissions to default roles
            self._assign_default_role_permissions()
    
    def _assign_default_role_permissions(self):
        """Assign default permissions to system roles"""
        role_permissions = {
            "super_admin": ["*"],  # All permissions
            "admin": [
                "user.read", "user.write", "transaction.read", "transaction.write",
                "system.read", "analytics.read", "analytics.write", "email.read",
                "email.write", "file.read", "file.write", "api.read", "role.read",
                "permission.read", "vectorization.read", "vectorization.write",
                "monitoring.read", "monitoring.write"
            ],
            "moderator": [
                "user.read", "user.write", "transaction.read", "email.read",
                "file.read", "vectorization.read", "monitoring.read"
            ],
            "user": [
                "file.read", "file.write", "vectorization.read", "vectorization.write"
            ],
            "guest": [
                "file.read", "vectorization.read"
            ],
        }
        
        with db.get_db_connection() as conn:
            for role_name, permissions in role_permissions.items():
                role_id = self._get_role_id_by_name(role_name)
                if not role_id:
                    continue
                
                if permissions == ["*"]:
                    # Assign all permissions to super_admin
                    conn.execute('''
                        INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                        SELECT ?, id FROM permissions
                    ''', (role_id,))
                else:
                    for perm_name in permissions:
                        perm_id = self._get_permission_id_by_name(perm_name)
                        if perm_id:
                            conn.execute('''
                                INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                                VALUES (?, ?)
                            ''', (role_id, perm_id))
            
            conn.commit()
    
    def _get_role_id_by_name(self, role_name: str) -> Optional[int]:
        """Get role ID by name"""
        with db.get_db_connection() as conn:
            result = conn.execute(
                'SELECT id FROM roles WHERE name = ?',
                (role_name,)
            ).fetchone()
            return result[0] if result else None
    
    def _get_permission_id_by_name(self, permission_name: str) -> Optional[int]:
        """Get permission ID by name"""
        with db.get_db_connection() as conn:
            result = conn.execute(
                'SELECT id FROM permissions WHERE name = ?',
                (permission_name,)
            ).fetchone()
            return result[0] if result else None
    
    def create_permission(self, name: str, description: str, resource: str, action: str) -> Optional[int]:
        """Create a new permission"""
        try:
            with db.get_db_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO permissions (name, description, resource, action)
                    VALUES (?, ?, ?, ?)
                ''', (name, description, resource, action))
                
                permission_id = cursor.lastrowid
                conn.commit()
                
                # Log the creation
                self._log_permission_audit(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    action="create_permission",
                    resource_type="permission",
                    resource_id=permission_id,
                    permission_name=name,
                    new_value=json.dumps({"name": name, "description": description, "resource": resource, "action": action})
                )
                
                # Clear cache
                self._clear_permission_cache()
                
                return permission_id
                
        except Exception as e:
            self.logger.error(f"Error creating permission {name}: {e}")
            return None
    
    def create_role(self, name: str, description: str, parent_role_id: Optional[int] = None) -> Optional[int]:
        """Create a new role"""
        try:
            with db.get_db_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO roles (name, description, parent_role_id)
                    VALUES (?, ?, ?)
                ''', (name, description, parent_role_id))
                
                role_id = cursor.lastrowid
                conn.commit()
                
                # Log the creation
                self._log_permission_audit(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    action="create_role",
                    resource_type="role",
                    resource_id=role_id,
                    role_name=name,
                    new_value=json.dumps({"name": name, "description": description, "parent_role_id": parent_role_id})
                )
                
                # Clear cache
                self._clear_role_cache()
                
                return role_id
                
        except Exception as e:
            self.logger.error(f"Error creating role {name}: {e}")
            return None
    
    def assign_role_to_user(self, user_id: int, role_id: int, assigned_by: int, expires_at: Optional[datetime] = None) -> bool:
        """Assign a role to a user"""
        try:
            with db.get_db_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO user_roles (user_id, role_id, assigned_by, expires_at)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, role_id, assigned_by, expires_at))
                
                conn.commit()
                
                # Log the assignment
                self._log_permission_audit(
                    user_id=user_id,
                    action="assign_role",
                    resource_type="user_role",
                    resource_id=role_id,
                    new_value=json.dumps({"user_id": user_id, "role_id": role_id, "assigned_by": assigned_by}),
                    performed_by=assigned_by
                )
                
                # Clear user permissions cache
                self._clear_user_permissions_cache(user_id)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error assigning role {role_id} to user {user_id}: {e}")
            return False
    
    def revoke_role_from_user(self, user_id: int, role_id: int, revoked_by: int) -> bool:
        """Revoke a role from a user"""
        try:
            with db.get_db_connection() as conn:
                conn.execute('''
                    UPDATE user_roles 
                    SET is_active = 0 
                    WHERE user_id = ? AND role_id = ?
                ''', (user_id, role_id))
                
                conn.commit()
                
                # Log the revocation
                self._log_permission_audit(
                    user_id=user_id,
                    action="revoke_role",
                    resource_type="user_role",
                    resource_id=role_id,
                    old_value=json.dumps({"user_id": user_id, "role_id": role_id}),
                    performed_by=revoked_by
                )
                
                # Clear user permissions cache
                self._clear_user_permissions_cache(user_id)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error revoking role {role_id} from user {user_id}: {e}")
            return False
    
    def grant_permission_to_user(self, user_id: int, permission_id: int, granted_by: int, expires_at: Optional[datetime] = None) -> bool:
        """Grant a specific permission to a user"""
        try:
            with db.get_db_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO user_permissions (user_id, permission_id, granted_by, expires_at)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, permission_id, granted_by, expires_at))
                
                conn.commit()
                
                # Log the grant
                self._log_permission_audit(
                    user_id=user_id,
                    action="grant_permission",
                    resource_type="user_permission",
                    resource_id=permission_id,
                    new_value=json.dumps({"user_id": user_id, "permission_id": permission_id, "granted_by": granted_by}),
                    performed_by=granted_by
                )
                
                # Clear user permissions cache
                self._clear_user_permissions_cache(user_id)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error granting permission {permission_id} to user {user_id}: {e}")
            return False
    
    def revoke_permission_from_user(self, user_id: int, permission_id: int, revoked_by: int) -> bool:
        """Revoke a specific permission from a user"""
        try:
            with db.get_db_connection() as conn:
                conn.execute('''
                    UPDATE user_permissions 
                    SET is_active = 0 
                    WHERE user_id = ? AND permission_id = ?
                ''', (user_id, permission_id))
                
                conn.commit()
                
                # Log the revocation
                self._log_permission_audit(
                    user_id=user_id,
                    action="revoke_permission",
                    resource_type="user_permission",
                    resource_id=permission_id,
                    old_value=json.dumps({"user_id": user_id, "permission_id": permission_id}),
                    performed_by=revoked_by
                )
                
                # Clear user permissions cache
                self._clear_user_permissions_cache(user_id)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error revoking permission {permission_id} from user {user_id}: {e}")
            return False
    
    def has_permission(self, user_id: int, permission_name: str) -> bool:
        """Check if a user has a specific permission"""
        try:
            user_permissions = self.get_user_permissions(user_id)
            return permission_name in user_permissions
        except Exception as e:
            self.logger.error(f"Error checking permission {permission_name} for user {user_id}: {e}")
            return False
    
    def has_role(self, user_id: int, role_name: str) -> bool:
        """Check if a user has a specific role"""
        try:
            user_roles = self.get_user_roles(user_id)
            return role_name in [role.name for role in user_roles]
        except Exception as e:
            self.logger.error(f"Error checking role {role_name} for user {user_id}: {e}")
            return False
    
    def get_user_permissions(self, user_id: int) -> Set[str]:
        """Get all permissions for a user (including inherited from roles)"""
        cache_key = f"user_permissions_{user_id}"
        cached_permissions = self._get_from_cache(cache_key)
        
        if cached_permissions is not None:
            return cached_permissions
        
        permissions = set()
        
        try:
            with db.get_db_connection() as conn:
                # Get direct permissions
                direct_permissions = conn.execute('''
                    SELECT p.name FROM permissions p
                    JOIN user_permissions up ON p.id = up.permission_id
                    WHERE up.user_id = ? AND up.is_active = 1
                    AND (up.expires_at IS NULL OR up.expires_at > datetime('now'))
                ''', (user_id,)).fetchall()
                
                permissions.update([perm[0] for perm in direct_permissions])
                
                # Get permissions from roles
                role_permissions = conn.execute('''
                    SELECT p.name FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    JOIN user_roles ur ON rp.role_id = ur.role_id
                    WHERE ur.user_id = ? AND ur.is_active = 1
                    AND (ur.expires_at IS NULL OR ur.expires_at > datetime('now'))
                    AND (rp.expires_at IS NULL OR rp.expires_at > datetime('now'))
                ''', (user_id,)).fetchall()
                
                permissions.update([perm[0] for perm in role_permissions])
                
                # Get permissions from parent roles (inheritance)
                permissions.update(self._get_inherited_permissions(user_id))
                
                # Cache the result
                self._set_cache(cache_key, permissions)
                
                return permissions
                
        except Exception as e:
            self.logger.error(f"Error getting permissions for user {user_id}: {e}")
            return set()
    
    def get_user_roles(self, user_id: int) -> List[Role]:
        """Get all active roles for a user"""
        try:
            with db.get_db_connection() as conn:
                roles_data = conn.execute('''
                    SELECT r.id, r.name, r.description, r.parent_role_id, r.is_system_role, r.is_active, r.created_at, r.updated_at
                    FROM roles r
                    JOIN user_roles ur ON r.id = ur.role_id
                    WHERE ur.user_id = ? AND ur.is_active = 1 AND r.is_active = 1
                    AND (ur.expires_at IS NULL OR ur.expires_at > datetime('now'))
                ''', (user_id,)).fetchall()
                
                return [Role(
                    id=role[0],
                    name=role[1],
                    description=role[2],
                    parent_role_id=role[3],
                    is_system_role=bool(role[4]),
                    is_active=bool(role[5]),
                    created_at=datetime.fromisoformat(role[6]) if role[6] else None,
                    updated_at=datetime.fromisoformat(role[7]) if role[7] else None
                ) for role in roles_data]
                
        except Exception as e:
            self.logger.error(f"Error getting roles for user {user_id}: {e}")
            return []
    
    def _get_inherited_permissions(self, user_id: int) -> Set[str]:
        """Get permissions inherited from parent roles"""
        permissions = set()
        
        try:
            with db.get_db_connection() as conn:
                # Get all user roles with their parent hierarchies
                user_roles = conn.execute('''
                    SELECT r.id, r.parent_role_id FROM roles r
                    JOIN user_roles ur ON r.id = ur.role_id
                    WHERE ur.user_id = ? AND ur.is_active = 1 AND r.is_active = 1
                    AND (ur.expires_at IS NULL OR ur.expires_at > datetime('now'))
                ''', (user_id,)).fetchall()
                
                # For each role, get permissions from parent roles
                for role_id, parent_role_id in user_roles:
                    parent_permissions = self._get_parent_role_permissions(parent_role_id)
                    permissions.update(parent_permissions)
                
        except Exception as e:
            self.logger.error(f"Error getting inherited permissions for user {user_id}: {e}")
        
        return permissions
    
    def _get_parent_role_permissions(self, role_id: Optional[int]) -> Set[str]:
        """Recursively get permissions from parent roles"""
        if not role_id:
            return set()
        
        permissions = set()
        
        try:
            with db.get_db_connection() as conn:
                # Get permissions for this role
                role_permissions = conn.execute('''
                    SELECT p.name FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    WHERE rp.role_id = ?
                    AND (rp.expires_at IS NULL OR rp.expires_at > datetime('now'))
                ''', (role_id,)).fetchall()
                
                permissions.update([perm[0] for perm in role_permissions])
                
                # Get parent role
                parent_role = conn.execute('''
                    SELECT parent_role_id FROM roles WHERE id = ?
                ''', (role_id,)).fetchone()
                
                if parent_role and parent_role[0]:
                    parent_permissions = self._get_parent_role_permissions(parent_role[0])
                    permissions.update(parent_permissions)
                
        except Exception as e:
            self.logger.error(f"Error getting parent role permissions for role {role_id}: {e}")
        
        return permissions
    
    def get_all_permissions(self) -> List[Permission]:
        """Get all permissions in the system"""
        try:
            with db.get_db_connection() as conn:
                permissions_data = conn.execute('''
                    SELECT id, name, description, resource, action, is_system_permission, created_at
                    FROM permissions
                    ORDER BY resource, action
                ''').fetchall()
                
                return [Permission(
                    id=perm[0],
                    name=perm[1],
                    description=perm[2],
                    resource=perm[3],
                    action=perm[4],
                    is_system_permission=bool(perm[5]),
                    created_at=datetime.fromisoformat(perm[6]) if perm[6] else None
                ) for perm in permissions_data]
                
        except Exception as e:
            self.logger.error(f"Error getting all permissions: {e}")
            return []
    
    def get_all_roles(self) -> List[Role]:
        """Get all roles in the system"""
        try:
            with db.get_db_connection() as conn:
                roles_data = conn.execute('''
                    SELECT id, name, description, parent_role_id, is_system_role, is_active, created_at, updated_at
                    FROM roles
                    WHERE is_active = 1
                    ORDER BY name
                ''').fetchall()
                
                return [Role(
                    id=role[0],
                    name=role[1],
                    description=role[2],
                    parent_role_id=role[3],
                    is_system_role=bool(role[4]),
                    is_active=bool(role[5]),
                    created_at=datetime.fromisoformat(role[6]) if role[6] else None,
                    updated_at=datetime.fromisoformat(role[7]) if role[7] else None
                ) for role in roles_data]
                
        except Exception as e:
            self.logger.error(f"Error getting all roles: {e}")
            return []
    
    def log_access_violation(self, user_id: int, attempted_action: str, resource: str, required_permission: str, severity: str = "medium"):
        """Log an access violation"""
        try:
            with db.get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO access_violations (user_id, attempted_action, resource, required_permission, violation_type, severity, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    attempted_action,
                    resource,
                    required_permission,
                    "permission_denied",
                    severity,
                    request.remote_addr if request else None,
                    request.user_agent.string if request else None
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error logging access violation: {e}")
    
    def _log_permission_audit(self, user_id: int, action: str, resource_type: str, resource_id: int = None, 
                            permission_name: str = None, role_name: str = None, old_value: str = None, 
                            new_value: str = None, performed_by: int = None):
        """Log permission audit trail"""
        try:
            with db.get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO permission_audit_log (user_id, action, resource_type, resource_id, permission_name, role_name, old_value, new_value, ip_address, user_agent, performed_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    action,
                    resource_type,
                    resource_id,
                    permission_name,
                    role_name,
                    old_value,
                    new_value,
                    request.remote_addr if request else None,
                    request.user_agent.string if request else None,
                    performed_by
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error logging permission audit: {e}")
    
    def _get_from_cache(self, key: str) -> Any:
        """Get value from cache if valid"""
        if key in self._user_permissions_cache:
            cached_data, timestamp = self._user_permissions_cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self._cache_timeout):
                return cached_data
        return None
    
    def _set_cache(self, key: str, value: Any):
        """Set value in cache"""
        self._user_permissions_cache[key] = (value, datetime.now())
    
    def _clear_permission_cache(self):
        """Clear permission cache"""
        self._permission_cache.clear()
    
    def _clear_role_cache(self):
        """Clear role cache"""
        self._role_cache.clear()
    
    def _clear_user_permissions_cache(self, user_id: int):
        """Clear user permissions cache"""
        cache_key = f"user_permissions_{user_id}"
        if cache_key in self._user_permissions_cache:
            del self._user_permissions_cache[cache_key]
    
    def require_permission(self, permission_name: str):
        """Decorator to require a specific permission"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not current_user.is_authenticated:
                    self.log_access_violation(
                        user_id=0,
                        attempted_action=f.__name__,
                        resource=permission_name,
                        required_permission=permission_name,
                        severity="high"
                    )
                    return {"error": "Authentication required"}, 401
                
                if not self.has_permission(current_user.id, permission_name):
                    self.log_access_violation(
                        user_id=current_user.id,
                        attempted_action=f.__name__,
                        resource=permission_name,
                        required_permission=permission_name,
                        severity="medium"
                    )
                    return {"error": "Insufficient permissions"}, 403
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def require_role(self, role_name: str):
        """Decorator to require a specific role"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not current_user.is_authenticated:
                    self.log_access_violation(
                        user_id=0,
                        attempted_action=f.__name__,
                        resource=role_name,
                        required_permission=f"role:{role_name}",
                        severity="high"
                    )
                    return {"error": "Authentication required"}, 401
                
                if not self.has_role(current_user.id, role_name):
                    self.log_access_violation(
                        user_id=current_user.id,
                        attempted_action=f.__name__,
                        resource=role_name,
                        required_permission=f"role:{role_name}",
                        severity="medium"
                    )
                    return {"error": "Insufficient role"}, 403
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator


# Global instance
permission_manager = PermissionManager()