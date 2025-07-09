#!/usr/bin/env python3
"""
Admin Pricing Management Routes for VectorCraft

This module provides comprehensive admin routes for pricing management including:
- Dynamic pricing tier management
- Discount code creation and management
- Pricing analytics and reporting
- Revenue optimization tools
- A/B testing for pricing strategies
"""

import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from functools import wraps

from services.pricing_manager import pricing_manager
from services.discount_engine import discount_engine
from database import db


# Import admin blueprint
from . import admin_bp
logger = logging.getLogger(__name__)


def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/pricing/dashboard')
@admin_required
def pricing_dashboard():
    """Main pricing dashboard"""
    try:
        # Get pricing summary
        pricing_summary = pricing_manager.get_pricing_summary()
        
        # Get discount summary
        discount_summary = discount_engine.get_discount_summary()
        
        # Get revenue analytics
        revenue_analytics = db.get_revenue_summary(days=30)
        
        # Get recent pricing changes
        recent_changes = db.get_pricing_history(limit=10)
        
        return render_template('admin/pricing_dashboard.html',
                             pricing_summary=pricing_summary,
                             discount_summary=discount_summary,
                             revenue_analytics=revenue_analytics,
                             recent_changes=recent_changes)
        
    except Exception as e:
        logger.error(f"Error loading pricing dashboard: {e}")
        flash('Error loading pricing dashboard', 'error')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/pricing/tiers')
@admin_required
def manage_tiers():
    """Manage pricing tiers"""
    try:
        tiers = pricing_manager.get_pricing_tiers()
        
        return render_template('admin/pricing_tiers.html', tiers=tiers)
        
    except Exception as e:
        logger.error(f"Error loading pricing tiers: {e}")
        flash('Error loading pricing tiers', 'error')
        return redirect(url_for('pricing.pricing_dashboard'))


@admin_bp.route('/pricing/tiers/create', methods=['GET', 'POST'])
@admin_required
def create_tier():
    """Create new pricing tier"""
    if request.method == 'POST':
        try:
            tier_data = {
                'name': request.form.get('name'),
                'base_price': float(request.form.get('base_price')),
                'description': request.form.get('description'),
                'max_uploads': int(request.form.get('max_uploads', -1)),
                'max_file_size': int(request.form.get('max_file_size', -1)),
                'priority_processing': request.form.get('priority_processing') == 'on',
                'features': request.form.getlist('features'),
                'is_active': request.form.get('is_active') == 'on',
                'sort_order': int(request.form.get('sort_order', 0))
            }
            
            tier_id = pricing_manager.create_pricing_tier(tier_data)
            
            if tier_id:
                flash(f'Pricing tier "{tier_data["name"]}" created successfully', 'success')
                return redirect(url_for('pricing.manage_tiers'))
            else:
                flash('Error creating pricing tier', 'error')
                
        except Exception as e:
            logger.error(f"Error creating pricing tier: {e}")
            flash('Error creating pricing tier', 'error')
    
    return render_template('admin/create_tier.html')


