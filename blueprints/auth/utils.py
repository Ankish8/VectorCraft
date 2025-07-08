"""
Authentication utilities for VectorCraft
"""

import logging
from datetime import datetime, timedelta
from flask_login import UserMixin
from functools import wraps
from flask import request, flash, redirect, url_for, current_app
from flask_login import current_user

logger = logging.getLogger(__name__)


class User(UserMixin):
    """User class for Flask-Login"""
    def __init__(self, user_data):
        self.id = str(user_data['id'])
        self.username = user_data['username']
        self.email = user_data['email']
        self.created_at = user_data['created_at']
        self.last_login = user_data['last_login']
        self.is_active = user_data.get('is_active', True)

    def get_id(self):
        """Return user ID as string"""
        return self.id

    def is_admin(self):
        """Check if user is admin"""
        return (self.username == 'admin' or 
                'admin' in self.email.lower())


def is_rate_limited(ip_address, login_attempts, max_attempts, cooldown_period):
    """Check if IP is rate limited for login attempts"""
    now = datetime.now()
    
    # Clean old attempts
    login_attempts[ip_address] = [
        attempt for attempt in login_attempts[ip_address] 
        if now - attempt < cooldown_period
    ]
    
    # Check if rate limited
    return len(login_attempts[ip_address]) >= max_attempts


def record_login_attempt(ip_address, login_attempts):
    """Record a login attempt"""
    login_attempts[ip_address].append(datetime.now())


def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access admin features.', 'error')
            return redirect(url_for('auth.login', next=request.url))
        
        # Check if user is admin
        if not current_user.is_admin():
            flash('Admin access required.', 'error')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


def login_required_api(f):
    """Decorator for API endpoints that require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return {'error': 'Authentication required'}, 401
        return f(*args, **kwargs)
    return decorated_function


def rate_limit_decorator(max_attempts=5, cooldown_minutes=15):
    """Rate limiting decorator for routes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            
            # Simple in-memory rate limiting (should use Redis in production)
            if not hasattr(current_app, 'rate_limit_storage'):
                current_app.rate_limit_storage = {}
            
            storage = current_app.rate_limit_storage
            now = datetime.now()
            cooldown = timedelta(minutes=cooldown_minutes)
            
            if client_ip not in storage:
                storage[client_ip] = []
            
            # Clean old attempts
            storage[client_ip] = [
                attempt for attempt in storage[client_ip] 
                if now - attempt < cooldown
            ]
            
            # Check rate limit
            if len(storage[client_ip]) >= max_attempts:
                return {'error': 'Rate limit exceeded'}, 429
            
            # Record attempt
            storage[client_ip].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_session_timeout():
    """Validate session timeout"""
    from flask import session
    
    if 'last_activity' in session:
        last_activity = datetime.fromisoformat(session['last_activity'])
        timeout = timedelta(seconds=current_app.config.get('PERMANENT_SESSION_LIFETIME', 3600))
        
        if datetime.now() - last_activity > timeout:
            return False
    
    # Update last activity
    session['last_activity'] = datetime.now().isoformat()
    return True


def get_user_permissions(user):
    """Get user permissions based on role"""
    permissions = ['view_dashboard', 'upload_files', 'download_results']
    
    if user.is_admin():
        permissions.extend([
            'admin_dashboard',
            'view_all_users',
            'view_transactions',
            'view_system_logs',
            'manage_alerts'
        ])
    
    return permissions