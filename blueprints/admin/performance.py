#!/usr/bin/env python3
"""
Admin Blueprint for Performance Management
Routes and handlers for performance monitoring, tuning, and optimization
"""

import json
import logging
import time
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from functools import wraps

# Import performance services
try:
    from services.performance_tuner import performance_tuner
    from services.auto_optimizer import auto_optimizer
    from services.benchmark_manager import benchmark_manager
    PERFORMANCE_SERVICES_AVAILABLE = True
except ImportError:
    PERFORMANCE_SERVICES_AVAILABLE = False

logger = logging.getLogger(__name__)

# Import admin blueprint
from . import admin_bp

def require_performance_services(f):
    """Decorator to check if performance services are available"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not PERFORMANCE_SERVICES_AVAILABLE:
            return jsonify({'error': 'Performance services not available'}), 503
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/performance')
@require_performance_services
def performance_dashboard():
    """Main performance dashboard"""
    try:
        # Get real-time metrics
        real_time_metrics = performance_tuner.get_real_time_metrics()
        
        # Get optimization status
        optimization_status = auto_optimizer.get_optimization_status()
        
        # Get benchmark summary
        benchmark_summary = benchmark_manager.get_performance_summary()
        
        # Get recent performance history
        performance_history = performance_tuner.get_performance_history(hours=24)
        
        # Process data for charts
        chart_data = _prepare_chart_data(performance_history)
        
        # Get active tests
        active_tests = benchmark_manager.get_active_tests()
        
        # Get tuning parameters
        tuning_params = performance_tuner.get_tuning_parameters()
        
        return render_template('admin/performance_tuning.html',
                             real_time_metrics=real_time_metrics,
                             optimization_status=optimization_status,
                             benchmark_summary=benchmark_summary,
                             chart_data=chart_data,
                             active_tests=active_tests,
                             tuning_params=tuning_params)
    
    except Exception as e:
        logger.error(f"Performance dashboard error: {e}")
        flash(f"Error loading performance dashboard: {str(e)}", 'error')
        return render_template('admin/error.html', error=str(e))

@admin_bp.route('/performance/api/real-time-metrics')
@require_performance_services
def api_real_time_metrics():
    """API endpoint for real-time metrics"""
    try:
        metrics = performance_tuner.get_real_time_metrics()
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Real-time metrics API error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/performance/api/optimization-status')
@require_performance_services
def api_optimization_status():
    """API endpoint for optimization status"""
    try:
        status = auto_optimizer.get_optimization_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Optimization status API error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/performance/api/optimization-recommendations')
@require_performance_services
def api_optimization_recommendations():
    """API endpoint for optimization recommendations"""
    try:
        recommendations = auto_optimizer.get_optimization_recommendations()
        return jsonify(recommendations)
    except Exception as e:
        logger.error(f"Optimization recommendations API error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/performance/api/tuning-parameters', methods=['GET', 'POST'])
@require_performance_services
def api_tuning_parameters():
    """API endpoint for tuning parameters"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            category = data.get('category')
            parameter = data.get('parameter')
            value = data.get('value')
            
            if not all([category, parameter, value is not None]):
                return jsonify({'error': 'Missing required parameters'}), 400
            
            # Apply tuning parameter
            success = performance_tuner.apply_tuning_parameter(category, parameter, value)
            
            if success:
                return jsonify({'success': True, 'message': 'Parameter updated successfully'})
            else:
                return jsonify({'error': 'Failed to update parameter'}), 400
                
        except Exception as e:
            logger.error(f"Tuning parameters API error: {e}")
            return jsonify({'error': str(e)}), 500
    
    else:
        try:
            parameters = performance_tuner.get_tuning_parameters()
            return jsonify(parameters)
        except Exception as e:
            logger.error(f"Get tuning parameters API error: {e}")
            return jsonify({'error': str(e)}), 500

