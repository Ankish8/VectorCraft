#!/usr/bin/env python3
"""
Security & Audit Management Routes for VectorCraft Admin
Handles security monitoring, audit logging, access control, and threat detection
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, make_response
from functools import wraps
import json
import csv
import io
from datetime import datetime, timedelta
import sqlite3
import logging
from typing import Dict, List, Optional

# Import the security service
from services.security_service import security_service

logger = logging.getLogger(__name__)

# Create security blueprint
security_bp = Blueprint('security', __name__, url_prefix='/admin/security')

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def log_admin_action(action: str, resource: str, details: Dict = None):
    """Log admin actions for audit trail"""
    try:
        admin_user = session.get('admin_user', 'admin')
        source_ip = request.remote_addr
        user_agent = request.user_agent.string
        
        security_service.log_audit_event(
            admin_user, action, resource, 
            source_ip, user_agent, True, details
        )
    except Exception as e:
        logger.error(f"Failed to log admin action: {e}")

# ========== SECURITY DASHBOARD ==========

@security_bp.route('/')
@admin_required
def dashboard():
    """Security dashboard main page"""
    try:
        # Get security metrics
        metrics = security_service.get_security_metrics()
        
        # Get recent security events
        security_events = security_service.get_recent_security_events(20)
        
        # Get threat indicators
        threat_indicators = get_threat_indicators()
        
        # Get blocked IPs
        blocked_ips = get_blocked_ips()
        
        # Get access permissions
        access_permissions = get_access_permissions()
        
        # Calculate additional metrics
        metrics['critical_events'] = len([
            event for event in security_events 
            if event.get('severity') == 'CRITICAL'
        ])
        
        log_admin_action('VIEW_SECURITY_DASHBOARD', 'security_dashboard')
        
        return render_template('admin/security.html',
                             metrics=metrics,
                             security_events=security_events,
                             threat_indicators=threat_indicators,
                             blocked_ips=blocked_ips,
                             access_permissions=access_permissions)
        
    except Exception as e:
        logger.error(f"Security dashboard error: {e}")
        return jsonify({'error': 'Failed to load security dashboard'}), 500

@security_bp.route('/metrics')
@admin_required
def get_metrics():
    """Get security metrics API endpoint"""
    try:
        metrics = security_service.get_security_metrics()
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Failed to get security metrics: {e}")
        return jsonify({'error': 'Failed to get metrics'}), 500

# ========== SECURITY EVENTS ==========

@security_bp.route('/events')
@admin_required
def get_security_events():
    """Get security events with filtering"""
    try:
        limit = request.args.get('limit', 50, type=int)
        severity = request.args.get('severity')
        event_type = request.args.get('event_type')
        source_ip = request.args.get('source_ip')
        
        events = security_service.get_recent_security_events(limit)
        
        # Apply filters
        if severity:
            events = [e for e in events if e.get('severity') == severity]
        if event_type:
            events = [e for e in events if e.get('event_type') == event_type]
        if source_ip:
            events = [e for e in events if e.get('source_ip') == source_ip]
        
        return jsonify(events)
        
    except Exception as e:
        logger.error(f"Failed to get security events: {e}")
        return jsonify({'error': 'Failed to get security events'}), 500

@security_bp.route('/events/<event_id>')
@admin_required
def get_security_event(event_id):
    """Get specific security event details"""
    try:
        conn = sqlite3.connect('vectorcraft.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, timestamp, event_type, severity, source_ip, user_id, description, details
            FROM security_events 
            WHERE id = ?
        ''', (event_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Event not found'}), 404
        
        event = {
            'id': row[0],
            'timestamp': row[1],
            'event_type': row[2],
            'severity': row[3],
            'source_ip': row[4],
            'user_id': row[5],
            'description': row[6],
            'details': json.loads(row[7]) if row[7] else {}
        }
        
        log_admin_action('VIEW_SECURITY_EVENT', f'security_event_{event_id}')
        
        return jsonify(event)
        
    except Exception as e:
        logger.error(f"Failed to get security event: {e}")
        return jsonify({'error': 'Failed to get security event'}), 500

# ========== THREAT INDICATORS ==========

def get_threat_indicators():
    """Get threat indicators from database"""
    try:
        conn = sqlite3.connect('vectorcraft.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT indicator_type, value, severity, description, first_seen, last_seen, count
            FROM threat_indicators
            ORDER BY last_seen DESC
            LIMIT 20
        ''')
        
        indicators = []
        for row in cursor.fetchall():
            indicators.append({
                'indicator_type': row[0],
                'value': row[1],
                'severity': row[2],
                'description': row[3],
                'first_seen': row[4],
                'last_seen': row[5],
                'count': row[6]
            })
        
        conn.close()
        return indicators
        
    except Exception as e:
        logger.error(f"Failed to get threat indicators: {e}")
        return []

@security_bp.route('/threats')
@admin_required
def get_threats():
    """Get threat indicators API endpoint"""
    try:
        indicators = get_threat_indicators()
        return jsonify(indicators)
    except Exception as e:
        logger.error(f"Failed to get threat indicators: {e}")
        return jsonify({'error': 'Failed to get threat indicators'}), 500

@security_bp.route('/threats/<indicator_id>', methods=['DELETE'])
@admin_required
def delete_threat_indicator(indicator_id):
    """Delete a threat indicator"""
    try:
        conn = sqlite3.connect('vectorcraft.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM threat_indicators WHERE id = ?', (indicator_id,))
        conn.commit()
        conn.close()
        
        log_admin_action('DELETE_THREAT_INDICATOR', f'threat_indicator_{indicator_id}')
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Failed to delete threat indicator: {e}")
        return jsonify({'error': 'Failed to delete threat indicator'}), 500

# ========== IP BLOCKING ==========

def get_blocked_ips():
    """Get blocked IPs from database"""
    try:
        conn = sqlite3.connect('vectorcraft.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ip_address, reason, blocked_at, blocked_until, blocked_by
            FROM ip_blocks
            WHERE blocked_until > datetime('now')
            ORDER BY blocked_at DESC
        ''')
        
        blocked_ips = []
        for row in cursor.fetchall():
            blocked_ips.append({
                'ip_address': row[0],
                'reason': row[1],
                'blocked_at': row[2],
                'blocked_until': row[3],
                'blocked_by': row[4]
            })
        
        conn.close()
        return blocked_ips
        
    except Exception as e:
        logger.error(f"Failed to get blocked IPs: {e}")
        return []

@security_bp.route('/blocked-ips')
@admin_required
def get_blocked_ips_api():
    """Get blocked IPs API endpoint"""
    try:
        blocked_ips = get_blocked_ips()
        return jsonify(blocked_ips)
    except Exception as e:
        logger.error(f"Failed to get blocked IPs: {e}")
        return jsonify({'error': 'Failed to get blocked IPs'}), 500

@security_bp.route('/block-ip', methods=['POST'])
@admin_required
def block_ip():
    """Block an IP address"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address')
        reason = data.get('reason', 'Manual block by admin')
        duration_hours = data.get('duration_hours', 24)
        
        if not ip_address:
            return jsonify({'error': 'IP address is required'}), 400
        
        admin_user = session.get('admin_user', 'admin')
        security_service.block_ip(ip_address, reason, duration_hours, admin_user)
        
        log_admin_action('BLOCK_IP', f'ip_block_{ip_address}', {
            'reason': reason,
            'duration_hours': duration_hours
        })
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Failed to block IP: {e}")
        return jsonify({'error': 'Failed to block IP'}), 500

