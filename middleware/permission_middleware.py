#!/usr/bin/env python3
"""
Permission Middleware for VectorCraft
Route-level access control and permission enforcement
"""

import json
import logging
from functools import wraps
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from flask import request, session, current_app, jsonify, abort, redirect, url_for, flash
from flask_login import current_user
from werkzeug.exceptions import Forbidden, Unauthorized

from services.permission_manager import permission_manager
from services.role_manager import role_manager


class PermissionMiddleware:
    """Middleware for enforcing permissions at route level"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.permission_manager = permission_manager
        self.role_manager = role_manager
        
        # Route permission mappings
        self.route_permissions = {
            # Admin routes
            'admin.dashboard': 'system.read',
            'admin.users': 'user.read',
            'admin.user_detail': 'user.read',
            'admin.transactions': 'transaction.read',
            'admin.analytics': 'analytics.read',
            'admin.system': 'system.read',
            'admin.logs': 'system.read',
            'admin.alerts': 'system.read',
            'admin.security': 'system.admin',
            'admin.email_analytics': 'email.read',
            'admin.email_templates': 'email.admin',
            'admin.api_management': 'api.admin',
            'admin.file_management': 'file.admin',
            'admin.permissions': 'permission.admin',
            'admin.roles': 'role.admin',
            
            # API routes
            'api.vectorize': 'vectorization.write',
            'api.upload': 'file.write',
            'api.download': 'file.read',
            'api.management': 'api.admin',
            'api.health': 'system.read',
            
            # User routes
            'main.dashboard': 'user.read',
            'main.profile': 'user.read',
            'main.settings': 'user.write',
            
            # Payment routes
            'payment.create': 'transaction.write',
            'payment.status': 'transaction.read',
        }
        
        # HTTP method to permission action mapping
        self.method_to_action = {
            'GET': 'read',
            'POST': 'write',
            'PUT': 'write',
            'PATCH': 'write',
            'DELETE': 'delete'
        }
        
        # Resource extraction from routes
        self.route_to_resource = {
            'admin.users': 'user',
            'admin.transactions': 'transaction',
            'admin.analytics': 'analytics',
            'admin.system': 'system',
            'admin.email_analytics': 'email',
            'admin.api_management': 'api',
            'admin.file_management': 'file',
            'admin.permissions': 'permission',
            'admin.roles': 'role',
            'api.vectorize': 'vectorization',
            'api.upload': 'file',
            'api.download': 'file',
            'main.dashboard': 'user',
            'main.profile': 'user',
            'payment.create': 'transaction',
        }
    
    def require_permission(self, permission_name: str, resource_id: Optional[int] = None):
        """Decorator to require a specific permission"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self._check_permission(permission_name, resource_id):
                    return self._handle_permission_denied(permission_name, f.__name__)
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def require_role(self, role_name: str):
        """Decorator to require a specific role"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self._check_role(role_name):
                    return self._handle_permission_denied(f"role:{role_name}", f.__name__)
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def require_any_permission(self, permissions: List[str]):
        """Decorator to require any of the specified permissions"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self._check_any_permission(permissions):
                    return self._handle_permission_denied(f"any:{','.join(permissions)}", f.__name__)
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def require_all_permissions(self, permissions: List[str]):
        """Decorator to require all of the specified permissions"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self._check_all_permissions(permissions):
                    return self._handle_permission_denied(f"all:{','.join(permissions)}", f.__name__)
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def auto_permission_check(self, route_name: str = None):
        """Decorator that automatically determines required permission from route"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Determine permission from route name or function name
                endpoint = route_name or request.endpoint or f.__name__
                
                # Check if permission is defined for this route
                if endpoint in self.route_permissions:
                    permission_name = self.route_permissions[endpoint]
                    if not self._check_permission(permission_name):
                        return self._handle_permission_denied(permission_name, f.__name__)
                else:
                    # Auto-generate permission from route and method
                    permission_name = self._generate_permission_from_route(endpoint)
                    if permission_name and not self._check_permission(permission_name):
                        return self._handle_permission_denied(permission_name, f.__name__)
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def api_permission_check(self, resource: str, action: str = None):
        """Decorator specifically for API endpoints"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Determine action from HTTP method if not specified
                if not action:
                    method = request.method
                    action = self.method_to_action.get(method, 'read')
                
                permission_name = f"{resource}.{action}"
                
                if not self._check_permission(permission_name):
                    return self._handle_api_permission_denied(permission_name, f.__name__)
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def admin_only(self, level: str = "admin"):
        """Decorator to restrict access to admin users only"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self._check_admin_access(level):
                    return self._handle_permission_denied(f"admin:{level}", f.__name__)
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def resource_owner_or_permission(self, resource_type: str, permission_name: str, resource_id_param: str = 'id'):
        """Decorator to allow access if user owns resource or has permission"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Get resource ID from request parameters
                resource_id = request.view_args.get(resource_id_param) or request.args.get(resource_id_param)
                
                # Check if user owns the resource
                if self._check_resource_ownership(resource_type, resource_id):
                    return f(*args, **kwargs)
                
                # Check if user has the required permission
                if self._check_permission(permission_name):
                    return f(*args, **kwargs)
                
                return self._handle_permission_denied(permission_name, f.__name__)
            return decorated_function
        return decorator
    
    def time_limited_permission(self, permission_name: str, max_duration_minutes: int = 60):
        """Decorator for permissions that expire after a certain time"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self._check_time_limited_permission(permission_name, max_duration_minutes):
                    return self._handle_permission_denied(permission_name, f.__name__)
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def _check_permission(self, permission_name: str, resource_id: Optional[int] = None) -> bool:
        """Check if current user has the specified permission"""
        if not current_user.is_authenticated:
            return False
        
        return self.permission_manager.has_permission(current_user.id, permission_name)
    
    def _check_role(self, role_name: str) -> bool:
        """Check if current user has the specified role"""
        if not current_user.is_authenticated:
            return False
        
        return self.permission_manager.has_role(current_user.id, role_name)
    
    def _check_any_permission(self, permissions: List[str]) -> bool:
        """Check if current user has any of the specified permissions"""
        if not current_user.is_authenticated:
            return False
        
        user_permissions = self.permission_manager.get_user_permissions(current_user.id)
        return any(perm in user_permissions for perm in permissions)
    
    def _check_all_permissions(self, permissions: List[str]) -> bool:
        """Check if current user has all of the specified permissions"""
        if not current_user.is_authenticated:
            return False
        
        user_permissions = self.permission_manager.get_user_permissions(current_user.id)
        return all(perm in user_permissions for perm in permissions)
    
    def _check_admin_access(self, level: str = "admin") -> bool:
        """Check if current user has admin access"""
        if not current_user.is_authenticated:
            return False
        
        admin_roles = {
            "super_admin": ["super_admin"],
            "admin": ["super_admin", "admin"],
            "moderator": ["super_admin", "admin", "moderator"]
        }
        
        user_roles = [role.name for role in self.permission_manager.get_user_roles(current_user.id)]
        allowed_roles = admin_roles.get(level, [])
        
        return any(role in user_roles for role in allowed_roles)
    
    def _check_resource_ownership(self, resource_type: str, resource_id: int) -> bool:
        """Check if current user owns the specified resource"""
        if not current_user.is_authenticated or not resource_id:
            return False
        
        # Resource ownership checks
        ownership_checks = {
            'user': lambda rid: current_user.id == int(rid),
            'file': self._check_file_ownership,
            'transaction': self._check_transaction_ownership,
            'vectorization': self._check_vectorization_ownership,
        }
        
        check_func = ownership_checks.get(resource_type)
        if check_func:
            return check_func(resource_id)
        
        return False
    
    def _check_file_ownership(self, file_id: int) -> bool:
        """Check if current user owns the file"""
        try:
            from database import db
            with db.get_db_connection() as conn:
                result = conn.execute(
                    'SELECT user_id FROM user_uploads WHERE id = ?',
                    (file_id,)
                ).fetchone()
                return result and result[0] == current_user.id
        except Exception:
            return False
    
    def _check_transaction_ownership(self, transaction_id: int) -> bool:
        """Check if current user owns the transaction"""
        try:
            from database import db
            with db.get_db_connection() as conn:
                result = conn.execute(
                    'SELECT email FROM transactions WHERE id = ?',
                    (transaction_id,)
                ).fetchone()
                return result and result[0] == current_user.email
        except Exception:
            return False
    
    def _check_vectorization_ownership(self, vectorization_id: int) -> bool:
        """Check if current user owns the vectorization job"""
        try:
            from database import db
            with db.get_db_connection() as conn:
                result = conn.execute(
                    'SELECT user_id FROM user_uploads WHERE id = ?',
                    (vectorization_id,)
                ).fetchone()
                return result and result[0] == current_user.id
        except Exception:
            return False
    
    def _check_time_limited_permission(self, permission_name: str, max_duration_minutes: int) -> bool:
        """Check if user has permission and it hasn't expired"""
        if not self._check_permission(permission_name):
            return False
        
        # Check session for permission grant time
        permission_key = f"permission_granted_{permission_name}"
        granted_at = session.get(permission_key)
        
        if not granted_at:
            return False
        
        granted_time = datetime.fromisoformat(granted_at)
        elapsed_minutes = (datetime.now() - granted_time).total_seconds() / 60
        
        return elapsed_minutes <= max_duration_minutes
    
    def _generate_permission_from_route(self, endpoint: str) -> Optional[str]:
        """Generate permission name from route endpoint"""
        if not endpoint:
            return None
        
        # Extract resource from endpoint
        resource = self.route_to_resource.get(endpoint)
        if not resource:
            return None
        
        # Determine action from HTTP method
        method = request.method
        action = self.method_to_action.get(method, 'read')
        
        return f"{resource}.{action}"
    
    def _handle_permission_denied(self, permission_name: str, function_name: str):
        """Handle permission denied scenarios"""
        if not current_user.is_authenticated:
            self.permission_manager.log_access_violation(
                user_id=0,
                attempted_action=function_name,
                resource=permission_name,
                required_permission=permission_name,
                severity="high"
            )
            
            # Redirect to login for web requests
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"error": "Authentication required"}), 401
            else:
                flash("Please log in to access this resource", "error")
                return redirect(url_for('auth.login'))
        
        # Log access violation
        self.permission_manager.log_access_violation(
            user_id=current_user.id,
            attempted_action=function_name,
            resource=permission_name,
            required_permission=permission_name,
            severity="medium"
        )
        
        # Return appropriate response based on request type
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                "error": "Insufficient permissions",
                "required_permission": permission_name
            }), 403
        else:
            flash("You don't have permission to access this resource", "error")
            return redirect(url_for('main.dashboard'))
    
    def _handle_api_permission_denied(self, permission_name: str, function_name: str):
        """Handle API permission denied scenarios"""
        if not current_user.is_authenticated:
            self.permission_manager.log_access_violation(
                user_id=0,
                attempted_action=function_name,
                resource=permission_name,
                required_permission=permission_name,
                severity="high"
            )
            return jsonify({"error": "Authentication required"}), 401
        
        self.permission_manager.log_access_violation(
            user_id=current_user.id,
            attempted_action=function_name,
            resource=permission_name,
            required_permission=permission_name,
            severity="medium"
        )
        
        return jsonify({
            "error": "Insufficient permissions",
            "required_permission": permission_name,
            "user_permissions": list(self.permission_manager.get_user_permissions(current_user.id))
        }), 403
    
    def grant_temporary_permission(self, permission_name: str, duration_minutes: int = 60):
        """Grant temporary permission to current user"""
        if current_user.is_authenticated:
            permission_key = f"permission_granted_{permission_name}"
            session[permission_key] = datetime.now().isoformat()
            session.permanent = True
            self.logger.info(f"Granted temporary permission {permission_name} to user {current_user.id} for {duration_minutes} minutes")
    
    def revoke_temporary_permission(self, permission_name: str):
        """Revoke temporary permission from current user"""
        if current_user.is_authenticated:
            permission_key = f"permission_granted_{permission_name}"
            session.pop(permission_key, None)
            self.logger.info(f"Revoked temporary permission {permission_name} from user {current_user.id}")
    
    def get_user_effective_permissions(self, user_id: int = None) -> Dict[str, Any]:
        """Get effective permissions for a user"""
        if not user_id:
            user_id = current_user.id if current_user.is_authenticated else None
        
        if not user_id:
            return {}
        
        user_permissions = self.permission_manager.get_user_permissions(user_id)
        user_roles = self.permission_manager.get_user_roles(user_id)
        
        return {
            "user_id": user_id,
            "permissions": list(user_permissions),
            "roles": [{"id": role.id, "name": role.name, "description": role.description} for role in user_roles],
            "admin_level": self._get_admin_level(user_roles),
            "can_access": {
                "admin_dashboard": self._check_admin_access("moderator"),
                "user_management": self._check_permission("user.admin"),
                "system_management": self._check_permission("system.admin"),
                "analytics": self._check_permission("analytics.read"),
                "file_management": self._check_permission("file.admin"),
                "api_management": self._check_permission("api.admin"),
                "permission_management": self._check_permission("permission.admin"),
            }
        }
    
    def _get_admin_level(self, user_roles: List[Any]) -> str:
        """Determine admin level from user roles"""
        role_names = [role.name for role in user_roles]
        
        if "super_admin" in role_names:
            return "super_admin"
        elif "admin" in role_names:
            return "admin"
        elif "moderator" in role_names:
            return "moderator"
        else:
            return "user"
    
    def check_route_access(self, route_name: str, method: str = "GET") -> bool:
        """Check if current user can access a specific route"""
        if route_name in self.route_permissions:
            permission_name = self.route_permissions[route_name]
            return self._check_permission(permission_name)
        
        # Auto-generate permission
        resource = self.route_to_resource.get(route_name)
        if resource:
            action = self.method_to_action.get(method, 'read')
            permission_name = f"{resource}.{action}"
            return self._check_permission(permission_name)
        
        return True  # Allow access if no permission defined


