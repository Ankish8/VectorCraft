#!/usr/bin/env python3
"""
Admin Permission Management Routes for VectorCraft
Advanced permission and role management interface
"""

import json
import logging
from datetime import datetime, timedelta
from flask import render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import current_user
import uuid

from . import admin_bp
from middleware import require_permission, require_role, admin_only
from services.permission_manager import permission_manager
from services.role_manager import role_manager
from database import db


logger = logging.getLogger(__name__)


@admin_bp.route('/permissions')
@admin_only('admin')
@require_permission('permission.read')
def permissions_dashboard():
    """Permission management dashboard"""
    try:
        # Get all permissions
        permissions = permission_manager.get_all_permissions()
        roles = permission_manager.get_all_roles()
        
        # Get permission statistics
        with db.get_db_connection() as conn:
            stats = {
                'total_permissions': len(permissions),
                'total_roles': len(roles),
                'active_users': conn.execute('SELECT COUNT(*) FROM users WHERE is_active = 1').fetchone()[0],
                'system_permissions': len([p for p in permissions if p.is_system_permission]),
                'custom_permissions': len([p for p in permissions if not p.is_system_permission]),
                'system_roles': len([r for r in roles if r.is_system_role]),
                'custom_roles': len([r for r in roles if not r.is_system_role])
            }
        
        # Get role permissions matrix
        permissions_matrix = role_manager.get_role_permissions_matrix()
        
        return render_template('admin/permissions/dashboard.html',
                             permissions=permissions,
                             roles=roles,
                             stats=stats,
                             permissions_matrix=permissions_matrix)
    
    except Exception as e:
        logger.error(f"Error loading permissions dashboard: {e}")
        flash("Error loading permissions dashboard", "error")
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/permissions/roles')
@admin_only('admin')
@require_permission('role.read')
def roles_management():
    """Role management interface"""
    try:
        roles = permission_manager.get_all_roles()
        role_hierarchy = role_manager.get_role_hierarchy()
        role_templates = role_manager.get_role_templates()
        
        return render_template('admin/permissions/roles.html',
                             roles=roles,
                             role_hierarchy=role_hierarchy,
                             role_templates=role_templates)
    
    except Exception as e:
        logger.error(f"Error loading roles management: {e}")
        flash("Error loading roles management", "error")
        return redirect(url_for('admin.permissions_dashboard'))


@admin_bp.route('/permissions/users')
@admin_only('admin')
@require_permission('user.read')
def users_permissions():
    """User permissions management"""
    try:
        with db.get_db_connection() as conn:
            users = conn.execute('''
                SELECT u.id, u.username, u.email, u.is_active, u.created_at
                FROM users u
                ORDER BY u.username
            ''').fetchall()
            
            users_data = []
            for user in users:
                user_roles = permission_manager.get_user_roles(user[0])
                user_permissions = permission_manager.get_user_permissions(user[0])
                
                users_data.append({
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'is_active': bool(user[3]),
                    'created_at': user[4],
                    'roles': [{'id': role.id, 'name': role.name, 'description': role.description} for role in user_roles],
                    'permissions_count': len(user_permissions),
                    'roles_count': len(user_roles)
                })
        
        roles = permission_manager.get_all_roles()
        permissions = permission_manager.get_all_permissions()
        
        return render_template('admin/permissions/users.html',
                             users=users_data,
                             roles=roles,
                             permissions=permissions)
    
    except Exception as e:
        logger.error(f"Error loading users permissions: {e}")
        flash("Error loading users permissions", "error")
        return redirect(url_for('admin.permissions_dashboard'))


@admin_bp.route('/permissions/matrix')
@admin_only('admin')
@require_permission('permission.read')
def permissions_matrix():
    """Permission matrix view"""
    try:
        permissions_matrix = role_manager.get_role_permissions_matrix()
        roles = permission_manager.get_all_roles()
        permissions = permission_manager.get_all_permissions()
        
        # Group permissions by resource
        permissions_by_resource = {}
        for perm in permissions:
            resource = perm.resource
            if resource not in permissions_by_resource:
                permissions_by_resource[resource] = []
            permissions_by_resource[resource].append(perm)
        
        return render_template('admin/permissions/matrix.html',
                             permissions_matrix=permissions_matrix,
                             permissions_by_resource=permissions_by_resource,
                             roles=roles)
    
    except Exception as e:
        logger.error(f"Error loading permissions matrix: {e}")
        flash("Error loading permissions matrix", "error")
        return redirect(url_for('admin.permissions_dashboard'))


