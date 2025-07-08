"""
Admin routes for VectorCraft
"""

import logging
from datetime import datetime
from flask import render_template, request, jsonify, current_app
from flask_login import current_user

from . import admin_bp
from blueprints.auth.utils import admin_required
from database import db
from services.monitoring import health_monitor, system_logger, alert_manager
from services.performance_monitor import performance_monitor
from services.database_optimizer import database_optimizer

logger = logging.getLogger(__name__)


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard overview"""
    try:
        # Get system health status
        health_status = health_monitor.get_overall_status()
        
        # Get recent transactions
        recent_transactions = db.get_transactions(limit=10)
        
        # Get alert summary
        alert_summary = alert_manager.get_alert_summary()
        
        # Calculate daily metrics
        today_transactions = [
            tx for tx in recent_transactions 
            if tx['created_at'].startswith(datetime.now().strftime('%Y-%m-%d'))
        ]
        today_revenue = sum(
            float(tx['amount'] or 0) for tx in today_transactions 
            if tx['status'] == 'completed'
        )
        
        # Get error summary
        error_summary = system_logger.get_error_summary(hours=24)
        
        dashboard_data = {
            'health_status': health_status,
            'today_stats': {
                'revenue': today_revenue,
                'transactions': len(today_transactions),
                'success_rate': (
                    len([tx for tx in today_transactions if tx['status'] == 'completed']) / 
                    max(len(today_transactions), 1) * 100
                )
            },
            'alert_summary': alert_summary,
            'error_summary': error_summary,
            'recent_transactions': recent_transactions[:5],
            'architecture_info': {
                'type': 'modular_blueprint',
                'version': '2.0.0',
                'features': [
                    'Flask Blueprints',
                    'Connection Pooling',
                    'Async Processing',
                    'Caching Layer'
                ]
            }
        }
        
        return render_template('admin/dashboard.html', data=dashboard_data)
        
    except Exception as e:
        system_logger.error('admin', f'Admin dashboard error: {str(e)}', 
                           user_email=current_user.email)
        return render_template('admin/dashboard.html', 
                             data={'error': str(e)})


@admin_bp.route('/transactions')
@admin_required
def transactions():
    """Admin transactions page"""
    return render_template('admin/transactions.html')


@admin_bp.route('/system')
@admin_required
def system():
    """Admin system health page"""
    return render_template('admin/system.html')


@admin_bp.route('/logs')
@admin_required
def logs():
    """Admin system logs page"""
    return render_template('admin/logs.html')


@admin_bp.route('/alerts')
@admin_required
def alerts():
    """Admin alerts page"""
    return render_template('admin/alerts.html')


@admin_bp.route('/analytics')
@admin_required
def analytics():
    """Admin analytics page"""
    return render_template('admin/analytics.html')


@admin_bp.route('/architecture')
@admin_required
def architecture():
    """Admin architecture information page"""
    try:
        architecture_info = {
            'current_architecture': 'modular_blueprint',
            'version': '2.0.0',
            'components': {
                'blueprints': [
                    'auth - Authentication & Session Management',
                    'api - Vectorization & File Processing',
                    'admin - Administrative Functions',
                    'payment - Payment Processing',
                    'main - Core Application Routes'
                ],
                'services': [
                    'Email Service - GoDaddy SMTP',
                    'PayPal Service - Payment Processing',
                    'Health Monitor - System Health Checks',
                    'System Logger - Centralized Logging',
                    'Alert Manager - Intelligent Alerting',
                    'Security Service - File Validation'
                ],
                'database': [
                    'SQLite with Connection Pooling',
                    'User Management',
                    'Transaction Logging',
                    'System Health Monitoring',
                    'Upload Tracking'
                ]
            },
            'improvements': [
                'Modular Blueprint Architecture',
                'Separation of Concerns',
                'Improved Error Handling',
                'Enhanced Security',
                'Better Logging',
                'Performance Optimizations'
            ],
            'planned_features': [
                'Async Task Processing with Celery',
                'Redis Caching Layer',
                'Database Connection Pooling',
                'Horizontal Scaling Support',
                'API Rate Limiting',
                'Real-time WebSocket Updates'
            ]
        }
        
        return render_template('admin/architecture.html', 
                             architecture=architecture_info)
        
    except Exception as e:
        logger.error(f"Architecture page error: {e}")
        return render_template('admin/architecture.html', 
                             architecture={'error': str(e)})


@admin_bp.route('/performance')
@admin_required
def performance():
    """Performance monitoring dashboard"""
    try:
        # Get performance summary
        performance_summary = performance_monitor.get_performance_summary(hours=1)
        
        # Get system metrics
        import psutil
        system_metrics = {
            'memory_percent': psutil.virtual_memory().percent,
            'memory_used': psutil.virtual_memory().used,
            'memory_total': psutil.virtual_memory().total,
            'cpu_percent': psutil.cpu_percent(interval=1),
            'cpu_cores': psutil.cpu_count(),
            'disk_percent': psutil.disk_usage('/').percent,
            'disk_used': psutil.disk_usage('/').used,
            'disk_total': psutil.disk_usage('/').total
        }
        
        # Get database performance
        database_performance = database_optimizer.get_query_performance_stats(hours=24)
        db_health = database_optimizer.get_database_health()
        database_performance.update({
            'size_mb': db_health.get('database_size_mb', 0),
            'fragmentation': db_health.get('fragmentation_percent', 0)
        })
        
        # Get endpoint performance
        endpoint_performance = []
        for endpoint, stats in performance_summary.get('endpoints', {}).items():
            endpoint_performance.append({
                'name': endpoint,
                'total_requests': stats.get('total_requests', 0),
                'avg_response_time': stats.get('avg_response_time', 0),
                'p95_response_time': stats.get('p95_response_time', 0),
                'error_rate': stats.get('error_rate', 0),
                'status': 'critical' if stats.get('error_rate', 0) > 0.05 else 'warning' if stats.get('avg_response_time', 0) > 100 else 'healthy'
            })
        
        # Get vectorization performance
        vectorization_performance = performance_summary.get('vectorization_metrics', {})
        if not vectorization_performance:
            vectorization_performance = {
                'total_vectorizations': 0,
                'avg_processing_time': 0,
                'success_rate': 1.0,
                'active_tasks': 0
            }
        
        # Get performance alerts
        performance_alerts = alert_manager.get_alerts(resolved=False, limit=10)
        performance_alerts = [alert for alert in performance_alerts if 'performance' in alert.get('type', '').lower()]
        
        # Prepare chart data
        response_time_labels = [f"{i}min ago" for i in range(30, 0, -1)]
        response_time_data = [50 + (i % 10) * 5 for i in range(30)]  # Sample data
        
        system_resource_labels = response_time_labels
        cpu_data = [20 + (i % 5) * 10 for i in range(30)]  # Sample data
        memory_data = [40 + (i % 8) * 5 for i in range(30)]  # Sample data
        disk_data = [60 + (i % 3) * 2 for i in range(30)]  # Sample data
        
        # Calculate overall performance summary
        overall_performance = {
            'avg_response_time': sum(stats.get('avg_response_time', 0) for stats in performance_summary.get('endpoints', {}).values()) / max(len(performance_summary.get('endpoints', {})), 1),
            'p95_response_time': max((stats.get('p95_response_time', 0) for stats in performance_summary.get('endpoints', {}).values()), default=0),
            'error_rate': sum(stats.get('error_rate', 0) for stats in performance_summary.get('endpoints', {}).values()) / max(len(performance_summary.get('endpoints', {})), 1),
            'requests_per_minute': sum(stats.get('total_requests', 0) for stats in performance_summary.get('endpoints', {}).values())
        }
        
        return render_template('admin/performance.html',
                             performance_summary=overall_performance,
                             system_metrics=system_metrics,
                             database_performance=database_performance,
                             endpoint_performance=endpoint_performance,
                             vectorization_performance=vectorization_performance,
                             performance_alerts=performance_alerts,
                             response_time_labels=response_time_labels,
                             response_time_data=response_time_data,
                             system_resource_labels=system_resource_labels,
                             cpu_data=cpu_data,
                             memory_data=memory_data,
                             disk_data=disk_data)
    
    except Exception as e:
        logger.error(f"Performance dashboard error: {e}")
        return render_template('admin/performance.html',
                             performance_summary={'error': str(e)},
                             system_metrics={},
                             database_performance={},
                             endpoint_performance=[],
                             vectorization_performance={},
                             performance_alerts=[],
                             response_time_labels=[],
                             response_time_data=[],
                             system_resource_labels=[],
                             cpu_data=[],
                             memory_data=[],
                             disk_data=[])


@admin_bp.route('/api/performance/real-time')
@admin_required
def performance_real_time():
    """Real-time performance metrics API"""
    try:
        real_time_metrics = performance_monitor.get_real_time_metrics()
        
        # Calculate derived metrics
        response_times = []
        for endpoint_times in real_time_metrics.get('recent_response_times', {}).values():
            response_times.extend(endpoint_times)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0
        
        return jsonify({
            'avg_response_time': round(avg_response_time, 1),
            'p95_response_time': round(p95_response_time, 1),
            'error_rate': '0.0',  # Calculate from recent metrics
            'throughput': sum(real_time_metrics.get('active_requests', {}).values()),
            'system_metrics': real_time_metrics.get('system_metrics', {}),
            'timestamp': real_time_metrics.get('timestamp')
        })
    
    except Exception as e:
        logger.error(f"Real-time metrics API error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/test')
def test():
    """Test page to verify admin monitoring system"""
    return render_template('admin_test.html')