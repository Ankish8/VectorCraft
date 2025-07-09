"""
Admin file management routes for VectorCraft
Handles file analytics, storage management, and optimization
"""

import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for

from services.vectorization_service import vectorization_service
from services.file_service import file_service
from services.monitoring.system_logger import system_logger
from database_optimized import db_optimized

# Import admin blueprint
from . import admin_bp


@admin_bp.route('/files')
def index():
    """File management dashboard"""
    try:
        # Get file analytics
        analytics = file_service.get_file_analytics(days=30)
        
        # Get storage summary
        storage_summary = file_service.get_storage_summary()
        
        # Get vectorization analytics
        vectorization_analytics = vectorization_service.get_vectorization_analytics(days=30)
        
        # Get optimization opportunities
        optimization_opportunities = file_service.optimize_storage(action='analyze')
        
        return render_template('admin/file_management/dashboard.html',
                             analytics=analytics,
                             storage_summary=storage_summary,
                             vectorization_analytics=vectorization_analytics,
                             optimization_opportunities=optimization_opportunities)
        
    except Exception as e:
        system_logger.error('admin', f'Error in file management dashboard: {e}')
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('admin/file_management/dashboard.html',
                             analytics={}, storage_summary={}, 
                             vectorization_analytics={}, optimization_opportunities={})


@admin_bp.route('/files/analytics')
def analytics():
    """File analytics page"""
    try:
        days = request.args.get('days', 30, type=int)
        
        # Get comprehensive analytics
        file_analytics = file_service.get_file_analytics(days=days)
        quality_metrics = file_service.get_file_quality_metrics()
        processing_metrics = file_service.monitor_file_processing()
        
        return render_template('admin/file_management/analytics.html',
                             file_analytics=file_analytics,
                             quality_metrics=quality_metrics,
                             processing_metrics=processing_metrics,
                             days=days)
        
    except Exception as e:
        system_logger.error('admin', f'Error in file analytics: {e}')
        flash(f'Error loading analytics: {str(e)}', 'error')
        return render_template('admin/file_management/analytics.html',
                             file_analytics={}, quality_metrics={}, 
                             processing_metrics={}, days=30)


@admin_bp.route('/files/storage')
def storage_management():
    """Storage management page"""
    try:
        # Get storage summary
        storage_summary = file_service.get_storage_summary()
        
        # Get storage analytics
        storage_analytics = file_service.get_storage_analytics()
        
        # Get optimization opportunities
        optimization_analysis = file_service.optimize_storage(action='analyze')
        
        return render_template('admin/file_management/storage.html',
                             storage_summary=storage_summary,
                             storage_analytics=storage_analytics,
                             optimization_analysis=optimization_analysis)
        
    except Exception as e:
        system_logger.error('admin', f'Error in storage management: {e}')
        flash(f'Error loading storage management: {str(e)}', 'error')
        return render_template('admin/file_management/storage.html',
                             storage_summary={}, storage_analytics={}, 
                             optimization_analysis={})


@admin_bp.route('/files/vectorization')
def vectorization_monitoring():
    """Vectorization monitoring page"""
    try:
        days = request.args.get('days', 30, type=int)
        
        # Get vectorization analytics
        vectorization_analytics = vectorization_service.get_vectorization_analytics(days=days)
        
        # Get real-time metrics
        real_time_metrics = vectorization_service.get_real_time_metrics()
        
        # Get quality metrics
        quality_metrics = vectorization_service.get_quality_metrics(days=days)
        
        # Get performance suggestions
        performance_suggestions = vectorization_service.get_performance_optimization_suggestions()
        
        return render_template('admin/file_management/vectorization.html',
                             vectorization_analytics=vectorization_analytics,
                             real_time_metrics=real_time_metrics,
                             quality_metrics=quality_metrics,
                             performance_suggestions=performance_suggestions,
                             days=days)
        
    except Exception as e:
        system_logger.error('admin', f'Error in vectorization monitoring: {e}')
        flash(f'Error loading vectorization monitoring: {str(e)}', 'error')
        return render_template('admin/file_management/vectorization.html',
                             vectorization_analytics={}, real_time_metrics={},
                             quality_metrics={}, performance_suggestions=[], days=30)


