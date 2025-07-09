#!/usr/bin/env python3
"""
Admin System Control Routes
Provides API endpoints for live system control functionality
"""

from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from functools import wraps
import json
from datetime import datetime
from services.system_controller import system_controller
from services.feature_flags import feature_flags, FeatureStatus, RolloutStrategy
from services.deployment_manager import deployment_manager, DeploymentStrategy, ReleaseStage
from services.monitoring.health_monitor import health_monitor
from services.monitoring.system_logger import system_logger
from services.monitoring.alert_manager import alert_manager

# Import admin blueprint
from . import admin_bp

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_admin_user():
    """Get current admin user from session"""
    return session.get('admin_username', 'unknown')

def api_response(success=True, data=None, error=None, message=None):
    """Standardized API response format"""
    response = {
        'success': success,
        'timestamp': datetime.now().isoformat()
    }
    
    if data is not None:
        response['data'] = data
    if error:
        response['error'] = error
    if message:
        response['message'] = message
    
    return jsonify(response)

# Main System Control Dashboard
@admin_bp.route('/system-control')
@admin_required
def system_control():
    """Main system control dashboard"""
    return render_template('admin/system_control.html')

# System State Management
@admin_bp.route('/system-control/api/system-state')
@admin_required
def get_system_state():
    """Get current system state"""
    try:
        state = system_controller.get_system_state()
        return api_response(data=state)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/maintenance-mode', methods=['POST'])
