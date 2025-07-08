"""
Admin monitoring API endpoints
"""

import logging
from datetime import datetime
from flask import request, jsonify
from flask_login import current_user

from . import admin_bp
from blueprints.auth.utils import admin_required
from database import db
from services.monitoring import health_monitor, system_logger, alert_manager

logger = logging.getLogger(__name__)


@admin_bp.route('/api/health')
@admin_required
def api_health():
    """API endpoint for system health status"""
    try:
        health_results = health_monitor.check_all_components()
        overall_status = health_monitor.get_overall_status()
        
        response = jsonify({
            'success': True,
            'health_results': health_results,
            'overall_status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'architecture': {
                'type': 'modular_blueprint',
                'version': '2.0.0'
            }
        })
        
        # Add cache-busting headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        logger.error(f"Admin health API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/transactions')
@admin_required
def api_transactions():
    """API endpoint for transaction data"""
    try:
        limit = request.args.get('limit', 50, type=int)
        status = request.args.get('status')
        email = request.args.get('email')
        
        transactions = db.get_transactions(limit=limit, status=status, email=email)
        
        return jsonify({
            'success': True,
            'transactions': transactions,
            'count': len(transactions),
            'architecture': 'modular_blueprint'
        })
        
    except Exception as e:
        logger.error(f"Admin transactions API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/logs')
@admin_required
def api_logs():
    """API endpoint for system logs"""
    try:
        limit = request.args.get('limit', 100, type=int)
        level = request.args.get('level')
        component = request.args.get('component')
        hours = request.args.get('hours', 24, type=int)
        
        logs = system_logger.get_recent_logs(
            hours=hours, 
            level=level, 
            component=component, 
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs),
            'architecture': 'modular_blueprint'
        })
        
    except Exception as e:
        logger.error(f"Admin logs API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/alerts')
@admin_required
def api_alerts():
    """API endpoint for admin alerts"""
    try:
        resolved = request.args.get('resolved')
        if resolved is not None:
            resolved = resolved.lower() == 'true'
        
        alerts = db.get_alerts(resolved=resolved)
        alert_summary = alert_manager.get_alert_summary()
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'summary': alert_summary,
            'architecture': 'modular_blueprint'
        })
        
    except Exception as e:
        logger.error(f"Admin alerts API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/alerts/<int:alert_id>/resolve', methods=['POST'])
@admin_required
def api_resolve_alert(alert_id):
    """API endpoint to resolve an alert"""
    try:
        success = alert_manager.resolve_alert(alert_id, current_user.email)
        
        if success:
            return jsonify({
                'success': True, 
                'message': 'Alert resolved',
                'architecture': 'modular_blueprint'
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Failed to resolve alert'
            }), 500
            
    except Exception as e:
        logger.error(f"Admin resolve alert API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/analytics')
@admin_required
def api_analytics():
    """API endpoint for analytics data"""
    try:
        # Get transaction analytics
        transactions = db.get_transactions(limit=100)
        
        # Calculate metrics
        completed_transactions = [tx for tx in transactions if tx['status'] == 'completed']
        total_revenue = sum(float(tx['amount'] or 0) for tx in completed_transactions)
        
        # Group by date for charts
        from collections import defaultdict
        daily_stats = defaultdict(lambda: {'revenue': 0, 'count': 0})
        
        for tx in completed_transactions:
            date = tx['created_at'][:10]  # Get YYYY-MM-DD
            daily_stats[date]['revenue'] += float(tx['amount'] or 0)
            daily_stats[date]['count'] += 1
        
        # Format for charts
        chart_data = [
            {
                'date': date,
                'revenue': stats['revenue'],
                'transactions': stats['count']
            }
            for date, stats in sorted(daily_stats.items())
        ]
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_revenue': total_revenue,
                'total_transactions': len(completed_transactions),
                'avg_order_value': total_revenue / max(len(completed_transactions), 1),
                'daily_data': chart_data[-7:]  # Last 7 days
            },
            'architecture': {
                'type': 'modular_blueprint',
                'version': '2.0.0',
                'improvements': [
                    'Better data separation',
                    'Improved query performance',
                    'Enhanced error handling'
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Admin analytics API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/system-metrics')
@admin_required
def api_system_metrics():
    """API endpoint for system performance metrics"""
    try:
        import psutil
        import os
        
        # System metrics
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database metrics
        db_path = db.db_path
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        
        # Application metrics
        recent_uploads = db.get_user_uploads(current_user.id, limit=100)
        avg_processing_time = sum(
            upload.get('processing_time', 0) for upload in recent_uploads
        ) / max(len(recent_uploads), 1)
        
        return jsonify({
            'success': True,
            'metrics': {
                'system': {
                    'memory_percent': memory.percent,
                    'disk_percent': disk.percent,
                    'memory_total': memory.total,
                    'disk_total': disk.total
                },
                'database': {
                    'size': db_size,
                    'path': db_path
                },
                'application': {
                    'avg_processing_time': avg_processing_time,
                    'recent_uploads': len(recent_uploads)
                }
            },
            'architecture': {
                'type': 'modular_blueprint',
                'version': '2.0.0',
                'optimizations': [
                    'Blueprint separation',
                    'Improved monitoring',
                    'Better resource usage'
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Admin system metrics API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500