@admin_bp.route('/files/quality')
def quality_analyzer():
    """Quality analyzer page"""
    try:
        # Get file quality metrics
        file_quality = file_service.get_file_quality_metrics()
        
        # Get vectorization quality metrics
        vectorization_quality = vectorization_service.get_quality_metrics(days=30)
        
        # Get quality trends
        quality_trends = _get_quality_trends()
        
        return render_template('admin/file_management/quality.html',
                             file_quality=file_quality,
                             vectorization_quality=vectorization_quality,
                             quality_trends=quality_trends)
        
    except Exception as e:
        system_logger.error('admin', f'Error in quality analyzer: {e}')
        flash(f'Error loading quality analyzer: {str(e)}', 'error')
        return render_template('admin/file_management/quality.html',
                             file_quality={}, vectorization_quality={}, 
                             quality_trends={})


@admin_bp.route('/files/optimizer')
def file_optimizer():
    """File processing optimizer page"""
    try:
        # Get optimization opportunities
        optimization_opportunities = file_service.optimize_storage(action='analyze')
        
        # Get performance suggestions
        performance_suggestions = vectorization_service.get_performance_optimization_suggestions()
        
        # Get system metrics
        real_time_metrics = vectorization_service.get_real_time_metrics()
        
        return render_template('admin/file_management/optimizer.html',
                             optimization_opportunities=optimization_opportunities,
                             performance_suggestions=performance_suggestions,
                             real_time_metrics=real_time_metrics)
        
    except Exception as e:
        system_logger.error('admin', f'Error in file optimizer: {e}')
        flash(f'Error loading file optimizer: {str(e)}', 'error')
        return render_template('admin/file_management/optimizer.html',
                             optimization_opportunities={}, performance_suggestions=[], 
                             real_time_metrics={})


# API Routes

