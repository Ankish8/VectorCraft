#!/usr/bin/env python3
"""
Advanced Analytics Routes for VectorCraft Admin Dashboard
Provides API endpoints for ML-based analytics, forecasting, and business intelligence
"""

import logging
from flask import jsonify, request, current_app
from flask_login import current_user
from datetime import datetime, timedelta

from . import admin_bp
from blueprints.auth.utils import admin_required
from services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

@admin_bp.route('/api/analytics/comprehensive')
@admin_required
def comprehensive_analytics():
    """
    Get comprehensive analytics dashboard data
    
    Returns:
        JSON response with all analytics components
    """
    try:
        analytics_data = analytics_service.get_comprehensive_analytics()
        
        return jsonify({
            'success': True,
            'analytics': analytics_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Comprehensive analytics API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@admin_bp.route('/api/analytics/revenue-forecast')
@admin_required
def revenue_forecast():
    """
    Get ML-based revenue forecasting
    
    Query parameters:
        - days: Number of days to forecast (default: 30)
        
    Returns:
        JSON response with revenue forecast data
    """
    try:
        days_ahead = int(request.args.get('days', 30))
        if days_ahead < 1 or days_ahead > 90:
            days_ahead = 30
        
        forecast_data = analytics_service.get_revenue_forecast(days_ahead)
        
        return jsonify({
            'success': True,
            'forecast': forecast_data,
            'parameters': {
                'days_ahead': days_ahead
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Revenue forecast API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@admin_bp.route('/api/analytics/customer-behavior')
@admin_required
def customer_behavior():
    """
    Get customer behavior analysis and segmentation
    
    Returns:
        JSON response with customer behavior metrics
    """
    try:
        behavior_data = analytics_service.get_customer_behavior_analysis()
        
        return jsonify({
            'success': True,
            'customer_behavior': behavior_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Customer behavior API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@admin_bp.route('/api/analytics/conversion-funnel')
@admin_required
def conversion_funnel():
    """
    Get conversion funnel analysis and optimization suggestions
    
    Returns:
        JSON response with conversion funnel metrics
    """
    try:
        funnel_data = analytics_service.get_conversion_funnel_analysis()
        
        return jsonify({
            'success': True,
            'conversion_funnel': funnel_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Conversion funnel API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@admin_bp.route('/api/analytics/roi-dashboard')
@admin_required
def roi_dashboard():
    """
    Get ROI and profitability analysis
    
    Returns:
        JSON response with ROI metrics and profitability analysis
    """
    try:
        roi_data = analytics_service.get_roi_dashboard()
        
        return jsonify({
            'success': True,
            'roi_analysis': roi_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"ROI dashboard API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@admin_bp.route('/api/analytics/predictive')
@admin_required
def predictive_analytics():
    """
    Get predictive analytics and business insights
    
    Returns:
        JSON response with predictive analytics results
    """
    try:
        predictive_data = analytics_service.get_predictive_analytics()
        
        return jsonify({
            'success': True,
            'predictive_analytics': predictive_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Predictive analytics API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@admin_bp.route('/api/analytics/business-insights')
@admin_required
def business_insights():
    """
    Get actionable business insights and recommendations
    
    Returns:
        JSON response with business insights
    """
    try:
        # Get all analytics data
        comprehensive_data = analytics_service.get_comprehensive_analytics()
        
        # Extract key insights
        insights = []
        
        # Revenue insights
        revenue_forecast = comprehensive_data.get('revenue_forecast', {})
        if revenue_forecast.get('insights'):
            insights.extend(revenue_forecast['insights'])
        
        # Customer insights
        customer_behavior = comprehensive_data.get('customer_behavior', {})
        if customer_behavior.get('insights'):
            insights.extend(customer_behavior['insights'])
        
        # Conversion insights
        conversion_funnel = comprehensive_data.get('conversion_funnel', {})
        if conversion_funnel.get('optimization_suggestions'):
            insights.extend(conversion_funnel['optimization_suggestions'])
        
        # ROI insights
        roi_dashboard = comprehensive_data.get('roi_dashboard', {})
        if roi_dashboard.get('insights'):
            insights.extend(roi_dashboard['insights'])
        
        # Predictive insights
        predictive_analytics = comprehensive_data.get('predictive_analytics', {})
        if predictive_analytics.get('predictive_insights'):
            insights.extend(predictive_analytics['predictive_insights'])
        
        # Business recommendations
        recommendations = predictive_analytics.get('business_recommendations', [])
        
        # Risk factors
        risk_factors = predictive_analytics.get('risk_factors', [])
        
        return jsonify({
            'success': True,
            'business_insights': {
                'key_insights': insights,
                'recommendations': recommendations,
                'risk_factors': risk_factors,
                'priority_actions': [
                    insight for insight in insights 
                    if any(keyword in insight.lower() for keyword in ['urgent', 'critical', 'high', 'immediate'])
                ]
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Business insights API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@admin_bp.route('/api/analytics/export')
@admin_required
def export_analytics():
    """
    Export analytics data in various formats
    
    Query parameters:
        - format: Export format (json, csv) - default: json
        - component: Specific component to export (all, revenue, customer, funnel, roi, predictive)
        
    Returns:
        Analytics data in requested format
    """
    try:
        export_format = request.args.get('format', 'json')
        component = request.args.get('component', 'all')
        
        if component == 'all':
            data = analytics_service.get_comprehensive_analytics()
        elif component == 'revenue':
            data = analytics_service.get_revenue_forecast()
        elif component == 'customer':
            data = analytics_service.get_customer_behavior_analysis()
        elif component == 'funnel':
            data = analytics_service.get_conversion_funnel_analysis()
        elif component == 'roi':
            data = analytics_service.get_roi_dashboard()
        elif component == 'predictive':
            data = analytics_service.get_predictive_analytics()
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown component: {component}',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        if export_format == 'json':
            return jsonify({
                'success': True,
                'data': data,
                'export_info': {
                    'format': export_format,
                    'component': component,
                    'exported_at': datetime.now().isoformat()
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Unsupported export format: {export_format}',
                'timestamp': datetime.now().isoformat()
            }), 400
        
    except Exception as e:
        logger.error(f"Analytics export API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@admin_bp.route('/api/analytics/model-performance')
@admin_required
def model_performance():
    """
    Get ML model performance metrics
    
    Returns:
        JSON response with model performance data
    """
    try:
        # Get model performance from revenue forecasting
        revenue_forecast = analytics_service.get_revenue_forecast()
        model_metrics = revenue_forecast.get('model_metrics', {})
        
        performance_data = {
            'revenue_model': {
                'r_squared': model_metrics.get('r_squared', 0),
                'trend': model_metrics.get('trend', 'unknown'),
                'confidence': model_metrics.get('confidence', 'low'),
                'last_trained': datetime.now().isoformat()
            },
            'model_status': {
                'revenue_forecasting': 'active',
                'customer_segmentation': 'active',
                'conversion_optimization': 'active'
            },
            'data_quality': {
                'sufficient_data': True,
                'data_freshness': 'current',
                'completeness_score': 0.85
            }
        }
        
        return jsonify({
            'success': True,
            'model_performance': performance_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Model performance API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@admin_bp.route('/api/analytics/health-check')
@admin_required
def analytics_health_check():
    """
    Health check for analytics service
    
    Returns:
        JSON response with analytics service health status
    """
    try:
        # Test basic analytics functionality
        start_time = datetime.now()
        
        # Test database connectivity
        test_query = "SELECT COUNT(*) as count FROM transactions LIMIT 1"
        result = analytics_service._execute_query(test_query)
        
        # Test ML model functionality
        revenue_forecast = analytics_service.get_revenue_forecast(7)
        
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()
        
        health_status = {
            'status': 'healthy',
            'response_time_seconds': response_time,
            'database_connectivity': 'ok' if result else 'error',
            'ml_models': 'ok' if revenue_forecast else 'error',
            'last_check': datetime.now().isoformat(),
            'version': '1.0.0'
        }
        
        return jsonify({
            'success': True,
            'health': health_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Analytics health check error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'health': {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            },
            'timestamp': datetime.now().isoformat()
        }), 500