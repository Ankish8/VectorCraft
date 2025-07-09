"""
Admin routes for VectorCraft
"""

import logging
from datetime import datetime, timedelta
from flask import render_template, request, jsonify, current_app
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
import json
import time
import psutil

from . import admin_bp
from blueprints.auth.utils import admin_required
from database import db
from services.monitoring import health_monitor, system_logger, alert_manager
from services.performance_monitor import performance_monitor
from services.database_optimizer import database_optimizer

# Import email management routes
from . import email_routes
from services.transaction_analytics import transaction_analytics
from services.payment_monitor import payment_monitor
from services.fraud_detection import fraud_detector
from services.financial_reporting import financial_reporter
from services.dispute_manager import dispute_manager
from services.cache_manager import metrics_cache, error_handler, rate_limiter, cache_response, handle_errors
try:
    from app_factory import socketio
except ImportError:
    socketio = None
# from services.user_management import user_management_service

logger = logging.getLogger(__name__)


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
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


@admin_bp.route('/api/analytics')
@admin_required
def analytics_api():
    """Analytics API endpoint for dashboard"""
    try:
        # Get comprehensive analytics data
        analytics_data = analytics_service.get_comprehensive_analytics()
        
        return jsonify({
            'success': True,
            'analytics': analytics_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Analytics API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Advanced Transaction Management API Routes

@admin_bp.route('/api/transaction-summary')
@admin_required
def transaction_summary():
    """Get transaction summary for dashboard cards"""
    try:
        # Get basic transaction statistics
        recent_transactions = db.get_transactions(limit=1000)
        
        total_revenue = sum(float(tx['amount'] or 0) for tx in recent_transactions if tx['status'] == 'completed')
        total_transactions = len(recent_transactions)
        successful_transactions = len([tx for tx in recent_transactions if tx['status'] == 'completed'])
        pending_count = len([tx for tx in recent_transactions if tx['status'] == 'pending'])
        
        success_rate = (successful_transactions / max(total_transactions, 1)) * 100
        
        # Get fraud alerts count
        fraud_alerts = len(alert_manager.get_alerts(resolved=False, limit=100))
        
        return jsonify({
            'success': True,
            'total_revenue': total_revenue,
            'success_rate': success_rate,
            'pending_count': pending_count,
            'fraud_alerts': fraud_alerts
        })
        
    except Exception as e:
        logger.error(f"Error getting transaction summary: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/api/transactions')
@admin_required
def api_transactions():
    """Enhanced transactions API with filtering"""
    try:
        # Get filter parameters
        status = request.args.get('status')
        email = request.args.get('email')
        limit = int(request.args.get('limit', 50))
        date_range = request.args.get('date_range', 'month')
        risk = request.args.get('risk')
        
        # Get transactions with filters
        transactions = db.get_transactions(
            limit=limit,
            status=status,
            email=email
        )
        
        # Add risk levels (simulated for now)
        for tx in transactions:
            tx['risk_level'] = 'low'  # Default risk level
            
            # Simple risk assessment
            if float(tx['amount'] or 0) > 100:
                tx['risk_level'] = 'medium'
            if tx['status'] == 'failed':
                tx['risk_level'] = 'high'
        
        # Apply risk filter
        if risk:
            transactions = [tx for tx in transactions if tx['risk_level'] == risk]
        
        return jsonify({
            'success': True,
            'transactions': transactions,
            'count': len(transactions)
        })
        
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/api/transaction-details/<transaction_id>')
@admin_required
def transaction_details(transaction_id):
    """Get detailed transaction information"""
    try:
        details = transaction_analytics.get_transaction_details(transaction_id)
        
        if 'error' in details:
            return jsonify({'success': False, 'error': details['error']})
        
        return jsonify({
            'success': True,
            'transaction': details
        })
        
    except Exception as e:
        logger.error(f"Error getting transaction details: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/api/transaction-analytics')
@admin_required
def transaction_analytics_api():
    """Get transaction analytics data"""
    try:
        analytics = transaction_analytics.get_transaction_analytics()
        performance = payment_monitor.get_processing_performance()
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_transactions': analytics.total_transactions,
                'completed_transactions': analytics.total_transactions * (analytics.success_rate / 100),
                'pending_transactions': 0,  # Calculate from data
                'failed_transactions': analytics.total_transactions - (analytics.total_transactions * (analytics.success_rate / 100)),
                'disputed_transactions': 0,  # Calculate from data
                'daily_trends': analytics.daily_trends,
                'hourly_trends': analytics.hourly_trends
            },
            'performance': performance
        })
        
    except Exception as e:
        logger.error(f"Error getting transaction analytics: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/api/fraud-analysis/<transaction_id>')
@admin_required
def fraud_analysis(transaction_id):
    """Get fraud analysis for transaction"""
    try:
        transaction = db.get_transaction(transaction_id)
        if not transaction:
            return jsonify({'success': False, 'error': 'Transaction not found'})
        
        analysis = fraud_detector.analyze_transaction(transaction)
        
        return jsonify({
            'success': True,
            'analysis': {
                'risk_score': analysis.risk_score,
                'risk_level': analysis.risk_level.value,
                'indicators': [{
                    'type': indicator.indicator_type,
                    'description': indicator.description,
                    'weight': indicator.weight
                } for indicator in analysis.indicators],
                'recommended_action': analysis.recommended_action,
                'is_blocked': analysis.is_blocked
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting fraud analysis: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/api/fraud-statistics')
@admin_required
def fraud_statistics():
    """Get fraud detection statistics"""
    try:
        fraud_stats = fraud_detector.get_fraud_statistics()
        
        # Get high-risk transactions (simulated)
        high_risk_transactions = [
            tx for tx in db.get_transactions(limit=100) 
            if float(tx['amount'] or 0) > 100 or tx['status'] == 'failed'
        ][:10]
        
        return jsonify({
            'success': True,
            'fraud_stats': fraud_stats,
            'high_risk_transactions': high_risk_transactions
        })
        
    except Exception as e:
        logger.error(f"Error getting fraud statistics: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/api/dispute-summary')
@admin_required
def dispute_summary():
    """Get dispute management summary"""
    try:
        metrics = dispute_manager.get_dispute_metrics()
        open_disputes = dispute_manager.get_open_disputes(limit=10)
        
        return jsonify({
            'success': True,
            'dispute_stats': {
                'total_disputes': metrics.total_disputes,
                'open_disputes': metrics.open_disputes,
                'resolved_disputes': metrics.resolved_disputes,
                'resolution_rate': metrics.resolution_rate
            },
            'open_disputes': open_disputes
        })
        
    except Exception as e:
        logger.error(f"Error getting dispute summary: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/api/create-dispute/<transaction_id>', methods=['POST'])
@admin_required
def create_dispute(transaction_id):
    """Create a dispute case for transaction"""
    try:
        data = request.get_json()
        dispute_type = data.get('dispute_type', 'billing_inquiry')
        message = data.get('message', 'Admin initiated dispute')
        
        from services.dispute_manager import DisputeType
        case_id = dispute_manager.create_dispute(
            transaction_id=transaction_id,
            dispute_type=DisputeType(dispute_type),
            customer_message=message
        )
        
        return jsonify({
            'success': True,
            'case_id': case_id
        })
        
    except Exception as e:
        logger.error(f"Error creating dispute: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/api/export-transactions')
@admin_required
def export_transactions():
    """Export transaction data"""
    try:
        format_type = request.args.get('format', 'json')
        date_range = request.args.get('date_range', 'month')
        
        export_data = financial_reporter.export_financial_data(
            format_type=format_type
        )
        
        if format_type == 'csv':
            from flask import Response
            return Response(
                export_data['content'],
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename={export_data["filename"]}'
                }
            )
        else:
            return jsonify(export_data)
        
    except Exception as e:
        logger.error(f"Error exporting transactions: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/api/generate-report')
@admin_required
def generate_report():
    """Generate financial report"""
    try:
        report_type = request.args.get('type', 'financial')
        period = request.args.get('period', 'month')
        
        from services.financial_reporting import ReportPeriod
        
        report = financial_reporter.generate_financial_report(
            period=ReportPeriod(period)
        )
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/test')
@admin_required
def test():
    """Test page to verify admin monitoring system"""
    return render_template('admin_test.html')


# User Management Routes (temporarily disabled)
@admin_bp.route('/users')
@admin_required
def users():
    """User management page"""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25))
        search = request.args.get('search', '').strip()
        status = request.args.get('status')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'DESC')
        
        # Convert status to boolean if provided
        if status == 'active':
            status = True
        elif status == 'inactive':
            status = False
        else:
            status = None
        
        # Get users with pagination
        users_data = user_management_service.get_users_with_pagination(
            page=page,
            per_page=per_page,
            search=search if search else None,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Get user insights for summary cards
        insights = user_management_service.get_user_insights()
        
        return render_template('admin/users.html', 
                             users_data=users_data, 
                             insights=insights,
                             current_filters={
                                 'search': search,
                                 'status': request.args.get('status', ''),
                                 'sort_by': sort_by,
                                 'sort_order': sort_order
                             })
        
    except Exception as e:
        logger.error(f"User management page error: {e}")
        return render_template('admin/users.html', 
                             users_data={'users': [], 'pagination': {}, 'error': str(e)},
                             insights={})


@admin_bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    """User detail page"""
    try:
        user_details = user_management_service.get_user_details(user_id)
        
        if 'error' in user_details:
            return render_template('admin/user_detail.html', 
                                 user_details={'error': user_details['error']})
        
        return render_template('admin/user_detail.html', 
                             user_details=user_details)
        
    except Exception as e:
        logger.error(f"User detail page error: {e}")
        return render_template('admin/user_detail.html', 
                             user_details={'error': str(e)})


@admin_bp.route('/users/bulk-action', methods=['POST'])
@admin_required
def bulk_user_action():
    """Handle bulk user actions"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_ids = data.get('user_ids', [])
        action = data.get('action')
        
        if not user_ids or not action:
            return jsonify({'error': 'User IDs and action are required'}), 400
        
        # Perform bulk action
        result = user_management_service.bulk_update_users(
            user_ids=user_ids,
            action=action,
            admin_user=current_user.username
        )
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Bulk user action error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/users/search')
@admin_required
def search_users():
    """Search users API endpoint"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'users': []})
        
        filters = {
            'status': request.args.get('status'),
            'sort_by': request.args.get('sort_by', 'created_at'),
            'sort_order': request.args.get('sort_order', 'DESC'),
            'limit': int(request.args.get('limit', 50))
        }
        
        # Convert status filter
        if filters['status'] == 'active':
            filters['status'] = True
        elif filters['status'] == 'inactive':
            filters['status'] = False
        else:
            filters['status'] = None
        
        users = user_management_service.search_users(query, filters)
        
        return jsonify({'users': users})
        
    except Exception as e:
        logger.error(f"User search error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/users/<int:user_id>/activity')
@admin_required
def user_activity(user_id):
    """Get user activity timeline"""
    try:
        limit = int(request.args.get('limit', 50))
        activity_type = request.args.get('type')
        
        timeline = db.get_user_activity_timeline(
            user_id=user_id,
            limit=limit,
            activity_type=activity_type
        )
        
        return jsonify({'timeline': timeline})
        
    except Exception as e:
        logger.error(f"User activity error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/users/segments')
@admin_required
def user_segments():
    """Get user segmentation data"""
    try:
        segments = user_management_service.get_user_segments()
        return jsonify(segments)
        
    except Exception as e:
        logger.error(f"User segments error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/users/insights')
@admin_required
def user_insights():
    """Get user insights for dashboard"""
    try:
        insights = user_management_service.get_user_insights()
        return jsonify(insights)
        
    except Exception as e:
        logger.error(f"User insights error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/metrics/live')
@admin_required
@cache_response(ttl=30)
@handle_errors(fallback_response={'success': False, 'error': 'Service temporarily unavailable'})
def live_metrics():
    """Live metrics API endpoint"""
    try:
        # Get current timestamp
        current_time = datetime.now()
        
        # Get real-time system metrics
        system_metrics = {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'network_io': dict(psutil.net_io_counters()._asdict()),
            'timestamp': current_time.isoformat()
        }
        
        # Get recent transactions (last 5 minutes)
        recent_transactions = db.get_transactions_since(
            since=current_time - timedelta(minutes=5)
        )
        
        # Calculate revenue metrics
        revenue_metrics = {
            'total_revenue': sum(float(tx.get('amount', 0)) for tx in recent_transactions if tx.get('status') == 'completed'),
            'transaction_count': len(recent_transactions),
            'pending_transactions': len([tx for tx in recent_transactions if tx.get('status') == 'pending']),
            'failed_transactions': len([tx for tx in recent_transactions if tx.get('status') == 'failed'])
        }
        
        # Get health status
        health_results = health_monitor.check_all_components()
        health_summary = {
            'overall_status': health_monitor.get_overall_status(),
            'components': health_results
        }
        
        # Get performance metrics
        performance_metrics = performance_monitor.get_real_time_metrics()
        
        return jsonify({
            'success': True,
            'timestamp': current_time.isoformat(),
            'system_metrics': system_metrics,
            'revenue_metrics': revenue_metrics,
            'health_summary': health_summary,
            'performance_metrics': performance_metrics
        })
        
    except Exception as e:
        logger.error(f"Live metrics API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/analytics/revenue')
@admin_required
@cache_response(ttl=300)
@handle_errors(fallback_response={'success': False, 'error': 'Analytics service unavailable'})
def revenue_analytics():
    """Advanced revenue analytics endpoint"""
    try:
        # Get time range from request
        timeframe = request.args.get('timeframe', 'daily')  # hourly, daily, weekly
        
        current_time = datetime.now()
        
        # Calculate time ranges based on timeframe
        if timeframe == 'hourly':
            time_periods = [(current_time - timedelta(hours=i), current_time - timedelta(hours=i-1)) for i in range(24, 0, -1)]
            labels = [f"{i}h ago" for i in range(24, 0, -1)]
        elif timeframe == 'weekly':
            time_periods = [(current_time - timedelta(weeks=i), current_time - timedelta(weeks=i-1)) for i in range(12, 0, -1)]
            labels = [f"{i}w ago" for i in range(12, 0, -1)]
        else:  # daily
            time_periods = [(current_time - timedelta(days=i), current_time - timedelta(days=i-1)) for i in range(30, 0, -1)]
            labels = [f"{i}d ago" for i in range(30, 0, -1)]
        
        # Get revenue data for each time period
        revenue_data = []
        transaction_data = []
        
        for start_time, end_time in time_periods:
            transactions = db.get_transactions_between(start_time, end_time)
            period_revenue = sum(float(tx.get('amount', 0)) for tx in transactions if tx.get('status') == 'completed')
            
            revenue_data.append(period_revenue)
            transaction_data.append(len(transactions))
        
        # Calculate summary statistics
        total_revenue = sum(revenue_data)
        avg_revenue = total_revenue / len(revenue_data) if revenue_data else 0
        max_revenue = max(revenue_data) if revenue_data else 0
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'labels': labels,
            'revenue_data': revenue_data,
            'transaction_data': transaction_data,
            'summary': {
                'total_revenue': total_revenue,
                'avg_revenue': avg_revenue,
                'max_revenue': max_revenue,
                'total_transactions': sum(transaction_data)
            }
        })
        
    except Exception as e:
        logger.error(f"Revenue analytics API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/user-activity')
@admin_required
@cache_response(ttl=120)
@handle_errors(fallback_response={'success': False, 'error': 'User activity service unavailable'})
def user_activity_tracking():
    """User activity tracking endpoint"""
    try:
        # Get recent user activities
        recent_activities = db.get_user_activities(limit=50)
        
        # Get active users (last 30 minutes)
        active_users = db.get_active_users(minutes=30)
        
        # Get vectorization activities
        vectorization_activities = db.get_vectorization_activities(limit=20)
        
        return jsonify({
            'success': True,
            'recent_activities': recent_activities,
            'active_users': active_users,
            'vectorization_activities': vectorization_activities,
            'summary': {
                'active_users_count': len(active_users),
                'recent_activities_count': len(recent_activities),
                'vectorization_count': len(vectorization_activities)
            }
        })
        
    except Exception as e:
        logger.error(f"User activity tracking API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# WebSocket event handlers for real-time updates
@socketio.on('join_admin_room')
def handle_join_admin_room():
    """Handle admin joining the real-time updates room"""
    if current_user.is_authenticated:
        join_room('admin_dashboard')
        emit('status', {'message': 'Connected to admin dashboard updates'})


@socketio.on('leave_admin_room')
def handle_leave_admin_room():
    """Handle admin leaving the real-time updates room"""
    if current_user.is_authenticated:
        leave_room('admin_dashboard')
        emit('status', {'message': 'Disconnected from admin dashboard updates'})


@socketio.on('request_live_update')
def handle_live_update_request():
    """Handle request for live update"""
    if current_user.is_authenticated:
        try:
            # Get current metrics
            current_time = datetime.now()
            
            # System metrics
            system_metrics = {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'timestamp': current_time.isoformat()
            }
            
            # Recent transactions
            recent_transactions = db.get_transactions_since(
                since=current_time - timedelta(minutes=5)
            )
            
            # Performance metrics
            performance_metrics = performance_monitor.get_real_time_metrics()
            
            # Emit live update to admin room
            socketio.emit('live_update', {
                'system_metrics': system_metrics,
                'recent_transactions': recent_transactions[:5],  # Last 5 transactions
                'performance_metrics': performance_metrics,
                'timestamp': current_time.isoformat()
            }, room='admin_dashboard')
            
        except Exception as e:
            logger.error(f"Live update error: {e}")
            emit('error', {'message': 'Error fetching live update'})


@admin_bp.route('/api/health')
@admin_required
@cache_response(ttl=60)
@handle_errors(fallback_response={'success': False, 'error': 'Health check failed'})
def health_check():
    """Comprehensive health check endpoint"""
    try:
        # Check if circuit breakers are open
        circuit_breaker_status = error_handler.get_error_summary()
        
        # Get system health
        health_results = health_monitor.check_all_components()
        overall_status = health_monitor.get_overall_status()
        
        # Get cache statistics
        cache_stats = metrics_cache.cache_manager.get_stats()
        
        # Get rate limiting statistics
        rate_limit_stats = rate_limiter.get_stats()
        
        # Get performance metrics
        performance_stats = performance_monitor.get_real_time_metrics()
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'health_results': health_results,
            'overall_status': overall_status,
            'circuit_breakers': circuit_breaker_status,
            'cache_stats': cache_stats,
            'rate_limit_stats': rate_limit_stats,
            'performance_summary': performance_stats.get('performance_summary', {}),
            'system_healthy': overall_status['status'] == 'healthy' and len(circuit_breaker_status['active_circuit_breakers']) == 0
        })
        
    except Exception as e:
        logger.error(f"Health check endpoint error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'system_healthy': False
        }), 500


@admin_bp.route('/api/alerts')
@admin_required
@cache_response(ttl=60)
@handle_errors(fallback_response={'success': False, 'error': 'Alerts service unavailable'})
def alerts_summary():
    """Get alerts summary"""
    try:
        # Get alert summary from alert manager
        alert_summary = alert_manager.get_alert_summary()
        
        # Get recent alerts
        recent_alerts = alert_manager.get_alerts(limit=20)
        
        # Get error summary
        error_summary = error_handler.get_error_summary()
        
        return jsonify({
            'success': True,
            'summary': alert_summary,
            'recent_alerts': recent_alerts,
            'error_summary': error_summary,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Alerts summary error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/cache/stats')
@admin_required
def cache_stats():
    """Get cache statistics"""
    try:
        return jsonify({
            'success': True,
            'cache_stats': metrics_cache.cache_manager.get_stats(),
            'aggregated_cache_stats': metrics_cache.aggregated_cache.get_stats(),
            'error_stats': error_handler.get_error_summary(),
            'rate_limit_stats': rate_limiter.get_stats()
        })
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/cache/clear', methods=['POST'])
@admin_required
def clear_cache():
    """Clear cache (admin only)"""
    try:
        cache_type = request.json.get('type', 'all')
        
        if cache_type == 'all':
            metrics_cache.cache_manager.clear()
            metrics_cache.aggregated_cache.clear()
            message = 'All caches cleared'
        elif cache_type == 'metrics':
            metrics_cache.cache_manager.clear()
            message = 'Metrics cache cleared'
        elif cache_type == 'aggregated':
            metrics_cache.aggregated_cache.clear()
            message = 'Aggregated cache cleared'
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid cache type'
            }), 400
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500