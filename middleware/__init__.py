"""
Middleware package for VectorCraft
"""

from .permission_middleware import (
    permission_middleware,
    require_permission,
    require_role,
    require_any_permission,
    require_all_permissions,
    auto_permission_check,
    api_permission_check,
    admin_only,
    resource_owner_or_permission,
    time_limited_permission
)

__all__ = [
    'permission_middleware',
    'require_permission',
    'require_role',
    'require_any_permission',
    'require_all_permissions',
    'auto_permission_check',
    'api_permission_check',
    'admin_only',
    'resource_owner_or_permission',
    'time_limited_permission'
]