@admin_bp.route('/permissions/audit')
@admin_only('admin')
@require_permission('permission.read')
def permissions_audit():
    """Permission audit log"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        with db.get_db_connection() as conn:
            # Get total count
            total = conn.execute('SELECT COUNT(*) FROM permission_audit_log').fetchone()[0]
            
            # Get audit log entries
            offset = (page - 1) * per_page
            audit_entries = conn.execute('''
                SELECT pal.*, u1.username as user_name, u2.username as performed_by_name
                FROM permission_audit_log pal
                LEFT JOIN users u1 ON pal.user_id = u1.id
                LEFT JOIN users u2 ON pal.performed_by = u2.id
                ORDER BY pal.performed_at DESC
                LIMIT ? OFFSET ?
            ''', (per_page, offset)).fetchall()
            
            # Get access violations
            violations = conn.execute('''
                SELECT av.*, u.username
                FROM access_violations av
                LEFT JOIN users u ON av.user_id = u.id
                ORDER BY av.blocked_at DESC
                LIMIT 20
            ''').fetchall()
        
        # Calculate pagination
        total_pages = (total + per_page - 1) // per_page
        
        return render_template('admin/permissions/audit.html',
                             audit_entries=audit_entries,
                             violations=violations,
                             page=page,
                             per_page=per_page,
                             total=total,
                             total_pages=total_pages)
    
    except Exception as e:
        logger.error(f"Error loading permissions audit: {e}")
        flash("Error loading permissions audit", "error")
        return redirect(url_for('admin.permissions_dashboard'))


# API Routes for Permission Management

@admin_bp.route('/api/permissions/create', methods=['POST'])
@admin_only('admin')
@require_permission('permission.admin')
def create_permission():
    """Create a new permission"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'description', 'resource', 'action']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create permission
        permission_id = permission_manager.create_permission(
            name=data['name'],
            description=data['description'],
            resource=data['resource'],
            action=data['action']
        )
        
        if permission_id:
            return jsonify({
                'success': True,
                'message': 'Permission created successfully',
                'permission_id': permission_id
            })
        else:
            return jsonify({'error': 'Failed to create permission'}), 500
    
    except Exception as e:
        logger.error(f"Error creating permission: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/roles/create', methods=['POST'])
@admin_only('admin')
@require_permission('role.admin')
def create_role():
    """Create a new role"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'name' not in data or 'description' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Create role
        role_id = permission_manager.create_role(
            name=data['name'],
            description=data['description'],
            parent_role_id=data.get('parent_role_id')
        )
        
        if role_id:
            return jsonify({
                'success': True,
                'message': 'Role created successfully',
                'role_id': role_id
            })
        else:
            return jsonify({'error': 'Failed to create role'}), 500
    
    except Exception as e:
        logger.error(f"Error creating role: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/roles/<int:role_id>/permissions', methods=['POST'])
@admin_only('admin')
@require_permission('role.admin')
def assign_permission_to_role(role_id):
    """Assign permission to role"""
    try:
        data = request.get_json()
        
        if 'permission_id' not in data:
            return jsonify({'error': 'Missing permission_id'}), 400
        
        expires_at = None
        if data.get('expires_at'):
            expires_at = datetime.fromisoformat(data['expires_at'])
        
        success = role_manager.assign_permission_to_role(
            role_id=role_id,
            permission_id=data['permission_id'],
            granted_by=current_user.id,
            expires_at=expires_at
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Permission assigned to role successfully'
            })
        else:
            return jsonify({'error': 'Failed to assign permission to role'}), 500
    
    except Exception as e:
        logger.error(f"Error assigning permission to role: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/roles/<int:role_id>/permissions/<int:permission_id>', methods=['DELETE'])
@admin_only('admin')
@require_permission('role.admin')
def revoke_permission_from_role(role_id, permission_id):
    """Revoke permission from role"""
    try:
        success = role_manager.revoke_permission_from_role(
            role_id=role_id,
            permission_id=permission_id,
            revoked_by=current_user.id
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Permission revoked from role successfully'
            })
        else:
            return jsonify({'error': 'Failed to revoke permission from role'}), 500
    
    except Exception as e:
        logger.error(f"Error revoking permission from role: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/users/<int:user_id>/roles', methods=['POST'])
@admin_only('admin')
@require_permission('user.admin')
def assign_role_to_user(user_id):
    """Assign role to user"""
    try:
        data = request.get_json()
        
        if 'role_id' not in data:
            return jsonify({'error': 'Missing role_id'}), 400
        
        expires_at = None
        if data.get('expires_at'):
            expires_at = datetime.fromisoformat(data['expires_at'])
        
        success = permission_manager.assign_role_to_user(
            user_id=user_id,
            role_id=data['role_id'],
            assigned_by=current_user.id,
            expires_at=expires_at
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Role assigned to user successfully'
            })
        else:
            return jsonify({'error': 'Failed to assign role to user'}), 500
    
    except Exception as e:
        logger.error(f"Error assigning role to user: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/users/<int:user_id>/roles/<int:role_id>', methods=['DELETE'])
@admin_only('admin')
@require_permission('user.admin')
def revoke_role_from_user(user_id, role_id):
    """Revoke role from user"""
    try:
        success = permission_manager.revoke_role_from_user(
            user_id=user_id,
            role_id=role_id,
            revoked_by=current_user.id
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Role revoked from user successfully'
            })
        else:
            return jsonify({'error': 'Failed to revoke role from user'}), 500
    
    except Exception as e:
        logger.error(f"Error revoking role from user: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/users/<int:user_id>/permissions', methods=['POST'])
@admin_only('admin')
@require_permission('user.admin')
def grant_permission_to_user(user_id):
    """Grant direct permission to user"""
    try:
        data = request.get_json()
        
        if 'permission_id' not in data:
            return jsonify({'error': 'Missing permission_id'}), 400
        
        expires_at = None
        if data.get('expires_at'):
            expires_at = datetime.fromisoformat(data['expires_at'])
        
        success = permission_manager.grant_permission_to_user(
            user_id=user_id,
            permission_id=data['permission_id'],
            granted_by=current_user.id,
            expires_at=expires_at
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Permission granted to user successfully'
            })
        else:
            return jsonify({'error': 'Failed to grant permission to user'}), 500
    
    except Exception as e:
        logger.error(f"Error granting permission to user: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/users/<int:user_id>/permissions/<int:permission_id>', methods=['DELETE'])
@admin_only('admin')
@require_permission('user.admin')
def revoke_permission_from_user(user_id, permission_id):
    """Revoke direct permission from user"""
    try:
        success = permission_manager.revoke_permission_from_user(
            user_id=user_id,
            permission_id=permission_id,
            revoked_by=current_user.id
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Permission revoked from user successfully'
            })
        else:
            return jsonify({'error': 'Failed to revoke permission from user'}), 500
    
    except Exception as e:
        logger.error(f"Error revoking permission from user: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/roles/<int:role_id>/clone', methods=['POST'])
@admin_only('admin')
@require_permission('role.admin')
def clone_role(role_id):
    """Clone a role"""
    try:
        data = request.get_json()
        
        if 'name' not in data or 'description' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        new_role_id = role_manager.clone_role(
            source_role_id=role_id,
            new_role_name=data['name'],
            new_role_description=data['description'],
            cloned_by=current_user.id
        )
        
        if new_role_id:
            return jsonify({
                'success': True,
                'message': 'Role cloned successfully',
                'new_role_id': new_role_id
            })
        else:
            return jsonify({'error': 'Failed to clone role'}), 500
    
    except Exception as e:
        logger.error(f"Error cloning role: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/roles/<int:role_id>/hierarchy', methods=['PUT'])
@admin_only('admin')
@require_permission('role.admin')
def update_role_hierarchy(role_id):
    """Update role hierarchy"""
    try:
        data = request.get_json()
        
        new_parent_id = data.get('parent_role_id')
        
        # Validate hierarchy
        if new_parent_id:
            is_valid, message = role_manager.validate_role_hierarchy(role_id, new_parent_id)
            if not is_valid:
                return jsonify({'error': message}), 400
        
        success = role_manager.update_role_hierarchy(
            role_id=role_id,
            new_parent_id=new_parent_id,
            updated_by=current_user.id
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Role hierarchy updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update role hierarchy'}), 500
    
    except Exception as e:
        logger.error(f"Error updating role hierarchy: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/roles/<int:role_id>/effective-permissions')
@admin_only('admin')
@require_permission('role.read')
def get_role_effective_permissions(role_id):
    """Get effective permissions for a role"""
    try:
        effective_permissions = role_manager.get_effective_permissions(role_id)
        
        if effective_permissions:
            return jsonify({
                'success': True,
                'data': effective_permissions
            })
        else:
            return jsonify({'error': 'Role not found'}), 404
    
    except Exception as e:
        logger.error(f"Error getting effective permissions for role: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/users/<int:user_id>/effective-permissions')
@admin_only('admin')
@require_permission('user.read')
def get_user_effective_permissions(user_id):
    """Get effective permissions for a user"""
    try:
        from middleware.permission_middleware import permission_middleware
        
        effective_permissions = permission_middleware.get_user_effective_permissions(user_id)
        
        if effective_permissions:
            return jsonify({
                'success': True,
                'data': effective_permissions
            })
        else:
            return jsonify({'error': 'User not found'}), 404
    
    except Exception as e:
        logger.error(f"Error getting effective permissions for user: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/role-templates/create', methods=['POST'])
@admin_only('admin')
@require_permission('role.admin')
def create_role_template():
    """Create a role template"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'description', 'permissions']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        template_id = role_manager.create_role_template(
            name=data['name'],
            description=data['description'],
            permissions=data['permissions']
        )
        
        if template_id:
            return jsonify({
                'success': True,
                'message': 'Role template created successfully',
                'template_id': template_id
            })
        else:
            return jsonify({'error': 'Failed to create role template'}), 500
    
    except Exception as e:
        logger.error(f"Error creating role template: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/api/role-templates/<template_id>/create-role', methods=['POST'])
@admin_only('admin')
@require_permission('role.admin')
def create_role_from_template(template_id):
    """Create a role from template"""
    try:
        data = request.get_json()
        
        if 'name' not in data:
            return jsonify({'error': 'Missing role name'}), 400
        
        role_id = role_manager.create_role_from_template(
            template_id=template_id,
            role_name=data['name'],
            role_description=data.get('description')
        )
        
        if role_id:
            return jsonify({
                'success': True,
                'message': 'Role created from template successfully',
                'role_id': role_id
            })
        else:
            return jsonify({'error': 'Failed to create role from template'}), 500
    
    except Exception as e:
        logger.error(f"Error creating role from template: {e}")
        return jsonify({'error': 'Internal server error'}), 500