# Global instance
permission_middleware = PermissionMiddleware()


# Convenience decorators
def require_permission(permission_name: str, resource_id: Optional[int] = None):
    """Convenience decorator for requiring permissions"""
    return permission_middleware.require_permission(permission_name, resource_id)


def require_role(role_name: str):
    """Convenience decorator for requiring roles"""
    return permission_middleware.require_role(role_name)


def require_any_permission(permissions: List[str]):
    """Convenience decorator for requiring any permission"""
    return permission_middleware.require_any_permission(permissions)


def require_all_permissions(permissions: List[str]):
    """Convenience decorator for requiring all permissions"""
    return permission_middleware.require_all_permissions(permissions)


def auto_permission_check(route_name: str = None):
    """Convenience decorator for automatic permission checking"""
    return permission_middleware.auto_permission_check(route_name)


def api_permission_check(resource: str, action: str = None):
    """Convenience decorator for API permission checking"""
    return permission_middleware.api_permission_check(resource, action)


def admin_only(level: str = "admin"):
    """Convenience decorator for admin-only access"""
    return permission_middleware.admin_only(level)


def resource_owner_or_permission(resource_type: str, permission_name: str, resource_id_param: str = 'id'):
    """Convenience decorator for resource ownership or permission"""
    return permission_middleware.resource_owner_or_permission(resource_type, permission_name, resource_id_param)


def time_limited_permission(permission_name: str, max_duration_minutes: int = 60):
    """Convenience decorator for time-limited permissions"""
    return permission_middleware.time_limited_permission(permission_name, max_duration_minutes)