@admin_bp.route('/pricing/tiers/<tier_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_tier(tier_id):
    """Edit pricing tier"""
    try:
        tier = pricing_manager.get_pricing_tier(tier_id)
        if not tier:
            flash('Pricing tier not found', 'error')
            return redirect(url_for('pricing.manage_tiers'))
        
        if request.method == 'POST':
            updates = {}
            
            # Get form data
            if request.form.get('name'):
                updates['name'] = request.form.get('name')
            if request.form.get('base_price'):
                updates['base_price'] = float(request.form.get('base_price'))
            if request.form.get('description'):
                updates['description'] = request.form.get('description')
            if request.form.get('max_uploads'):
                updates['max_uploads'] = int(request.form.get('max_uploads'))
            if request.form.get('max_file_size'):
                updates['max_file_size'] = int(request.form.get('max_file_size'))
            
            updates['priority_processing'] = request.form.get('priority_processing') == 'on'
            updates['is_active'] = request.form.get('is_active') == 'on'
            
            if request.form.getlist('features'):
                updates['features'] = request.form.getlist('features')
            
            if request.form.get('sort_order'):
                updates['sort_order'] = int(request.form.get('sort_order'))
            
            # Track changes
            updates['changed_by'] = session.get('admin_username', 'Admin')
            updates['change_reason'] = request.form.get('change_reason', 'Manual update')
            
            success = pricing_manager.update_pricing_tier(tier_id, updates)
            
            if success:
                flash(f'Pricing tier updated successfully', 'success')
                return redirect(url_for('pricing.manage_tiers'))
            else:
                flash('Error updating pricing tier', 'error')
        
        return render_template('admin/edit_tier.html', tier=tier)
        
    except Exception as e:
        logger.error(f"Error editing pricing tier: {e}")
        flash('Error editing pricing tier', 'error')
        return redirect(url_for('pricing.manage_tiers'))


@admin_bp.route('/pricing/tiers/<tier_id>/analytics')
@admin_required
def tier_analytics(tier_id):
    """View tier analytics"""
    try:
        tier = pricing_manager.get_pricing_tier(tier_id)
        if not tier:
            flash('Pricing tier not found', 'error')
            return redirect(url_for('pricing.manage_tiers'))
        
        analytics = pricing_manager.get_tier_analytics(tier_id, days=30)
        optimization = pricing_manager.optimize_pricing(tier_id)
        forecast = pricing_manager.get_revenue_forecast(tier_id)
        
        return render_template('admin/tier_analytics.html',
                             tier=tier,
                             analytics=analytics,
                             optimization=optimization,
                             forecast=forecast)
        
    except Exception as e:
        logger.error(f"Error loading tier analytics: {e}")
        flash('Error loading tier analytics', 'error')
        return redirect(url_for('pricing.manage_tiers'))


@admin_bp.route('/pricing/discounts')
@admin_required
def manage_discounts():
    """Manage discount codes"""
    try:
        discounts = db.get_discounts()
        
        return render_template('admin/pricing_discounts.html', discounts=discounts)
        
    except Exception as e:
        logger.error(f"Error loading discounts: {e}")
        flash('Error loading discounts', 'error')
        return redirect(url_for('pricing.pricing_dashboard'))


@admin_bp.route('/pricing/discounts/create', methods=['GET', 'POST'])
@admin_required
def create_discount():
    """Create new discount code"""
    if request.method == 'POST':
        try:
            discount_data = {
                'name': request.form.get('name'),
                'code': request.form.get('code'),
                'discount_type': request.form.get('discount_type'),
                'discount_value': float(request.form.get('discount_value')),
                'description': request.form.get('description'),
                'min_amount': float(request.form.get('min_amount', 0)),
                'max_discount': float(request.form.get('max_discount')) if request.form.get('max_discount') else None,
                'usage_limit': int(request.form.get('usage_limit', -1)),
                'per_user_limit': int(request.form.get('per_user_limit', -1)),
                'is_active': request.form.get('is_active') == 'on',
                'is_public': request.form.get('is_public') == 'on',
                'valid_from': request.form.get('valid_from'),
                'valid_until': request.form.get('valid_until'),
                'first_time_only': request.form.get('first_time_only') == 'on'
            }
            
            # Handle arrays
            if request.form.getlist('applicable_tiers'):
                discount_data['applicable_tiers'] = request.form.getlist('applicable_tiers')
            
            if request.form.get('target_countries'):
                discount_data['target_countries'] = request.form.get('target_countries').split(',')
            
            if request.form.get('target_emails'):
                discount_data['target_emails'] = request.form.get('target_emails').split(',')
            
            discount_id = discount_engine.create_discount_code(discount_data)
            
            if discount_id:
                flash(f'Discount code "{discount_data["code"]}" created successfully', 'success')
                return redirect(url_for('pricing.manage_discounts'))
            else:
                flash('Error creating discount code', 'error')
                
        except Exception as e:
            logger.error(f"Error creating discount: {e}")
            flash('Error creating discount code', 'error')
    
    # Get pricing tiers for form
    tiers = pricing_manager.get_pricing_tiers()
    
    return render_template('admin/create_discount.html', tiers=tiers)


@admin_bp.route('/pricing/discounts/bulk', methods=['GET', 'POST'])
@admin_required
def bulk_create_discounts():
    """Bulk create discount codes"""
    if request.method == 'POST':
        try:
            template = {
                'name': request.form.get('name'),
                'discount_type': request.form.get('discount_type'),
                'discount_value': float(request.form.get('discount_value')),
                'description': request.form.get('description'),
                'min_amount': float(request.form.get('min_amount', 0)),
                'usage_limit': int(request.form.get('usage_limit', -1)),
                'per_user_limit': int(request.form.get('per_user_limit', -1)),
                'is_active': request.form.get('is_active') == 'on',
                'is_public': request.form.get('is_public') == 'on',
                'valid_from': request.form.get('valid_from'),
                'valid_until': request.form.get('valid_until')
            }
            
            count = int(request.form.get('count', 10))
            prefix = request.form.get('prefix', '')
            
            codes = discount_engine.bulk_create_discount_codes(template, count, prefix)
            
            if codes:
                flash(f'Successfully created {len(codes)} discount codes', 'success')
                return redirect(url_for('pricing.manage_discounts'))
            else:
                flash('Error creating discount codes', 'error')
                
        except Exception as e:
            logger.error(f"Error bulk creating discounts: {e}")
            flash('Error creating discount codes', 'error')
    
    return render_template('admin/bulk_create_discounts.html')


@admin_bp.route('/pricing/discounts/<discount_id>/analytics')
@admin_required
def discount_analytics(discount_id):
    """View discount analytics"""
    try:
        discount = db.get_discount(discount_id=discount_id)
        if not discount:
            flash('Discount not found', 'error')
            return redirect(url_for('pricing.manage_discounts'))
        
        analytics = discount_engine.get_discount_analytics(discount_id, days=30)
        usage_stats = db.get_discount_usage_stats(discount_id)
        
        return render_template('admin/discount_analytics.html',
                             discount=discount,
                             analytics=analytics,
                             usage_stats=usage_stats)
        
    except Exception as e:
        logger.error(f"Error loading discount analytics: {e}")
        flash('Error loading discount analytics', 'error')
        return redirect(url_for('pricing.manage_discounts'))


@admin_bp.route('/pricing/analytics')
@admin_required
def pricing_analytics():
    """Comprehensive pricing analytics"""
    try:
        # Get date range from query params
        days = int(request.args.get('days', 30))
        
        # Get pricing analytics
        pricing_analytics = db.get_pricing_analytics(days=days)
        
        # Get revenue summary
        revenue_summary = db.get_revenue_summary(days=days)
        
        # Get discount analytics
        discount_analytics = discount_engine.get_discount_analytics(days=days)
        
        # Get optimization suggestions
        optimization = pricing_manager.optimize_pricing('all')
        
        return render_template('admin/pricing_analytics.html',
                             pricing_analytics=pricing_analytics,
                             revenue_summary=revenue_summary,
                             discount_analytics=discount_analytics,
                             optimization=optimization,
                             days=days)
        
    except Exception as e:
        logger.error(f"Error loading pricing analytics: {e}")
        flash('Error loading pricing analytics', 'error')
        return redirect(url_for('pricing.pricing_dashboard'))


@admin_bp.route('/pricing/api/tiers/<tier_id>/price', methods=['POST'])
@admin_required
def update_tier_price():
    """API endpoint to update tier price"""
    try:
        tier_id = request.json.get('tier_id')
        new_price = float(request.json.get('price'))
        reason = request.json.get('reason', 'Quick price update')
        
        current_tier = pricing_manager.get_pricing_tier(tier_id)
        if not current_tier:
            return jsonify({'error': 'Tier not found'}), 404
        
        success = pricing_manager.update_pricing_tier(tier_id, {
            'base_price': new_price,
            'change_reason': reason,
            'changed_by': session.get('admin_username', 'Admin')
        })
        
        if success:
            return jsonify({'success': True, 'new_price': new_price})
        else:
            return jsonify({'error': 'Failed to update price'}), 500
            
    except Exception as e:
        logger.error(f"Error updating tier price: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/pricing/api/discounts/validate', methods=['POST'])
@admin_required
def validate_discount_api():
    """API endpoint to validate discount code"""
    try:
        code = request.json.get('code')
        user_email = request.json.get('user_email')
        tier_id = request.json.get('tier_id')
        amount = float(request.json.get('amount', 0))
        
        discount, error = discount_engine.validate_discount_code(code, user_email, tier_id, amount)
        
        if error:
            return jsonify({'valid': False, 'error': error})
        else:
            return jsonify({
                'valid': True,
                'discount': {
                    'code': discount['code'],
                    'name': discount['name'],
                    'discount_type': discount['discount_type'],
                    'discount_value': discount['discount_value'],
                    'description': discount['description']
                }
            })
            
    except Exception as e:
        logger.error(f"Error validating discount: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/pricing/api/analytics/revenue', methods=['GET'])
@admin_required
def revenue_analytics_api():
    """API endpoint for revenue analytics data"""
    try:
        days = int(request.args.get('days', 30))
        tier_id = request.args.get('tier_id')
        
        if tier_id:
            analytics = pricing_manager.get_tier_analytics(tier_id, days)
        else:
            analytics = db.get_pricing_analytics(days=days)
        
        return jsonify(analytics)
        
    except Exception as e:
        logger.error(f"Error getting revenue analytics: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/pricing/api/forecast', methods=['GET'])
@admin_required
def forecast_api():
    """API endpoint for revenue forecast"""
    try:
        tier_id = request.args.get('tier_id')
        days = int(request.args.get('days', 30))
        
        forecast = pricing_manager.get_revenue_forecast(tier_id, days)
        
        return jsonify(forecast)
        
    except Exception as e:
        logger.error(f"Error getting forecast: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/pricing/api/optimization/<tier_id>', methods=['GET'])
@admin_required
def optimization_api(tier_id):
    """API endpoint for pricing optimization suggestions"""
    try:
        optimization = pricing_manager.optimize_pricing(tier_id)
        
        return jsonify(optimization)
        
    except Exception as e:
        logger.error(f"Error getting optimization: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/pricing/experiments')
@admin_required
def pricing_experiments():
    """Manage pricing experiments (A/B testing)"""
    try:
        # Get active experiments (would need to implement in database)
        experiments = []  # Placeholder
        
        return render_template('admin/pricing_experiments.html', experiments=experiments)
        
    except Exception as e:
        logger.error(f"Error loading pricing experiments: {e}")
        flash('Error loading pricing experiments', 'error')
        return redirect(url_for('pricing.pricing_dashboard'))


@admin_bp.route('/pricing/settings')
@admin_required
def pricing_settings():
    """Pricing system settings"""
    try:
        # Get current settings
        settings = {
            'default_currency': 'USD',
            'currency_conversion_enabled': True,
            'auto_discount_cleanup': True,
            'analytics_retention_days': 365
        }
        
        return render_template('admin/pricing_settings.html', settings=settings)
        
    except Exception as e:
        logger.error(f"Error loading pricing settings: {e}")
        flash('Error loading pricing settings', 'error')
        return redirect(url_for('pricing.pricing_dashboard'))


@admin_bp.route('/pricing/export/discounts')
@admin_required
def export_discounts():
    """Export discount codes to CSV"""
    try:
        import csv
        import io
        from flask import make_response
        
        discounts = db.get_discounts()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Code', 'Name', 'Type', 'Value', 'Usage Count', 'Status', 'Created'])
        
        # Write data
        for discount in discounts:
            writer.writerow([
                discount['code'],
                discount['name'],
                discount['discount_type'],
                discount['discount_value'],
                discount['usage_count'],
                'Active' if discount['is_active'] else 'Inactive',
                discount['created_at']
            ])
        
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=discounts.csv'
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting discounts: {e}")
        flash('Error exporting discounts', 'error')
        return redirect(url_for('pricing.manage_discounts'))


@admin_bp.route('/pricing/cleanup')
@admin_required
def cleanup_expired():
    """Clean up expired discounts"""
    try:
        count = discount_engine.cleanup_expired_discounts()
        
        if count > 0:
            flash(f'Cleaned up {count} expired discount codes', 'success')
        else:
            flash('No expired discount codes found', 'info')
        
        return redirect(url_for('pricing.manage_discounts'))
        
    except Exception as e:
        logger.error(f"Error cleaning up expired discounts: {e}")
        flash('Error cleaning up expired discounts', 'error')
        return redirect(url_for('pricing.manage_discounts'))


# Error handlers
@pricing_bp.errorhandler(404)
def not_found(error):
    flash('Page not found', 'error')
    return redirect(url_for('pricing.pricing_dashboard'))


@pricing_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error in pricing module: {error}")
    flash('Internal server error', 'error')
    return redirect(url_for('pricing.pricing_dashboard'))