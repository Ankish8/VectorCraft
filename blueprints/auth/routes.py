"""
Authentication routes for VectorCraft
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict
from flask import render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from . import auth_bp
from .forms import LoginForm, RegistrationForm, PasswordResetRequestForm, PasswordResetForm
from .utils import User, is_rate_limited, record_login_attempt
from database import db
from services.monitoring import system_logger

logger = logging.getLogger(__name__)

# Rate limiting for login attempts
login_attempts = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOGIN_COOLDOWN = timedelta(minutes=15)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login endpoint"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    
    # Check for message parameter
    message = request.args.get('message')
    if message == 'credentials_sent':
        flash('Login credentials have been sent to your email. Please check your inbox.', 'info')
    
    if form.validate_on_submit():
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Check rate limiting
        if is_rate_limited(client_ip, login_attempts, MAX_LOGIN_ATTEMPTS, LOGIN_COOLDOWN):
            flash('Too many login attempts. Please try again later.', 'error')
            logger.warning(f"Rate limited login attempt from {client_ip}")
            return render_template('login.html', form=form, error='Too many login attempts. Please try again later.')
        
        # Record login attempt
        record_login_attempt(client_ip, login_attempts)
        
        # Authenticate user
        user_data = db.authenticate_user(form.username.data, form.password.data)
        if user_data:
            user = User(user_data)
            login_user(user, remember=False)  # Disable remember me for security
            session['login_success'] = True
            logger.info(f"Successful login for user: {user.username}")
            
            # Log successful login
            system_logger.info('auth', f'User login successful: {user.username}',
                              user_email=user.email,
                              details={'username': user.username, 'ip': client_ip})
            
            # Redirect to next page or appropriate dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            
            # Check if user is admin and redirect to admin dashboard
            if user_data['username'] == 'admin' or 'admin' in user_data['email'].lower():
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            logger.warning(f"Failed login attempt for username: {form.username.data} from {client_ip}")
            
            # Log failed login attempt
            system_logger.warning('auth', f'Failed login attempt: {form.username.data}',
                                 details={'username': form.username.data, 'ip': client_ip})
            
            return render_template('login.html', form=form, error='Invalid username or password.')
    
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout endpoint"""
    username = current_user.username if current_user.is_authenticated else 'Unknown'
    
    # Log logout
    system_logger.info('auth', f'User logout: {username}',
                      user_email=current_user.email if current_user.is_authenticated else None)
    
    logout_user()
    session.clear()  # Clear all session data
    flash('You have been signed out successfully.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration endpoint (manual registration)"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        try:
            user_id = db.create_user(
                form.username.data,
                form.email.data,
                form.password.data
            )
            
            if user_id:
                flash('Registration successful! Please log in.', 'success')
                
                # Log successful registration
                system_logger.info('auth', f'User registration successful: {form.username.data}',
                                  user_email=form.email.data,
                                  details={'username': form.username.data})
                
                return redirect(url_for('auth.login'))
            else:
                flash('Registration failed. Please try again.', 'error')
                
        except Exception as e:
            logger.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'error')
            
            # Log registration error
            system_logger.error('auth', f'User registration failed: {str(e)}',
                               details={'username': form.username.data, 'email': form.email.data})
    
    return render_template('register.html', form=form)


@auth_bp.route('/password-reset-request', methods=['GET', 'POST'])
def password_reset_request():
    """Password reset request endpoint"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = PasswordResetRequestForm()
    
    if form.validate_on_submit():
        user = db.get_user_by_email(form.email.data)
        if user:
            # Generate password reset token
            # TODO: Implement password reset token generation and email sending
            flash('Password reset instructions have been sent to your email.', 'info')
            
            # Log password reset request
            system_logger.info('auth', f'Password reset requested for: {form.email.data}',
                              user_email=form.email.data)
        else:
            # Don't reveal if email exists or not
            flash('Password reset instructions have been sent to your email.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('password_reset_request.html', form=form)


@auth_bp.route('/password-reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    """Password reset endpoint"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # TODO: Implement token verification
    form = PasswordResetForm()
    
    if form.validate_on_submit():
        # TODO: Implement password reset logic
        flash('Your password has been reset successfully.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('password_reset.html', form=form)


@auth_bp.route('/clear-session')
def clear_session():
    """Clear session for testing/debugging"""
    logout_user()
    session.clear()
    return jsonify({
        'message': 'Session cleared',
        'authenticated': current_user.is_authenticated,
        'redirect_to': '/'
    })