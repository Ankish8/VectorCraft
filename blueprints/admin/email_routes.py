"""
Email Management Routes for VectorCraft Admin
Advanced email and notification management system
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from flask import render_template, request, jsonify, current_app, send_file, url_for
from flask_login import current_user

from . import admin_bp
from blueprints.auth.utils import admin_required
from database import db
from services.email_service import email_service
from services.email_performance_tracker import email_performance_tracker
from services.monitoring import system_logger

logger = logging.getLogger(__name__)

# Email Analytics Routes
@admin_bp.route('/email-analytics')
@admin_required
def email_analytics():
    """Email analytics dashboard"""
    try:
        # Get email performance summary
        email_performance = email_performance_tracker.get_performance_summary(hours=24)
        
        # Get recent email logs
        email_logs = db.get_email_logs(limit=20)
        
        # Get template performance
        templates = db.get_email_templates(is_active=True)
        template_performance = []
        for template in templates:
            perf = email_performance_tracker.get_template_performance(template['template_id'])
            template_performance.append({
                'name': template['name'],
                'template_id': template['template_id'],
                'sent_count': perf.get('total_sent', 0),
                'open_rate': perf.get('open_rate', 0),
                'click_rate': perf.get('click_rate', 0),
                'bounce_rate': perf.get('bounce_rate', 0),
                'opened_count': int(perf.get('total_sent', 0) * perf.get('open_rate', 0) / 100),
                'clicked_count': int(perf.get('total_sent', 0) * perf.get('click_rate', 0) / 100)
            })
        
        # Generate chart data
        performance_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        performance_data = {
            'sent': [45, 52, 38, 67, 89, 43, 56],
            'delivered': [43, 50, 36, 65, 85, 41, 54],
            'opened': [12, 18, 15, 22, 28, 16, 21]
        }
        
        type_distribution = {
            'labels': ['Credentials', 'Purchase Confirmation', 'Error Notifications', 'Admin Notifications'],
            'data': [65, 25, 8, 2]
        }
        
        return render_template('admin/email_analytics.html',
                             email_performance=email_performance.__dict__,
                             email_logs=email_logs,
                             template_performance=template_performance,
                             performance_labels=performance_labels,
                             performance_data=performance_data,
                             type_distribution=type_distribution)
        
    except Exception as e:
        logger.error(f"Email analytics error: {e}")
        return render_template('admin/email_analytics.html',
                             email_performance={},
                             email_logs=[],
                             template_performance=[],
                             performance_labels=[],
                             performance_data={},
                             type_distribution={})

@admin_bp.route('/api/email-analytics', methods=['POST'])
@admin_required
def api_email_analytics():
    """API endpoint for email analytics data"""
    try:
        data = request.get_json()
        time_range = data.get('time_range', '7d')
        email_type = data.get('email_type', 'all')
        status = data.get('status', 'all')
        
        # Convert time range to hours
        hours_map = {'24h': 24, '7d': 168, '30d': 720, '90d': 2160}
        hours = hours_map.get(time_range, 168)
        
        # Get filtered performance data
        email_performance = email_performance_tracker.get_performance_summary(hours=hours)
        
        # Get recent emails with filters
        filters = {}
        if email_type != 'all':
            filters['email_type'] = email_type
        if status != 'all':
            filters['status'] = status
        
        recent_emails = db.get_email_logs(limit=50, **filters)
        
        # Generate updated chart data
        chart_data = {
            'performance_labels': ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'],
            'performance_data': {
                'sent': [45, 52, 38, 67, 89, 43, 56],
                'delivered': [43, 50, 36, 65, 85, 41, 54],
                'opened': [12, 18, 15, 22, 28, 16, 21]
            },
            'type_distribution': {
                'labels': ['Credentials', 'Purchase Confirmation', 'Error Notifications', 'Admin Notifications'],
                'data': [65, 25, 8, 2]
            }
        }
        
        return jsonify({
            'success': True,
            'metrics': email_performance.__dict__,
            'charts': chart_data,
            'recent_emails': recent_emails
        })
        
    except Exception as e:
        logger.error(f"API email analytics error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-details/<email_id>')
@admin_required
def api_email_details(email_id):
    """Get detailed information about a specific email"""
    try:
        email_logs = db.get_email_logs(limit=1, transaction_id=email_id)
        
        if not email_logs:
            return jsonify({'success': False, 'error': 'Email not found'}), 404
        
        email_log = email_logs[0]
        
        return jsonify({
            'success': True,
            'email': email_log
        })
        
    except Exception as e:
        logger.error(f"API email details error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Notification Center Routes
@admin_bp.route('/notifications')
@admin_required
def notifications():
    """Notification center page"""
    try:
        # Get filter parameters
        status = request.args.get('status', 'all')
        priority = request.args.get('priority', 'all')
        notification_type = request.args.get('type', 'all')
        category = request.args.get('category', 'all')
        page = int(request.args.get('page', 1))
        
        # Build filters
        filters = {}
        if status != 'all':
            filters['status'] = status
        if priority != 'all':
            filters['priority'] = priority
        if notification_type != 'all':
            filters['notification_type'] = notification_type
        
        # Get notifications
        notifications = db.get_notifications(limit=50, **filters)
        
        # Get notification summary
        notification_summary = db.get_notification_summary()
        
        # Calculate pagination
        total_notifications = len(notifications)
        per_page = 20
        total_pages = (total_notifications + per_page - 1) // per_page
        
        # Paginate notifications
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_notifications = notifications[start_idx:end_idx]
        
        return render_template('admin/notification_center.html',
                             notifications=paginated_notifications,
                             notification_summary=notification_summary,
                             current_page=page,
                             total_pages=total_pages)
        
    except Exception as e:
        logger.error(f"Notifications page error: {e}")
        return render_template('admin/notification_center.html',
                             notifications=[],
                             notification_summary={},
                             current_page=1,
                             total_pages=1)

@admin_bp.route('/api/notifications', methods=['POST'])
@admin_required
def api_create_notification():
    """Create new notification"""
    try:
        data = request.get_json()
        
        notification_id = str(uuid.uuid4())
        user_id = None if data.get('global', False) else current_user.id
        
        # Create notification
        db.create_notification(
            notification_id=notification_id,
            user_id=user_id,
            notification_type=data['type'],
            title=data['title'],
            message=data['message'],
            priority=data.get('priority', 'medium'),
            category=data.get('category'),
            action_url=data.get('action_url'),
            action_text=data.get('action_text'),
            expires_at=data.get('expires_at')
        )
        
        system_logger.info('notification', f'Notification created: {notification_id}', 
                          user_email=current_user.email)
        
        return jsonify({'success': True, 'notification_id': notification_id})
        
    except Exception as e:
        logger.error(f"API create notification error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/notifications/<notification_id>/read', methods=['POST'])
@admin_required
def api_mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        db.update_notification_status(notification_id, 'read', read_at=True)
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"API mark notification read error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/notifications/<notification_id>/dismiss', methods=['POST'])
@admin_required
def api_dismiss_notification(notification_id):
    """Dismiss notification"""
    try:
        db.update_notification_status(notification_id, 'dismissed', dismissed_at=True)
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"API dismiss notification error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/notifications/<notification_id>', methods=['DELETE'])
@admin_required
def api_delete_notification(notification_id):
    """Delete notification"""
    try:
        # This would need to be implemented in the database
        # For now, just dismiss it
        db.update_notification_status(notification_id, 'dismissed', dismissed_at=True)
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"API delete notification error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Email Template Management Routes
@admin_bp.route('/email-templates')
@admin_required
def email_templates():
    """Email template management page"""
    try:
        # Get filter parameters
        template_type = request.args.get('type', 'all')
        is_active = request.args.get('status', 'all')
        
        # Build filters
        filters = {}
        if template_type != 'all':
            filters['template_type'] = template_type
        if is_active != 'all':
            filters['is_active'] = is_active == 'active'
        
        # Get templates
        templates = db.get_email_templates(**filters)
        
        # Add performance data to templates
        for template in templates:
            perf = email_performance_tracker.get_template_performance(template['template_id'])
            template.update({
                'sent_count': perf.get('total_sent', 0),
                'open_rate': perf.get('open_rate', 0),
                'click_rate': perf.get('click_rate', 0),
                'variables': json.loads(template.get('variables', '[]')) if template.get('variables') else []
            })
        
        return render_template('admin/email_templates.html',
                             templates=templates)
        
    except Exception as e:
        logger.error(f"Email templates page error: {e}")
        return render_template('admin/email_templates.html',
                             templates=[])

@admin_bp.route('/api/email-templates', methods=['POST'])
@admin_required
def api_create_email_template():
    """Create new email template"""
    try:
        data = request.get_json()
        
        # Extract variables from template content
        variables = []
        import re
        text_vars = re.findall(r'\{\{(\w+)\}\}', data['body_text'])
        html_vars = re.findall(r'\{\{(\w+)\}\}', data.get('body_html', ''))
        subject_vars = re.findall(r'\{\{(\w+)\}\}', data['subject'])
        
        variables = list(set(text_vars + html_vars + subject_vars))
        
        # Create template
        template_id = db.create_email_template(
            template_id=data['template_id'],
            name=data['name'],
            subject=data['subject'],
            body_text=data['body_text'],
            body_html=data.get('body_html'),
            template_type=data['template_type'],
            variables=variables
        )
        
        system_logger.info('email_template', f'Template created: {data["template_id"]}', 
                          user_email=current_user.email)
        
        return jsonify({'success': True, 'template_id': template_id})
        
    except Exception as e:
        logger.error(f"API create email template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-templates/<template_id>', methods=['GET'])
@admin_required
def api_get_email_template(template_id):
    """Get email template details"""
    try:
        template = db.get_email_template(template_id)
        
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
        
        # Parse variables
        if template.get('variables'):
            template['variables'] = json.loads(template['variables'])
        
        return jsonify({
            'success': True,
            'template': template
        })
        
    except Exception as e:
        logger.error(f"API get email template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-templates/<template_id>', methods=['PUT'])
@admin_required
def api_update_email_template(template_id):
    """Update email template"""
    try:
        data = request.get_json()
        
        # Extract variables from template content
        variables = []
        import re
        text_vars = re.findall(r'\{\{(\w+)\}\}', data['body_text'])
        html_vars = re.findall(r'\{\{(\w+)\}\}', data.get('body_html', ''))
        subject_vars = re.findall(r'\{\{(\w+)\}\}', data['subject'])
        
        variables = list(set(text_vars + html_vars + subject_vars))
        
        # Update template
        db.update_email_template(
            template_id=template_id,
            name=data['name'],
            subject=data['subject'],
            body_text=data['body_text'],
            body_html=data.get('body_html'),
            template_type=data['template_type'],
            variables=variables,
            is_active=data['is_active']
        )
        
        system_logger.info('email_template', f'Template updated: {template_id}', 
                          user_email=current_user.email)
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"API update email template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-templates/<template_id>', methods=['DELETE'])
@admin_required
def api_delete_email_template(template_id):
    """Delete email template"""
    try:
        # Deactivate template instead of deleting
        db.update_email_template(template_id=template_id, is_active=False)
        
        system_logger.info('email_template', f'Template deleted: {template_id}', 
                          user_email=current_user.email)
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"API delete email template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/email-templates/<template_id>/test', methods=['POST'])
@admin_required
def api_test_email_template(template_id):
    """Send test email using template"""
    try:
        data = request.get_json()
        test_email = data['email']
        test_data = data.get('test_data', {})
        
        # Get template
        template = db.get_email_template(template_id)
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
        
        # Replace variables in template
        subject = template['subject']
        body_text = template['body_text']
        body_html = template.get('body_html', '')
        
        for var, value in test_data.items():
            subject = subject.replace(f'{{{{{var}}}}}', str(value))
            body_text = body_text.replace(f'{{{{{var}}}}}', str(value))
            if body_html:
                body_html = body_html.replace(f'{{{{{var}}}}}', str(value))
        
        # Send test email
        message = email_service._create_message(test_email, subject, body_text, body_html)
        success = email_service._send_email(message, email_type='test')
        
        if success:
            system_logger.info('email_template', f'Test email sent for template: {template_id}', 
                              user_email=current_user.email)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to send test email'}), 500
        
    except Exception as e:
        logger.error(f"API test email template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Communication Logs Routes
@admin_bp.route('/communication-logs')
@admin_required
def communication_logs():
    """Communication logs page"""
    try:
        # Get filter parameters
        comm_type = request.args.get('type', 'all')
        direction = request.args.get('direction', 'all')
        status = request.args.get('status', 'all')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        page = int(request.args.get('page', 1))
        
        # Build filters
        filters = {}
        if comm_type != 'all':
            filters['communication_type'] = comm_type
        if direction != 'all':
            filters['direction'] = direction
        if status != 'all':
            filters['status'] = status
        
        # Get communication logs
        communication_logs = db.get_communication_logs(limit=100, **filters)
        
        # Get communication summary
        stats = db.get_communication_summary(hours=24)
        
        # Process stats for display
        stats_summary = {
            'email_count': sum(s['total_count'] for s in stats if s['communication_type'] == 'email'),
            'sms_count': sum(s['total_count'] for s in stats if s['communication_type'] == 'sms'),
            'call_count': sum(s['total_count'] for s in stats if s['communication_type'] == 'call'),
            'chat_count': sum(s['total_count'] for s in stats if s['communication_type'] == 'chat'),
            'email_change': 5,  # Mock data
            'sms_change': 3,
            'call_change': -2,
            'chat_change': 8
        }
        
        # Generate chart data
        chart_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        chart_data = {
            'email': [25, 30, 22, 35, 42, 28, 33],
            'sms': [8, 12, 10, 15, 18, 14, 16],
            'calls': [3, 5, 4, 6, 8, 5, 7],
            'chat': [12, 15, 13, 18, 22, 17, 20]
        }
        
        # Calculate pagination
        total_logs = len(communication_logs)
        per_page = 50
        total_pages = (total_logs + per_page - 1) // per_page
        
        # Paginate logs
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_logs = communication_logs[start_idx:end_idx]
        
        return render_template('admin/communication_logs.html',
                             communication_logs=paginated_logs,
                             stats=stats_summary,
                             chart_labels=chart_labels,
                             chart_data=chart_data,
                             current_page=page,
                             total_pages=total_pages)
        
    except Exception as e:
        logger.error(f"Communication logs page error: {e}")
        return render_template('admin/communication_logs.html',
                             communication_logs=[],
                             stats={},
                             chart_labels=[],
                             chart_data={},
                             current_page=1,
                             total_pages=1)

@admin_bp.route('/api/communication-logs/<log_id>')
@admin_required
def api_communication_log_details(log_id):
    """Get detailed information about a specific communication log"""
    try:
        logs = db.get_communication_logs(limit=1, log_id=log_id)
        
        if not logs:
            return jsonify({'success': False, 'error': 'Log not found'}), 404
        
        log = logs[0]
        
        return jsonify({
            'success': True,
            'log': log
        })
        
    except Exception as e:
        logger.error(f"API communication log details error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/communication-logs/timeline/<contact>')
@admin_required
def api_communication_timeline(contact):
    """Get communication timeline for a contact"""
    try:
        # Get logs for this contact
        logs = db.get_communication_logs(email_address=contact, limit=50)
        
        # Sort by date
        timeline = sorted(logs, key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'timeline': timeline
        })
        
    except Exception as e:
        logger.error(f"API communication timeline error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Export Routes
@admin_bp.route('/export/email-analytics')
@admin_required
def export_email_analytics():
    """Export email analytics data"""
    try:
        # Get parameters
        time_range = request.args.get('time_range', '7d')
        email_type = request.args.get('email_type', 'all')
        status = request.args.get('status', 'all')
        
        # Convert to hours
        hours_map = {'24h': 24, '7d': 168, '30d': 720, '90d': 2160}
        hours = hours_map.get(time_range, 168)
        
        # Get data
        email_performance = email_performance_tracker.get_performance_summary(hours=hours)
        email_logs = db.get_email_logs(limit=1000)
        
        # Create CSV content
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Email ID', 'Type', 'Recipient', 'Subject', 'Status', 'Created', 'Delivered'])
        
        # Write data
        for log in email_logs:
            writer.writerow([
                log.get('id', ''),
                log.get('email_type', ''),
                log.get('recipient_email', ''),
                log.get('subject', ''),
                log.get('status', ''),
                log.get('created_at', ''),
                log.get('delivered_at', '')
            ])
        
        output.seek(0)
        
        # Create response
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=email_analytics.csv'}
        )
        
    except Exception as e:
        logger.error(f"Export email analytics error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/export/communication-logs')
@admin_required
def export_communication_logs():
    """Export communication logs"""
    try:
        # Get parameters
        format_type = request.args.get('format', 'csv')
        include_content = request.args.get('include_content', 'true') == 'true'
        include_metadata = request.args.get('include_metadata', 'true') == 'true'
        
        # Get data
        logs = db.get_communication_logs(limit=10000)
        
        if format_type == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            headers = ['Log ID', 'Type', 'Direction', 'Contact', 'Subject', 'Status', 'Created']
            if include_content:
                headers.append('Content')
            if include_metadata:
                headers.append('Metadata')
            
            writer.writerow(headers)
            
            # Write data
            for log in logs:
                row = [
                    log.get('log_id', ''),
                    log.get('communication_type', ''),
                    log.get('direction', ''),
                    log.get('email_address', ''),
                    log.get('subject', ''),
                    log.get('status', ''),
                    log.get('created_at', '')
                ]
                
                if include_content:
                    row.append(log.get('content', ''))
                if include_metadata:
                    row.append(log.get('metadata', ''))
                
                writer.writerow(row)
            
            output.seek(0)
            
            # Create response
            from flask import Response
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=communication_logs.csv'}
            )
        
        else:
            return jsonify({'success': False, 'error': 'Unsupported format'}), 400
        
    except Exception as e:
        logger.error(f"Export communication logs error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500