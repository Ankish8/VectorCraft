"""
Main application routes for VectorCraft
"""

import os
import logging
from flask import render_template, request, redirect, url_for, send_file, current_app
from flask_login import current_user, login_required

from . import main_bp
from database import db

logger = logging.getLogger(__name__)


@main_bp.route('/')
def index():
    """Main page - show landing page if not authenticated"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('landing.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with upload history and stats"""
    try:
        # Get user's upload history
        uploads = db.get_user_uploads(current_user.id, limit=20)
        
        # Get user's statistics
        stats = db.get_upload_stats(current_user.id)
        
        # Add architecture information
        architecture_info = {
            'version': '2.0.0',
            'type': 'modular_blueprint',
            'features': [
                'Modular Architecture',
                'Improved Performance',
                'Better Security',
                'Enhanced Monitoring'
            ]
        }
        
        return render_template('dashboard.html', 
                             uploads=uploads, 
                             stats=stats,
                             architecture=architecture_info)
        
    except Exception as e:
        logger.error(f"Dashboard error for user {current_user.username}: {e}")
        return render_template('dashboard.html', 
                             uploads=[], 
                             stats={}, 
                             error=str(e))


@main_bp.route('/app')
@login_required
def vectorcraft_app():
    """Main VectorCraft application interface"""
    return render_template('index.html')


@main_bp.route('/download/<filename>')
@login_required
def download_result(filename):
    """Download SVG result file"""
    try:
        # Verify that the file belongs to the current user
        uploads = db.get_user_uploads(current_user.id, limit=1000)
        user_files = [upload['svg_filename'] for upload in uploads if upload['svg_filename']]
        
        if filename not in user_files:
            logger.warning(f"Unauthorized download attempt by {current_user.username} for {filename}")
            return "File not found or access denied", 404
        
        file_path = os.path.join(current_app.config['RESULTS_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            logger.warning(f"File not found: {filename}")
            return "File not found", 404
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        return f"Download error: {str(e)}", 500


@main_bp.route('/view/<filename>')
@login_required
def view_result(filename):
    """View SVG result file for preview"""
    try:
        # Verify that the file belongs to the current user
        uploads = db.get_user_uploads(current_user.id, limit=1000)
        user_files = [upload['svg_filename'] for upload in uploads if upload['svg_filename']]
        
        if filename not in user_files:
            logger.warning(f"Unauthorized view attempt by {current_user.username} for {filename}")
            return "File not found or access denied", 404
        
        file_path = os.path.join(current_app.config['RESULTS_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='image/svg+xml')
        else:
            logger.warning(f"File not found: {filename}")
            return "File not found", 404
            
    except Exception as e:
        logger.error(f"View error: {e}")
        return f"View error: {str(e)}", 500


@main_bp.route('/about')
def about():
    """About page with architecture information"""
    architecture_info = {
        'version': '2.0.0',
        'type': 'Modular Blueprint Architecture',
        'description': 'VectorCraft v2.0 features a completely refactored architecture with Flask blueprints for better maintainability and scalability.',
        'improvements': [
            'Modular Blueprint Structure',
            'Separation of Concerns',
            'Enhanced Security',
            'Better Error Handling',
            'Improved Logging',
            'Performance Optimizations',
            'Scalable Foundation'
        ],
        'blueprints': [
            {
                'name': 'Authentication',
                'description': 'User authentication, session management, and security'
            },
            {
                'name': 'API',
                'description': 'Vectorization endpoints and file processing'
            },
            {
                'name': 'Admin',
                'description': 'Administrative dashboard and monitoring'
            },
            {
                'name': 'Payment',
                'description': 'PayPal integration and transaction processing'
            },
            {
                'name': 'Main',
                'description': 'Core application routes and user interface'
            }
        ]
    }
    
    return render_template('about.html', architecture=architecture_info)


@main_bp.route('/features')
def features():
    """Features page"""
    features_info = {
        'core_features': [
            'High-quality vector conversion',
            'Multiple vectorization strategies',
            'Real-time processing',
            'Secure file handling',
            'User dashboard',
            'Download management'
        ],
        'architecture_features': [
            'Modular blueprint structure',
            'Connection pooling ready',
            'Async processing support',
            'Comprehensive monitoring',
            'Enhanced security',
            'Scalable design'
        ],
        'technical_features': [
            'Flask blueprints',
            'SQLite with optimization',
            'Email notifications',
            'PayPal integration',
            'Health monitoring',
            'System logging'
        ]
    }
    
    return render_template('features.html', features=features_info)