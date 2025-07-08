"""
Health check and monitoring API endpoints
"""

import logging
from flask import jsonify
from flask_login import current_user

from . import api_bp
from blueprints.auth.utils import admin_required

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Public health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'name': 'VectorCraft',
        'authentication': 'enabled',
        'authenticated': current_user.is_authenticated,
        'vectorizers': ['standard', 'optimized'],
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'features': [
            'async_processing',
            'connection_pooling',
            'caching',
            'blueprint_architecture'
        ]
    })


@api_bp.route('/system-status', methods=['GET'])
@admin_required
def system_status():
    """Detailed system status for admins"""
    try:
        from services.monitoring import health_monitor
        
        # Get system health status
        health_results = health_monitor.check_all_components()
        overall_status = health_monitor.get_overall_status()
        
        return jsonify({
            'success': True,
            'system_health': overall_status,
            'components': health_results,
            'architecture': {
                'type': 'modular_blueprint',
                'async_processing': True,
                'connection_pooling': True,
                'caching': True
            }
        })
        
    except Exception as e:
        logger.error(f"System status error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/performance-metrics', methods=['GET'])
@admin_required
def performance_metrics():
    """Get performance metrics"""
    try:
        import psutil
        import os
        from database import db
        
        # System metrics
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database metrics
        db_path = db.db_path
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        
        # Get recent upload stats
        recent_uploads = db.get_user_uploads(current_user.id, limit=100)
        avg_processing_time = sum(
            upload.get('processing_time', 0) for upload in recent_uploads
        ) / max(len(recent_uploads), 1)
        
        return jsonify({
            'success': True,
            'metrics': {
                'memory': {
                    'total': memory.total,
                    'used': memory.used,
                    'free': memory.free,
                    'percent': memory.percent
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                },
                'database': {
                    'size': db_size,
                    'path': db_path
                },
                'processing': {
                    'avg_processing_time': avg_processing_time,
                    'recent_uploads': len(recent_uploads)
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Performance metrics error: {e}")
        return jsonify({'error': str(e)}), 500