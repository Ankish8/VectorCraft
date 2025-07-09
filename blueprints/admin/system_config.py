#!/usr/bin/env python3
"""
Admin System Configuration Routes for VectorCraft
Handles system configuration management interface
"""

import json
import logging
from flask import render_template, request, jsonify, redirect, url_for, flash, session
from functools import wraps
from datetime import datetime

from . import admin_bp
from services.system_config_manager import system_config_manager
from services.auth_service import require_admin_auth

logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/system-config')
@admin_required
def system_config():
    """Main system configuration page"""
    try:
        # Get configuration summary
        summary = system_config_manager.get_configuration_summary()
        
        # Get all configurations
        paypal_config = system_config_manager.get_paypal_config()
        email_config = system_config_manager.get_email_config()
        system_config = system_config_manager.get_system_config()
        api_keys = system_config_manager.get_api_keys()
        database_config = system_config_manager.get_database_config()
        
        return render_template('admin/system_config.html',
                             summary=summary,
                             paypal_config=paypal_config,
                             email_config=email_config,
                             system_config=system_config,
                             api_keys=api_keys,
                             database_config=database_config)
        
    except Exception as e:
        logger.error(f"Failed to load system configuration: {e}")
        flash(f"Failed to load system configuration: {str(e)}", 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/system-config/paypal', methods=['GET', 'POST'])
@admin_required
def paypal_config():
    """PayPal configuration management"""
    if request.method == 'GET':
        try:
            config = system_config_manager.get_paypal_config()
            return jsonify({'success': True, 'data': config})
        except Exception as e:
            logger.error(f"Failed to get PayPal config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Get admin user from session
            admin_user = session.get('admin_user', 'admin')
            
            result = system_config_manager.update_paypal_config(data, changed_by=admin_user)
            
            if result.success:
                return jsonify({
                    'success': True, 
                    'message': result.message,
                    'data': result.data
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': result.message,
                    'errors': result.errors
                }), 400
                
        except Exception as e:
            logger.error(f"Failed to update PayPal config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/system-config/paypal/test', methods=['POST'])
@admin_required
def test_paypal_connection():
    """Test PayPal API connection"""
    try:
        result = system_config_manager.test_paypal_connection()
        
        if result.success:
            return jsonify({
                'success': True, 
                'message': result.message,
                'data': result.data
            })
        else:
            return jsonify({
                'success': False, 
                'message': result.message,
                'errors': result.errors
            }), 400
            
    except Exception as e:
        logger.error(f"PayPal connection test failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/system-config/email', methods=['GET', 'POST'])
@admin_required
def email_config():
    """Email configuration management"""
    if request.method == 'GET':
        try:
            config = system_config_manager.get_email_config()
            return jsonify({'success': True, 'data': config})
        except Exception as e:
            logger.error(f"Failed to get Email config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Get admin user from session
            admin_user = session.get('admin_user', 'admin')
            
            result = system_config_manager.update_email_config(data, changed_by=admin_user)
            
            if result.success:
                return jsonify({
                    'success': True, 
                    'message': result.message,
                    'data': result.data
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': result.message,
                    'errors': result.errors
                }), 400
                
        except Exception as e:
            logger.error(f"Failed to update Email config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/system-config/email/test', methods=['POST'])
@admin_required
def test_email_connection():
    """Test Email SMTP connection"""
    try:
        result = system_config_manager.test_email_connection()
        
        if result.success:
            return jsonify({
                'success': True, 
                'message': result.message,
                'data': result.data
            })
        else:
            return jsonify({
                'success': False, 
                'message': result.message,
                'errors': result.errors
            }), 400
            
    except Exception as e:
        logger.error(f"Email connection test failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/system-config/system', methods=['GET', 'POST'])
@admin_required
def system_environment_config():
    """System environment configuration management"""
    if request.method == 'GET':
        try:
            config = system_config_manager.get_system_config()
            return jsonify({'success': True, 'data': config})
        except Exception as e:
            logger.error(f"Failed to get System config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Get admin user from session
            admin_user = session.get('admin_user', 'admin')
            
            result = system_config_manager.update_system_config(data, changed_by=admin_user)
            
            if result.success:
                return jsonify({
                    'success': True, 
                    'message': result.message,
                    'data': result.data
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': result.message,
                    'errors': result.errors
                }), 400
                
        except Exception as e:
            logger.error(f"Failed to update System config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/system-config/api-keys', methods=['GET'])
@admin_required
def get_api_keys():
    """Get API keys configuration"""
    try:
        api_keys = system_config_manager.get_api_keys()
        return jsonify({'success': True, 'data': api_keys})
    except Exception as e:
        logger.error(f"Failed to get API keys: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/system-config/api-keys', methods=['POST'])
@admin_required
def add_api_key():
    """Add new API key"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        key_name = data.get('key_name', '').strip()
        key_value = data.get('key_value', '').strip()
        description = data.get('description', '').strip()
        
        if not key_name or not key_value:
            return jsonify({'success': False, 'message': 'Key name and value are required'}), 400
        
        # Get admin user from session
        admin_user = session.get('admin_user', 'admin')
        
        result = system_config_manager.add_api_key(key_name, key_value, description, changed_by=admin_user)
        
        if result.success:
            return jsonify({
                'success': True, 
                'message': result.message,
                'data': result.data
            })
        else:
            return jsonify({
                'success': False, 
                'message': result.message,
                'errors': result.errors
            }), 400
            
    except Exception as e:
        logger.error(f"Failed to add API key: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/system-config/api-keys/<key_name>', methods=['DELETE'])
@admin_required
def delete_api_key(key_name):
    """Delete API key"""
    try:
        # Get admin user from session
        admin_user = session.get('admin_user', 'admin')
        
        result = system_config_manager.delete_api_key(key_name, changed_by=admin_user)
        
        if result.success:
            return jsonify({
                'success': True, 
                'message': result.message
            })
        else:
            return jsonify({
                'success': False, 
                'message': result.message,
                'errors': result.errors
            }), 400
            
    except Exception as e:
        logger.error(f"Failed to delete API key: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/system-config/database', methods=['GET'])
@admin_required
def get_database_config():
    """Get database configuration"""
    try:
        config = system_config_manager.get_database_config()
        return jsonify({'success': True, 'data': config})
    except Exception as e:
        logger.error(f"Failed to get Database config: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/system-config/export', methods=['GET'])
@admin_required
def export_configuration():
    """Export system configuration"""
    try:
        categories = request.args.getlist('categories')
        include_sensitive = request.args.get('include_sensitive', 'false').lower() == 'true'
        
        export_data = system_config_manager.export_configuration(
            categories if categories else None,
            include_sensitive
        )
        
        return jsonify({'success': True, 'data': export_data})
        
    except Exception as e:
        logger.error(f"Failed to export configuration: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/system-config/summary', methods=['GET'])
@admin_required
def configuration_summary():
    """Get configuration summary"""
    try:
        summary = system_config_manager.get_configuration_summary()
        return jsonify({'success': True, 'data': summary})
    except Exception as e:
        logger.error(f"Failed to get configuration summary: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/system-config/feature-flags', methods=['GET', 'POST'])
@admin_required
def feature_flags():
    """Feature flags management"""
    if request.method == 'GET':
        try:
            config = system_config_manager.get_system_config()
            feature_flags = config.get('feature_flags', {}).get('value', {})
            return jsonify({'success': True, 'data': feature_flags})
        except Exception as e:
            logger.error(f"Failed to get feature flags: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Get admin user from session
            admin_user = session.get('admin_user', 'admin')
            
            # Update feature flags
            result = system_config_manager.update_system_config(
                {'feature_flags': data}, 
                changed_by=admin_user
            )
            
            if result.success:
                return jsonify({
                    'success': True, 
                    'message': result.message,
                    'data': result.data
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': result.message,
                    'errors': result.errors
                }), 400
                
        except Exception as e:
            logger.error(f"Failed to update feature flags: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/system-config/health', methods=['GET'])
@admin_required
def system_health():
    """Get system health status"""
    try:
        health_status = {
            'database': system_config_manager._test_database_connection(),
            'paypal': False,
            'email': False,
            'timestamp': datetime.now().isoformat()
        }
        
        # Test PayPal connection
        paypal_result = system_config_manager.test_paypal_connection()
        health_status['paypal'] = paypal_result.success
        
        # Test Email connection
        email_result = system_config_manager.test_email_connection()
        health_status['email'] = email_result.success
        
        # Overall health
        health_status['overall'] = all([
            health_status['database'],
            health_status['paypal'],
            health_status['email']
        ])
        
        return jsonify({'success': True, 'data': health_status})
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500