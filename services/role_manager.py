#!/usr/bin/env python3
"""
Role Management Service for VectorCraft
Manages hierarchical roles and role inheritance
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

from database import db
from services.permission_manager import Permission, Role, permission_manager


class RoleType(Enum):
    """Role type classification"""
    SYSTEM = "system"
    CUSTOM = "custom"
    TEMPLATE = "template"


@dataclass
class RoleTemplate:
    """Role template data structure"""
    id: int
    name: str
    description: str
    permissions: List[str]
    is_active: bool = True
    created_at: datetime = None


@dataclass
class RoleHierarchy:
    """Role hierarchy data structure"""
    role_id: int
    role_name: str
    parent_role_id: Optional[int]
    parent_role_name: Optional[str]
    children: List['RoleHierarchy']
    level: int
    permissions: Set[str]


class RoleManager:
    """Advanced role management with hierarchical support"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.permission_manager = permission_manager
        self._role_hierarchy_cache = {}
        self._cache_timeout = 300  # 5 minutes
    
    def create_role_template(self, name: str, description: str, permissions: List[str]) -> Optional[int]:
        """Create a role template for common user types"""
        template_id = str(uuid.uuid4())
        
        try:
            with db.get_db_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO role_templates (template_id, name, description, permissions)
                    VALUES (?, ?, ?, ?)
                ''', (template_id, name, description, json.dumps(permissions)))
                
                template_db_id = cursor.lastrowid
                conn.commit()
                
                self.logger.info(f"Created role template: {name} with {len(permissions)} permissions")
                return template_db_id
                
        except Exception as e:
            self.logger.error(f"Error creating role template {name}: {e}")
            return None
    
    def create_role_from_template(self, template_id: str, role_name: str, role_description: str = None) -> Optional[int]:
        """Create a new role from a template"""
        try:
            with db.get_db_connection() as conn:
                # Get template
                template = conn.execute('''
                    SELECT name, description, permissions FROM role_templates
                    WHERE template_id = ? AND is_active = 1
                ''', (template_id,)).fetchone()
                
                if not template:
                    self.logger.error(f"Role template {template_id} not found")
                    return None
                
                template_name, template_desc, permissions_json = template
                permissions = json.loads(permissions_json) if permissions_json else []
                
                # Create role
                role_id = self.permission_manager.create_role(
                    name=role_name,
                    description=role_description or template_desc
                )
                
                if not role_id:
                    return None
                
                # Assign permissions from template
                for perm_name in permissions:
                    perm_id = self.permission_manager._get_permission_id_by_name(perm_name)
                    if perm_id:
                        conn.execute('''
                            INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                            VALUES (?, ?)
                        ''', (role_id, perm_id))
                
                conn.commit()
                
                self.logger.info(f"Created role {role_name} from template {template_name}")
                return role_id
                
        except Exception as e:
            self.logger.error(f"Error creating role from template {template_id}: {e}")
            return None
    
    def get_role_hierarchy(self, role_id: int = None) -> Dict[str, Any]:
        """Get complete role hierarchy or specific role hierarchy"""
        cache_key = f"role_hierarchy_{role_id or 'all'}"
        cached_hierarchy = self._get_from_cache(cache_key)
        
        if cached_hierarchy:
            return cached_hierarchy
        
        try:
            with db.get_db_connection() as conn:
                if role_id:
                    # Get specific role hierarchy
                    roles_data = conn.execute('''
                        WITH RECURSIVE role_hierarchy AS (
                            SELECT id, name, parent_role_id, 0 as level
                            FROM roles
                            WHERE id = ?
                            UNION ALL
                            SELECT r.id, r.name, r.parent_role_id, rh.level + 1
                            FROM roles r
                            JOIN role_hierarchy rh ON r.parent_role_id = rh.id
                        )
                        SELECT * FROM role_hierarchy
                    ''', (role_id,)).fetchall()
                else:
                    # Get all roles hierarchy
                    roles_data = conn.execute('''
                        SELECT id, name, parent_role_id, 0 as level
                        FROM roles
                        WHERE is_active = 1
                        ORDER BY name
                    ''').fetchall()
                
                hierarchy = self._build_role_hierarchy(roles_data)
                
                # Cache the result
                self._set_cache(cache_key, hierarchy)
                
                return hierarchy
                
        except Exception as e:
            self.logger.error(f"Error getting role hierarchy: {e}")
            return {}
    
    def _build_role_hierarchy(self, roles_data: List[tuple]) -> Dict[str, Any]:
        """Build hierarchical structure from roles data"""
        roles_dict = {}
        root_roles = []
        
        # First pass: create role objects
        for role_data in roles_data:
            role_id, name, parent_role_id, level = role_data
            
            # Get role permissions
            permissions = self._get_role_permissions(role_id)
            
            role_hierarchy = RoleHierarchy(
                role_id=role_id,
                role_name=name,
                parent_role_id=parent_role_id,
                parent_role_name=None,
                children=[],
                level=level,
                permissions=permissions
            )
            
            roles_dict[role_id] = role_hierarchy
            
            if not parent_role_id:
                root_roles.append(role_hierarchy)
        
        # Second pass: build parent-child relationships
        for role_id, role_hierarchy in roles_dict.items():
            if role_hierarchy.parent_role_id:
                parent_role = roles_dict.get(role_hierarchy.parent_role_id)
                if parent_role:
                    parent_role.children.append(role_hierarchy)
                    role_hierarchy.parent_role_name = parent_role.role_name
        
        return {
            "root_roles": [asdict(role) for role in root_roles],
            "all_roles": {role_id: asdict(role) for role_id, role in roles_dict.items()}
        }
    
    def _get_role_permissions(self, role_id: int) -> Set[str]:
        """Get all permissions for a role (including inherited)"""
        permissions = set()
        
        try:
            with db.get_db_connection() as conn:
                # Get direct permissions
                direct_permissions = conn.execute('''
                    SELECT p.name FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    WHERE rp.role_id = ?
                    AND (rp.expires_at IS NULL OR rp.expires_at > datetime('now'))
                ''', (role_id,)).fetchall()
                
                permissions.update([perm[0] for perm in direct_permissions])
                
                # Get inherited permissions from parent roles
                inherited_permissions = self._get_inherited_role_permissions(role_id)
                permissions.update(inherited_permissions)
                
        except Exception as e:
            self.logger.error(f"Error getting permissions for role {role_id}: {e}")
        
        return permissions
    
    def _get_inherited_role_permissions(self, role_id: int) -> Set[str]:
        """Get permissions inherited from parent roles"""
        permissions = set()
        
        try:
            with db.get_db_connection() as conn:
                # Get parent role
                parent_role = conn.execute('''
                    SELECT parent_role_id FROM roles WHERE id = ?
                ''', (role_id,)).fetchone()
                
                if parent_role and parent_role[0]:
                    parent_role_id = parent_role[0]
                    
                    # Get parent permissions
                    parent_permissions = self._get_role_permissions(parent_role_id)
                    permissions.update(parent_permissions)
                    
        except Exception as e:
            self.logger.error(f"Error getting inherited permissions for role {role_id}: {e}")
        
        return permissions
    
    def assign_permission_to_role(self, role_id: int, permission_id: int, granted_by: int, expires_at: Optional[datetime] = None) -> bool:
        """Assign a permission to a role"""
        try:
            with db.get_db_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO role_permissions (role_id, permission_id, granted_by, expires_at)
                    VALUES (?, ?, ?, ?)
                ''', (role_id, permission_id, granted_by, expires_at))
                
                conn.commit()
                
                # Clear cache
                self._clear_cache()
                
                # Log the assignment
                self.permission_manager._log_permission_audit(
                    user_id=granted_by,
                    action="assign_permission_to_role",
                    resource_type="role_permission",
                    resource_id=role_id,
                    new_value=json.dumps({"role_id": role_id, "permission_id": permission_id}),
                    performed_by=granted_by
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error assigning permission {permission_id} to role {role_id}: {e}")
            return False
    
    def revoke_permission_from_role(self, role_id: int, permission_id: int, revoked_by: int) -> bool:
        """Revoke a permission from a role"""
        try:
            with db.get_db_connection() as conn:
                conn.execute('''
                    DELETE FROM role_permissions
                    WHERE role_id = ? AND permission_id = ?
                ''', (role_id, permission_id))
                
                conn.commit()
                
                # Clear cache
                self._clear_cache()
                
                # Log the revocation
                self.permission_manager._log_permission_audit(
                    user_id=revoked_by,
                    action="revoke_permission_from_role",
                    resource_type="role_permission",
                    resource_id=role_id,
                    old_value=json.dumps({"role_id": role_id, "permission_id": permission_id}),
                    performed_by=revoked_by
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error revoking permission {permission_id} from role {role_id}: {e}")
            return False
    
    def clone_role(self, source_role_id: int, new_role_name: str, new_role_description: str, cloned_by: int) -> Optional[int]:
        """Clone a role with all its permissions"""
        try:
            with db.get_db_connection() as conn:
                # Get source role
                source_role = conn.execute('''
                    SELECT name, description, parent_role_id FROM roles
                    WHERE id = ? AND is_active = 1
                ''', (source_role_id,)).fetchone()
                
                if not source_role:
                    self.logger.error(f"Source role {source_role_id} not found")
                    return None
                
                # Create new role
                new_role_id = self.permission_manager.create_role(
                    name=new_role_name,
                    description=new_role_description,
                    parent_role_id=source_role[2]
                )
                
                if not new_role_id:
                    return None
                
                # Copy permissions
                conn.execute('''
                    INSERT INTO role_permissions (role_id, permission_id, granted_by)
                    SELECT ?, permission_id, ?
                    FROM role_permissions
                    WHERE role_id = ?
                ''', (new_role_id, cloned_by, source_role_id))
                
                conn.commit()
                
                # Clear cache
                self._clear_cache()
                
                self.logger.info(f"Cloned role {source_role[0]} to {new_role_name}")
                return new_role_id
                
        except Exception as e:
            self.logger.error(f"Error cloning role {source_role_id}: {e}")
            return None
    
    def get_role_templates(self) -> List[RoleTemplate]:
        """Get all available role templates"""
        try:
            with db.get_db_connection() as conn:
                templates_data = conn.execute('''
                    SELECT id, name, description, permissions, is_active, created_at
                    FROM role_templates
                    WHERE is_active = 1
                    ORDER BY name
                ''').fetchall()
                
                return [RoleTemplate(
                    id=template[0],
                    name=template[1],
                    description=template[2],
                    permissions=json.loads(template[3]) if template[3] else [],
                    is_active=bool(template[4]),
                    created_at=datetime.fromisoformat(template[5]) if template[5] else None
                ) for template in templates_data]
                
        except Exception as e:
            self.logger.error(f"Error getting role templates: {e}")
            return []
    
    def get_role_permissions_matrix(self) -> Dict[str, Any]:
        """Get a matrix of roles and their permissions"""
        try:
            roles = self.permission_manager.get_all_roles()
            permissions = self.permission_manager.get_all_permissions()
            
            matrix = {}
            
            for role in roles:
                role_permissions = self._get_role_permissions(role.id)
                matrix[role.name] = {
                    "role_id": role.id,
                    "description": role.description,
                    "is_system_role": role.is_system_role,
                    "permissions": list(role_permissions)
                }
            
            return {
                "roles": matrix,
                "all_permissions": [perm.name for perm in permissions]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting role permissions matrix: {e}")
            return {}
    
    def validate_role_hierarchy(self, role_id: int, proposed_parent_id: int) -> Tuple[bool, str]:
        """Validate if a role hierarchy change would create a cycle"""
        try:
            # Check if proposed parent is a descendant of the role
            if self._is_descendant(role_id, proposed_parent_id):
                return False, "Cannot set parent role as it would create a circular dependency"
            
            # Check if role exists
            with db.get_db_connection() as conn:
                role_exists = conn.execute('''
                    SELECT 1 FROM roles WHERE id = ? AND is_active = 1
                ''', (role_id,)).fetchone()
                
                parent_exists = conn.execute('''
                    SELECT 1 FROM roles WHERE id = ? AND is_active = 1
                ''', (proposed_parent_id,)).fetchone()
                
                if not role_exists:
                    return False, "Role does not exist"
                
                if not parent_exists:
                    return False, "Parent role does not exist"
            
            return True, "Valid hierarchy"
            
        except Exception as e:
            self.logger.error(f"Error validating role hierarchy: {e}")
            return False, "Error validating hierarchy"
    
    def _is_descendant(self, role_id: int, potential_descendant_id: int) -> bool:
        """Check if a role is a descendant of another role"""
        try:
            with db.get_db_connection() as conn:
                # Get all children of the role
                children = conn.execute('''
                    WITH RECURSIVE role_children AS (
                        SELECT id, parent_role_id
                        FROM roles
                        WHERE parent_role_id = ?
                        UNION ALL
                        SELECT r.id, r.parent_role_id
                        FROM roles r
                        JOIN role_children rc ON r.parent_role_id = rc.id
                    )
                    SELECT id FROM role_children
                ''', (role_id,)).fetchall()
                
                descendant_ids = [child[0] for child in children]
                return potential_descendant_id in descendant_ids
                
        except Exception as e:
            self.logger.error(f"Error checking if role {potential_descendant_id} is descendant of {role_id}: {e}")
            return False
    
    def update_role_hierarchy(self, role_id: int, new_parent_id: Optional[int], updated_by: int) -> bool:
        """Update role hierarchy"""
        try:
            # Validate hierarchy
            if new_parent_id:
                is_valid, message = self.validate_role_hierarchy(role_id, new_parent_id)
                if not is_valid:
                    self.logger.error(f"Invalid hierarchy update: {message}")
                    return False
            
            with db.get_db_connection() as conn:
                # Get old parent for audit
                old_parent = conn.execute('''
                    SELECT parent_role_id FROM roles WHERE id = ?
                ''', (role_id,)).fetchone()
                
                # Update parent
                conn.execute('''
                    UPDATE roles 
                    SET parent_role_id = ?, updated_at = datetime('now')
                    WHERE id = ?
                ''', (new_parent_id, role_id))
                
                conn.commit()
                
                # Clear cache
                self._clear_cache()
                
                # Log the update
                self.permission_manager._log_permission_audit(
                    user_id=updated_by,
                    action="update_role_hierarchy",
                    resource_type="role",
                    resource_id=role_id,
                    old_value=json.dumps({"parent_role_id": old_parent[0] if old_parent else None}),
                    new_value=json.dumps({"parent_role_id": new_parent_id}),
                    performed_by=updated_by
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error updating role hierarchy for role {role_id}: {e}")
            return False
    
    def get_effective_permissions(self, role_id: int) -> Dict[str, Any]:
        """Get effective permissions for a role including inherited permissions"""
        try:
            direct_permissions = set()
            inherited_permissions = set()
            
            with db.get_db_connection() as conn:
                # Get direct permissions
                direct_perms = conn.execute('''
                    SELECT p.name, p.description, p.resource, p.action
                    FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    WHERE rp.role_id = ?
                    AND (rp.expires_at IS NULL OR rp.expires_at > datetime('now'))
                ''', (role_id,)).fetchall()
                
                for perm in direct_perms:
                    direct_permissions.add(perm[0])
                
                # Get inherited permissions
                inherited_perms = self._get_inherited_role_permissions(role_id)
                inherited_permissions.update(inherited_perms)
                
                # Get role info
                role_info = conn.execute('''
                    SELECT name, description, parent_role_id FROM roles WHERE id = ?
                ''', (role_id,)).fetchone()
                
                if not role_info:
                    return {}
                
                role_name, role_description, parent_role_id = role_info
                
                return {
                    "role_id": role_id,
                    "role_name": role_name,
                    "role_description": role_description,
                    "parent_role_id": parent_role_id,
                    "direct_permissions": list(direct_permissions),
                    "inherited_permissions": list(inherited_permissions - direct_permissions),
                    "all_permissions": list(direct_permissions | inherited_permissions),
                    "permissions_count": {
                        "direct": len(direct_permissions),
                        "inherited": len(inherited_permissions - direct_permissions),
                        "total": len(direct_permissions | inherited_permissions)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error getting effective permissions for role {role_id}: {e}")
            return {}
    
    def _get_from_cache(self, key: str) -> Any:
        """Get value from cache if valid"""
        if key in self._role_hierarchy_cache:
            cached_data, timestamp = self._role_hierarchy_cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self._cache_timeout):
                return cached_data
        return None
    
    def _set_cache(self, key: str, value: Any):
        """Set value in cache"""
        self._role_hierarchy_cache[key] = (value, datetime.now())
    
    def _clear_cache(self):
        """Clear all role caches"""
        self._role_hierarchy_cache.clear()


# Global instance
role_manager = RoleManager()