"""
Application factory for VectorCraft modular architecture
Creates and configures Flask application with blueprints
"""

import os
import secrets
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from flask import Flask, session, request, redirect, url_for, flash
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO

from blueprints import auth_bp, api_bp, admin_bp, payment_bp, main_bp
from blueprints.admin.file_management import file_management_bp
from blueprints.auth.utils import User
from database import db

# Global SocketIO instance for real-time features
socketio = None


def create_app(config_name='development'):
    """Create and configure Flask application"""
    global socketio
    app = Flask(__name__)
    
    # Load configuration
    app.config.update(_get_config(config_name))
    
    # Initialize extensions
    _init_extensions(app)
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Register blueprints
    _register_blueprints(app)
    
    # Set up error handlers
    _setup_error_handlers(app)
    
    # Set up request handlers
    _setup_request_handlers(app)
    
    # Create directories
    _create_directories(app)
    
    # Configure logging
    _configure_logging(app)
    
    return app, socketio


def _get_config(config_name):
    """Get configuration based on environment"""
    base_config = {
        'SECRET_KEY': os.getenv('SECRET_KEY', secrets.token_hex(32)),
        'UPLOAD_FOLDER': 'uploads',
        'RESULTS_FOLDER': 'results',
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max file size
        'WTF_CSRF_TIME_LIMIT': 3600,  # 1 hour CSRF token lifetime
        'PERMANENT_SESSION_LIFETIME': int(os.getenv('SESSION_TIMEOUT', 3600)),
        'PREFERRED_URL_SCHEME': 'https' if os.getenv('FLASK_ENV') == 'production' else 'http'
    }
    
    # Environment-specific configuration
    if config_name == 'production':
        base_config.update({
            'SESSION_COOKIE_SECURE': True,
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'DEBUG': False,
            'TESTING': False
        })
    else:
        base_config.update({
            'SESSION_COOKIE_SECURE': False,
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'DEBUG': True,
            'TESTING': False
        })
    
    return base_config


def _init_extensions(app):
    """Initialize Flask extensions"""
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Initialize rate limiter
    limiter = Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access VectorCraft.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user from database"""
        user_data = db.get_user_by_id(int(user_id))
        if user_data:
            return User(user_data)
        return None
    
    # Store extensions in app
    app.csrf = csrf
    app.limiter = limiter
    app.login_manager = login_manager


def _register_blueprints(app):
    """Register all blueprints"""
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(file_management_bp)
    app.register_blueprint(payment_bp)


def _setup_error_handlers(app):
    """Set up error handlers"""
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        app.logger.warning(f"404 error: {request.url}")
        return _render_error_template(404, "Page Not Found", 
                                    "The page you're looking for doesn't exist.")
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        app.logger.error(f"500 error: {error}")
        return _render_error_template(500, "Server Error", 
                                    "An internal server error occurred. Please try again later.")
    
    @app.errorhandler(413)
    def too_large(error):
        """Handle file too large errors"""
        app.logger.warning(f"File too large error: {error}")
        return _render_error_template(413, "File Too Large", 
                                    "The file you uploaded is too large. Maximum size is 16MB.")
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle rate limit exceeded errors"""
        app.logger.warning(f"Rate limit exceeded: {error}")
        return _render_error_template(429, "Rate Limit Exceeded", 
                                    "You have exceeded the rate limit. Please try again later.")


def _render_error_template(code, title, message):
    """Render error template"""
    try:
        from flask import render_template
        return render_template('error.html', 
                             code=code, 
                             title=title, 
                             message=message), code
    except:
        # Fallback if template rendering fails
        return f"<h1>{title}</h1><p>{message}</p>", code


def _setup_request_handlers(app):
    """Set up request handlers"""
    @app.before_request
    def before_request():
        """Handle session timeout and security checks"""
        # Make session permanent to use PERMANENT_SESSION_LIFETIME
        session.permanent = True
        
        # Check if session should expire
        if _should_expire_session(app):
            return _handle_session_expiry()
        
        # Update last activity timestamp
        session['last_activity'] = datetime.now().isoformat()
    
    @app.after_request
    def after_request(response):
        """Add security headers"""
        return _add_security_headers(response, app)


def _should_expire_session(app):
    """Check if session should expire"""
    if 'last_activity' in session:
        last_activity = datetime.fromisoformat(session['last_activity'])
        timeout = timedelta(seconds=app.config['PERMANENT_SESSION_LIFETIME'])
        return datetime.now() - last_activity > timeout
    return False


def _handle_session_expiry():
    """Handle session expiry"""
    session.clear()
    flash('Session expired. Please log in again.', 'warning')
    return redirect(url_for('auth.login'))


def _add_security_headers(response, app):
    """Add security headers to responses"""
    # Basic security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy
    if app.config.get('DEBUG'):
        # Development CSP (more permissive)
        csp = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.tailwindcss.com unpkg.com cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.tailwindcss.com; img-src 'self' data:;"
    else:
        # Production CSP (more restrictive)
        csp = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'"
    
    response.headers['Content-Security-Policy'] = csp
    
    # HTTPS security headers in production
    if not app.config.get('DEBUG'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response


def _create_directories(app):
    """Create necessary directories"""
    directories = [
        app.config['UPLOAD_FOLDER'],
        app.config['RESULTS_FOLDER'],
        'static/images',
        'output'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def _configure_logging(app):
    """Configure application logging"""
    log_level = logging.INFO if not app.config.get('DEBUG') else logging.DEBUG
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('vectorcraft.log'),
            logging.StreamHandler()
        ]
    )
    
    app.logger.setLevel(log_level)
    
    # Log application startup
    app.logger.info("VectorCraft application factory initialized")
    app.logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    app.logger.info(f"Debug mode: {'ON' if app.config.get('DEBUG') else 'OFF'}")
    app.logger.info("Architecture: Modular Blueprint (v2.0.0)")


def _log_startup_info(app):
    """Log startup information"""
    app.logger.info("=" * 60)
    app.logger.info("VectorCraft v2.0.0 - Modular Blueprint Architecture")
    app.logger.info("=" * 60)
    app.logger.info("🏗️  Architecture: Modular Flask Blueprints")
    app.logger.info("🔐 Authentication: Flask-Login with session management")
    app.logger.info("🛡️  Security: CSRF protection, rate limiting, secure headers")
    app.logger.info("📊 Monitoring: System health, logging, and alerts")
    app.logger.info("💳 Payment: PayPal integration")
    app.logger.info("📧 Email: GoDaddy SMTP service")
    app.logger.info("🎨 Vectorization: Advanced algorithms with optimization")
    app.logger.info("=" * 60)
    app.logger.info("Blueprints registered:")
    app.logger.info("  • main - Core application routes")
    app.logger.info("  • auth - Authentication and session management")
    app.logger.info("  • api - Vectorization and file processing")
    app.logger.info("  • admin - Administrative dashboard")
    app.logger.info("  • payment - PayPal integration")
    app.logger.info("=" * 60)
    app.logger.info("🚀 Ready to accept requests!")
    app.logger.info("Access VectorCraft at: http://localhost:8080")
    app.logger.info("Press Ctrl+C to stop the server")


if __name__ == '__main__':
    # Create application
    env = os.getenv('FLASK_ENV', 'development')
    app = create_app(env)
    
    # Log startup information
    _log_startup_info(app)
    
    # Run application
    debug_mode = env != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=8080)