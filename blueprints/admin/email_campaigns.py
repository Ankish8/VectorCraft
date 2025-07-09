"""
Email Campaign Management Routes for VectorCraft Admin
Advanced email campaign builder and automation management
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from flask import render_template, request, jsonify, current_app, url_for
from flask_login import current_user

from . import admin_bp
from blueprints.auth.utils import admin_required
from database import db
from services.email_campaign_manager import email_campaign_manager
from services.marketing_automation import marketing_automation
from services.email_performance_tracker import email_performance_tracker
from services.monitoring import system_logger

logger = logging.getLogger(__name__)

# Campaign Management Routes
@admin_bp.route('/email-campaigns')
@admin_required
def email_campaigns():
    """Email campaigns dashboard"""
    try:
        # Get filter parameters
        status = request.args.get('status', 'all')
        campaign_type = request.args.get('type', 'all')
        
        # Get campaigns
        campaigns = email_campaign_manager.get_campaigns(
            status=status if status != 'all' else None,
            limit=50
        )
        
        # Get dashboard metrics
        dashboard_metrics = email_campaign_manager.get_dashboard_metrics()
        
        # Get recent activity
        recent_activity = campaigns[:5]
        
        # Generate chart data for campaign performance
        campaign_performance = {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'datasets': [
                {
                    'label': 'Campaigns Sent',
                    'data': [12, 19, 15, 25, 22, 18],
                    'borderColor': 'rgb(102, 126, 234)',
                    'backgroundColor': 'rgba(102, 126, 234, 0.1)'
                },
                {
                    'label': 'Campaigns Completed',
                    'data': [10, 16, 13, 22, 20, 16],
                    'borderColor': 'rgb(16, 185, 129)',
                    'backgroundColor': 'rgba(16, 185, 129, 0.1)'
                }
            ]
        }
        
        return render_template('admin/email_campaigns/dashboard.html',
                             campaigns=campaigns,
                             dashboard_metrics=dashboard_metrics,
                             recent_activity=recent_activity,
                             campaign_performance=campaign_performance)
        
    except Exception as e:
        logger.error(f"Email campaigns dashboard error: {e}")
        return render_template('admin/email_campaigns/dashboard.html',
                             campaigns=[],
                             dashboard_metrics={},
                             recent_activity=[],
                             campaign_performance={})

@admin_bp.route('/email-campaigns/create')
@admin_required
def create_campaign():
    """Create new email campaign page"""
    try:
        # Get templates and segments
        templates = email_campaign_manager.get_templates()
        segments = email_campaign_manager.get_segments()
        
        return render_template('admin/email_campaigns/create.html',
                             templates=templates,
                             segments=segments)
        
    except Exception as e:
        logger.error(f"Create campaign page error: {e}")
        return render_template('admin/email_campaigns/create.html',
                             templates=[],
                             segments=[])

@admin_bp.route('/email-campaigns/<campaign_id>')
@admin_required
def campaign_details(campaign_id):
    """Campaign details page"""
    try:
        # Get campaign details
        campaign = email_campaign_manager.get_campaign(campaign_id)
        if not campaign:
            return render_template('admin/error.html', 
                                 message='Campaign not found'), 404
        
        # Get campaign analytics
        analytics = email_campaign_manager.get_campaign_analytics(campaign_id)
        
        # Get template and segment details
        template = email_campaign_manager.get_template(campaign['template_id'])
        segment = email_campaign_manager.get_segment(campaign['segment_id'])
        
        return render_template('admin/email_campaigns/details.html',
                             campaign=campaign,
                             analytics=analytics,
                             template=template,
                             segment=segment)
        
    except Exception as e:
        logger.error(f"Campaign details error: {e}")
        return render_template('admin/error.html', 
                             message='Error loading campaign details'), 500

@admin_bp.route('/email-campaigns/<campaign_id>/edit')
@admin_required
def edit_campaign(campaign_id):
    """Edit campaign page"""
    try:
        # Get campaign details
        campaign = email_campaign_manager.get_campaign(campaign_id)
        if not campaign:
            return render_template('admin/error.html', 
                                 message='Campaign not found'), 404
        
        # Get templates and segments
        templates = email_campaign_manager.get_templates()
        segments = email_campaign_manager.get_segments()
        
        return render_template('admin/email_campaigns/edit.html',
                             campaign=campaign,
                             templates=templates,
                             segments=segments)
        
    except Exception as e:
        logger.error(f"Edit campaign page error: {e}")
        return render_template('admin/error.html', 
                             message='Error loading campaign for editing'), 500

# Campaign API Routes
@admin_bp.route('/api/email-campaigns', methods=['POST'])
@admin_required
def api_create_campaign():
    """Create new email campaign"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'template_id', 'segment_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Create campaign
        campaign_id = email_campaign_manager.create_campaign(
            name=data['name'],
            description=data.get('description', ''),
            template_id=data['template_id'],
            segment_id=data['segment_id'],
            trigger_type=data.get('trigger_type', 'manual'),
            scheduled_at=datetime.fromisoformat(data['scheduled_at']) if data.get('scheduled_at') else None,
            settings=data.get('settings', {}),
            created_by=current_user.email
        )
        
        system_logger.info('email_campaign', f'Campaign created: {campaign_id}', 
                          user_email=current_user.email)
        
        return jsonify({'success': True, 'campaign_id': campaign_id})
        
    except Exception as e:
        logger.error(f"API create campaign error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-campaigns/<campaign_id>', methods=['PUT'])
@admin_required
def api_update_campaign(campaign_id):
    """Update email campaign"""
    try:
        data = request.get_json()
        
        # Update campaign
        success = email_campaign_manager.update_campaign(campaign_id, **data)
        
        if success:
            system_logger.info('email_campaign', f'Campaign updated: {campaign_id}', 
                              user_email=current_user.email)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to update campaign'}), 500
        
    except Exception as e:
        logger.error(f"API update campaign error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-campaigns/<campaign_id>', methods=['DELETE'])
@admin_required
def api_delete_campaign(campaign_id):
    """Delete email campaign"""
    try:
        # Stop campaign if running
        email_campaign_manager.stop_campaign(campaign_id)
        
        # For now, just mark as cancelled instead of deleting
        success = email_campaign_manager.update_campaign(campaign_id, status='cancelled')
        
        if success:
            system_logger.info('email_campaign', f'Campaign deleted: {campaign_id}', 
                              user_email=current_user.email)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete campaign'}), 500
        
    except Exception as e:
        logger.error(f"API delete campaign error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-campaigns/<campaign_id>/launch', methods=['POST'])
@admin_required
def api_launch_campaign(campaign_id):
    """Launch email campaign"""
    try:
        data = request.get_json()
        send_immediately = data.get('send_immediately', False)
        
        success = email_campaign_manager.launch_campaign(campaign_id, send_immediately)
        
        if success:
            system_logger.info('email_campaign', f'Campaign launched: {campaign_id}', 
                              user_email=current_user.email)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to launch campaign'}), 500
        
    except Exception as e:
        logger.error(f"API launch campaign error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-campaigns/<campaign_id>/pause', methods=['POST'])
@admin_required
def api_pause_campaign(campaign_id):
    """Pause email campaign"""
    try:
        success = email_campaign_manager.pause_campaign(campaign_id)
        
        if success:
            system_logger.info('email_campaign', f'Campaign paused: {campaign_id}', 
                              user_email=current_user.email)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to pause campaign'}), 500
        
    except Exception as e:
        logger.error(f"API pause campaign error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-campaigns/<campaign_id>/stop', methods=['POST'])
@admin_required
def api_stop_campaign(campaign_id):
    """Stop email campaign"""
    try:
        success = email_campaign_manager.stop_campaign(campaign_id)
        
        if success:
            system_logger.info('email_campaign', f'Campaign stopped: {campaign_id}', 
                              user_email=current_user.email)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to stop campaign'}), 500
        
    except Exception as e:
        logger.error(f"API stop campaign error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-campaigns/<campaign_id>/analytics')
@admin_required
def api_campaign_analytics(campaign_id):
    """Get campaign analytics"""
    try:
        analytics = email_campaign_manager.get_campaign_analytics(campaign_id)
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
        
    except Exception as e:
        logger.error(f"API campaign analytics error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Template Management Routes
@admin_bp.route('/email-templates/builder')
@admin_required
def template_builder():
    """Email template builder page"""
    try:
        # Get existing templates for reference
        templates = email_campaign_manager.get_templates()
        
        return render_template('admin/email_campaigns/template_builder.html',
                             templates=templates)
        
    except Exception as e:
        logger.error(f"Template builder page error: {e}")
        return render_template('admin/email_campaigns/template_builder.html',
                             templates=[])

@admin_bp.route('/email-templates/<template_id>/edit')
@admin_required
def edit_template(template_id):
    """Edit email template page"""
    try:
        template = email_campaign_manager.get_template(template_id)
        if not template:
            return render_template('admin/error.html', 
                                 message='Template not found'), 404
        
        return render_template('admin/email_campaigns/template_editor.html',
                             template=template)
        
    except Exception as e:
        logger.error(f"Edit template page error: {e}")
        return render_template('admin/error.html', 
                             message='Error loading template for editing'), 500

@admin_bp.route('/api/email-templates', methods=['POST'])
@admin_required
def api_create_template():
    """Create new email template"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'subject', 'html_content', 'text_content']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Create template
        template_id = email_campaign_manager.create_template(
            name=data['name'],
            subject=data['subject'],
            html_content=data['html_content'],
            text_content=data['text_content'],
            template_type=data.get('template_type', 'email'),
            preview_text=data.get('preview_text', '')
        )
        
        system_logger.info('email_template', f'Template created: {template_id}', 
                          user_email=current_user.email)
        
        return jsonify({'success': True, 'template_id': template_id})
        
    except Exception as e:
        logger.error(f"API create template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-templates/<template_id>/preview', methods=['POST'])
@admin_required
def api_preview_template(template_id):
    """Preview email template"""
    try:
        data = request.get_json()
        variables = data.get('variables', {})
        
        preview = email_campaign_manager.preview_template(template_id, variables)
        
        return jsonify({
            'success': True,
            'preview': preview
        })
        
    except Exception as e:
        logger.error(f"API preview template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-templates/<template_id>/test', methods=['POST'])
@admin_required
def api_test_template(template_id):
    """Send test email using template"""
    try:
        data = request.get_json()
        test_email = data.get('test_email')
        variables = data.get('variables', {})
        
        if not test_email:
            return jsonify({'success': False, 'error': 'Test email address required'}), 400
        
        success = email_campaign_manager.test_template(template_id, test_email, variables)
        
        if success:
            system_logger.info('email_template', f'Test email sent for template: {template_id}', 
                              user_email=current_user.email)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to send test email'}), 500
        
    except Exception as e:
        logger.error(f"API test template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Segment Management Routes
@admin_bp.route('/email-segments')
@admin_required
def email_segments():
    """Email segments management page"""
    try:
        segments = email_campaign_manager.get_segments()
        
        return render_template('admin/email_campaigns/segments.html',
                             segments=segments)
        
    except Exception as e:
        logger.error(f"Email segments page error: {e}")
        return render_template('admin/email_campaigns/segments.html',
                             segments=[])

@admin_bp.route('/email-segments/create')
@admin_required
def create_segment():
    """Create new segment page"""
    try:
        return render_template('admin/email_campaigns/create_segment.html')
        
    except Exception as e:
        logger.error(f"Create segment page error: {e}")
        return render_template('admin/email_campaigns/create_segment.html')

@admin_bp.route('/api/email-segments', methods=['POST'])
@admin_required
def api_create_segment():
    """Create new email segment"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'segment_type', 'conditions']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Create segment
        segment_id = email_campaign_manager.create_segment(
            name=data['name'],
            description=data.get('description', ''),
            segment_type=data['segment_type'],
            conditions=data['conditions'],
            is_dynamic=data.get('is_dynamic', True)
        )
        
        system_logger.info('email_segment', f'Segment created: {segment_id}', 
                          user_email=current_user.email)
        
        return jsonify({'success': True, 'segment_id': segment_id})
        
    except Exception as e:
        logger.error(f"API create segment error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-segments/<segment_id>/size', methods=['POST'])
@admin_required
def api_update_segment_size(segment_id):
    """Update segment size"""
    try:
        size = email_campaign_manager.update_segment_size(segment_id)
        
        return jsonify({
            'success': True,
            'size': size
        })
        
    except Exception as e:
        logger.error(f"API update segment size error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# A/B Testing Routes
@admin_bp.route('/email-campaigns/<campaign_id>/ab-test')
@admin_required
def ab_test_setup(campaign_id):
    """A/B test setup page"""
    try:
        campaign = email_campaign_manager.get_campaign(campaign_id)
        if not campaign:
            return render_template('admin/error.html', 
                                 message='Campaign not found'), 404
        
        templates = email_campaign_manager.get_templates()
        
        return render_template('admin/email_campaigns/ab_test.html',
                             campaign=campaign,
                             templates=templates)
        
    except Exception as e:
        logger.error(f"A/B test setup page error: {e}")
        return render_template('admin/error.html', 
                             message='Error loading A/B test setup'), 500

@admin_bp.route('/api/email-campaigns/<campaign_id>/ab-test', methods=['POST'])
@admin_required
def api_create_ab_test(campaign_id):
    """Create A/B test for campaign"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['test_name', 'variants', 'traffic_split']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Create A/B test
        test_id = email_campaign_manager.create_ab_test(
            campaign_id=campaign_id,
            test_name=data['test_name'],
            variants=data['variants'],
            traffic_split=data['traffic_split'],
            success_metric=data.get('success_metric', 'open_rate')
        )
        
        system_logger.info('ab_test', f'A/B test created: {test_id}', 
                          user_email=current_user.email)
        
        return jsonify({'success': True, 'test_id': test_id})
        
    except Exception as e:
        logger.error(f"API create A/B test error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/ab-tests/<test_id>/results')
@admin_required
def api_ab_test_results(test_id):
    """Get A/B test results"""
    try:
        results = email_campaign_manager.get_ab_test_results(test_id)
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"API A/B test results error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Marketing Automation Routes
@admin_bp.route('/marketing-automation')
@admin_required
def marketing_automation_dashboard():
    """Marketing automation dashboard"""
    try:
        # Get automation metrics
        metrics = marketing_automation.get_automation_metrics()
        
        # Get automation rules
        rules = marketing_automation.get_automation_rules()
        
        return render_template('admin/email_campaigns/automation_dashboard.html',
                             metrics=metrics,
                             rules=rules)
        
    except Exception as e:
        logger.error(f"Marketing automation dashboard error: {e}")
        return render_template('admin/email_campaigns/automation_dashboard.html',
                             metrics={},
                             rules=[])

@admin_bp.route('/marketing-automation/create')
@admin_required
def create_automation_rule():
    """Create automation rule page"""
    try:
        templates = email_campaign_manager.get_templates()
        segments = email_campaign_manager.get_segments()
        
        return render_template('admin/email_campaigns/create_automation.html',
                             templates=templates,
                             segments=segments)
        
    except Exception as e:
        logger.error(f"Create automation rule page error: {e}")
        return render_template('admin/email_campaigns/create_automation.html',
                             templates=[],
                             segments=[])

@admin_bp.route('/api/marketing-automation/rules', methods=['POST'])
@admin_required
def api_create_automation_rule():
    """Create automation rule"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'trigger', 'actions']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Create automation rule
        rule_id = marketing_automation.create_automation_rule(
            name=data['name'],
            description=data.get('description', ''),
            trigger=data['trigger'],
            actions=data['actions'],
            created_by=current_user.email,
            tags=data.get('tags', [])
        )
        
        system_logger.info('automation_rule', f'Automation rule created: {rule_id}', 
                          user_email=current_user.email)
        
        return jsonify({'success': True, 'rule_id': rule_id})
        
    except Exception as e:
        logger.error(f"API create automation rule error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/marketing-automation/rules/<rule_id>', methods=['PUT'])
@admin_required
def api_update_automation_rule(rule_id):
    """Update automation rule"""
    try:
        data = request.get_json()
        
        success = marketing_automation.update_automation_rule(rule_id, **data)
        
        if success:
            system_logger.info('automation_rule', f'Automation rule updated: {rule_id}', 
                              user_email=current_user.email)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to update automation rule'}), 500
        
    except Exception as e:
        logger.error(f"API update automation rule error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/marketing-automation/rules/<rule_id>', methods=['DELETE'])
@admin_required
def api_delete_automation_rule(rule_id):
    """Delete automation rule"""
    try:
        success = marketing_automation.delete_automation_rule(rule_id)
        
        if success:
            system_logger.info('automation_rule', f'Automation rule deleted: {rule_id}', 
                              user_email=current_user.email)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete automation rule'}), 500
        
    except Exception as e:
        logger.error(f"API delete automation rule error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/marketing-automation/trigger', methods=['POST'])
@admin_required
def api_trigger_automation():
    """Trigger automation event"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['event_type', 'user_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Trigger automation
        execution_ids = marketing_automation.trigger_event(
            event_type=data['event_type'],
            user_id=data['user_id'],
            event_data=data.get('event_data', {})
        )
        
        return jsonify({
            'success': True,
            'execution_ids': execution_ids
        })
        
    except Exception as e:
        logger.error(f"API trigger automation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/marketing-automation/executions/<execution_id>')
@admin_required
def api_automation_execution_status(execution_id):
    """Get automation execution status"""
    try:
        status = marketing_automation.get_execution_status(execution_id)
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"API automation execution status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/marketing-automation/executions/<execution_id>/cancel', methods=['POST'])
@admin_required
def api_cancel_automation_execution(execution_id):
    """Cancel automation execution"""
    try:
        success = marketing_automation.cancel_execution(execution_id)
        
        if success:
            system_logger.info('automation_execution', f'Automation execution cancelled: {execution_id}', 
                              user_email=current_user.email)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to cancel automation execution'}), 500
        
    except Exception as e:
        logger.error(f"API cancel automation execution error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Analytics and Reporting Routes
@admin_bp.route('/email-campaigns/analytics')
@admin_required
def campaign_analytics():
    """Campaign analytics dashboard"""
    try:
        # Get overall metrics
        dashboard_metrics = email_campaign_manager.get_dashboard_metrics()
        
        # Get campaign performance data
        campaigns = email_campaign_manager.get_campaigns(limit=20)
        
        # Get automation metrics
        automation_metrics = marketing_automation.get_automation_metrics()
        
        return render_template('admin/email_campaigns/analytics.html',
                             dashboard_metrics=dashboard_metrics,
                             campaigns=campaigns,
                             automation_metrics=automation_metrics)
        
    except Exception as e:
        logger.error(f"Campaign analytics page error: {e}")
        return render_template('admin/email_campaigns/analytics.html',
                             dashboard_metrics={},
                             campaigns=[],
                             automation_metrics={})

@admin_bp.route('/api/email-campaigns/analytics', methods=['POST'])
@admin_required
def api_campaign_analytics_data():
    """Get campaign analytics data"""
    try:
        data = request.get_json()
        time_range = data.get('time_range', '7d')
        campaign_id = data.get('campaign_id')
        
        if campaign_id:
            # Get specific campaign analytics
            analytics = email_campaign_manager.get_campaign_analytics(campaign_id)
        else:
            # Get overall dashboard metrics
            analytics = email_campaign_manager.get_dashboard_metrics()
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
        
    except Exception as e:
        logger.error(f"API campaign analytics data error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Export Routes
@admin_bp.route('/export/campaign-analytics')
@admin_required
def export_campaign_analytics():
    """Export campaign analytics data"""
    try:
        # Get parameters
        format_type = request.args.get('format', 'csv')
        campaign_id = request.args.get('campaign_id')
        
        if format_type == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            if campaign_id:
                # Export specific campaign data
                analytics = email_campaign_manager.get_campaign_analytics(campaign_id)
                
                # Write headers
                writer.writerow(['Campaign ID', 'Campaign Name', 'Status', 'Sent Count', 
                               'Open Rate', 'Click Rate', 'Bounce Rate', 'ROI'])
                
                # Write data
                writer.writerow([
                    analytics.get('campaign_id', ''),
                    analytics.get('campaign_name', ''),
                    analytics.get('status', ''),
                    analytics.get('performance', {}).get('sent_count', 0),
                    analytics.get('performance', {}).get('open_rate', 0),
                    analytics.get('performance', {}).get('click_rate', 0),
                    analytics.get('performance', {}).get('bounce_rate', 0),
                    analytics.get('roi', {}).get('roi_percentage', 0)
                ])
            else:
                # Export all campaigns
                campaigns = email_campaign_manager.get_campaigns(limit=1000)
                
                # Write headers
                writer.writerow(['Campaign ID', 'Name', 'Status', 'Created', 'Template', 'Segment'])
                
                # Write data
                for campaign in campaigns:
                    writer.writerow([
                        campaign.get('campaign_id', ''),
                        campaign.get('name', ''),
                        campaign.get('status', ''),
                        campaign.get('created_at', ''),
                        campaign.get('template_id', ''),
                        campaign.get('segment_id', '')
                    ])
            
            output.seek(0)
            
            # Create response
            from flask import Response
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=campaign_analytics.csv'}
            )
        
        else:
            return jsonify({'success': False, 'error': 'Unsupported format'}), 400
        
    except Exception as e:
        logger.error(f"Export campaign analytics error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500