@admin_bp.route('/files/api/analytics/<int:days>')
def api_analytics(days):
    """API endpoint for file analytics"""
    try:
        analytics = file_service.get_file_analytics(days=days)
        return jsonify(analytics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/files/api/storage')
def api_storage():
    """API endpoint for storage information"""
    try:
        storage_summary = file_service.get_storage_summary()
        return jsonify(storage_summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/files/api/vectorization/<int:days>')
def api_vectorization(days):
    """API endpoint for vectorization analytics"""
    try:
        analytics = vectorization_service.get_vectorization_analytics(days=days)
        return jsonify(analytics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/files/api/real-time-metrics')
def api_real_time_metrics():
    """API endpoint for real-time metrics"""
    try:
        metrics = vectorization_service.get_real_time_metrics()
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/files/api/quality-metrics/<int:days>')
def api_quality_metrics(days):
    """API endpoint for quality metrics"""
    try:
        quality_metrics = vectorization_service.get_quality_metrics(days=days)
        return jsonify(quality_metrics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/files/api/optimization-opportunities')
def api_optimization_opportunities():
    """API endpoint for optimization opportunities"""
    try:
        opportunities = file_service.optimize_storage(action='analyze')
        return jsonify(opportunities)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Action Routes

@admin_bp.route('/files/action/optimize', methods=['POST'])
def action_optimize():
    """Perform storage optimization"""
    try:
        action = request.json.get('action', 'analyze')
        
        if action not in ['analyze', 'cleanup_temp', 'compress_large_files', 'archive_old_files', 'deduplicate']:
            return jsonify({'error': 'Invalid action'}), 400
        
        result = file_service.optimize_storage(action=action)
        
        # Log the action
        system_logger.info('admin', f'Storage optimization action: {action}',
                          details={'result': result})
        
        return jsonify(result)
        
    except Exception as e:
        system_logger.error('admin', f'Error in storage optimization: {e}')
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/files/action/cleanup-temp', methods=['POST'])
def action_cleanup_temp():
    """Clean up temporary files"""
    try:
        max_age_hours = request.json.get('max_age_hours', 24)
        
        cleaned_count = file_service.cleanup_temp_files(max_age_hours=max_age_hours)
        
        system_logger.info('admin', f'Cleaned {cleaned_count} temporary files',
                          details={'max_age_hours': max_age_hours})
        
        return jsonify({
            'success': True,
            'cleaned_count': cleaned_count,
            'message': f'Cleaned {cleaned_count} temporary files'
        })
        
    except Exception as e:
        system_logger.error('admin', f'Error cleaning temp files: {e}')
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/files/action/refresh-analytics', methods=['POST'])
def action_refresh_analytics():
    """Refresh analytics data"""
    try:
        days = request.json.get('days', 30)
        
        # Get fresh analytics data
        file_analytics = file_service.get_file_analytics(days=days)
        vectorization_analytics = vectorization_service.get_vectorization_analytics(days=days)
        real_time_metrics = vectorization_service.get_real_time_metrics()
        
        return jsonify({
            'success': True,
            'file_analytics': file_analytics,
            'vectorization_analytics': vectorization_analytics,
            'real_time_metrics': real_time_metrics
        })
        
    except Exception as e:
        system_logger.error('admin', f'Error refreshing analytics: {e}')
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/files/action/export-analytics', methods=['POST'])
def action_export_analytics():
    """Export analytics data"""
    try:
        days = request.json.get('days', 30)
        format_type = request.json.get('format', 'json')
        
        # Get analytics data
        analytics_data = {
            'file_analytics': file_service.get_file_analytics(days=days),
            'vectorization_analytics': vectorization_service.get_vectorization_analytics(days=days),
            'storage_summary': file_service.get_storage_summary(),
            'quality_metrics': vectorization_service.get_quality_metrics(days=days),
            'export_timestamp': datetime.now().isoformat(),
            'export_period_days': days
        }
        
        if format_type == 'json':
            return jsonify(analytics_data)
        else:
            return jsonify({'error': 'Unsupported format'}), 400
        
    except Exception as e:
        system_logger.error('admin', f'Error exporting analytics: {e}')
        return jsonify({'error': str(e)}), 500


# Helper Functions

def _get_quality_trends():
    """Get quality trends data"""
    try:
        # This would typically query the database for historical quality data
        # For now, return sample data structure
        return {
            'daily_quality': [],
            'strategy_performance': {},
            'improvement_trends': []
        }
    except Exception as e:
        system_logger.error('admin', f'Error getting quality trends: {e}')
        return {}


def _calculate_storage_efficiency(storage_data):
    """Calculate storage efficiency metrics"""
    try:
        if not storage_data or storage_data.get('total_size', 0) == 0:
            return 0.0
        
        # Calculate efficiency as files per MB
        efficiency = storage_data.get('total_files', 0) / (storage_data.get('total_size', 1) / (1024 * 1024))
        return round(efficiency, 2)
        
    except Exception as e:
        system_logger.error('admin', f'Error calculating storage efficiency: {e}')
        return 0.0


def _get_performance_recommendations(analytics_data):
    """Get performance recommendations based on analytics"""
    try:
        recommendations = []
        
        # Check processing times
        avg_processing_time = analytics_data.get('vectorization_analytics', {}).get('summary', {}).get('avg_processing_time', 0)
        if avg_processing_time > 45:
            recommendations.append({
                'type': 'performance',
                'priority': 'high',
                'title': 'High Processing Times',
                'description': f'Average processing time is {avg_processing_time:.1f} seconds',
                'recommendation': 'Consider optimizing vectorization parameters or hardware'
            })
        
        # Check storage usage
        total_size = analytics_data.get('storage_summary', {}).get('total_size', 0)
        if total_size > 10 * 1024 * 1024 * 1024:  # 10GB
            recommendations.append({
                'type': 'storage',
                'priority': 'medium',
                'title': 'High Storage Usage',
                'description': f'Total storage usage is {total_size / (1024**3):.1f} GB',
                'recommendation': 'Implement file cleanup and compression policies'
            })
        
        return recommendations
        
    except Exception as e:
        system_logger.error('admin', f'Error getting performance recommendations: {e}')
        return []


# Error Handlers

@file_management_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('admin/file_management/error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404


@file_management_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    system_logger.error('admin', f'Internal error in file management: {error}')
    return render_template('admin/file_management/error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500


if __name__ == '__main__':
    print("File Management Blueprint - VectorCraft Admin")
    print("Routes registered:")
    for rule in file_management_bp.url_map.iter_rules():
        print(f"  {rule.rule} [{', '.join(rule.methods)}]")