@admin_bp.route('/performance/benchmarks')
@require_performance_services
def benchmarks():
    """Benchmark management page"""
    try:
        # Get available tests
        available_tests = benchmark_manager.get_available_tests()
        
        # Get active tests
        active_tests = benchmark_manager.get_active_tests()
        
        # Get recent results
        recent_results = []
        for test in available_tests:
            history = benchmark_manager.get_benchmark_history(test['id'], days=7)
            if history:
                recent_results.extend(history[:3])  # Last 3 results per test
        
        # Sort by timestamp
        recent_results.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Get performance summary
        summary = benchmark_manager.get_performance_summary()
        
        return render_template('admin/benchmarks.html',
                             available_tests=available_tests,
                             active_tests=active_tests,
                             recent_results=recent_results[:20],  # Show last 20
                             summary=summary)
    
    except Exception as e:
        logger.error(f"Benchmarks page error: {e}")
        flash(f"Error loading benchmarks: {str(e)}", 'error')
        return render_template('admin/error.html', error=str(e))

@admin_bp.route('/performance/api/benchmark/run', methods=['POST'])
@require_performance_services
def api_run_benchmark():
    """API endpoint to run benchmark test"""
    try:
        data = request.get_json()
        test_id = data.get('test_id')
        custom_params = data.get('custom_params', {})
        
        if not test_id:
            return jsonify({'error': 'Test ID required'}), 400
        
        # Run benchmark in background
        import threading
        
        def run_benchmark():
            try:
                result = benchmark_manager.run_benchmark(test_id, custom_params)
                logger.info(f"Benchmark completed: {test_id} - Score: {result.score}")
            except Exception as e:
                logger.error(f"Benchmark execution error: {e}")
        
        thread = threading.Thread(target=run_benchmark)
        thread.start()
        
        return jsonify({'success': True, 'message': 'Benchmark started'})
        
    except Exception as e:
        logger.error(f"Run benchmark API error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/performance/api/benchmark/status/<test_id>')
@require_performance_services
def api_benchmark_status(test_id):
    """API endpoint to get benchmark status"""
    try:
        active_tests = benchmark_manager.get_active_tests()
        
        if test_id in active_tests:
            return jsonify(active_tests[test_id])
        else:
            # Check for recent results
            history = benchmark_manager.get_benchmark_history(test_id, days=1)
            if history:
                latest = history[0]
                return jsonify({
                    'status': 'completed',
                    'result': {
                        'score': latest.score,
                        'success': latest.success,
                        'timestamp': latest.timestamp.isoformat()
                    }
                })
            else:
                return jsonify({'status': 'not_found'}), 404
                
    except Exception as e:
        logger.error(f"Benchmark status API error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/performance/api/benchmark/history/<test_id>')
@require_performance_services
def api_benchmark_history(test_id):
    """API endpoint to get benchmark history"""
    try:
        days = request.args.get('days', 7, type=int)
        history = benchmark_manager.get_benchmark_history(test_id, days)
        
        # Convert to JSON-serializable format
        history_data = []
        for result in history:
            history_data.append({
                'timestamp': result.timestamp.isoformat(),
                'score': result.score,
                'success': result.success,
                'avg_response_time': result.avg_response_time,
                'throughput': result.throughput,
                'error_rate': result.error_rate,
                'total_requests': result.total_requests
            })
        
        return jsonify(history_data)
        
    except Exception as e:
        logger.error(f"Benchmark history API error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/performance/api/benchmark/compare', methods=['POST'])
@require_performance_services
def api_benchmark_compare():
    """API endpoint to compare benchmark results"""
    try:
        data = request.get_json()
        baseline_test_id = data.get('baseline_test_id')
        current_test_id = data.get('current_test_id')
        
        if not baseline_test_id or not current_test_id:
            return jsonify({'error': 'Both baseline and current test IDs required'}), 400
        
        comparison = benchmark_manager.compare_results(baseline_test_id, current_test_id)
        
        # Convert to JSON-serializable format
        comparison_data = {
            'improvement_percentage': comparison.improvement_percentage,
            'regression_detected': comparison.regression_detected,
            'significant_changes': comparison.significant_changes,
            'recommendation': comparison.recommendation,
            'baseline_score': comparison.baseline_result.score,
            'current_score': comparison.current_result.score
        }
        
        return jsonify(comparison_data)
        
    except Exception as e:
        logger.error(f"Benchmark comparison API error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/performance/optimization')
@require_performance_services
def optimization():
    """Optimization management page"""
    try:
        # Get optimization status
        status = auto_optimizer.get_optimization_status()
        
        # Get recommendations
        recommendations = auto_optimizer.get_optimization_recommendations()
        
        # Get optimization history
        history = auto_optimizer.get_optimization_history(hours=24)
        
        return render_template('admin/optimization.html',
                             status=status,
                             recommendations=recommendations,
                             history=history)
    
    except Exception as e:
        logger.error(f"Optimization page error: {e}")
        flash(f"Error loading optimization page: {str(e)}", 'error')
        return render_template('admin/error.html', error=str(e))

@admin_bp.route('/performance/monitoring')
@require_performance_services
def monitoring():
    """Performance monitoring page"""
    try:
        # Get performance history
        history = performance_tuner.get_performance_history(hours=24)
        
        # Get performance summary
        summary = performance_tuner.get_performance_summary(hours=24)
        
        # Process data for detailed charts
        chart_data = _prepare_detailed_chart_data(history)
        
        return render_template('admin/performance_monitoring.html',
                             history=history,
                             summary=summary,
                             chart_data=chart_data)
    
    except Exception as e:
        logger.error(f"Monitoring page error: {e}")
        flash(f"Error loading monitoring page: {str(e)}", 'error')
        return render_template('admin/error.html', error=str(e))

@admin_bp.route('/performance/api/performance-history')
@require_performance_services
def api_performance_history():
    """API endpoint for performance history"""
    try:
        hours = request.args.get('hours', 24, type=int)
        history = performance_tuner.get_performance_history(hours)
        
        # Convert to JSON-serializable format
        history_data = {}
        for metric_type, data_points in history.items():
            history_data[metric_type] = [
                {
                    'value': point['value'],
                    'timestamp': point['timestamp']
                }
                for point in data_points
            ]
        
        return jsonify(history_data)
        
    except Exception as e:
        logger.error(f"Performance history API error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/performance/api/system-health')
@require_performance_services
def api_system_health():
    """API endpoint for system health check"""
    try:
        # Get current metrics
        metrics = performance_tuner.get_real_time_metrics()
        
        # Determine health status
        health_status = {
            'status': 'healthy',
            'checks': []
        }
        
        if 'metrics' in metrics:
            for metric_type, data in metrics['metrics'].items():
                if isinstance(data, dict) and 'status' in data:
                    health_status['checks'].append({
                        'name': metric_type,
                        'status': data['status'],
                        'value': data.get('current', 0)
                    })
                    
                    # Update overall status
                    if data['status'] == 'critical':
                        health_status['status'] = 'critical'
                    elif data['status'] == 'warning' and health_status['status'] == 'healthy':
                        health_status['status'] = 'warning'
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"System health API error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/performance/api/export-metrics')
@require_performance_services
def api_export_metrics():
    """API endpoint to export performance metrics"""
    try:
        hours = request.args.get('hours', 24, type=int)
        format_type = request.args.get('format', 'json')
        
        # Get performance data
        history = performance_tuner.get_performance_history(hours)
        summary = performance_tuner.get_performance_summary(hours)
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'period_hours': hours,
            'summary': summary,
            'history': history
        }
        
        if format_type == 'json':
            return jsonify(export_data)
        else:
            # Could implement CSV, Excel export here
            return jsonify({'error': 'Format not supported'}), 400
            
    except Exception as e:
        logger.error(f"Export metrics API error: {e}")
        return jsonify({'error': str(e)}), 500

def _prepare_chart_data(history):
    """Prepare chart data for dashboard"""
    chart_data = {
        'labels': [],
        'datasets': {
            'response_time': [],
            'throughput': [],
            'error_rate': [],
            'memory_usage': [],
            'cpu_usage': []
        }
    }
    
    try:
        # Process history data
        if history:
            # Get timestamps from any metric type
            timestamps = []
            for metric_type, data_points in history.items():
                for point in data_points:
                    if point['timestamp'] not in timestamps:
                        timestamps.append(point['timestamp'])
            
            # Sort timestamps
            timestamps.sort()
            
            # Prepare labels (last 24 hours)
            for ts in timestamps[-24:]:  # Show last 24 data points
                chart_data['labels'].append(ts)
            
            # Prepare data series
            for metric_type, points in history.items():
                if metric_type in chart_data['datasets']:
                    values = [point['value'] for point in points[-24:]]
                    chart_data['datasets'][metric_type] = values
    
    except Exception as e:
        logger.error(f"Chart data preparation error: {e}")
    
    return chart_data

def _prepare_detailed_chart_data(history):
    """Prepare detailed chart data for monitoring page"""
    chart_data = {
        'hourly_performance': {
            'labels': [],
            'response_times': [],
            'throughput': [],
            'error_rates': []
        },
        'system_resources': {
            'labels': [],
            'memory_usage': [],
            'cpu_usage': [],
            'disk_usage': []
        }
    }
    
    try:
        # Process last 24 hours of data
        now = datetime.now()
        hourly_data = {}
        
        # Group data by hour
        for metric_type, data_points in history.items():
            for point in data_points:
                timestamp = datetime.fromisoformat(point['timestamp'])
                hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
                
                if hour_key not in hourly_data:
                    hourly_data[hour_key] = {}
                
                if metric_type not in hourly_data[hour_key]:
                    hourly_data[hour_key][metric_type] = []
                
                hourly_data[hour_key][metric_type].append(point['value'])
        
        # Calculate hourly averages
        sorted_hours = sorted(hourly_data.keys())
        
        for hour in sorted_hours:
            hour_data = hourly_data[hour]
            
            # Performance metrics
            chart_data['hourly_performance']['labels'].append(hour.strftime('%H:%M'))
            chart_data['hourly_performance']['response_times'].append(
                sum(hour_data.get('response_time_avg', [0])) / len(hour_data.get('response_time_avg', [1]))
            )
            chart_data['hourly_performance']['throughput'].append(
                sum(hour_data.get('throughput', [0])) / len(hour_data.get('throughput', [1]))
            )
            chart_data['hourly_performance']['error_rates'].append(
                sum(hour_data.get('error_rate', [0])) / len(hour_data.get('error_rate', [1]))
            )
            
            # System resources
            chart_data['system_resources']['labels'].append(hour.strftime('%H:%M'))
            chart_data['system_resources']['memory_usage'].append(
                sum(hour_data.get('memory_usage', [0])) / len(hour_data.get('memory_usage', [1]))
            )
            chart_data['system_resources']['cpu_usage'].append(
                sum(hour_data.get('cpu_usage', [0])) / len(hour_data.get('cpu_usage', [1]))
            )
            chart_data['system_resources']['disk_usage'].append(
                sum(hour_data.get('disk_usage', [0])) / len(hour_data.get('disk_usage', [1]))
            )
    
    except Exception as e:
        logger.error(f"Detailed chart data preparation error: {e}")
    
    return chart_data

# Error handlers
@admin_bp.errorhandler(404)
def not_found(error):
    return render_template('admin/error.html', error="Page not found"), 404

@admin_bp.errorhandler(500)
def internal_error(error):
    return render_template('admin/error.html', error="Internal server error"), 500

@admin_bp.errorhandler(503)
def service_unavailable(error):
    return render_template('admin/error.html', error="Performance services unavailable"), 503

# Context processors
@admin_bp.context_processor
def inject_performance_status():
    """Inject performance status into templates"""
    if PERFORMANCE_SERVICES_AVAILABLE:
        try:
            status = {
                'services_available': True,
                'optimization_active': auto_optimizer.optimization_active,
                'monitoring_active': performance_tuner.monitoring_active
            }
        except Exception:
            status = {'services_available': False}
    else:
        status = {'services_available': False}
    
    return {'performance_status': status}

if __name__ == '__main__':
    print("🔧 Performance Blueprint - Admin Routes")
    print("Available routes:")
    for rule in admin_bp.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")