@security_bp.route('/unblock-ip', methods=['POST'])
@admin_required
def unblock_ip():
    """Unblock an IP address"""
    try:
        data = request.get_json()
        ip_address = data.get('ip')
        
        if not ip_address:
            return jsonify({'error': 'IP address is required'}), 400
        
        # Remove from database
        conn = sqlite3.connect('vectorcraft.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ip_blocks WHERE ip_address = ?', (ip_address,))
        conn.commit()
        conn.close()
        
        # Remove from memory cache
        if ip_address in security_service.blocked_ips:
            del security_service.blocked_ips[ip_address]
        
        log_admin_action('UNBLOCK_IP', f'ip_unblock_{ip_address}')
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Failed to unblock IP: {e}")
        return jsonify({'error': 'Failed to unblock IP'}), 500

# ========== ACCESS CONTROL ==========

def get_access_permissions():
    """Get access control permissions from database"""
    try:
        conn = sqlite3.connect('vectorcraft.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, resource, permission, granted_by, granted_at, expires_at
            FROM access_control
            WHERE expires_at IS NULL OR expires_at > datetime('now')
            ORDER BY granted_at DESC
        ''')
        
        permissions = []
        for row in cursor.fetchall():
            permissions.append({
                'user_id': row[0],
                'resource': row[1],
                'permission': row[2],
                'granted_by': row[3],
                'granted_at': row[4],
                'expires_at': row[5]
            })
        
        conn.close()
        return permissions
        
    except Exception as e:
        logger.error(f"Failed to get access permissions: {e}")
        return []

@security_bp.route('/permissions')
@admin_required
def get_permissions():
    """Get access permissions API endpoint"""
    try:
        permissions = get_access_permissions()
        return jsonify(permissions)
    except Exception as e:
        logger.error(f"Failed to get permissions: {e}")
        return jsonify({'error': 'Failed to get permissions'}), 500

@security_bp.route('/add-permission', methods=['POST'])
@admin_required
def add_permission():
    """Add access permission"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        resource = data.get('resource')
        permission = data.get('permission')
        expires_at = data.get('expires_at')
        
        if not all([user_id, resource, permission]):
            return jsonify({'error': 'user_id, resource, and permission are required'}), 400
        
        admin_user = session.get('admin_user', 'admin')
        expires_datetime = datetime.fromisoformat(expires_at) if expires_at else None
        
        security_service.grant_permission(user_id, resource, permission, admin_user, expires_datetime)
        
        log_admin_action('ADD_PERMISSION', f'permission_{user_id}_{resource}_{permission}', {
            'user_id': user_id,
            'resource': resource,
            'permission': permission,
            'expires_at': expires_at
        })
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Failed to add permission: {e}")
        return jsonify({'error': 'Failed to add permission'}), 500

@security_bp.route('/revoke-permission', methods=['POST'])
@admin_required
def revoke_permission():
    """Revoke access permission"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        resource = data.get('resource')
        permission = data.get('permission')
        
        if not all([user_id, resource, permission]):
            return jsonify({'error': 'user_id, resource, and permission are required'}), 400
        
        admin_user = session.get('admin_user', 'admin')
        security_service.revoke_permission(user_id, resource, permission, admin_user)
        
        log_admin_action('REVOKE_PERMISSION', f'permission_{user_id}_{resource}_{permission}', {
            'user_id': user_id,
            'resource': resource,
            'permission': permission
        })
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Failed to revoke permission: {e}")
        return jsonify({'error': 'Failed to revoke permission'}), 500

# ========== AUDIT LOGS ==========

@security_bp.route('/audit')
@admin_required
def audit_logs():
    """Audit logs page"""
    try:
        # Get filters from request
        user_id = request.args.get('user_id')
        action = request.args.get('action')
        resource = request.args.get('resource')
        source_ip = request.args.get('source_ip')
        success = request.args.get('success')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        # Build query
        query = 'SELECT * FROM audit_logs WHERE 1=1'
        params = []
        
        if user_id:
            query += ' AND user_id LIKE ?'
            params.append(f'%{user_id}%')
        
        if action:
            query += ' AND action = ?'
            params.append(action)
        
        if resource:
            query += ' AND resource LIKE ?'
            params.append(f'%{resource}%')
        
        if source_ip:
            query += ' AND source_ip LIKE ?'
            params.append(f'%{source_ip}%')
        
        if success:
            query += ' AND success = ?'
            params.append(success == 'true')
        
        if date_from:
            query += ' AND timestamp >= ?'
            params.append(date_from)
        
        if date_to:
            query += ' AND timestamp <= ?'
            params.append(date_to)
        
        # Get total count
        count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
        
        conn = sqlite3.connect('vectorcraft.db')
        cursor = conn.cursor()
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Get paginated results
        query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Get column names
        columns = [desc[0] for desc in cursor.description]
        
        # Convert to dictionaries
        audit_logs = []
        for row in rows:
            log_dict = dict(zip(columns, row))
            if log_dict.get('details'):
                try:
                    log_dict['details'] = json.loads(log_dict['details'])
                except json.JSONDecodeError:
                    log_dict['details'] = {}
            audit_logs.append(log_dict)
        
        conn.close()
        
        # Calculate pagination
        total_pages = (total_count + per_page - 1) // per_page
        
        # Get statistics
        stats = get_audit_statistics()
        
        log_admin_action('VIEW_AUDIT_LOGS', 'audit_logs', {
            'page': page,
            'filters': {
                'user_id': user_id,
                'action': action,
                'resource': resource,
                'source_ip': source_ip,
                'success': success,
                'date_from': date_from,
                'date_to': date_to
            }
        })
        
        return render_template('admin/audit.html',
                             audit_logs=audit_logs,
                             stats=stats,
                             current_page=page,
                             total_pages=total_pages,
                             total_count=total_count)
        
    except Exception as e:
        logger.error(f"Audit logs error: {e}")
        return jsonify({'error': 'Failed to load audit logs'}), 500

def get_audit_statistics():
    """Get audit log statistics"""
    try:
        conn = sqlite3.connect('vectorcraft.db')
        cursor = conn.cursor()
        
        # Total events
        cursor.execute('SELECT COUNT(*) FROM audit_logs')
        total_events = cursor.fetchone()[0]
        
        # Successful events
        cursor.execute('SELECT COUNT(*) FROM audit_logs WHERE success = 1')
        successful_events = cursor.fetchone()[0]
        
        # Failed events
        cursor.execute('SELECT COUNT(*) FROM audit_logs WHERE success = 0')
        failed_events = cursor.fetchone()[0]
        
        # Unique users
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM audit_logs WHERE user_id IS NOT NULL')
        unique_users = cursor.fetchone()[0]
        
        # Events today
        cursor.execute('''
            SELECT COUNT(*) FROM audit_logs 
            WHERE timestamp >= date('now')
        ''')
        events_today = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_events': total_events,
            'successful_events': successful_events,
            'failed_events': failed_events,
            'unique_users': unique_users,
            'events_today': events_today
        }
        
    except Exception as e:
        logger.error(f"Failed to get audit statistics: {e}")
        return {}

@security_bp.route('/audit/export')
@admin_required
def export_audit_logs():
    """Export audit logs to CSV"""
    try:
        # Get the same filters as the main audit page
        user_id = request.args.get('user_id')
        action = request.args.get('action')
        resource = request.args.get('resource')
        source_ip = request.args.get('source_ip')
        success = request.args.get('success')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Build query (same as audit_logs function)
        query = 'SELECT * FROM audit_logs WHERE 1=1'
        params = []
        
        if user_id:
            query += ' AND user_id LIKE ?'
            params.append(f'%{user_id}%')
        
        if action:
            query += ' AND action = ?'
            params.append(action)
        
        if resource:
            query += ' AND resource LIKE ?'
            params.append(f'%{resource}%')
        
        if source_ip:
            query += ' AND source_ip LIKE ?'
            params.append(f'%{source_ip}%')
        
        if success:
            query += ' AND success = ?'
            params.append(success == 'true')
        
        if date_from:
            query += ' AND timestamp >= ?'
            params.append(date_from)
        
        if date_to:
            query += ' AND timestamp <= ?'
            params.append(date_to)
        
        query += ' ORDER BY timestamp DESC'
        
        conn = sqlite3.connect('vectorcraft.db')
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Get column names
        columns = [desc[0] for desc in cursor.description]
        
        conn.close()
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(columns)
        
        # Write data
        for row in rows:
            writer.writerow(row)
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        log_admin_action('EXPORT_AUDIT_LOGS', 'audit_logs_export', {
            'format': 'csv',
            'filters': {
                'user_id': user_id,
                'action': action,
                'resource': resource,
                'source_ip': source_ip,
                'success': success,
                'date_from': date_from,
                'date_to': date_to
            }
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to export audit logs: {e}")
        return jsonify({'error': 'Failed to export audit logs'}), 500

# ========== SECURITY ANALYTICS ==========

@security_bp.route('/analytics')
@admin_required
def security_analytics():
    """Security analytics and reporting"""
    try:
        # Get time-based analytics
        analytics = get_security_analytics()
        
        log_admin_action('VIEW_SECURITY_ANALYTICS', 'security_analytics')
        
        return jsonify(analytics)
        
    except Exception as e:
        logger.error(f"Security analytics error: {e}")
        return jsonify({'error': 'Failed to load security analytics'}), 500

def get_security_analytics():
    """Get security analytics data"""
    try:
        conn = sqlite3.connect('vectorcraft.db')
        cursor = conn.cursor()
        
        # Security events by day (last 30 days)
        cursor.execute('''
            SELECT date(timestamp) as day, COUNT(*) as count
            FROM security_events
            WHERE timestamp >= datetime('now', '-30 days')
            GROUP BY date(timestamp)
            ORDER BY day
        ''')
        events_by_day = dict(cursor.fetchall())
        
        # Security events by type
        cursor.execute('''
            SELECT event_type, COUNT(*) as count
            FROM security_events
            WHERE timestamp >= datetime('now', '-7 days')
            GROUP BY event_type
            ORDER BY count DESC
        ''')
        events_by_type = dict(cursor.fetchall())
        
        # Top source IPs
        cursor.execute('''
            SELECT source_ip, COUNT(*) as count
            FROM security_events
            WHERE timestamp >= datetime('now', '-7 days')
            AND source_ip IS NOT NULL
            GROUP BY source_ip
            ORDER BY count DESC
            LIMIT 10
        ''')
        top_source_ips = dict(cursor.fetchall())
        
        # Failed login attempts by IP
        cursor.execute('''
            SELECT source_ip, COUNT(*) as count
            FROM security_events
            WHERE event_type = 'FAILED_LOGIN'
            AND timestamp >= datetime('now', '-7 days')
            GROUP BY source_ip
            ORDER BY count DESC
            LIMIT 10
        ''')
        failed_logins_by_ip = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'events_by_day': events_by_day,
            'events_by_type': events_by_type,
            'top_source_ips': top_source_ips,
            'failed_logins_by_ip': failed_logins_by_ip
        }
        
    except Exception as e:
        logger.error(f"Failed to get security analytics: {e}")
        return {}

# ========== MIDDLEWARE INTEGRATION ==========

@security_bp.before_request
def security_middleware():
    """Security middleware for all admin security routes"""
    try:
        # Check if admin is logged in
        if 'admin_logged_in' not in session:
            return
        
        # Get request info
        source_ip = request.remote_addr
        endpoint = request.endpoint
        method = request.method
        
        # Check rate limiting
        if not security_service.check_rate_limit(source_ip, endpoint):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        # Check if IP is blocked
        if security_service.check_ip_blocked(source_ip):
            return jsonify({'error': 'IP address is blocked'}), 403
        
        # Log security access
        security_service.log_security_event(
            'ADMIN_ACCESS',
            'LOW',
            source_ip,
            session.get('admin_user', 'admin'),
            f'Admin access to {endpoint}',
            {'method': method, 'endpoint': endpoint}
        )
        
    except Exception as e:
        logger.error(f"Security middleware error: {e}")
        # Don't block request on middleware errors
        pass

# Register the blueprint
def register_security_routes(app):
    """Register security routes with the Flask app"""
    app.register_blueprint(security_bp)
    logger.info("Security routes registered successfully")