"""
Admin API Management Routes
"""

import logging
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from typing import Dict, Any

from services.api_service import api_service
from services.monitoring.system_logger import system_logger
from blueprints.auth.utils import admin_required

logger = logging.getLogger(__name__)

api_management_bp = Blueprint('api_management', __name__)


@api_management_bp.route('/admin/api-management')
@login_required
@admin_required
def api_management():
    """API Management dashboard page"""
    try:
        return render_template('admin/api_management.html')
    except Exception as e:
        logger.error(f"Error loading API management page: {e}")
        return render_template('error.html', error="Failed to load API management page"), 500


@api_management_bp.route('/admin/api/analytics')
@login_required
@admin_required
def get_analytics():
    """Get API analytics data"""
    try:
        hours = request.args.get('hours', 24, type=int)
        analytics_data = api_service.get_api_analytics(hours)
        
        # Log the request
        system_logger.log_activity(
            user_id=current_user.id,
            activity_type='admin_api_analytics',
            details=f'Viewed API analytics for {hours} hours'
        )
        
        return jsonify(analytics_data)
    except Exception as e:
        logger.error(f"Error getting API analytics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_management_bp.route('/admin/api/integrations')
@login_required
@admin_required
def get_integrations():
    """Get integration status"""
    try:
        integration_data = api_service.get_integration_status()
        
        # Log the request
        system_logger.log_activity(
            user_id=current_user.id,
            activity_type='admin_integration_status',
            details='Viewed integration status'
        )
        
        return jsonify(integration_data)
    except Exception as e:
        logger.error(f"Error getting integration status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_management_bp.route('/admin/api/rate-limits', methods=['GET', 'POST'])
@login_required
@admin_required
def rate_limits():
    """Get or update rate limits"""
    try:
        if request.method == 'GET':
            rate_limit_data = api_service.get_rate_limit_status()
            
            # Log the request
            system_logger.log_activity(
                user_id=current_user.id,
                activity_type='admin_rate_limits_view',
                details='Viewed rate limit status'
            )
            
            return jsonify(rate_limit_data)
        
        elif request.method == 'POST':
            data = request.get_json()
            
            if not data or not all(k in data for k in ['endpoint', 'limit', 'window']):
                return jsonify({
                    'success': False,
                    'error': 'Missing required fields: endpoint, limit, window'
                }), 400
            
            result = api_service.update_rate_limit(
                endpoint=data['endpoint'],
                limit=data['limit'],
                window=data['window']
            )
            
            # Log the update
            system_logger.log_activity(
                user_id=current_user.id,
                activity_type='admin_rate_limit_update',
                details=f'Updated rate limit for {data["endpoint"]}: {data["limit"]} requests per {data["window"]}s'
            )
            
            return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error handling rate limits: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_management_bp.route('/admin/api/performance')
@login_required
@admin_required
def get_performance():
    """Get API performance metrics"""
    try:
        performance_data = api_service.get_performance_metrics()
        
        # Log the request
        system_logger.log_activity(
            user_id=current_user.id,
            activity_type='admin_performance_metrics',
            details='Viewed API performance metrics'
        )
        
        return jsonify(performance_data)
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_management_bp.route('/admin/api/documentation')
@login_required
@admin_required
def get_documentation():
    """Get API documentation"""
    try:
        format_type = request.args.get('format', 'json')
        documentation_data = api_service.get_api_documentation(format_type)
        
        # Log the request
        system_logger.log_activity(
            user_id=current_user.id,
            activity_type='admin_api_documentation',
            details=f'Viewed API documentation in {format_type} format'
        )
        
        return jsonify(documentation_data)
    except Exception as e:
        logger.error(f"Error getting API documentation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_management_bp.route('/admin/api/health')
@login_required
@admin_required
def api_health():
    """Get API health status"""
    try:
        health_data = api_service.get_system_health()
        
        # Log the request
        system_logger.log_activity(
            user_id=current_user.id,
            activity_type='admin_api_health',
            details='Viewed API health status'
        )
        
        return jsonify(health_data)
    except Exception as e:
        logger.error(f"Error getting API health: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_management_bp.route('/admin/api/metrics')
@login_required
@admin_required
def api_metrics():
    """Get detailed API metrics"""
    try:
        metrics_data = api_service.get_api_metrics()
        
        # Log the request
        system_logger.log_activity(
            user_id=current_user.id,
            activity_type='admin_api_metrics',
            details='Viewed detailed API metrics'
        )
        
        return jsonify(metrics_data)
    except Exception as e:
        logger.error(f"Error getting API metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_management_bp.route('/admin/api/clear-analytics', methods=['POST'])
@login_required
@admin_required
def clear_analytics():
    """Clear old analytics data"""
    try:
        data = request.get_json()
        days = data.get('days', 30) if data else 30
        
        result = api_service.clear_analytics_data(days)
        
        # Log the action
        system_logger.log_activity(
            user_id=current_user.id,
            activity_type='admin_clear_analytics',
            details=f'Cleared analytics data older than {days} days'
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error clearing analytics data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_management_bp.route('/admin/api/cache/invalidate', methods=['POST'])
@login_required
@admin_required
def invalidate_cache():
    """Invalidate API cache"""
    try:
        data = request.get_json()
        pattern = data.get('pattern') if data else None
        prefix = data.get('prefix', 'api_cache') if data else 'api_cache'
        
        result = api_service.invalidate_cache(pattern, prefix)
        
        # Log the action
        system_logger.log_activity(
            user_id=current_user.id,
            activity_type='admin_cache_invalidate',
            details=f'Invalidated cache with pattern: {pattern}, prefix: {prefix}'
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_management_bp.route('/admin/api/service-health/<service_name>')
@login_required
@admin_required
def check_service_health(service_name):
    """Check health of a specific service"""
    try:
        health_result = api_service.integration_monitor.check_service_health(service_name)
        
        # Log the request
        system_logger.log_activity(
            user_id=current_user.id,
            activity_type='admin_service_health_check',
            details=f'Checked health of service: {service_name}'
        )
        
        return jsonify({
            'success': True,
            'service_health': health_result
        })
    except Exception as e:
        logger.error(f"Error checking service health: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_management_bp.route('/admin/api/export-analytics')
@login_required
@admin_required
def export_analytics():
    """Export analytics data"""
    try:
        hours = request.args.get('hours', 24, type=int)
        format_type = request.args.get('format', 'json')
        
        analytics_data = api_service.get_api_analytics(hours)
        
        if format_type == 'csv':
            # Convert to CSV format
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow(['Endpoint', 'Method', 'Count', 'Avg Response Time', 'Max Response Time', 'Min Response Time'])
            
            # Write data
            for stat in analytics_data['analytics']['summary']['request_stats']:
                writer.writerow([
                    stat['endpoint'],
                    stat['method'],
                    stat['count'],
                    stat['avg_response_time'],
                    stat['max_response_time'],
                    stat['min_response_time']
                ])
            
            response = current_app.response_class(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=api_analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
            )
            
            # Log the export
            system_logger.log_activity(
                user_id=current_user.id,
                activity_type='admin_export_analytics',
                details=f'Exported analytics data as CSV for {hours} hours'
            )
            
            return response
        
        else:
            # Return as JSON
            # Log the export
            system_logger.log_activity(
                user_id=current_user.id,
                activity_type='admin_export_analytics',
                details=f'Exported analytics data as JSON for {hours} hours'
            )
            
            return jsonify(analytics_data)
    
    except Exception as e:
        logger.error(f"Error exporting analytics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Error handlers
@api_management_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@api_management_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error in API management: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500