@admin_required
def set_maintenance_mode():
    """Toggle maintenance mode"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        message = data.get('message', 'System is temporarily unavailable for maintenance.')
        
        result = system_controller.set_maintenance_mode(
            enabled=enabled,
            message=message,
            admin_user=get_admin_user()
        )
        
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/maintenance-status')
@admin_required
def get_maintenance_status():
    """Get maintenance mode status"""
    try:
        status = system_controller.get_maintenance_status()
        return api_response(data=status)
    except Exception as e:
        return api_response(success=False, error=str(e))

# Health Override Controls
@admin_bp.route('/system-control/api/health-override', methods=['POST'])
@admin_required
def override_health():
    """Override system health status"""
    try:
        data = request.get_json()
        status = data.get('status')
        reason = data.get('reason', '')
        
        result = system_controller.override_system_health(
            status=status,
            reason=reason,
            admin_user=get_admin_user()
        )
        
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/health-override', methods=['DELETE'])
@admin_required
def clear_health_override():
    """Clear health status override"""
    try:
        result = system_controller.clear_health_override(admin_user=get_admin_user())
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

# Emergency Controls
@admin_bp.route('/system-control/api/emergency-shutdown', methods=['POST'])
@admin_required
def emergency_shutdown():
    """Emergency system shutdown"""
    try:
        data = request.get_json()
        reason = data.get('reason', 'Emergency shutdown requested')
        
        result = system_controller.emergency_shutdown(
            reason=reason,
            admin_user=get_admin_user()
        )
        
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/rolling-restart', methods=['POST'])
@admin_required
def rolling_restart():
    """Perform rolling restart"""
    try:
        data = request.get_json()
        reason = data.get('reason', 'Rolling restart requested')
        
        result = system_controller.rolling_restart(
            reason=reason,
            admin_user=get_admin_user()
        )
        
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

# Traffic Control
@admin_bp.route('/system-control/api/traffic-control', methods=['POST'])
@admin_required
def set_traffic_control():
    """Set traffic control parameters"""
    try:
        data = request.get_json()
        rate_limit = data.get('rate_limit')
        max_concurrent = data.get('max_concurrent')
        
        result = system_controller.set_traffic_control(
            rate_limit=rate_limit,
            max_concurrent=max_concurrent,
            admin_user=get_admin_user()
        )
        
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/traffic-stats')
@admin_required
def get_traffic_stats():
    """Get traffic statistics"""
    try:
        stats = system_controller.get_traffic_stats()
        return api_response(data=stats)
    except Exception as e:
        return api_response(success=False, error=str(e))

# System Metrics
@admin_bp.route('/system-control/api/system-metrics')
@admin_required
def get_system_metrics():
    """Get system performance metrics"""
    try:
        metrics = system_controller.get_system_metrics()
        return api_response(data=metrics)
    except Exception as e:
        return api_response(success=False, error=str(e))

# Configuration Management
@admin_bp.route('/system-control/api/system-config')
@admin_required
def get_system_config():
    """Get system configuration"""
    try:
        config = system_controller.get_system_config()
        return api_response(data=config)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/system-config', methods=['POST'])
@admin_required
def update_system_config():
    """Update system configuration"""
    try:
        data = request.get_json()
        config = data.get('config', {})
        
        result = system_controller.update_system_config(
            config=config,
            admin_user=get_admin_user()
        )
        
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

# Feature Flag Management
@admin_bp.route('/system-control/api/feature-flags')
@admin_required
def get_feature_flags():
    """Get all feature flags"""
    try:
        flags = feature_flags.get_all_feature_flags()
        # Convert enums to strings for JSON serialization
        serializable_flags = {}
        for name, flag in flags.items():
            serializable_flags[name] = {
                'name': flag['name'],
                'description': flag['description'],
                'status': flag['status'].value,
                'rollout_strategy': flag['rollout_strategy'].value,
                'rollout_percentage': flag['rollout_percentage'],
                'target_users': flag['target_users'],
                'beta_users': flag['beta_users'],
                'dependencies': flag['dependencies'],
                'metadata': flag['metadata']
            }
        
        return api_response(data=serializable_flags)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/feature-flags', methods=['POST'])
@admin_required
def create_feature_flag():
    """Create a new feature flag"""
    try:
        data = request.get_json()
        
        result = feature_flags.create_feature_flag(
            name=data['name'],
            description=data.get('description', ''),
            status=FeatureStatus(data.get('status', 'disabled')),
            rollout_strategy=RolloutStrategy(data.get('rollout_strategy', 'all_users')),
            rollout_percentage=data.get('rollout_percentage', 0),
            target_users=data.get('target_users', []),
            beta_users=data.get('beta_users', []),
            dependencies=data.get('dependencies', []),
            user=get_admin_user()
        )
        
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/feature-flags/<feature_name>', methods=['PUT'])
@admin_required
def update_feature_flag(feature_name):
    """Update a feature flag"""
    try:
        data = request.get_json()
        data['user'] = get_admin_user()
        
        result = feature_flags.update_feature_flag(feature_name, **data)
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/feature-flags/<feature_name>', methods=['DELETE'])
@admin_required
def delete_feature_flag(feature_name):
    """Delete a feature flag"""
    try:
        result = feature_flags.delete_feature_flag(feature_name, user=get_admin_user())
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/feature-flags/<feature_name>/emergency-disable', methods=['POST'])
@admin_required
def emergency_disable_feature(feature_name):
    """Emergency disable a feature flag"""
    try:
        data = request.get_json()
        reason = data.get('reason', 'Emergency disable requested')
        
        result = feature_flags.emergency_disable_feature(
            feature_name=feature_name,
            user=get_admin_user(),
            reason=reason
        )
        
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/feature-flags/<feature_name>/usage-stats')
@admin_required
def get_feature_usage_stats(feature_name):
    """Get feature usage statistics"""
    try:
        stats = feature_flags.get_feature_usage_stats(feature_name)
        return api_response(data=stats)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/feature-flags/<feature_name>/history')
@admin_required
def get_feature_history(feature_name):
    """Get feature flag history"""
    try:
        history = feature_flags.get_feature_history(feature_name)
        return api_response(data=history)
    except Exception as e:
        return api_response(success=False, error=str(e))

# Deployment Management
@admin_bp.route('/system-control/api/releases')
@admin_required
def get_releases():
    """Get all releases"""
    try:
        # This would need to be implemented in deployment_manager
        return api_response(data=[])
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/releases', methods=['POST'])
@admin_required
def create_release():
    """Create a new release"""
    try:
        data = request.get_json()
        
        result = deployment_manager.create_release(
            version=data['version'],
            name=data.get('name'),
            description=data.get('description'),
            changelog=data.get('changelog'),
            stage=ReleaseStage(data.get('stage', 'development')),
            user=get_admin_user()
        )
        
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/deployments')
@admin_required
def get_deployments():
    """Get deployment history"""
    try:
        history = deployment_manager.get_deployment_history(limit=50)
        return api_response(data=history)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/deployments/active')
@admin_required
def get_active_deployments():
    """Get active deployments"""
    try:
        deployments = deployment_manager.get_active_deployments()
        # Convert enums to strings for JSON serialization
        serializable_deployments = []
        for deployment in deployments:
            serializable_deployments.append({
                'deployment_id': deployment['deployment_id'],
                'version': deployment['version'],
                'strategy': deployment['strategy'].value,
                'stage': deployment['stage'].value,
                'status': deployment['status'].value,
                'progress': deployment['progress'],
                'started_by': deployment['started_by'],
                'started_at': deployment['started_at'],
                'metadata': deployment['metadata']
            })
        
        return api_response(data=serializable_deployments)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/deployments', methods=['POST'])
@admin_required
def start_deployment():
    """Start a new deployment"""
    try:
        data = request.get_json()
        
        result = deployment_manager.start_deployment(
            version=data['version'],
            strategy=DeploymentStrategy(data.get('strategy', 'blue_green')),
            stage=ReleaseStage(data.get('stage', 'staging')),
            config=data.get('config', {}),
            user=get_admin_user()
        )
        
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/deployments/<deployment_id>')
@admin_required
def get_deployment_status(deployment_id):
    """Get deployment status"""
    try:
        status = deployment_manager.get_deployment_status(deployment_id)
        if status:
            # Convert enums to strings for JSON serialization
            serializable_status = {
                'deployment_id': status['deployment_id'],
                'version': status['version'],
                'strategy': status['strategy'].value,
                'stage': status['stage'].value,
                'status': status['status'].value,
                'progress': status['progress'],
                'started_by': status['started_by'],
                'started_at': status['started_at'],
                'metadata': status['metadata']
            }
            return api_response(data=serializable_status)
        else:
            return api_response(success=False, error="Deployment not found")
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/deployments/<deployment_id>/logs')
@admin_required
def get_deployment_logs(deployment_id):
    """Get deployment logs"""
    try:
        logs = deployment_manager.get_deployment_logs(deployment_id)
        return api_response(data=logs)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/deployments/<deployment_id>/cancel', methods=['POST'])
@admin_required
def cancel_deployment(deployment_id):
    """Cancel a deployment"""
    try:
        result = deployment_manager.cancel_deployment(deployment_id, user=get_admin_user())
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/deployments/<deployment_id>/rollback', methods=['POST'])
@admin_required
def rollback_deployment(deployment_id):
    """Rollback a deployment"""
    try:
        result = deployment_manager.rollback_deployment(deployment_id, user=get_admin_user())
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

# Health Monitoring
@admin_bp.route('/system-control/api/health-status')
@admin_required
def get_health_status():
    """Get system health status"""
    try:
        status = health_monitor.get_overall_status()
        return api_response(data=status)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/health-check', methods=['POST'])
@admin_required
def run_health_check():
    """Run health check on all components"""
    try:
        results = health_monitor.check_all_components()
        return api_response(data=results)
    except Exception as e:
        return api_response(success=False, error=str(e))

# Alert Management
@admin_bp.route('/system-control/api/alerts')
@admin_required
def get_alerts():
    """Get system alerts"""
    try:
        alerts = alert_manager.get_recent_alerts(limit=100)
        return api_response(data=alerts)
    except Exception as e:
        return api_response(success=False, error=str(e))

@admin_bp.route('/system-control/api/alerts/<alert_id>/acknowledge', methods=['POST'])
@admin_required
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    try:
        result = alert_manager.acknowledge_alert(alert_id, user=get_admin_user())
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

# WebSocket endpoint for real-time updates
@admin_bp.route('/system-control/api/realtime-status')
@admin_required
def get_realtime_status():
    """Get real-time system status for dashboard updates"""
    try:
        status = {
            'system_state': system_controller.get_system_state(),
            'health_status': health_monitor.get_overall_status(),
            'active_deployments': len(deployment_manager.get_active_deployments()),
            'traffic_stats': system_controller.get_traffic_stats(),
            'system_metrics': system_controller.get_system_metrics(),
            'timestamp': datetime.now().isoformat()
        }
        
        return api_response(data=status)
    except Exception as e:
        return api_response(success=False, error=str(e))

# Bulk Operations
@admin_bp.route('/system-control/api/bulk-feature-update', methods=['POST'])
@admin_required
def bulk_update_features():
    """Bulk update feature flags"""
    try:
        data = request.get_json()
        updates = data.get('updates', {})
        
        result = feature_flags.bulk_update_features(updates, user=get_admin_user())
        return api_response(data=result)
    except Exception as e:
        return api_response(success=False, error=str(e))

# Error handlers
@admin_bp.errorhandler(400)
def bad_request(error):
    return api_response(success=False, error="Bad request")

@admin_bp.errorhandler(403)
def forbidden(error):
    return api_response(success=False, error="Forbidden")

@admin_bp.errorhandler(404)
def not_found(error):
    return api_response(success=False, error="Not found")

@admin_bp.errorhandler(500)
def internal_error(error):
    return api_response(success=False, error="Internal server error")