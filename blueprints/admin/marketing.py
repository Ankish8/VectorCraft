"""
Admin Marketing Blueprint - Routes and Views
Provides comprehensive marketing management interface for the admin dashboard.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from datetime import datetime, timedelta
from functools import wraps
import json
import logging
from typing import Dict, List, Optional, Any

from services.marketing_manager import MarketingManager
from services.customer_journey import CustomerJourneyManager
from services.engagement_engine import EngagementAutomationEngine
from services.database_pool import DatabasePool
from services.email_service import EmailService
from services.analytics_service import AnalyticsService
from services.monitoring.system_logger import SystemLogger

# Create blueprint
marketing_bp = Blueprint('admin_marketing', __name__, url_prefix='/admin/marketing')

logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_marketing_services():
    """Get marketing service instances"""
    from app import db_pool, email_service, analytics_service, system_logger
    
    marketing_manager = MarketingManager(db_pool, email_service, analytics_service, system_logger)
    journey_manager = CustomerJourneyManager(db_pool, email_service, system_logger)
    engagement_engine = EngagementAutomationEngine(db_pool, email_service, system_logger)
    
    return marketing_manager, journey_manager, engagement_engine

# Dashboard Routes

@marketing_bp.route('/')
@marketing_bp.route('/dashboard')
@admin_required
def dashboard():
    """Marketing dashboard overview"""
    try:
        marketing_manager, journey_manager, engagement_engine = get_marketing_services()
        
        # Get dashboard data
        marketing_data = marketing_manager.get_marketing_dashboard_data()
        journey_data = journey_manager.get_journey_dashboard_data()
        engagement_data = engagement_engine.get_engagement_dashboard_data()
        
        return render_template('admin/marketing/dashboard.html',
                             marketing_data=marketing_data,
                             journey_data=journey_data,
                             engagement_data=engagement_data,
                             title='Marketing Dashboard')
    
    except Exception as e:
        logger.error(f"Error loading marketing dashboard: {str(e)}")
        flash('Error loading marketing dashboard', 'error')
        return redirect(url_for('admin.dashboard'))

# Campaign Management Routes

@marketing_bp.route('/campaigns')
@admin_required
def campaigns():
    """List all marketing campaigns"""
    try:
        marketing_manager, _, _ = get_marketing_services()
        
        # Get filter parameters
        status = request.args.get('status')
        campaign_type = request.args.get('type')
        
        campaigns = marketing_manager.get_campaigns(status, campaign_type)
        
        return render_template('admin/marketing/campaigns.html',
                             campaigns=campaigns,
                             title='Marketing Campaigns')
    
    except Exception as e:
        logger.error(f"Error loading campaigns: {str(e)}")
        flash('Error loading campaigns', 'error')
        return redirect(url_for('admin_marketing.dashboard'))

@marketing_bp.route('/campaigns/create', methods=['GET', 'POST'])
@admin_required
def create_campaign():
    """Create new marketing campaign"""
    try:
        if request.method == 'POST':
            marketing_manager, _, _ = get_marketing_services()
            
            campaign_data = {
                'name': request.form.get('name'),
                'campaign_type': request.form.get('campaign_type'),
                'status': request.form.get('status', 'draft'),
                'target_audience': json.loads(request.form.get('target_audience', '{}')),
                'content_config': json.loads(request.form.get('content_config', '{}')),
                'schedule_config': json.loads(request.form.get('schedule_config', '{}')),
                'budget_config': json.loads(request.form.get('budget_config', '{}')),
                'created_by': session.get('admin_username', 'admin'),
                'start_date': datetime.fromisoformat(request.form.get('start_date')) if request.form.get('start_date') else None,
                'end_date': datetime.fromisoformat(request.form.get('end_date')) if request.form.get('end_date') else None
            }
            
            campaign = marketing_manager.create_campaign(campaign_data)
            flash(f'Campaign "{campaign.name}" created successfully', 'success')
            return redirect(url_for('admin_marketing.campaigns'))
        
        return render_template('admin/marketing/create_campaign.html',
                             title='Create Campaign')
    
    except Exception as e:
        logger.error(f"Error creating campaign: {str(e)}")
        flash('Error creating campaign', 'error')
        return redirect(url_for('admin_marketing.campaigns'))

@marketing_bp.route('/campaigns/<campaign_id>')
@admin_required
def campaign_detail(campaign_id):
    """View campaign details and performance"""
    try:
        marketing_manager, _, _ = get_marketing_services()
        
        # Get campaign performance
        performance = marketing_manager.get_campaign_performance(campaign_id)
        
        if not performance:
            flash('Campaign not found', 'error')
            return redirect(url_for('admin_marketing.campaigns'))
        
        return render_template('admin/marketing/campaign_detail.html',
                             campaign=performance,
                             title=f'Campaign: {performance.get("campaign_name", "Unknown")}')
    
    except Exception as e:
        logger.error(f"Error loading campaign details: {str(e)}")
        flash('Error loading campaign details', 'error')
        return redirect(url_for('admin_marketing.campaigns'))

@marketing_bp.route('/campaigns/<campaign_id>/analytics')
@admin_required
def campaign_analytics(campaign_id):
    """View detailed campaign analytics"""
    try:
        marketing_manager, _, engagement_engine = get_marketing_services()
        
        # Get campaign analytics
        analytics = engagement_engine.get_engagement_analytics(campaign_id)
        
        return render_template('admin/marketing/campaign_analytics.html',
                             analytics=analytics,
                             campaign_id=campaign_id,
                             title='Campaign Analytics')
    
    except Exception as e:
        logger.error(f"Error loading campaign analytics: {str(e)}")
        flash('Error loading campaign analytics', 'error')
        return redirect(url_for('admin_marketing.campaigns'))

# Customer Journey Routes

@marketing_bp.route('/journeys')
@admin_required
def customer_journeys():
    """List all customer journeys"""
    try:
        _, journey_manager, _ = get_marketing_services()
        
        journeys = journey_manager.get_all_journeys()
        
        return render_template('admin/marketing/journeys.html',
                             journeys=journeys,
                             title='Customer Journeys')
    
    except Exception as e:
        logger.error(f"Error loading customer journeys: {str(e)}")
        flash('Error loading customer journeys', 'error')
        return redirect(url_for('admin_marketing.dashboard'))

@marketing_bp.route('/journeys/create', methods=['GET', 'POST'])
@admin_required
def create_journey():
    """Create new customer journey"""
    try:
        if request.method == 'POST':
            _, journey_manager, _ = get_marketing_services()
            
            journey_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'trigger_type': request.form.get('trigger_type'),
                'trigger_conditions': json.loads(request.form.get('trigger_conditions', '{}')),
                'is_active': request.form.get('is_active') == 'on',
                'created_by': session.get('admin_username', 'admin')
            }
            
            journey_id = journey_manager.create_journey(journey_data)
            flash(f'Journey "{journey_data["name"]}" created successfully', 'success')
            return redirect(url_for('admin_marketing.journey_detail', journey_id=journey_id))
        
        return render_template('admin/marketing/create_journey.html',
                             title='Create Customer Journey')
    
    except Exception as e:
        logger.error(f"Error creating journey: {str(e)}")
        flash('Error creating journey', 'error')
        return redirect(url_for('admin_marketing.customer_journeys'))

@marketing_bp.route('/journeys/<journey_id>')
@admin_required
def journey_detail(journey_id):
    """View journey details and analytics"""
    try:
        _, journey_manager, _ = get_marketing_services()
        
        # Get journey analytics
        analytics = journey_manager.get_journey_analytics(journey_id)
        
        if not analytics:
            flash('Journey not found', 'error')
            return redirect(url_for('admin_marketing.customer_journeys'))
        
        return render_template('admin/marketing/journey_detail.html',
                             analytics=analytics,
                             journey_id=journey_id,
                             title=f'Journey Analytics')
    
    except Exception as e:
        logger.error(f"Error loading journey details: {str(e)}")
        flash('Error loading journey details', 'error')
        return redirect(url_for('admin_marketing.customer_journeys'))

@marketing_bp.route('/journeys/<journey_id>/steps', methods=['GET', 'POST'])
@admin_required
def journey_steps(journey_id):
    """Manage journey steps"""
    try:
        if request.method == 'POST':
            _, journey_manager, _ = get_marketing_services()
            
            step_data = {
                'step_name': request.form.get('step_name'),
                'step_type': request.form.get('step_type'),
                'step_order': int(request.form.get('step_order', 1)),
                'trigger_conditions': json.loads(request.form.get('trigger_conditions', '{}')),
                'actions': json.loads(request.form.get('actions', '[]')),
                'success_criteria': json.loads(request.form.get('success_criteria', '{}')),
                'failure_criteria': json.loads(request.form.get('failure_criteria', '{}')),
                'next_step_id': request.form.get('next_step_id') or None,
                'alternative_step_id': request.form.get('alternative_step_id') or None,
                'is_active': request.form.get('is_active') == 'on'
            }
            
            step_id = journey_manager.add_journey_step(journey_id, step_data)
            flash(f'Step "{step_data["step_name"]}" added successfully', 'success')
            return redirect(url_for('admin_marketing.journey_steps', journey_id=journey_id))
        
        return render_template('admin/marketing/journey_steps.html',
                             journey_id=journey_id,
                             title='Journey Steps')
    
    except Exception as e:
        logger.error(f"Error managing journey steps: {str(e)}")
        flash('Error managing journey steps', 'error')
        return redirect(url_for('admin_marketing.journey_detail', journey_id=journey_id))

# Lead Management Routes

@marketing_bp.route('/leads')
@admin_required
def leads():
    """List and manage leads"""
    try:
        marketing_manager, _, _ = get_marketing_services()
        
        # Get filter parameters
        qualification_status = request.args.get('status')
        limit = int(request.args.get('limit', 100))
        
        leads = marketing_manager.get_lead_scores(qualification_status, limit)
        
        return render_template('admin/marketing/leads.html',
                             leads=leads,
                             title='Lead Management')
    
    except Exception as e:
        logger.error(f"Error loading leads: {str(e)}")
        flash('Error loading leads', 'error')
        return redirect(url_for('admin_marketing.dashboard'))

@marketing_bp.route('/leads/<lead_id>')
@admin_required
def lead_detail(lead_id):
    """View lead details and history"""
    try:
        marketing_manager, _, engagement_engine = get_marketing_services()
        
        # Get lead details (simplified - would need enhancement)
        leads = marketing_manager.get_lead_scores(limit=1000)
        lead = next((l for l in leads if l.lead_id == lead_id), None)
        
        if not lead:
            flash('Lead not found', 'error')
            return redirect(url_for('admin_marketing.leads'))
        
        # Get engagement profile
        engagement_profile = engagement_engine.get_customer_engagement_profile(lead.user_id or lead.email)
        
        return render_template('admin/marketing/lead_detail.html',
                             lead=lead,
                             engagement_profile=engagement_profile,
                             title=f'Lead: {lead.email}')
    
    except Exception as e:
        logger.error(f"Error loading lead details: {str(e)}")
        flash('Error loading lead details', 'error')
        return redirect(url_for('admin_marketing.leads'))

# Engagement Automation Routes

@marketing_bp.route('/automation')
@admin_required
def automation():
    """Engagement automation overview"""
    try:
        _, _, engagement_engine = get_marketing_services()
        
        # Get automation analytics
        analytics = engagement_engine.get_engagement_analytics()
        
        return render_template('admin/marketing/automation.html',
                             analytics=analytics,
                             title='Engagement Automation')
    
    except Exception as e:
        logger.error(f"Error loading automation: {str(e)}")
        flash('Error loading automation', 'error')
        return redirect(url_for('admin_marketing.dashboard'))

@marketing_bp.route('/automation/rules')
@admin_required
def automation_rules():
    """List automation rules"""
    try:
        # This would need to be implemented in the engagement engine
        return render_template('admin/marketing/automation_rules.html',
                             title='Automation Rules')
    
    except Exception as e:
        logger.error(f"Error loading automation rules: {str(e)}")
        flash('Error loading automation rules', 'error')
        return redirect(url_for('admin_marketing.automation'))

@marketing_bp.route('/automation/rules/create', methods=['GET', 'POST'])
@admin_required
def create_automation_rule():
    """Create new automation rule"""
    try:
        if request.method == 'POST':
            _, _, engagement_engine = get_marketing_services()
            
            rule_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'trigger_type': request.form.get('trigger_type'),
                'trigger_conditions': json.loads(request.form.get('trigger_conditions', '{}')),
                'target_audience': json.loads(request.form.get('target_audience', '{}')),
                'channels': request.form.getlist('channels'),
                'content_templates': json.loads(request.form.get('content_templates', '{}')),
                'scheduling': json.loads(request.form.get('scheduling', '{}')),
                'personalization': json.loads(request.form.get('personalization', '{}')),
                'frequency_limits': json.loads(request.form.get('frequency_limits', '{}')),
                'is_active': request.form.get('is_active') == 'on'
            }
            
            rule_id = engagement_engine.create_engagement_rule(rule_data)
            flash(f'Automation rule "{rule_data["name"]}" created successfully', 'success')
            return redirect(url_for('admin_marketing.automation_rules'))
        
        return render_template('admin/marketing/create_automation_rule.html',
                             title='Create Automation Rule')
    
    except Exception as e:
        logger.error(f"Error creating automation rule: {str(e)}")
        flash('Error creating automation rule', 'error')
        return redirect(url_for('admin_marketing.automation_rules'))

# Customer Insights Routes

@marketing_bp.route('/insights')
@admin_required
def customer_insights():
    """Customer insights overview"""
    try:
        marketing_manager, _, _ = get_marketing_services()
        
        # Get recent insights (simplified)
        insights = []  # This would need proper implementation
        
        return render_template('admin/marketing/insights.html',
                             insights=insights,
                             title='Customer Insights')
    
    except Exception as e:
        logger.error(f"Error loading customer insights: {str(e)}")
        flash('Error loading customer insights', 'error')
        return redirect(url_for('admin_marketing.dashboard'))

@marketing_bp.route('/insights/customer/<customer_id>')
@admin_required
def customer_insight_detail(customer_id):
    """View detailed customer insights"""
    try:
        marketing_manager, journey_manager, engagement_engine = get_marketing_services()
        
        # Generate customer insights
        insights = marketing_manager.generate_customer_insights(customer_id)
        
        # Get journey status
        journey_status = journey_manager.get_customer_journey_status(customer_id)
        
        # Get engagement profile
        engagement_profile = engagement_engine.get_customer_engagement_profile(customer_id)
        
        # Get CLV and churn prediction
        clv = marketing_manager.get_customer_lifetime_value(customer_id)
        churn_prediction = marketing_manager.predict_churn_risk(customer_id)
        
        return render_template('admin/marketing/customer_insight_detail.html',
                             insights=insights,
                             journey_status=journey_status,
                             engagement_profile=engagement_profile,
                             clv=clv,
                             churn_prediction=churn_prediction,
                             customer_id=customer_id,
                             title=f'Customer Insights: {customer_id}')
    
    except Exception as e:
        logger.error(f"Error loading customer insight details: {str(e)}")
        flash('Error loading customer insight details', 'error')
        return redirect(url_for('admin_marketing.customer_insights'))

# Segments Routes

@marketing_bp.route('/segments')
@admin_required
def segments():
    """Customer segments management"""
    try:
        # This would need proper implementation
        return render_template('admin/marketing/segments.html',
                             title='Customer Segments')
    
    except Exception as e:
        logger.error(f"Error loading segments: {str(e)}")
        flash('Error loading segments', 'error')
        return redirect(url_for('admin_marketing.dashboard'))

@marketing_bp.route('/segments/create', methods=['GET', 'POST'])
@admin_required
def create_segment():
    """Create new customer segment"""
    try:
        if request.method == 'POST':
            _, _, engagement_engine = get_marketing_services()
            
            segment_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'criteria': json.loads(request.form.get('criteria', '{}')),
                'is_active': request.form.get('is_active') == 'on'
            }
            
            segment_id = engagement_engine.create_customer_segment(segment_data)
            flash(f'Segment "{segment_data["name"]}" created successfully', 'success')
            return redirect(url_for('admin_marketing.segments'))
        
        return render_template('admin/marketing/create_segment.html',
                             title='Create Customer Segment')
    
    except Exception as e:
        logger.error(f"Error creating segment: {str(e)}")
        flash('Error creating segment', 'error')
        return redirect(url_for('admin_marketing.segments'))

# A/B Testing Routes

@marketing_bp.route('/ab-tests')
@admin_required
def ab_tests():
    """A/B testing management"""
    try:
        return render_template('admin/marketing/ab_tests.html',
                             title='A/B Testing')
    
    except Exception as e:
        logger.error(f"Error loading A/B tests: {str(e)}")
        flash('Error loading A/B tests', 'error')
        return redirect(url_for('admin_marketing.dashboard'))

@marketing_bp.route('/ab-tests/create', methods=['GET', 'POST'])
@admin_required
def create_ab_test():
    """Create new A/B test"""
    try:
        if request.method == 'POST':
            marketing_manager, _, _ = get_marketing_services()
            
            test_config = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'variants': json.loads(request.form.get('variants', '[]')),
                'success_metric': request.form.get('success_metric'),
                'sample_size': int(request.form.get('sample_size', 1000)),
                'confidence_level': float(request.form.get('confidence_level', 0.95))
            }
            
            results = marketing_manager.run_ab_test(test_config)
            flash(f'A/B test "{test_config["name"]}" created successfully', 'success')
            return redirect(url_for('admin_marketing.ab_test_detail', test_id=results['test_id']))
        
        return render_template('admin/marketing/create_ab_test.html',
                             title='Create A/B Test')
    
    except Exception as e:
        logger.error(f"Error creating A/B test: {str(e)}")
        flash('Error creating A/B test', 'error')
        return redirect(url_for('admin_marketing.ab_tests'))

@marketing_bp.route('/ab-tests/<test_id>')
@admin_required
def ab_test_detail(test_id):
    """View A/B test results"""
    try:
        # This would need proper implementation to get test results
        return render_template('admin/marketing/ab_test_detail.html',
                             test_id=test_id,
                             title=f'A/B Test: {test_id}')
    
    except Exception as e:
        logger.error(f"Error loading A/B test details: {str(e)}")
        flash('Error loading A/B test details', 'error')
        return redirect(url_for('admin_marketing.ab_tests'))

# API Routes for AJAX/JSON responses

@marketing_bp.route('/api/dashboard-data')
@admin_required
def api_dashboard_data():
    """API endpoint for dashboard data"""
    try:
        marketing_manager, journey_manager, engagement_engine = get_marketing_services()
        
        data = {
            'marketing': marketing_manager.get_marketing_dashboard_data(),
            'journey': journey_manager.get_journey_dashboard_data(),
            'engagement': engagement_engine.get_engagement_dashboard_data()
        }
        
        return jsonify(data)
    
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        return jsonify({'error': 'Failed to load dashboard data'}), 500

@marketing_bp.route('/api/trigger-engagement', methods=['POST'])
@admin_required
def api_trigger_engagement():
    """API endpoint to trigger engagement"""
    try:
        _, _, engagement_engine = get_marketing_services()
        
        data = request.get_json()
        customer_id = data.get('customer_id')
        trigger_type = data.get('trigger_type')
        trigger_data = data.get('trigger_data', {})
        
        executions = engagement_engine.trigger_engagement(customer_id, trigger_type, trigger_data)
        
        return jsonify({
            'success': True,
            'executions': executions,
            'message': f'Triggered {len(executions)} engagements'
        })
    
    except Exception as e:
        logger.error(f"Error triggering engagement: {str(e)}")
        return jsonify({'error': 'Failed to trigger engagement'}), 500

@marketing_bp.route('/api/update-lead-score', methods=['POST'])
@admin_required
def api_update_lead_score():
    """API endpoint to update lead score"""
    try:
        marketing_manager, _, _ = get_marketing_services()
        
        data = request.get_json()
        email = data.get('email')
        score_change = data.get('score_change')
        factor = data.get('factor')
        user_id = data.get('user_id')
        
        lead_score = marketing_manager.update_lead_score(email, score_change, factor, user_id)
        
        return jsonify({
            'success': True,
            'lead_score': {
                'score': lead_score.score,
                'qualification_status': lead_score.qualification_status
            }
        })
    
    except Exception as e:
        logger.error(f"Error updating lead score: {str(e)}")
        return jsonify({'error': 'Failed to update lead score'}), 500

@marketing_bp.route('/api/start-journey', methods=['POST'])
@admin_required
def api_start_journey():
    """API endpoint to start customer journey"""
    try:
        _, journey_manager, _ = get_marketing_services()
        
        data = request.get_json()
        customer_id = data.get('customer_id')
        journey_id = data.get('journey_id')
        metadata = data.get('metadata', {})
        
        instance_id = journey_manager.start_customer_journey(customer_id, journey_id, metadata)
        
        return jsonify({
            'success': True,
            'instance_id': instance_id,
            'message': 'Journey started successfully'
        })
    
    except Exception as e:
        logger.error(f"Error starting journey: {str(e)}")
        return jsonify({'error': 'Failed to start journey'}), 500

@marketing_bp.route('/api/process-scheduled-engagements', methods=['POST'])
@admin_required
def api_process_scheduled_engagements():
    """API endpoint to process scheduled engagements"""
    try:
        _, _, engagement_engine = get_marketing_services()
        
        processed_count = engagement_engine.process_scheduled_engagements()
        
        return jsonify({
            'success': True,
            'processed_count': processed_count,
            'message': f'Processed {processed_count} scheduled engagements'
        })
    
    except Exception as e:
        logger.error(f"Error processing scheduled engagements: {str(e)}")
        return jsonify({'error': 'Failed to process scheduled engagements'}), 500

@marketing_bp.route('/api/campaign-performance/<campaign_id>')
@admin_required
def api_campaign_performance(campaign_id):
    """API endpoint for campaign performance data"""
    try:
        marketing_manager, _, _ = get_marketing_services()
        
        performance = marketing_manager.get_campaign_performance(campaign_id)
        
        return jsonify(performance)
    
    except Exception as e:
        logger.error(f"Error getting campaign performance: {str(e)}")
        return jsonify({'error': 'Failed to get campaign performance'}), 500

@marketing_bp.route('/api/journey-analytics/<journey_id>')
@admin_required
def api_journey_analytics(journey_id):
    """API endpoint for journey analytics"""
    try:
        _, journey_manager, _ = get_marketing_services()
        
        analytics = journey_manager.get_journey_analytics(journey_id)
        
        return jsonify(analytics)
    
    except Exception as e:
        logger.error(f"Error getting journey analytics: {str(e)}")
        return jsonify({'error': 'Failed to get journey analytics'}), 500

@marketing_bp.route('/api/engagement-analytics')
@admin_required
def api_engagement_analytics():
    """API endpoint for engagement analytics"""
    try:
        _, _, engagement_engine = get_marketing_services()
        
        rule_id = request.args.get('rule_id')
        days = int(request.args.get('days', 30))
        
        analytics = engagement_engine.get_engagement_analytics(rule_id, days)
        
        return jsonify(analytics)
    
    except Exception as e:
        logger.error(f"Error getting engagement analytics: {str(e)}")
        return jsonify({'error': 'Failed to get engagement analytics'}), 500

# Error handlers
@marketing_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('admin/marketing/error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404

@marketing_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return render_template('admin/marketing/error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500